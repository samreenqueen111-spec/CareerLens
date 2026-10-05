/**
 * CareerLens - Results Dashboard Controller (dashboard.js)
 * Animates score meters, handles interactive skill tabs, and report export.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Animate SVG Radial Score Gauge
  const meter = document.querySelector(".score-radial-meter");
  if (meter) {
    const targetScore = parseInt(meter.getAttribute("data-score") || "0", 10);
    const circumference = 314.16; // 2 * PI * 50
    const offset = circumference - (Math.max(0, Math.min(100, targetScore)) / 100) * circumference;

    // Apply color class based on score threshold
    if (targetScore >= 75) {
      meter.classList.add("meter-high");
    } else if (targetScore >= 50) {
      meter.classList.add("meter-mid");
    } else {
      meter.classList.add("meter-low");
    }

    // Trigger stroke animation
    setTimeout(() => {
      meter.style.strokeDashoffset = offset;
    }, 150);
  }

  // Smooth Count-Up Animation for Score Numbers
  function animateScoreCountUp(el, target, duration = 1100) {
    const targetNum = parseInt(target, 10);
    if (isNaN(targetNum)) return;
    let startTime = null;

    const step = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      // Ease out cubic
      const ease = 1 - Math.pow(1 - progress, 3);
      const val = Math.floor(ease * targetNum);
      el.textContent = `${val}%`;
      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        el.textContent = `${targetNum}%`;
      }
    };
    requestAnimationFrame(step);
  }

  // Animate all .count-up score elements
  document.querySelectorAll(".count-up").forEach((el) => {
    const target = el.getAttribute("data-target");
    if (target !== null && target !== undefined) {
      setTimeout(() => {
        animateScoreCountUp(el, target, 1100);
      }, 100);
    }
  });

  // Animate Linear Progress Bars
  document.querySelectorAll(".progress-bar-fill").forEach((bar) => {
    const percent = bar.getAttribute("data-percent") || "0";
    setTimeout(() => {
      bar.style.width = `${percent}%`;
    }, 250);
  });

  // Print / Export Action
  const exportBtn = document.getElementById("export-report-btn");
  if (exportBtn) {
    exportBtn.addEventListener("click", () => {
      window.print();
    });
  }

  // Copy Suggestion Action
  document.querySelectorAll(".copy-suggestion-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const card = btn.closest(".suggestion-card");
      const title = card ? card.querySelector(".suggestion-title").textContent : "";
      const desc = card ? card.querySelector(".suggestion-desc").textContent : "";
      const textToCopy = `${title}\n${desc}`;

      navigator.clipboard.writeText(textToCopy).then(() => {
        if (window.CareerLens) {
          window.CareerLens.showToast("Suggestion copied to clipboard", "success");
        }
      });
    });
  });

  // Skill Chip Info Toast
  document.querySelectorAll(".skill-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const name = chip.getAttribute("data-skill-name") || chip.textContent.trim();
      const category = chip.getAttribute("data-skill-category") || "Skill";
      if (window.CareerLens) {
        window.CareerLens.showToast(`${name} (${category})`, "info", 2000);
      }
    });
  });

  // Copy Parsed Resume Text Action (Stage 2)
  document.querySelectorAll(".copy-parsed-text-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const card = btn.closest(".card");
      const pre = card ? card.querySelector(".extracted-text-content") : null;
      if (pre && pre.textContent) {
        navigator.clipboard.writeText(pre.textContent).then(() => {
          if (window.CareerLens) {
            window.CareerLens.showToast("Extracted resume text copied to clipboard!", "success");
          }
        });
      }
    });
  });
});

