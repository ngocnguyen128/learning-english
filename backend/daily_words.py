"""Script chạy mỗi ngày: sinh N từ chuyên ngành qua DeepSeek rồi thêm vào DB.

Được gọi bởi systemd timer (vocab-daily.timer). Có thể chạy tay để test:
    .venv/bin/python daily_words.py
"""
import os
import asyncio
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

import database
import deepseek

# Lĩnh vực và số từ mỗi ngày — chỉnh ở đây hoặc qua biến môi trường
TOPIC = os.getenv(
    "DAILY_TOPIC",
    "Data / phân tích dữ liệu (data analytics, data engineering) VÀ Ngân hàng / tài chính (banking, finance)",
)
COUNT = int(os.getenv("DAILY_COUNT", "10"))


async def main():
    database.init_db()

    # Lấy danh sách từ đã có để tránh trùng
    with database.get_conn() as conn:
        existing = [r["word"].lower() for r in conn.execute("SELECT word FROM words").fetchall()]

    try:
        words = await deepseek.generate_batch(TOPIC, COUNT, avoid=existing)
    except deepseek.DeepSeekError as e:
        print(f"[{datetime.now():%Y-%m-%d %H:%M}] LỖI DeepSeek: {e}")
        raise SystemExit(1)

    added = 0
    with database.get_conn() as conn:
        for w in words:
            key = w["word"].lower()
            if not key or key in existing:
                continue  # bỏ qua từ trùng
            conn.execute(
                """INSERT INTO words (word, meaning, phonetic, part_of_speech, example, example_vi)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (w["word"], w["meaning"], w["phonetic"],
                 w["part_of_speech"], w["example"], w["example_vi"]),
            )
            existing.append(key)
            added += 1

    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Đã thêm {added}/{len(words)} từ mới về chủ đề data/ngân hàng.")


if __name__ == "__main__":
    asyncio.run(main())
