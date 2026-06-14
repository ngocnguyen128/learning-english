// Service worker — network-first: luôn lấy bản mới nhất khi có mạng,
// chỉ dùng cache khi offline. Nhờ vậy cập nhật code không cần xoá cache thủ công.
const CACHE = "vocab-v10";
const ASSETS = ["./", "index.html", "style.css", "app.js", "manifest.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  if (url.pathname.startsWith("/api/")) return; // dữ liệu API: luôn lấy từ server

  // Ưu tiên mạng (bản mới nhất); offline thì rơi về cache đã lưu.
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});
