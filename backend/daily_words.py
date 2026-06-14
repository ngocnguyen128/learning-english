"""Chạy TAY để sinh từ ngay lập tức (bỏ qua giới hạn 1 lần/ngày):
    .venv/bin/python daily_words.py

Lưu ý: việc sinh từ tự động giờ do app kích hoạt khi mở (xem daily.py +
endpoint /api/daily/ensure), KHÔNG còn chạy bằng cron nữa.
"""
import asyncio
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

import daily
import deepseek


async def main():
    try:
        result = await daily.run_daily_generation(force=True)
    except deepseek.DeepSeekError as e:
        print(f"[{datetime.now():%Y-%m-%d %H:%M}] LỖI DeepSeek: {e}")
        raise SystemExit(1)
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Đã thêm {result['generated']} từ mới.")


if __name__ == "__main__":
    asyncio.run(main())
