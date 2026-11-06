"""
routes/tasks.py
Task pages and CRUD form handling (non-AJAX fallback + main task list page).
AJAX/JSON endpoints live in routes/api.py
"""

from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from models import db, Task, Project
from forms import TaskForm

tasks_bp = Blueprint("tasks", __name__)


def _populate_project_choices(form):
    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.name).all()
    form.project_id.choices = [(0, "No Project")] + [(p.id, p.name) for p in projects]


@tasks_bp.route("/tasks")
@login_required
def task_list():
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.created_at.desc()).all()
    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.name).all()
    return render_template("tasks.html", tasks=tasks, projects=projects, today=date.today())


@tasks_bp.route("/tasks/new", methods=["GET", "POST"])
@login_required
def new_task():
    form = TaskForm()
    _populate_project_choices(form)

    if form.validate_on_submit():
        task = Task(
            title=form.title.data.strip(),
            description=form.description.data,
            priority=form.priority.data,
            category=form.category.data or "general",
            due_date=form.due_date.data,
            project_id=form.project_id.data or None,
            user_id=current_user.id,
        )
        db.session.add(task)
        db.session.commit()
        flash("Task created successfully!", "success")
        return redirect(url_for("tasks.task_list"))

    return render_template("task_form.html", form=form, title="New Task")


@tasks_bp.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        abort(403)

    form = TaskForm(obj=task)
    _populate_project_choices(form)
    if request.method == "GET":
        form.project_id.data = task.project_id or 0

    if form.validate_on_submit():
        task.title = form.title.data.strip()
        task.description = form.description.data
        task.priority = form.priority.data
        task.category = form.category.data or "general"
        task.due_date = form.due_date.data
        task.project_id = form.project_id.data or None
        db.session.commit()
        flash("Task updated successfully!", "success")
        return redirect(url_for("tasks.task_list"))

    return render_template("task_form.html", form=form, title="Edit Task", task=task)


@tasks_bp.route("/tasks/<int:task_id>")
@login_required
def task_detail(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        abort(403)
    return render_template("task_detail.html", task=task)


@tasks_bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        abort(403)
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted.", "info")
    return redirect(url_for("tasks.task_list"))
