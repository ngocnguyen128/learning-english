// Vì FastAPI phục vụ luôn frontend nên API cùng origin → dùng đường dẫn tương đối.
const API = "";

let reviewQueue = [];
let currentCard = null;
let practiceMode = false; // true = luyện tập ngẫu nhiên (không đụng lịch SRS)

// ----------------------- Điều hướng tab -----------------------
document.querySelectorAll("#tabbar button").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
  document.querySelectorAll("#tabbar button").forEach((b) => b.classList.remove("active"));
  document.getElementById("tab-" + name).classList.add("active");
  document.querySelector(`#tabbar button[data-tab="${name}"]`).classList.add("active");

  if (name === "review") loadReview();
  if (name === "list") loadList();
  if (name === "stats") loadStats();
}

// ----------------------- API helpers -----------------------
async function api(path, opts) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Lỗi không xác định");
  }
  return res.json();
}

// ----------------------- Ôn tập (theo lịch SRS) -----------------------
async function loadReview() {
  practiceMode = false;
  document.getElementById("btn-srs").classList.add("hidden");
  reviewQueue = await api("/api/review/next");
  showNextCard();
}

// ----------------------- Luyện tập ngẫu nhiên -----------------------
async function loadPractice() {
  practiceMode = true;
  document.getElementById("btn-srs").classList.remove("hidden");
  reviewQueue = await api("/api/words/random?limit=10");
  showNextCard();
}

document.getElementById("btn-practice").addEventListener("click", loadPractice);
document.getElementById("btn-srs").addEventListener("click", loadReview);

function showNextCard() {
  const empty = document.getElementById("review-empty");
  const card = document.getElementById("flashcard");
  if (reviewQueue.length === 0) {
    empty.querySelector("p").textContent = practiceMode
      ? "✅ Hết 10 từ luyện tập rồi!"
      : "🎉 Không còn từ nào cần ôn hôm nay!";
    empty.classList.remove("hidden");
    card.classList.add("hidden");
    return;
  }
  empty.classList.add("hidden");
  card.classList.remove("hidden");

  currentCard = reviewQueue[0];
  const label = practiceMode ? "luyện tập" : "ôn";
  document.getElementById("review-count").textContent = `Còn ${reviewQueue.length} từ (${label})`;
  document.getElementById("fc-word").textContent = currentCard.word;
  document.getElementById("fc-phonetic").textContent = currentCard.phonetic || "";
  document.getElementById("fc-pos").textContent = currentCard.part_of_speech || "";
  document.getElementById("fc-meaning").textContent = currentCard.meaning || "(chưa có nghĩa)";
  document.getElementById("fc-example").textContent = currentCard.example || "";
  document.getElementById("fc-example-vi").textContent = currentCard.example_vi || "";

  // Chế độ luyện tập: chỉ có nút "Tiếp"; chế độ ôn: 4 nút chấm điểm SRS
  document.getElementById("grade-buttons").classList.toggle("hidden", practiceMode);
  document.getElementById("btn-next").classList.toggle("hidden", !practiceMode);

  document.getElementById("fc-back").classList.add("hidden");
  document.getElementById("btn-show").classList.remove("hidden");
}

document.getElementById("btn-show").addEventListener("click", () => {
  document.getElementById("fc-back").classList.remove("hidden");
  document.getElementById("btn-show").classList.add("hidden");
});

// Luyện tập: chỉ lật sang từ kế, KHÔNG cập nhật lịch SRS
document.getElementById("btn-next").addEventListener("click", () => {
  reviewQueue.shift();
  showNextCard();
});

document.querySelectorAll(".grade").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const quality = parseInt(btn.dataset.q, 10);
    await api(`/api/review/${currentCard.id}`, {
      method: "POST",
      body: JSON.stringify({ quality }),
    });
    reviewQueue.shift(); // bỏ thẻ vừa ôn ra khỏi hàng đợi
    showNextCard();
  });
});

