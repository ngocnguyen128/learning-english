"""Thuật toán lặp lại ngắt quãng SM-2 (giống Anki).

Người dùng tự chấm điểm mức độ nhớ khi ôn:
    0 = Again (quên hẳn)
    3 = Hard  (nhớ khó khăn)
    4 = Good  (nhớ ổn)
    5 = Easy  (nhớ dễ dàng)

Hàm trả về (ease_factor, interval, repetitions) mới.
"""
from datetime import date, timedelta


def review(quality: int, ease_factor: float, interval: int, repetitions: int):
    quality = max(0, min(5, quality))

    if quality < 3:
        # Trả lời sai/quên → học lại từ đầu, ôn lại ngay ngày mai
        repetitions = 0
        interval = 1
    else:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(interval * ease_factor)
        repetitions += 1

    # Cập nhật ease factor theo công thức SM-2
    ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ease_factor = max(1.3, ease_factor)  # không cho tụt dưới 1.3

    return round(ease_factor, 2), interval, repetitions


def next_due_date(interval: int) -> str:
    return (date.today() + timedelta(days=interval)).isoformat()
