/**
 * theme.js
 * Handles dark/light theme toggling and persists the choice in localStorage.
 */
(function () {
  const root = document.documentElement;
  const toggleBtn = document.getElementById("themeToggle");

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    if (toggleBtn) {
      const icon = toggleBtn.querySelector("i");
      if (icon) {
        icon.className = theme === "dark" ? "fa-solid fa-sun" : "fa-solid fa-moon";
      }
    }
  }

  // Load saved theme on page load
  const savedTheme = localStorage.getItem("taskflow-theme") || "light";
  applyTheme(savedTheme);

  if (toggleBtn) {
    toggleBtn.addEventListener("click", function () {
      const current = root.getAttribute("data-theme");
      const next = current === "dark" ? "light" : "dark";
      applyTheme(next);
      localStorage.setItem("taskflow-theme", next);
    });
  }
})();
