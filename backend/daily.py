"""Logic sinh từ vựng hằng ngày — dùng chung cho endpoint /api/daily/ensure
và script chạy tay daily_words.py.

Quy tắc: mỗi NGÀY (theo giờ Việt Nam) chỉ sinh tối đa 1 lần. Việc gọi do
frontend kích hoạt khi mở app, nên ngày nào không mở app thì không sinh gì.
"""
from datetime import datetime

import database
import deepseek

# Mỗi ngày sinh theo các nhóm (chủ đề, số từ). Tổng hiện tại = 10 từ/ngày.
SEGMENTS = [
    ("thuật ngữ Ngân hàng / tài chính (banking & finance), ưu tiên từ chuyên ngành thật sự dùng trong ngành", 3),
    ("thuật ngữ Data / phân tích & kỹ thuật dữ liệu (data analytics & engineering), ưu tiên từ chuyên ngành", 3),
    ("từ tiếng Anh THÔNG DỤNG hằng ngày thuộc bộ Oxford 3000, trình độ A2–B2, dùng trong giao tiếp đời thường; KHÔNG phải thuật ngữ chuyên ngành", 4),
]

# Mốc "ngày" tính theo giờ Việt Nam để khớp trải nghiệm người dùng
try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:  # pragma: no cover - fallback nếu thiếu tzdata
    _TZ = None


def today_str() -> str:
    now = datetime.now(_TZ) if _TZ else datetime.utcnow()
    return now.date().isoformat()


def now_str() -> str:
    """Thời điểm hiện tại theo giờ Việt Nam, dạng 'YYYY-MM-DD HH:MM:SS'."""
    now = datetime.now(_TZ) if _TZ else datetime.utcnow()
    return now.strftime("%Y-%m-%d %H:%M:%S")


async def run_daily_generation(force: bool = False) -> dict:
    """Sinh từ mới theo các nhóm SEGMENTS nếu hôm nay chưa sinh."""
    database.init_db()
    today = today_str()

    if not force and database.get_meta("last_gen_date") == today:
        return {"generated": 0, "skipped": True, "reason": "Hôm nay đã có từ mới rồi"}

    with database.get_conn() as conn:
        existing = [r["word"].lower() for r in conn.execute("SELECT word FROM words").fetchall()]

    added = 0
    last_error = None
    for topic, count in SEGMENTS:
        try:
            words = await deepseek.generate_batch(topic, count, avoid=existing)
        except deepseek.DeepSeekError as e:
            last_error = e  # 1 nhóm lỗi thì bỏ qua, vẫn thử các nhóm còn lại
            continue
        with database.get_conn() as conn:
            for w in words:
                key = w["word"].lower()
                if not key or key in existing:
                    continue
                conn.execute(
                    """INSERT INTO words (word, meaning, phonetic, part_of_speech, example, example_vi)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (w["word"], w["meaning"], w["phonetic"],
                     w["part_of_speech"], w["example"], w["example_vi"]),
                )
                existing.append(key)
                added += 1

    # Nếu KHÔNG sinh được gì do lỗi: không đánh dấu để lần mở sau thử lại
    if added == 0 and last_error:
        raise last_error

    database.set_meta("last_gen_date", today)
    return {"generated": added, "skipped": False, "reason": ""}
