"""Tích hợp DeepSeek API để tự sinh dữ liệu cho từ mới.

DeepSeek dùng giao thức tương thích OpenAI nên ta gọi /chat/completions
và yêu cầu model trả về JSON theo đúng cấu trúc mong muốn.
"""
import os
import json
import httpx

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

PROMPT_TEMPLATE = """Bạn là từ điển Anh-Việt cho người học tiếng Anh.
Với từ tiếng Anh: "{word}"

Trả về DUY NHẤT một object JSON (không kèm giải thích) theo cấu trúc:
{{
  "word": "từ gốc đã chuẩn hoá",
  "phonetic": "phiên âm IPA, ví dụ /əˈbændən/",
  "part_of_speech": "loại từ viết tắt: n, v, adj, adv...",
  "meaning": "nghĩa tiếng Việt ngắn gọn, rõ ràng",
  "example": "một câu ví dụ tiếng Anh tự nhiên dùng từ này",
  "example_vi": "bản dịch tiếng Việt của câu ví dụ"
}}
"""


class DeepSeekError(Exception):
    pass


async def generate_word(word: str) -> dict:
    """Gọi DeepSeek để sinh thông tin đầy đủ cho một từ."""
    if not API_KEY:
        raise DeepSeekError("Chưa cấu hình DEEPSEEK_API_KEY trong file .env")

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Bạn trả lời chỉ bằng JSON hợp lệ."},
            {"role": "user", "content": PROMPT_TEMPLATE.format(word=word)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
    }
    headers = {"Authorization": f"Bearer {API_KEY}"}

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{BASE_URL}/chat/completions", json=payload, headers=headers
        )
        if resp.status_code != 200:
            raise DeepSeekError(f"DeepSeek lỗi {resp.status_code}: {resp.text}")
        data = resp.json()

    try:
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise DeepSeekError(f"Không đọc được kết quả từ DeepSeek: {e}")

    # Bảo đảm đủ các khóa, tránh thiếu trường
    return _normalize(result, fallback_word=word)


def _normalize(result: dict, fallback_word: str = "") -> dict:
    return {
        "word": (result.get("word") or fallback_word).strip(),
        "phonetic": (result.get("phonetic") or "").strip(),
        "part_of_speech": (result.get("part_of_speech") or "").strip(),
        "meaning": (result.get("meaning") or "").strip(),
        "example": (result.get("example") or "").strip(),
        "example_vi": (result.get("example_vi") or "").strip(),
    }


BATCH_PROMPT = """Bạn là giáo viên tiếng Anh.
Hãy đưa ra {count} từ hoặc cụm từ tiếng Anh MỚI, hữu ích, phù hợp đúng yêu cầu sau: {topic}.
{avoid_clause}
Trả về DUY NHẤT một object JSON dạng:
{{"words": [
  {{"word": "thuật ngữ", "phonetic": "/.../", "part_of_speech": "n/v/adj...",
    "meaning": "nghĩa tiếng Việt ngắn gọn", "example": "câu ví dụ tiếng Anh tự nhiên",
    "example_vi": "bản dịch tiếng Việt của câu ví dụ"}}
]}}
Đúng {count} phần tử trong mảng "words"."""


async def generate_batch(topic: str, count: int, avoid: list[str] | None = None) -> list[dict]:
    """Sinh một lô {count} từ thuộc {topic}, cố gắng không trùng các từ trong {avoid}."""
    if not API_KEY:
        raise DeepSeekError("Chưa cấu hình DEEPSEEK_API_KEY trong file .env")

    avoid_clause = ""
    if avoid:
        # Chỉ gửi tối đa 200 từ gần nhất để prompt không quá dài
        sample = ", ".join(avoid[-200:])
        avoid_clause = f"KHÔNG được lặp lại các từ đã có sau đây: {sample}."

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Bạn trả lời chỉ bằng JSON hợp lệ."},
            {"role": "user", "content": BATCH_PROMPT.format(
                topic=topic, count=count, avoid_clause=avoid_clause)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,  # cao hơn để từ đa dạng giữa các ngày
    }
    headers = {"Authorization": f"Bearer {API_KEY}"}

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{BASE_URL}/chat/completions", json=payload, headers=headers
        )
        if resp.status_code != 200:
            raise DeepSeekError(f"DeepSeek lỗi {resp.status_code}: {resp.text}")
        data = resp.json()

    try:
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise DeepSeekError(f"Không đọc được kết quả từ DeepSeek: {e}")

    words = result.get("words", [])
    if not isinstance(words, list):
        raise DeepSeekError("DeepSeek không trả về mảng 'words'")
    return [_normalize(w) for w in words if w.get("word")]


GRAMMAR_PROMPT = """Bạn là giáo viên tiếng Anh cho người Việt.
Hãy soạn một bài luyện NGẮN về điểm ngữ pháp: {topic}.

Trả về DUY NHẤT một object JSON dạng:
{{
  "topic": "{topic}",
  "title": "tên điểm ngữ pháp bằng tiếng Việt, kèm tên tiếng Anh trong ngoặc",
  "explanation": "giải thích NGẮN 2-4 câu bằng tiếng Việt: khi nào dùng + cấu trúc cơ bản",
  "questions": [
    {{
      "question": "một câu tiếng Anh có đúng một chỗ trống ghi là ___ (hoặc yêu cầu chọn dạng đúng)",
      "options": ["lựa chọn A", "lựa chọn B", "lựa chọn C", "lựa chọn D"],
      "answer": 0,
      "explanation": "giải thích NGẮN bằng tiếng Việt vì sao đáp án đúng"
    }}
  ]
}}

Tạo ĐÚNG 5 câu hỏi trắc nghiệm, mỗi câu 4 lựa chọn, chỉ 1 đáp án đúng.
"answer" là CHỈ SỐ (0,1,2,3) của đáp án đúng trong mảng "options".
Độ khó vừa phải, sát thực tế giao tiếp."""


async def generate_grammar(topic: str) -> dict:
    """Sinh một bài luyện ngữ pháp (giải thích + 5 câu trắc nghiệm)."""
    if not API_KEY:
        raise DeepSeekError("Chưa cấu hình DEEPSEEK_API_KEY trong file .env")

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Bạn trả lời chỉ bằng JSON hợp lệ."},
            {"role": "user", "content": GRAMMAR_PROMPT.format(topic=topic)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.6,
    }
    headers = {"Authorization": f"Bearer {API_KEY}"}

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{BASE_URL}/chat/completions", json=payload, headers=headers
        )
        if resp.status_code != 200:
            raise DeepSeekError(f"DeepSeek lỗi {resp.status_code}: {resp.text}")
        data = resp.json()

    try:
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise DeepSeekError(f"Không đọc được kết quả từ DeepSeek: {e}")

    questions = []
    for q in result.get("questions", []):
        opts = q.get("options") or []
        if not q.get("question") or len(opts) < 2:
            continue
        try:
            ans = int(q.get("answer", 0))
        except (TypeError, ValueError):
            ans = 0
        ans = max(0, min(len(opts) - 1, ans))
        questions.append({
            "question": str(q.get("question", "")).strip(),
            "options": [str(o).strip() for o in opts],
            "answer": ans,
            "explanation": str(q.get("explanation", "")).strip(),
        })

    if not questions:
        raise DeepSeekError("DeepSeek không trả về câu hỏi hợp lệ")

    return {
        "topic": result.get("topic", topic),
        "title": str(result.get("title", topic)).strip(),
        "explanation": str(result.get("explanation", "")).strip(),
        "questions": questions,
    }
