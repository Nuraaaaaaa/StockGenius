document.addEventListener("DOMContentLoaded", () => {
  const tabButtons = document.querySelectorAll(".tab-btn");
  const alertCards = document.querySelectorAll(".alert-card");
  const acknowledgeButtons = document.querySelectorAll(".ack-btn");
  const closeButtons = document.querySelectorAll(".close-btn");
  const searchInput = document.getElementById("alertSearch");
  const noResults = document.getElementById("noResults");

  let activeFilter = "all";

  function applyFilters() {
    const searchValue = (searchInput?.value || "").trim().toLowerCase();
    let visibleCount = 0;

    alertCards.forEach((card) => {
      const cardType = card.dataset.type || "";
      const searchText = card.dataset.search || "";

      const matchesTab = activeFilter === "all" || cardType === activeFilter;
      const matchesSearch = !searchValue || searchText.includes(searchValue);

      if (matchesTab && matchesSearch) {
        card.classList.remove("is-hidden");
        visibleCount++;
      } else {
        card.classList.add("is-hidden");
      }
    });

    if (noResults) {
      if (visibleCount === 0 && alertCards.length > 0) {
        noResults.classList.remove("hidden");
      } else {
        noResults.classList.add("hidden");
      }
    }
  }

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      activeFilter = button.dataset.filter;

      tabButtons.forEach((btn) => {
        btn.classList.remove("bg-blue-600", "text-white");
        btn.classList.add("bg-gray-100", "text-gray-700");
      });

      button.classList.remove("bg-gray-100", "text-gray-700");
      button.classList.add("bg-blue-600", "text-white");

      applyFilters();
    });
  });

  if (searchInput) {
    searchInput.addEventListener("input", applyFilters);
  }

  acknowledgeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const card = button.closest(".alert-card");
      if (!card) return;

      card.classList.add("is-acknowledged");
      button.textContent = "✓ Acknowledged";
      button.disabled = true;
    });
  });

  closeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const card = button.closest(".alert-card");
      if (!card) return;

      card.remove();
      applyFilters();
    });
  });

  applyFilters();
});
