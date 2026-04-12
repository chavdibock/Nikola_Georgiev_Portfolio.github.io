// ── Footer year ──────────────────────────────────────────────
document.getElementById("year").textContent = new Date().getFullYear();

// ── Filter chips ──────────────────────────────────────────────
const chips = document.querySelectorAll(".chip");
const cards = document.querySelectorAll(".project");

function setActive(btn) {
  chips.forEach(c => c.classList.remove("active"));
  btn.classList.add("active");
}

function applyFilter(tag) {
  cards.forEach(card => {
    const tags = (card.dataset.tags || "").split(" ");
    const show = tag === "all" || tags.includes(tag);
    card.style.display = show ? "" : "none";
  });
}

chips.forEach(btn => {
  btn.addEventListener("click", () => {
    setActive(btn);
    applyFilter(btn.dataset.filter);
  });
});

// ── Sys-bar live clock ────────────────────────────────────────
(function () {
  const timeEl = document.querySelector(".sys-time .sys-val");
  if (!timeEl) return;

  function tick() {
    const now = new Date();
    const hh  = String(now.getHours()).padStart(2, "0");
    const mm  = String(now.getMinutes()).padStart(2, "0");
    const ss  = String(now.getSeconds()).padStart(2, "0");
    timeEl.textContent = `● ${hh}:${mm}:${ss} UTC+${-(now.getTimezoneOffset() / 60)}`;
  }

  tick();
  setInterval(tick, 1000);
})();
