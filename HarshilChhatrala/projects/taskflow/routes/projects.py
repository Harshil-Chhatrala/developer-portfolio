"""
routes/projects.py
Project pages and CRUD (form-based).
"""

from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from models import db, Project
from forms import ProjectForm

projects_bp = Blueprint("projects", __name__)


@projects_bp.route("/projects")
@login_required
def project_list():
    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.created_at.desc()).all()
    return render_template("projects.html", projects=projects)


@projects_bp.route("/projects/new", methods=["GET", "POST"])
@login_required
def new_project():
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(
            name=form.name.data.strip(),
            description=form.description.data,
            color=form.color.data or "#6366f1",
            user_id=current_user.id,
        )
        db.session.add(project)
        db.session.commit()
        flash("Project created!", "success")
        return redirect(url_for("projects.project_list"))
    return render_template("project_form.html", form=form, title="New Project")


@projects_bp.route("/projects/<int:project_id>")
@login_required
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        abort(403)
    return render_template("project_detail.html", project=project)


@projects_bp.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        abort(403)

    form = ProjectForm(obj=project)
    if form.validate_on_submit():
        project.name = form.name.data.strip()
        project.description = form.description.data
        project.color = form.color.data or "#6366f1"
        db.session.commit()
        flash("Project updated!", "success")
        return redirect(url_for("projects.project_list"))

    return render_template("project_form.html", form=form, title="Edit Project", project=project)


@projects_bp.route("/projects/<int:project_id>/delete", methods=["POST"])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        abort(403)
    db.session.delete(project)
    db.session.commit()
    flash("Project deleted.", "info")
    return redirect(url_for("projects.project_list"))
