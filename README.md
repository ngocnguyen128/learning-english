# 📚 App Học Từ Vựng Tiếng Anh

PWA (cài được lên màn hình chính Android) để học từ vựng theo phương pháp
**lặp lại ngắt quãng (SRS – giống Anki)**. Từ mới có thể:

- **Tự sinh qua DeepSeek API** — nhập 1 từ, AI tự điền phiên âm, nghĩa, ví dụ.
- **Thêm thủ công** — tự gõ đầy đủ thông tin.

## Kiến trúc

```
[Điện thoại Android]  ──HTTPS──►  [VPS]
   PWA (frontend/)                 FastAPI (backend/)
                                   ├── SQLite (vocab.db)
                                   └── Gọi DeepSeek API
```

FastAPI phục vụ luôn cả frontend → chỉ cần chạy **1 process** trên VPS.

## Chạy thử ở máy local

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows
# source .venv/bin/activate     # Linux/macOS
pip install -r requirements.txt

cp .env.example .env            # rồi sửa .env, điền DEEPSEEK_API_KEY thật
python -m uvicorn main:app --reload --port 8000
```

Mở http://localhost:8000 trên trình duyệt.

## Triển khai lên VPS

1. Copy project lên VPS (git hoặc scp).
2. Cài deps trong venv như trên, tạo `.env` với key thật.
3. Chạy nền bằng systemd (xem `deploy/vocab.service` mẫu) hoặc:
   ```bash
   .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
   ```
4. **Bắt buộc có HTTPS** để PWA cài được và service worker chạy.
   Dùng Nginx + Let's Encrypt (Certbot) làm reverse proxy về cổng 8000.

### Cài lên điện thoại Android
Mở domain HTTPS bằng Chrome → menu **⋮** → **Thêm vào màn hình chính**.
App sẽ chạy toàn màn hình như app thật.

## Thuật toán SRS

Mỗi lần ôn, bạn tự chấm mức nhớ:

| Nút  | Điểm | Ý nghĩa |
|------|------|---------|
| Quên | 0    | học lại từ đầu, ôn lại ngày mai |
| Khó  | 3    | nhớ chật vật |
| Được | 4    | nhớ ổn |
| Dễ   | 5    | nhớ dễ dàng, giãn cách dài hơn |

Khoảng cách ôn được tính theo công thức SM-2 (xem `backend/srs.py`).

## API chính

| Method | Endpoint                | Mô tả |
|--------|-------------------------|-------|
| GET    | `/api/words`            | Danh sách tất cả từ |
| POST   | `/api/words`            | Thêm từ thủ công |
| POST   | `/api/words/generate`   | Sinh từ qua DeepSeek (`save=true/false`) |
| DELETE | `/api/words/{id}`       | Xoá từ |
| GET    | `/api/review/next`      | Các từ đến hạn ôn |
| POST   | `/api/review/{id}`      | Gửi kết quả ôn (`quality`) |
| GET    | `/api/stats`            | Thống kê |
