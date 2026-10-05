/**
 * CareerLens - Core Application Scripts (main.js)
 * Global navigation, toasts, modal windows, and accessible utilities.
 */

(function () {
  // Mobile Navigation Menu Toggle
  document.addEventListener("DOMContentLoaded", () => {
    const mobileToggle = document.querySelector(".mobile-nav-toggle");
    const mobileMenu = document.querySelector(".mobile-nav-menu");

    if (mobileToggle && mobileMenu) {
      mobileToggle.addEventListener("click", () => {
        const isOpen = mobileMenu.classList.toggle("is-open");
        mobileToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
      });

      // Close menu when clicking outside
      document.addEventListener("click", (e) => {
        if (!mobileToggle.contains(e.target) && !mobileMenu.contains(e.target)) {
          mobileMenu.classList.remove("is-open");
          mobileToggle.setAttribute("aria-expanded", "false");
        }
      });
    }

    // Modal close buttons
    document.querySelectorAll("[data-close-modal]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const modal = btn.closest(".modal-backdrop");
        if (modal) {
          modal.classList.remove("is-active");
        }
      });
    });

    // Close modal on backdrop click
    document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {
      backdrop.addEventListener("click", (e) => {
        if (e.target === backdrop) {
          backdrop.classList.remove("is-active");
        }
      });
    });

    // Close modal on ESC key
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        document.querySelectorAll(".modal-backdrop.is-active").forEach((m) => {
          m.classList.remove("is-active");
        });
      }
    });

    // Interactive Cursor Spotlight on Cards
    const cardSelector = ".card, .feature-card, .metric-card, .roadmap-card, .preview-card, .step-card, .hero-preview-wrapper, .overall-score-card";
    document.addEventListener("mousemove", (e) => {
      const targetCard = e.target.closest(cardSelector);
      if (targetCard) {
        const rect = targetCard.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        targetCard.style.setProperty("--mouse-x", `${x}px`);
        targetCard.style.setProperty("--mouse-y", `${y}px`);
      }
    }, { passive: true });

    // Interactive Button & Chip Click Ripple Effect
    document.addEventListener("click", (e) => {
      const btn = e.target.closest(".btn, .skill-chip");
      if (!btn) return;
      const rect = btn.getBoundingClientRect();
      const circle = document.createElement("span");
      const diameter = Math.max(rect.width, rect.height);
      const radius = diameter / 2;
      circle.style.width = circle.style.height = `${diameter}px`;
      circle.style.left = `${e.clientX - rect.left - radius}px`;
      circle.style.top = `${e.clientY - rect.top - radius}px`;
      circle.classList.add("interactive-ripple");

      const oldRipple = btn.querySelector(".interactive-ripple");
      if (oldRipple) oldRipple.remove();
      btn.appendChild(circle);
      setTimeout(() => circle.remove(), 600);
    });

    // Scroll & Load Staggered Reveal Animations
    const revealTargets = document.querySelectorAll(".feature-card, .step-card, .metric-card, .roadmap-card, .preview-card, .hero-preview-wrapper");
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("reveal-active");
            obs.unobserve(entry.target);
          }
        });
      }, { threshold: 0.08, rootMargin: "0px 0px -30px 0px" });

      revealTargets.forEach((el, index) => {
        el.classList.add("reveal-init");
        el.style.transitionDelay = `${(index % 4) * 75}ms`;
        observer.observe(el);
      });
    } else {
      revealTargets.forEach((el) => el.classList.add("reveal-active"));
    }
  });

  // Global Toast Notification System
  function showToast(message, type = "info", duration = 4000) {
    let container = document.querySelector(".toast-container");
    if (!container) {
      container = document.createElement("div");
      container.className = "toast-container";
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    // Status Icon
    let iconSvg = "";
    if (type === "success") {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
    } else if (type === "error") {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
    } else {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
    }

    toast.innerHTML = `
      <div style="flex-shrink:0;">${iconSvg}</div>
      <div style="flex:1;">${message}</div>
    `;

    container.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => {
      toast.classList.add("show");
    });

    // Auto remove
    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => {
        toast.remove();
      }, 300);
    }, duration);
  }

  // Global Modal Helpers
  function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add("is-active");
    }
  }

  function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove("is-active");
    }
  }

  window.CareerLens = {
    showToast,
    openModal,
    closeModal
  };
})();
