/**
 * tasks.js
 * Handles task list filtering, toggling completion, deleting via AJAX,
 * and drag-and-drop reordering/status changes on the task board.
 */

document.addEventListener("DOMContentLoaded", () => {
  initToggleComplete();
  initDeleteTask();
  initFilters();
  initDragAndDrop();
});

// ---------- Mark complete / move back to pending ----------
function initToggleComplete() {
  document.querySelectorAll(".toggle-complete").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.id;
      btn.disabled = true;
      try {
        const task = await apiFetch(`/api/tasks/${id}/toggle`, { method: "PATCH" });
        showToast(
          task.status === "completed" ? "Task marked complete!" : "Task moved back to pending.",
          "success"
        );
        setTimeout(() => window.location.reload(), 500);
      } catch (err) {
        showToast(err.message, "error");
        btn.disabled = false;
      }
    });
  });
}

// ---------- Delete task ----------
function initDeleteTask() {
  document.querySelectorAll(".delete-task").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("Delete this task? This cannot be undone.")) return;
      const id = btn.dataset.id;
      const card = btn.closest(".task-card");
      try {
        await apiFetch(`/api/tasks/${id}`, { method: "DELETE" });
        showToast("Task deleted.", "success");
        if (card) {
          card.style.transition = "opacity 0.25s ease, transform 0.25s ease";
          card.style.opacity = "0";
          card.style.transform = "scale(0.95)";
          setTimeout(() => card.remove(), 250);
        }
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  });
}

// ---------- Filters (status, due, priority, project) ----------
function initFilters() {
  const container = document.getElementById("taskListContainer");
  if (!container) return;

  const filterButtons = document.querySelectorAll(".filter-btn");
  const priorityFilter = document.getElementById("priorityFilter");
  const projectFilter = document.getElementById("projectFilter");

  let activeStatus = "";
  let activeDue = "";

  filterButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const filterType = btn.dataset.filter;

      // Deselect other buttons in the same filter group
      document.querySelectorAll(`.filter-btn[data-filter="${filterType}"]`).forEach((b) =>
        b.classList.remove("active")
      );
      btn.classList.add("active");

      if (filterType === "status") {
        activeStatus = btn.dataset.value;
        activeDue = "";
        document.querySelectorAll('.filter-btn[data-filter="due"]').forEach((b) => b.classList.remove("active"));
      } else if (filterType === "due") {
        activeDue = btn.dataset.value;
        activeStatus = "";
        document.querySelectorAll('.filter-btn[data-filter="status"]').forEach((b) => b.classList.remove("active"));
      }
      loadFilteredTasks();
    });
  });

  priorityFilter && priorityFilter.addEventListener("change", loadFilteredTasks);
  projectFilter && projectFilter.addEventListener("change", loadFilteredTasks);

  async function loadFilteredTasks() {
    showSpinner();
    const params = new URLSearchParams();
    if (activeStatus) params.set("status", activeStatus);
    if (activeDue) params.set("due", activeDue);
    if (priorityFilter && priorityFilter.value) params.set("priority", priorityFilter.value);
    if (projectFilter && projectFilter.value) params.set("project_id", projectFilter.value);

    try {
      const tasks = await apiFetch(`/api/tasks?${params.toString()}`);
      renderTasks(tasks);
    } catch (err) {
      showToast("Could not load tasks.", "error");
    }
  }

  function showSpinner() {
    container.innerHTML = `<div class="tf-spinner full-width"></div>`;
  }

  function renderTasks(tasks) {
    if (!tasks.length) {
      container.innerHTML = `<div class="empty-state full-width"><i class="fa-regular fa-clipboard"></i><p>No tasks match these filters.</p></div>`;
      return;
    }
    container.innerHTML = tasks.map(taskCardHtml).join("");
    initToggleComplete();
    initDeleteTask();
    initDragAndDrop();
  }

  function taskCardHtml(t) {
    const overdueClass = t.is_overdue ? "task-overdue" : "";
    const completedClass = t.status === "completed" ? "text-decoration-line-through" : "";
    const toggleIcon = t.status === "completed" ? "fa-rotate-left" : "fa-check";
    const projectChip = t.project_name
      ? `<span class="project-chip" style="background:${t.project_color}22; color:${t.project_color}"><span class="color-dot" style="background:${t.project_color}"></span>${escapeHtml(t.project_name)}</span>`
      : "";
    const dueChip = t.due_date
      ? `<span class="due-chip ${t.is_overdue ? "text-danger" : ""}"><i class="fa-regular fa-calendar"></i> ${t.due_date}</span>`
      : "";
    return `
      <div class="task-card ${overdueClass}" data-task-id="${t.id}" draggable="true">
        <div class="task-card-top">
          <span class="priority-badge priority-${t.priority}">${t.priority}</span>
          <div class="task-actions">
            <button class="icon-btn-sm toggle-complete" data-id="${t.id}"><i class="fa-solid ${toggleIcon}"></i></button>
            <a href="/tasks/${t.id}/edit" class="icon-btn-sm"><i class="fa-solid fa-pen"></i></a>
            <button class="icon-btn-sm delete-task text-danger" data-id="${t.id}"><i class="fa-solid fa-trash"></i></button>
          </div>
        </div>
        <h4 class="task-title ${completedClass}"><a href="/tasks/${t.id}">${escapeHtml(t.title)}</a></h4>
        ${t.description ? `<p class="task-desc">${escapeHtml(t.description.slice(0, 100))}</p>` : ""}
        <div class="task-meta">
          ${projectChip}
          ${dueChip}
          <span class="badge-status status-${t.status}">${t.status}</span>
        </div>
      </div>`;
  }
}

// ---------- Drag and drop ----------
function initDragAndDrop() {
  const cards = document.querySelectorAll(".task-card[draggable='true']");
  cards.forEach((card) => {
    card.addEventListener("dragstart", () => card.classList.add("dragging"));
    card.addEventListener("dragend", () => card.classList.remove("dragging"));
  });

  const container = document.getElementById("taskListContainer");
  if (!container) return;

  container.addEventListener("dragover", (e) => {
    e.preventDefault();
    const dragging = document.querySelector(".dragging");
    const afterElement = getDragAfterElement(container, e.clientY);
    if (!dragging) return;
    if (afterElement == null) {
      container.appendChild(dragging);
    } else {
      container.insertBefore(dragging, afterElement);
    }
  });

  container.addEventListener("drop", async (e) => {
    const dragging = document.querySelector(".dragging");
    if (!dragging) return;
    const taskId = dragging.dataset.taskId;
    // Dropping onto the board simply persists new relative order client-side;
    // toggling status via drop-zones (data-status) supported when present.
    const dropZone = e.target.closest("[data-status-zone]");
    if (dropZone) {
      const status = dropZone.dataset.statusZone;
      try {
        await apiFetch(`/api/tasks/${taskId}/move`, {
          method: "PATCH",
          body: JSON.stringify({ status }),
        });
        showToast("Task updated!", "success");
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  });
}

function getDragAfterElement(container, y) {
  const elements = [...container.querySelectorAll(".task-card:not(.dragging)")];
  return elements.reduce(
    (closest, child) => {
      const box = child.getBoundingClientRect();
      const offset = y - box.top - box.height / 2;
      if (offset < 0 && offset > closest.offset) {
        return { offset, element: child };
      }
      return closest;
    },
    { offset: Number.NEGATIVE_INFINITY, element: null }
  ).element;
}
