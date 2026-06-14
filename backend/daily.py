"""Logic sinh từ vựng hằng ngày — dùng chung cho endpoint /api/daily/ensure
và script chạy tay daily_words.py.

Quy tắc: mỗi NGÀY (theo giờ Việt Nam) chỉ sinh tối đa 1 lần. Việc gọi do
frontend kích hoạt khi mở app, nên ngày nào không mở app thì không sinh gì.
"""
import os
from datetime import datetime

import database
import deepseek

TOPIC = os.getenv(
    "DAILY_TOPIC",
    "Data / phân tích dữ liệu (data analytics, data engineering) VÀ Ngân hàng / tài chính (banking, finance)",
)
COUNT = int(os.getenv("DAILY_COUNT", "10"))

# Mốc "ngày" tính theo giờ Việt Nam để khớp trải nghiệm người dùng
try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:  # pragma: no cover - fallback nếu thiếu tzdata
    _TZ = None


def today_str() -> str:
    now = datetime.now(_TZ) if _TZ else datetime.utcnow()
    return now.date().isoformat()


async def run_daily_generation(force: bool = False) -> dict:
    """Sinh COUNT từ mới nếu hôm nay chưa sinh. Trả về dict mô tả kết quả."""
    database.init_db()
    today = today_str()

    if not force and database.get_meta("last_gen_date") == today:
        return {"generated": 0, "skipped": True, "reason": "Hôm nay đã có từ mới rồi"}

    with database.get_conn() as conn:
        existing = [r["word"].lower() for r in conn.execute("SELECT word FROM words").fetchall()]

    words = await deepseek.generate_batch(TOPIC, COUNT, avoid=existing)

    added = 0
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

    # Đánh dấu đã sinh hôm nay (kể cả khi added=0 do trùng) để không lặp lại trong ngày
    database.set_meta("last_gen_date", today)
    return {"generated": added, "skipped": False, "reason": ""}
