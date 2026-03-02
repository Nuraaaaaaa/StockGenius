// alerts.js

document.addEventListener("DOMContentLoaded", () => {
  // Tabs filter
  const tabBtns = document.querySelectorAll(".tab-btn");
  const cards = document.querySelectorAll(".alert-card");

  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => {
        b.classList.remove("bg-blue-600", "text-white");
        b.classList.add("bg-gray-100", "text-gray-700");
      });

      btn.classList.remove("bg-gray-100", "text-gray-700");
      btn.classList.add("bg-blue-600", "text-white");

      const filter = btn.dataset.filter;

      cards.forEach((card) => {
        const t = card.dataset.type;
        const show = filter === "all" || t === filter;
        card.style.display = show ? "" : "none";
      });
    });
  });

  // Acknowledge -> visually mark
  document.querySelectorAll(".ack-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const card = btn.closest(".alert-card");
      card.classList.add("opacity-60");
      btn.textContent = "✓ Acknowledged";
      btn.disabled = true;
      btn.classList.add("cursor-not-allowed");
    });
  });
});