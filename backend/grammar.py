"""Danh sách điểm ngữ pháp và bộ đếm tiến độ (lưu trong bảng meta).

Mỗi lần xin "bài mới" sẽ lấy chủ đề kế tiếp theo thứ tự cơ bản -> nâng cao,
hết danh sách thì quay vòng lại.
"""
import database

GRAMMAR_TOPICS = [
    "Present Simple (thì hiện tại đơn)",
    "Present Continuous (thì hiện tại tiếp diễn)",
    "Past Simple (thì quá khứ đơn)",
    "Past Continuous (thì quá khứ tiếp diễn)",
    "Present Perfect (thì hiện tại hoàn thành)",
    "Future: will vs be going to",
    "Articles (mạo từ a/an/the)",
    "Prepositions of time (in/on/at)",
    "Prepositions of place (in/on/at/under...)",
    "Countable and uncountable nouns",
    "Quantifiers (some/any/much/many/a lot of)",
    "Comparatives and superlatives (so sánh)",
    "Modal verbs (can/could/should/must/have to)",
    "Conditionals type 0 and 1 (câu điều kiện loại 0,1)",
    "Conditionals type 2 (câu điều kiện loại 2)",
    "Passive voice (câu bị động)",
    "Relative clauses (who/which/that)",
    "Gerunds and infinitives (V-ing và to V)",
    "Reported speech (câu tường thuật)",
    "Question formation (cách đặt câu hỏi)",
    "Present Perfect Continuous",
    "Past Perfect (thì quá khứ hoàn thành)",
    "Used to / be used to",
    "So / such / too / enough",
    "Common phrasal verbs (cụm động từ thông dụng)",
]


def current_topic():
    idx = int(database.get_meta("grammar_index", "0") or "0")
    return GRAMMAR_TOPICS[idx % len(GRAMMAR_TOPICS)]


def advance():
    idx = int(database.get_meta("grammar_index", "0") or "0")
    database.set_meta("grammar_index", str(idx + 1))
