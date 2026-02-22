// footer year
document.getElementById("year").textContent = new Date().getFullYear();

// filter chips
const chips = document.querySelectorAll(".chip");
const cards = document.querySelectorAll(".project");

function setActive(btn){
  chips.forEach(c => c.classList.remove("active"));
  btn.classList.add("active");
}

function applyFilter(tag){
  cards.forEach(card => {
    const tags = (card.dataset.tags || "").split(" ");
    const show = tag === "all" || tags.includes(tag);
    card.style.display = show ? "" : "none";
  });
}

chips.forEach(btn => {
  btn.addEventListener("click", () => {
    const tag = btn.dataset.filter;
    setActive(btn);
    applyFilter(tag);
  });
});
