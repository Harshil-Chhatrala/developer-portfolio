/**
 * main.js
 * Shared frontend behaviors: toast notifications, sidebar toggle,
 * global live search, delete confirmation dialogs, animated counters,
 * and a small fetch helper that attaches the CSRF token automatically.
 */

// ---------- CSRF helper ----------
function getCsrfToken() {
  const el = document.querySelector('input[name="csrf_token"]');
  return el ? el.value : "";
}

async function apiFetch(url, options = {}) {
  options.headers = Object.assign(
    {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
    options.headers || {}
  );
  const response = await fetch(url, options);
  if (!response.ok) {
    const errBody = await response.json().catch(() => ({}));
    throw new Error(errBody.error || `Request failed (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
}

// ---------- Toast Notifications ----------
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const icons = { success: "fa-circle-check", error: "fa-circle-xmark", info: "fa-circle-info" };
  const toast = document.createElement("div");
  toast.className = `toast-custom ${type}`;
  toast.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}"></i><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}
window.showToast = showToast;

// ---------- Sidebar toggle (mobile) ----------
document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const toggleBtn = document.getElementById("sidebarToggle");
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", () => sidebar.classList.toggle("open"));
    document.addEventListener("click", (e) => {
      if (window.innerWidth <= 991 && sidebar.classList.contains("open")) {
        if (!sidebar.contains(e.target) && e.target !== toggleBtn) {
          sidebar.classList.remove("open");
        }
      }
    });
  }
});

// ---------- Delete confirmation dialogs ----------
document.addEventListener("submit", (e) => {
  const form = e.target;
  if (form.classList.contains("confirm-delete-form")) {
    if (!confirm("Are you sure you want to delete this? This action cannot be undone.")) {
      e.preventDefault();
    }
  }
});

// ---------- Global live search ----------
document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("globalSearch");
  const resultsBox = document.getElementById("searchResults");
  if (!input || !resultsBox) return;

  let debounceTimer;
  input.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    const q = input.value.trim();
    if (!q) {
      resultsBox.classList.remove("show");
      resultsBox.innerHTML = "";
      return;
    }
    debounceTimer = setTimeout(() => runSearch(q), 250);
  });

  document.addEventListener("click", (e) => {
    if (!resultsBox.contains(e.target) && e.target !== input) {
      resultsBox.classList.remove("show");
    }
  });

  async function runSearch(q) {
    try {
      const results = await apiFetch(`/api/tasks/search?q=${encodeURIComponent(q)}`);
      renderResults(results);
    } catch (err) {
      resultsBox.innerHTML = `<div class="search-empty">Search failed. Try again.</div>`;
      resultsBox.classList.add("show");
    }
  }

  function renderResults(results) {
    if (!results.length) {
      resultsBox.innerHTML = `<div class="search-empty">No matching tasks found.</div>`;
      resultsBox.classList.add("show");
      return;
    }
    resultsBox.innerHTML = results
      .slice(0, 8)
      .map(
        (t) => `
        <div class="search-result-item" onclick="window.location.href='/tasks/${t.id}'">
          <strong>${escapeHtml(t.title)}</strong>
          <div class="text-muted small">${t.project_name ? escapeHtml(t.project_name) + " · " : ""}${t.priority} priority</div>
        </div>`
      )
      .join("");
    resultsBox.classList.add("show");
  }
});

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ---------- Animated counters (dashboard stat cards) ----------
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-counter]").forEach((el) => {
    const target = parseInt(el.getAttribute("data-counter"), 10) || 0;
    let current = 0;
    const step = Math.max(1, Math.ceil(target / 30));
    const timer = setInterval(() => {
      current += step;
      if (current >= target) {
        current = target;
        clearInterval(timer);
      }
      el.textContent = current;
    }, 25);
  });
});
