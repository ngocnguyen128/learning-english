# 🚀 Đưa app lên VPS (Ubuntu/Debian) để học trên điện thoại

Toàn bộ lệnh chạy trên VPS qua SSH. Thay các chỗ `<...>` bằng giá trị thật.

---

## Bước 0 — Bạn cần một TÊN MIỀN (để có HTTPS)

PWA chỉ cài lên điện thoại khi có HTTPS. HTTPS cần tên miền. Chọn 1 trong 3:

- **Đã có domain riêng** → trỏ bản ghi A của nó về IP VPS, xong.
- **Hostname nhà cung cấp cấp sẵn** (vd `vpsXXXX.provider.com`) → dùng luôn nếu nó trỏ đúng IP.
- **Chưa có gì → dùng DuckDNS (miễn phí):**
  1. Vào https://www.duckdns.org, đăng nhập (Google/GitHub).
  2. Tạo subdomain, vd `hoctu` → bạn được `hoctu.duckdns.org`.
  3. Điền IP VPS vào ô **current ip** → bấm **update ip**.

> Ghi nhớ tên miền này, ví dụ dưới đây dùng `hoctu.duckdns.org`.

---

## Bước 1 — Đưa code lên VPS

Cách A (qua Git, nếu bạn đã push lên GitHub):
```bash
ssh <user>@<ip-vps>
git clone <link-repo> learning-english
cd learning-english
```

Cách B (copy thẳng từ máy Windows, chạy trên MÁY BẠN — không phải VPS):
```powershell
scp -r "E:\gihub\learning english" <user>@<ip-vps>:~/learning-english
```
> Lưu ý: đừng copy thư mục `.venv` và `vocab.db` lên (tạo mới trên VPS).

---

## Bước 2 — Cài Python & dependencies trên VPS

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip nginx

cd ~/learning-english/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Tạo file `.env` với key DeepSeek thật:
```bash
cp .env.example .env
nano .env        # sửa dòng DEEPSEEK_API_KEY=sk-... rồi Ctrl+O, Enter, Ctrl+X
```

Chạy thử (Ctrl+C để dừng):
```bash
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

---

## Bước 3 — Chạy nền tự động bằng systemd

Sửa file `deploy/vocab.service` cho đúng user và đường dẫn, rồi:
```bash
sudo cp ~/learning-english/deploy/vocab.service /etc/systemd/system/vocab.service
sudo nano /etc/systemd/system/vocab.service   # đổi 'youruser' và đường dẫn
sudo systemctl daemon-reload
sudo systemctl enable --now vocab
sudo systemctl status vocab                    # kiểm tra "active (running)"
```

Từ giờ app tự chạy lại sau khi reboot. Xem log lỗi:
```bash
sudo journalctl -u vocab -f
```

---

## Bước 4 — Nginx + HTTPS (Let's Encrypt)

```bash
# Tạo cấu hình Nginx
sudo cp ~/learning-english/deploy/nginx.conf.example /etc/nginx/sites-available/vocab
sudo nano /etc/nginx/sites-available/vocab      # đổi server_name thành domain của bạn
sudo ln -s /etc/nginx/sites-available/vocab /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Cài Certbot và tự cấp HTTPS
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d hoctu.duckdns.org       # đổi thành domain của bạn
```

Certbot sẽ tự sửa Nginx sang HTTPS và tự gia hạn chứng chỉ.

---

## Bước 5 — Mở firewall (nếu có bật)

```bash
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow OpenSSH       # nhớ mở SSH kẻo khoá mình ra ngoài
```

---

## Bước 6 — Cài lên điện thoại Android

1. Mở `https://hoctu.duckdns.org` bằng **Chrome** trên điện thoại.
2. Bấm menu **⋮** (góc trên phải) → **Thêm vào màn hình chính** / **Cài đặt ứng dụng**.
3. App xuất hiện như app thật, chạy toàn màn hình. Xong! 🎉

---

## Cập nhật app sau này

```bash
cd ~/learning-english
git pull                      # hoặc scp lại file
sudo systemctl restart vocab  # nếu sửa backend
# Sửa frontend thì không cần restart, chỉ cần tải lại trang trên điện thoại
```

## Sự cố thường gặp

| Triệu chứng | Cách xử lý |
|---|---|
| Trang không mở được | `sudo systemctl status vocab` và `sudo journalctl -u vocab -f` |
| Certbot báo lỗi domain | Kiểm tra domain đã trỏ đúng IP chưa: `dig +short hoctu.duckdns.org` |
| Bấm "Tạo" báo lỗi DeepSeek | Sai/thiếu key trong `.env`, sửa rồi `sudo systemctl restart vocab` |
| Không thấy "Thêm vào màn hình chính" | Phải là HTTPS (https://), không phải http:// |
