/**
 * CareerLens AI - History Workspace Controller (history.js)
 * Manages search/filter, delete confirmations with modal, and empty state transitions.
 */

document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("history-search-input");
  const filterSelect = document.getElementById("history-filter-select");
  const historyList = document.getElementById("history-cards-container");
  const emptyState = document.getElementById("history-empty-state");
  const countBadge = document.getElementById("history-count-badge");

  const deleteModal = document.getElementById("delete-confirm-modal");
  const deleteModalTitle = document.getElementById("delete-modal-role-title");
  const confirmDeleteBtn = document.getElementById("confirm-delete-action-btn");

  let recordToDeleteId = null;
  let recordCardToDeleteElement = null;

  // Filter & Search Logic
  function applyFilters() {
    const searchTerm = (searchInput ? searchInput.value : "").toLowerCase().trim();
    const scoreFilter = filterSelect ? filterSelect.value : "all";

    const cards = document.querySelectorAll(".history-card");
    let visibleCount = 0;

    cards.forEach((card) => {
      const title = (card.getAttribute("data-role") || "").toLowerCase();
      const company = (card.getAttribute("data-company") || "").toLowerCase();
      const score = parseInt(card.getAttribute("data-score") || "0", 10);

      const matchesSearch = !searchTerm || title.includes(searchTerm) || company.includes(searchTerm);

      let matchesScore = true;
      if (scoreFilter === "high") {
        matchesScore = score >= 75;
      } else if (scoreFilter === "moderate") {
        matchesScore = score >= 50 && score < 75;
      } else if (scoreFilter === "low") {
        matchesScore = score < 50;
      }

      if (matchesSearch && matchesScore) {
        card.style.display = "flex";
        visibleCount++;
      } else {
        card.style.display = "none";
      }
    });

    if (countBadge) {
      countBadge.textContent = `${visibleCount} analyses`;
    }

    if (emptyState) {
      if (visibleCount === 0) {
        emptyState.style.display = "block";
      } else {
        emptyState.style.display = "none";
      }
    }
  }

  if (searchInput) {
    searchInput.addEventListener("input", applyFilters);
  }

  if (filterSelect) {
    filterSelect.addEventListener("change", applyFilters);
  }

  // Delete Action Click
  document.querySelectorAll(".delete-history-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const card = btn.closest(".history-card");
      if (!card) return;

      recordToDeleteId = card.getAttribute("data-id");
      recordCardToDeleteElement = card;
      const roleTitle = card.getAttribute("data-role") || "this analysis";

      if (deleteModalTitle) {
        deleteModalTitle.textContent = `"${roleTitle}"`;
      }

      if (deleteModal) {
        deleteModal.classList.add("is-active");
      }
    });
  });

  // Confirm Delete Action
  if (confirmDeleteBtn) {
    confirmDeleteBtn.addEventListener("click", async () => {
      if (!recordToDeleteId) return;

      confirmDeleteBtn.disabled = true;
      confirmDeleteBtn.textContent = "Deleting...";

      try {
        const resp = await fetch(`/api/history/${recordToDeleteId}`, {
          method: "DELETE"
        });
        const result = await resp.json();

        if (result.success) {
          if (recordCardToDeleteElement) {
            recordCardToDeleteElement.style.opacity = "0";
            recordCardToDeleteElement.style.transform = "scale(0.95)";
            setTimeout(() => {
              recordCardToDeleteElement.remove();
              applyFilters();
            }, 250);
          }

          if (window.CareerLens) {
            window.CareerLens.showToast("Analysis record removed from history", "success");
          }
        } else {
          throw new Error(result.error || "Failed to delete record.");
        }
      } catch (err) {
        console.error("Delete error:", err);
        if (window.CareerLens) {
          window.CareerLens.showToast(err.message || "Failed to delete record.", "error");
        }
      } finally {
        confirmDeleteBtn.disabled = false;
        confirmDeleteBtn.textContent = "Delete Record";
        if (deleteModal) {
          deleteModal.classList.remove("is-active");
        }
        recordToDeleteId = null;
        recordCardToDeleteElement = null;
      }
    });
  }
});
