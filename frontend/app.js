// Vì FastAPI phục vụ luôn frontend nên API cùng origin → dùng đường dẫn tương đối.
const API = "";

let reviewQueue = [];
let currentCard = null;
let practiceMode = false; // true = luyện tập ngẫu nhiên (không đụng lịch SRS)

// Cài đặt giọng đọc (lưu trong máy)
let enVoices = [];
const savedVoice = JSON.parse(localStorage.getItem("voiceSettings") || "{}");
let voicePref = {
  uri: savedVoice.uri || "",
  pitch: savedVoice.pitch ?? 0.8, // mặc định hơi trầm
  rate: savedVoice.rate ?? 0.9,
};
const MALE_HINT = /male|david|mark|daniel|aaron|fred|alex|rishi|guy|james|george|arthur|ryan|eric|tom/i;
const FEMALE_HINT = /female|zira|samantha|victoria|karen|moira|tessa|fiona|susan|hazel|jenny|aria/i;

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
  if (name === "settings") renderVoiceOptions();
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

  // Luyện tập: nút "Tiếp"; Ôn: 4 nút chấm điểm SRS.
  // Nút đánh dấu "Đã thuộc / Cần học lại" hiện ở CẢ hai chế độ.
  document.getElementById("grade-buttons").classList.toggle("hidden", practiceMode);
  document.getElementById("btn-next").classList.toggle("hidden", !practiceMode);
  document.getElementById("mark-buttons").classList.remove("hidden");

  document.getElementById("fc-back").classList.add("hidden");
  document.getElementById("btn-show").classList.remove("hidden");
}

document.getElementById("btn-show").addEventListener("click", () => {
  document.getElementById("fc-back").classList.remove("hidden");
  document.getElementById("btn-show").classList.add("hidden");
});

// Phát âm từ bằng giọng đọc của thiết bị (Web Speech API — miễn phí, chạy offline)
function speak(text) {
  if (!("speechSynthesis" in window) || !text) return;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-US";
  u.pitch = voicePref.pitch; // thấp = trầm hơn
  u.rate = voicePref.rate;
  const v = enVoices.find((x) => x.voiceURI === voicePref.uri);
  if (v) u.voice = v;
  speechSynthesis.cancel(); // dừng câu đang đọc nếu có
  speechSynthesis.speak(u);
}

document.getElementById("fc-speak").addEventListener("click", () => {
  if (currentCard) speak(currentCard.word);
});

// Đánh dấu từ hiện tại là "đã thuộc" → bỏ qua khỏi hàng đợi ôn/luyện tập
document.getElementById("btn-known").addEventListener("click", async () => {
  if (!currentCard) return;
  await api(`/api/words/${currentCard.id}/known`, {
    method: "POST",
    body: JSON.stringify({ known: true }),
  });
  showToast("✓ Đã đánh dấu thuộc, bỏ qua từ này");
  reviewQueue.shift();
  showNextCard();
});

// Đánh dấu "cần học lại" → đưa từ về ôn lại từ đầu
document.getElementById("btn-relearn").addEventListener("click", async () => {
  if (!currentCard) return;
  await api(`/api/words/${currentCard.id}/known`, {
    method: "POST",
    body: JSON.stringify({ known: false }),
  });
  showToast("↻ Sẽ học lại từ này từ đầu");
  reviewQueue.shift();
  showNextCard();
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
const MASTERED_INTERVAL = 21; // khớp với backend
let allWords = [];
let listFilter = "all";

// Phân loại trạng thái 1 từ dựa trên dữ liệu SRS
function wordStatus(w) {
  if (w.known) return { key: "mastered", label: "Đã thuộc" };
  if (!w.last_reviewed) return { key: "new", label: "Mới" };
  if (w.interval >= MASTERED_INTERVAL) return { key: "mastered", label: "Đã thuộc" };
  return { key: "learning", label: "Đang học" };
}

async function loadList() {
  allWords = await api("/api/words");
  renderList();
}

function renderList() {
  document.getElementById("list-count").textContent = allWords.length;
  const container = document.getElementById("word-list");
  const words = allWords.filter(
    (w) => listFilter === "all" || wordStatus(w).key === listFilter
  );
  container.innerHTML = "";
  if (words.length === 0) {
    container.innerHTML = `<p class="muted" style="text-align:center;padding:24px">Không có từ nào.</p>`;
    return;
  }
  words.forEach((w) => {
    const st = wordStatus(w);
    const div = document.createElement("div");
    div.className = "word-item";
    div.innerHTML = `
      <div class="w-head">
        <div>
          <span class="w-word">${esc(w.word)}</span>
          <button class="speak-btn sm" data-speak="${esc(w.word)}" aria-label="Phát âm">🔊</button>
          <span class="w-phon">${esc(w.phonetic)}</span>
        </div>
        <span class="badge ${st.key}">${st.label}</span>
      </div>
      <div class="w-meaning"><b>${esc(w.part_of_speech)}</b> ${esc(w.meaning)}</div>
      ${w.example ? `<div class="w-example">${esc(w.example)}</div>` : ""}
      <div class="w-foot">
        <span class="w-due">${w.known ? "Đã bỏ qua" : "Ôn lại: " + esc(w.due_date)}</span>
        <div class="w-actions">
          <button class="w-known" data-id="${w.id}" data-known="${w.known ? 1 : 0}">
            ${w.known ? "↩ Cần học" : "✓ Đã thuộc"}
          </button>
          <button class="w-del" data-id="${w.id}">🗑️</button>
        </div>
      </div>`;
    container.appendChild(div);
  });
  container.querySelectorAll(".speak-btn").forEach((btn) => {
    btn.addEventListener("click", () => speak(btn.dataset.speak));
  });
  container.querySelectorAll(".w-known").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const makeKnown = btn.dataset.known === "0"; // đang chưa thuộc → đánh dấu thuộc
      await api(`/api/words/${btn.dataset.id}/known`, {
        method: "POST",
        body: JSON.stringify({ known: makeKnown }),
      });
      loadList();
    });
  });
  container.querySelectorAll(".w-del").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("Xoá từ này?")) return;
      await api(`/api/words/${btn.dataset.id}`, { method: "DELETE" });
      loadList();
    });
  });
}

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    listFilter = chip.dataset.filter;
    renderList();
  });
});

