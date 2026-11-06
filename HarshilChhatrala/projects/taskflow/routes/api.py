"""
routes/api.py
JSON API endpoints consumed by the frontend via the Fetch API:
live search, filters, quick task CRUD, status toggling, stats, drag-and-drop
project reassignment.
"""

from datetime import date, datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from models import db, Task, Project

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/tasks", methods=["GET"])
@login_required
def get_tasks():
    """Return tasks for the current user, optionally filtered."""
    query = Task.query.filter_by(user_id=current_user.id)

    status = request.args.get("status")
    priority = request.args.get("priority")
    project_id = request.args.get("project_id")
    due = request.args.get("due")  # 'today' | 'week' | 'overdue'

    if status in ("pending", "completed"):
        query = query.filter_by(status=status)
    if priority in ("high", "medium", "low"):
        query = query.filter_by(priority=priority)
    if project_id:
        query = query.filter_by(project_id=int(project_id))

    tasks = query.order_by(Task.created_at.desc()).all()

    today = date.today()
    if due == "today":
        tasks = [t for t in tasks if t.due_date == today]
    elif due == "week":
        week_end = today + timedelta(days=7)
        tasks = [t for t in tasks if t.due_date and today <= t.due_date <= week_end]
    elif due == "overdue":
        tasks = [t for t in tasks if t.is_overdue()]

    return jsonify([t.to_dict() for t in tasks])


@api_bp.route("/tasks/search", methods=["GET"])
@login_required
def search_tasks():
    """Live search across title, description, project name, and priority."""
    q = request.args.get("q", "").strip().lower()
    if not q:
        return jsonify([])

    tasks = Task.query.filter_by(user_id=current_user.id).all()
    results = []
    for t in tasks:
        haystack = " ".join(
            [
                t.title.lower(),
                (t.description or "").lower(),
                t.project.name.lower() if t.project else "",
                t.priority.lower(),
            ]
        )
        if q in haystack:
            results.append(t.to_dict())

    return jsonify(results)


@api_bp.route("/tasks", methods=["POST"])
@login_required
def create_task():
    data = request.get_json(force=True)
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title is required."}), 400

    due_date = None
    if data.get("due_date"):
        try:
            due_date = datetime.strptime(data["due_date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid due date format."}), 400

    task = Task(
        title=title,
        description=data.get("description", ""),
        priority=data.get("priority", "medium"),
        category=data.get("category", "general"),
        due_date=due_date,
        project_id=data.get("project_id") or None,
        user_id=current_user.id,
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@api_bp.route("/tasks/<int:task_id>", methods=["PUT"])
@login_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(force=True)
    if "title" in data:
        if not data["title"].strip():
            return jsonify({"error": "Title cannot be empty."}), 400
        task.title = data["title"].strip()
    if "description" in data:
        task.description = data["description"]
    if "priority" in data:
        task.priority = data["priority"]
    if "category" in data:
        task.category = data["category"]
    if "project_id" in data:
        task.project_id = data["project_id"] or None
    if "due_date" in data:
        task.due_date = (
            datetime.strptime(data["due_date"], "%Y-%m-%d").date() if data["due_date"] else None
        )

    db.session.commit()
    return jsonify(task.to_dict())


@api_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
@login_required
def api_delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    db.session.delete(task)
    db.session.commit()
    return jsonify({"success": True})


@api_bp.route("/tasks/<int:task_id>/toggle", methods=["PATCH"])
@login_required
def toggle_task_status(task_id):
    """Mark a task complete or move it back to pending."""
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403

    if task.status == "completed":
        task.status = "pending"
        task.completed_at = None
    else:
        task.status = "completed"
        task.completed_at = datetime.utcnow()

    db.session.commit()
    return jsonify(task.to_dict())


@api_bp.route("/tasks/<int:task_id>/move", methods=["PATCH"])
@login_required
def move_task(task_id):
    """Drag-and-drop: reassign a task to a different project/column."""
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(force=True)
    if "project_id" in data:
        task.project_id = data["project_id"] or None
    if "status" in data and data["status"] in ("pending", "completed"):
        task.status = data["status"]
        task.completed_at = datetime.utcnow() if data["status"] == "completed" else None

    db.session.commit()
    return jsonify(task.to_dict())


@api_bp.route("/projects", methods=["GET"])
@login_required
def get_projects():
    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.name).all()
    return jsonify([p.to_dict() for p in projects])


@api_bp.route("/stats", methods=["GET"])
@login_required
def get_stats():
    return jsonify(
        {
            "total": current_user.total_tasks(),
            "completed": current_user.completed_tasks(),
            "pending": current_user.pending_tasks(),
            "overdue": current_user.overdue_tasks(),
            "completion_rate": current_user.completion_rate(),
        }
    )
