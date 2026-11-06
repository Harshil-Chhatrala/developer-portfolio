"""
routes/dashboard.py
Main dashboard: stats, recent tasks/projects, upcoming deadlines, chart data.
"""

from datetime import date, timedelta
from flask import Blueprint, render_template
from flask_login import login_required, current_user

from models import Task, Project

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.created_at.desc()).all()
    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.created_at.desc()).all()

    recent_tasks = tasks[:5]
    recent_projects = projects[:4]

    today = date.today()
    week_from_now = today + timedelta(days=7)
    upcoming = [
        t for t in tasks
        if t.due_date and today <= t.due_date <= week_from_now and t.status != "completed"
    ]
    upcoming.sort(key=lambda t: t.due_date)

    stats = {
        "total": current_user.total_tasks(),
        "completed": current_user.completed_tasks(),
        "pending": current_user.pending_tasks(),
        "overdue": current_user.overdue_tasks(),
        "completion_rate": current_user.completion_rate(),
    }

    # Priority distribution for chart
    priority_counts = {
        "high": len([t for t in tasks if t.priority == "high"]),
        "medium": len([t for t in tasks if t.priority == "medium"]),
        "low": len([t for t in tasks if t.priority == "low"]),
    }

    # Tasks completed per day for the last 7 days (for line chart)
    week_labels = []
    week_counts = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        week_labels.append(day.strftime("%a"))
        count = len([
            t for t in tasks
            if t.completed_at and t.completed_at.date() == day
        ])
        week_counts.append(count)

    return render_template(
        "dashboard.html",
        stats=stats,
        recent_tasks=recent_tasks,
        recent_projects=recent_projects,
        upcoming=upcoming,
        priority_counts=priority_counts,
        week_labels=week_labels,
        week_counts=week_counts,
    )