// ----------------------- Thống kê -----------------------
async function loadStats() {
  const s = await api("/api/stats");
  document.getElementById("stat-total").textContent = s.total;
  document.getElementById("stat-due").textContent = s.due;
  document.getElementById("stat-mastered").textContent = s.mastered;

  // Tiến độ: số + thanh tỉ lệ
  document.getElementById("stat-new").textContent = s.new;
  document.getElementById("stat-learning").textContent = s.learning;
  document.getElementById("stat-mastered2").textContent = s.mastered;
  const total = s.total || 1;
  document.getElementById("prog-bar").innerHTML = `
    <span class="seg new" style="width:${(s.new / total) * 100}%"></span>
    <span class="seg learning" style="width:${(s.learning / total) * 100}%"></span>
    <span class="seg mastered" style="width:${(s.mastered / total) * 100}%"></span>`;

  // Tốc độ học
  document.getElementById("stat-today").textContent = s.reviewed_today;
  document.getElementById("stat-streak").textContent = s.streak;

  // Biểu đồ cột 7 ngày
  const max = Math.max(1, ...s.daily.map((d) => d.count));
  document.getElementById("chart-7day").innerHTML = s.daily
    .map((d) => {
      const h = Math.round((d.count / max) * 100);
      const dayLabel = d.date.slice(5).replace("-", "/"); // MM/DD -> DD? giữ MM/DD
      return `<div class="bar-col">
        <div class="bar-val">${d.count || ""}</div>
        <div class="bar" style="height:${Math.max(h, 3)}%"></div>
        <div class="bar-day">${dayLabel}</div>
      </div>`;
    })
    .join("");
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

// ----------------------- Cài đặt giọng đọc -----------------------
function loadVoices() {
  if (!("speechSynthesis" in window)) return;
  enVoices = speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith("en"));
  // Chưa chọn giọng → tự ưu tiên giọng nam nếu tìm được
  if (!voicePref.uri && enVoices.length) {
    const male = enVoices.find((v) => MALE_HINT.test(v.name));
    voicePref.uri = (male || enVoices[0]).voiceURI;
  }
  renderVoiceOptions();
}

function renderVoiceOptions() {
  const sel = document.getElementById("voice-select");
  if (!sel) return;
  if (!enVoices.length) {
    sel.innerHTML = `<option>(Máy chưa có giọng tiếng Anh)</option>`;
  } else {
    sel.innerHTML = enVoices
      .map((v) => {
        const tag = MALE_HINT.test(v.name) ? " ♂" : FEMALE_HINT.test(v.name) ? " ♀" : "";
        const selected = v.voiceURI === voicePref.uri ? "selected" : "";
        return `<option value="${esc(v.voiceURI)}" ${selected}>${esc(v.name)}${tag}</option>`;
      })
      .join("");
  }
  const pr = document.getElementById("pitch-range");
  const rr = document.getElementById("rate-range");
  if (pr) { pr.value = voicePref.pitch; document.getElementById("pitch-val").textContent = voicePref.pitch.toFixed(1); }
  if (rr) { rr.value = voicePref.rate; document.getElementById("rate-val").textContent = voicePref.rate.toFixed(1); }
}

function saveVoice() {
  localStorage.setItem("voiceSettings", JSON.stringify(voicePref));
}

document.getElementById("voice-select").addEventListener("change", (e) => {
  voicePref.uri = e.target.value;
  saveVoice();
  speak("Hello"); // nghe thử ngay khi đổi giọng
});
document.getElementById("pitch-range").addEventListener("input", (e) => {
  voicePref.pitch = parseFloat(e.target.value);
  document.getElementById("pitch-val").textContent = voicePref.pitch.toFixed(1);
  saveVoice();
});
document.getElementById("rate-range").addEventListener("input", (e) => {
  voicePref.rate = parseFloat(e.target.value);
  document.getElementById("rate-val").textContent = voicePref.rate.toFixed(1);
  saveVoice();
});
document.getElementById("voice-test").addEventListener("click", () =>
  speak("Hello, this is the voice you will learn with.")
);

if ("speechSynthesis" in window) {
  speechSynthesis.onvoiceschanged = loadVoices;
  loadVoices();
}

// Đăng ký service worker (cho phép cài như app)
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}

// Tải tab đầu tiên + kiểm tra từ mới của ngày
loadReview();
ensureDailyWords();
