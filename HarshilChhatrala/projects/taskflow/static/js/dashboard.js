/**
 * dashboard.js
 * Renders Chart.js visualizations on the dashboard page.
 * Expects `priorityData`, `weekLabels`, and `weekData` globals set inline in dashboard.html.
 */

document.addEventListener("DOMContentLoaded", () => {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const textColor = isDark ? "#eef0fb" : "#1f2333";
  Chart.defaults.color = textColor;
  Chart.defaults.font.family = "Inter, sans-serif";

  const priorityCtx = document.getElementById("priorityChart");
  if (priorityCtx && typeof priorityData !== "undefined") {
    new Chart(priorityCtx, {
      type: "doughnut",
      data: {
        labels: ["High", "Medium", "Low"],
        datasets: [
          {
            data: [priorityData.high, priorityData.medium, priorityData.low],
            backgroundColor: ["#ef4444", "#f59e0b", "#10b981"],
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { position: "bottom" } },
        cutout: "65%",
      },
    });
  }

  const weekCtx = document.getElementById("weekChart");
  if (weekCtx && typeof weekLabels !== "undefined") {
    new Chart(weekCtx, {
      type: "line",
      data: {
        labels: weekLabels,
        datasets: [
          {
            label: "Tasks completed",
            data: weekData,
            borderColor: "#6366f1",
            backgroundColor: "rgba(99, 102, 241, 0.15)",
            tension: 0.35,
            fill: true,
            pointBackgroundColor: "#6366f1",
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { precision: 0 } },
        },
      },
    });
  }
});
