"""App học từ vựng tiếng Anh — FastAPI backend + phục vụ PWA frontend."""
import os
from pathlib import Path
from datetime import date

from dotenv import load_dotenv

load_dotenv()  # nạp biến môi trường từ .env trước khi import module dùng nó

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import database
import srs
import deepseek

app = FastAPI(title="Learning English API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.on_event("startup")
def _startup():
    database.init_db()


# ----------------------------- Models ---------------------------------
class WordIn(BaseModel):
    word: str
    meaning: str = ""
    phonetic: str = ""
    part_of_speech: str = ""
    example: str = ""
    example_vi: str = ""


class GenerateIn(BaseModel):
    word: str
    save: bool = True  # nếu True thì lưu luôn vào DB, nếu False chỉ xem trước


class ReviewIn(BaseModel):
    quality: int  # 0=Again, 3=Hard, 4=Good, 5=Easy


# ----------------------------- Helpers --------------------------------
def row_to_dict(row):
    return dict(row)


# ----------------------------- API ------------------------------------
@app.get("/api/words")
def list_words():
    with database.get_conn() as conn:
        rows = conn.execute("SELECT * FROM words ORDER BY created_at DESC").fetchall()
    return [row_to_dict(r) for r in rows]


@app.get("/api/words/random")
def random_words(limit: int = 10):
    """Bốc ngẫu nhiên N từ trong kho để luyện tập tự do (không liên quan SRS)."""
    with database.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM words ORDER BY RANDOM() LIMIT ?", (limit,)
        ).fetchall()
    return [row_to_dict(r) for r in rows]


@app.post("/api/words")
def add_word(w: WordIn):
    if not w.word.strip():
        raise HTTPException(400, "Từ không được để trống")
    with database.get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO words (word, meaning, phonetic, part_of_speech, example, example_vi)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (w.word.strip(), w.meaning, w.phonetic, w.part_of_speech, w.example, w.example_vi),
        )
        wid = cur.lastrowid
        row = conn.execute("SELECT * FROM words WHERE id = ?", (wid,)).fetchone()
    return row_to_dict(row)


@app.delete("/api/words/{word_id}")
def delete_word(word_id: int):
    with database.get_conn() as conn:
        conn.execute("DELETE FROM words WHERE id = ?", (word_id,))
    return {"ok": True}


@app.post("/api/words/generate")
async def generate(g: GenerateIn):
    """Gọi DeepSeek điền thông tin cho từ. Có thể lưu luôn hoặc chỉ trả về xem trước."""
    if not g.word.strip():
        raise HTTPException(400, "Từ không được để trống")
    try:
        data = await deepseek.generate_word(g.word.strip())
    except deepseek.DeepSeekError as e:
        raise HTTPException(502, str(e))

    if not g.save:
        return data

    with database.get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO words (word, meaning, phonetic, part_of_speech, example, example_vi)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (data["word"], data["meaning"], data["phonetic"],
             data["part_of_speech"], data["example"], data["example_vi"]),
        )
        row = conn.execute("SELECT * FROM words WHERE id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


@app.get("/api/review/next")
def review_next():
    """Lấy các từ đến hạn ôn hôm nay (due_date <= hôm nay)."""
    today = date.today().isoformat()
    with database.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM words WHERE due_date <= ? ORDER BY due_date ASC",
            (today,),
        ).fetchall()
    return [row_to_dict(r) for r in rows]


@app.post("/api/review/{word_id}")
def submit_review(word_id: int, r: ReviewIn):
    with database.get_conn() as conn:
        row = conn.execute("SELECT * FROM words WHERE id = ?", (word_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Không tìm thấy từ")

        ef, interval, reps = srs.review(
            r.quality, row["ease_factor"], row["interval"], row["repetitions"]
        )
        due = srs.next_due_date(interval)
        conn.execute(
            """UPDATE words SET ease_factor=?, interval=?, repetitions=?,
               due_date=?, last_reviewed=datetime('now') WHERE id=?""",
            (ef, interval, reps, due, word_id),
        )
        updated = conn.execute("SELECT * FROM words WHERE id = ?", (word_id,)).fetchone()
    return row_to_dict(updated)


@app.get("/api/stats")
def stats():
    today = date.today().isoformat()
    with database.get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM words").fetchone()["c"]
        due = conn.execute(
            "SELECT COUNT(*) c FROM words WHERE due_date <= ?", (today,)
        ).fetchone()["c"]
        learned = conn.execute(
            "SELECT COUNT(*) c FROM words WHERE repetitions >= 2"
        ).fetchone()["c"]
    return {"total": total, "due": due, "learned": learned}


# --------------------- Phục vụ frontend PWA ---------------------------
# Mount sau cùng để không che các route /api ở trên.
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