// ----------------------- Thêm từ qua DeepSeek -----------------------
document.getElementById("btn-generate").addEventListener("click", async () => {
  const input = document.getElementById("gen-input");
  const status = document.getElementById("gen-status");
  const word = input.value.trim();
  if (!word) return;

  const btn = document.getElementById("btn-generate");
  btn.disabled = true;
  status.textContent = "⏳ Đang hỏi DeepSeek...";
  try {
    // save:false → chỉ lấy dữ liệu để điền vào form, chưa lưu vội
    const w = await api("/api/words/generate", {
      method: "POST",
      body: JSON.stringify({ word, save: false }),
    });
    // Đổ kết quả DeepSeek vào các ô của form thủ công bên dưới
    const form = document.getElementById("manual-form");
    form.word.value = w.word || word;
    form.phonetic.value = w.phonetic || "";
    form.part_of_speech.value = w.part_of_speech || "";
    form.meaning.value = w.meaning || "";
    form.example.value = w.example || "";
    form.example_vi.value = w.example_vi || "";
    status.textContent = "✅ Đã điền sẵn bên dưới — kiểm tra/sửa rồi bấm \"Lưu từ\".";
    form.scrollIntoView({ behavior: "smooth" });
  } catch (e) {
    status.textContent = "❌ " + e.message;
  } finally {
    btn.disabled = false;
  }
});

// Nhấn Enter ở ô nhập từ = bấm nút "Tự điền"
document.getElementById("gen-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    document.getElementById("btn-generate").click();
  }
});

// ----------------------- Thêm thủ công -----------------------
document.getElementById("manual-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const data = Object.fromEntries(new FormData(form));
  const status = document.getElementById("manual-status");
  try {
    const w = await api("/api/words", { method: "POST", body: JSON.stringify(data) });
    status.textContent = `✅ Đã lưu: ${w.word}`;
    form.reset();
    document.getElementById("gen-input").value = "";
    document.getElementById("gen-status").textContent = "";
  } catch (err) {
    status.textContent = "❌ " + err.message;
  }
});

// ----------------------- Danh sách từ -----------------------
async function loadList() {
  const words = await api("/api/words");
  document.getElementById("list-count").textContent = words.length;
  const container = document.getElementById("word-list");
  container.innerHTML = "";
  words.forEach((w) => {
    const div = document.createElement("div");
    div.className = "word-item";
    div.innerHTML = `
      <div class="w-head">
        <div><span class="w-word">${esc(w.word)}</span><span class="w-phon">${esc(w.phonetic)}</span></div>
        <button class="w-del" data-id="${w.id}">🗑️</button>
      </div>
      <div class="w-meaning"><b>${esc(w.part_of_speech)}</b> ${esc(w.meaning)}</div>
      ${w.example ? `<div class="w-example">${esc(w.example)}</div>` : ""}
      <div class="w-due">Ôn lại: ${esc(w.due_date)}</div>`;
    container.appendChild(div);
  });
  container.querySelectorAll(".w-del").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("Xoá từ này?")) return;
      await api(`/api/words/${btn.dataset.id}`, { method: "DELETE" });
      loadList();
    });
  });
}

// ----------------------- Thống kê -----------------------
async function loadStats() {
  const s = await api("/api/stats");
  document.getElementById("stat-total").textContent = s.total;
  document.getElementById("stat-due").textContent = s.due;
  document.getElementById("stat-learned").textContent = s.learned;
}

function esc(str) {
  return (str || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

// ----------------------- Toast thông báo -----------------------
let toastTimer = null;
function showToast(msg, ms = 4000) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add("hidden"), ms);
}

// ----------------------- Sinh từ mới khi mở app -----------------------
// Chạy nền: hôm nay chưa có thì DeepSeek sinh 10 từ; có rồi thì server tự bỏ qua.
async function ensureDailyWords() {
  try {
    const r = await api("/api/daily/ensure", { method: "POST" });
    if (r.generated > 0) {
      showToast(`✨ Đã thêm ${r.generated} từ mới hôm nay!`);
      if (!practiceMode) loadReview(); // làm mới hàng đợi ôn nếu đang ở chế độ SRS
    }
  } catch (e) {
    // Im lặng — không để lỗi sinh từ làm gián đoạn việc dùng app
    console.warn("Sinh từ mới thất bại:", e.message);
  }
}

// Đăng ký service worker (cho phép cài như app)
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}

// Tải tab đầu tiên + kiểm tra từ mới của ngày
loadReview();
ensureDailyWords();
