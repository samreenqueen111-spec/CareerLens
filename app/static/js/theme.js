/**
 * CareerLens - Theme Controller (theme.js)
 * Manages light / dark mode switching, persistence via localStorage,
 * and system preference synchronization.
 */

(function () {
  const THEME_STORAGE_KEY = "careerlens-theme";

  // Get current preference or default to system
  function getPreferredTheme() {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "dark" || stored === "light") {
      return stored;
    }
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  // Apply theme to document root
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    updateThemeToggleIcons(theme);
  }

  // Update theme toggle button icons
  function updateThemeToggleIcons(theme) {
    const toggleButtons = document.querySelectorAll(".theme-toggle");
    toggleButtons.forEach((btn) => {
      if (theme === "dark") {
        btn.innerHTML = `
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
          </svg>
        `;
        btn.setAttribute("title", "Switch to Light Mode");
        btn.setAttribute("aria-label", "Switch to Light Mode");
      } else {
        btn.innerHTML = `
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
          </svg>
        `;
        btn.setAttribute("title", "Switch to Dark Mode");
        btn.setAttribute("aria-label", "Switch to Dark Mode");
      }
    });
  }

  // Toggle theme
  function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "light";
    const next = current === "dark" ? "light" : "dark";
    localStorage.setItem(THEME_STORAGE_KEY, next);
    applyTheme(next);
  }

  // Apply immediately before DOM render to prevent flash
  const initialTheme = getPreferredTheme();
  applyTheme(initialTheme);

  // Initialize toggle event listeners once DOM is ready
  document.addEventListener("DOMContentLoaded", () => {
    updateThemeToggleIcons(initialTheme);
    document.querySelectorAll(".theme-toggle").forEach((btn) => {
      btn.addEventListener("click", toggleTheme);
    });

    // Listen for OS system theme changes
    if (window.matchMedia) {
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
        if (!localStorage.getItem(THEME_STORAGE_KEY)) {
          applyTheme(e.matches ? "dark" : "light");
        }
      });
    }
  });

  window.CareerLensTheme = {
    getPreferredTheme,
    applyTheme,
    toggleTheme
  };
})();
