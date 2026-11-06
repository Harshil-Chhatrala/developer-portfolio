"""
models.py
SQLAlchemy ORM models for TaskFlow: User, Project, Task.
"""

from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.String(255), default="default.png")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notifications_enabled = db.Column(db.Boolean, default=True)
    theme = db.Column(db.String(10), default="light")  # 'light' or 'dark'

    projects = db.relationship(
        "Project", backref="owner", lazy=True, cascade="all, delete-orphan"
    )
    tasks = db.relationship(
        "Task", backref="owner", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ---- Convenience stats used by dashboard & profile ----
    def total_tasks(self):
        return len(self.tasks)

    def completed_tasks(self):
        return len([t for t in self.tasks if t.status == "completed"])

    def pending_tasks(self):
        return len([t for t in self.tasks if t.status == "pending"])

    def overdue_tasks(self):
        today = date.today()
        return len(
            [
                t
                for t in self.tasks
                if t.due_date and t.due_date < today and t.status != "completed"
            ]
        )

    def completion_rate(self):
        total = self.total_tasks()
        if total == 0:
            return 0
        return round((self.completed_tasks() / total) * 100)

    def __repr__(self):
        return f"<User {self.username}>"


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    color = db.Column(db.String(20), default="#6366f1")  # hex color for UI label
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    tasks = db.relationship(
        "Task", backref="project", lazy=True, cascade="all, delete-orphan"
    )

    def progress(self):
        total = len(self.tasks)
        if total == 0:
            return 0
        completed = len([t for t in self.tasks if t.status == "completed"])
        return round((completed / total) * 100)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "progress": self.progress(),
            "task_count": len(self.tasks),
        }

    def __repr__(self):
        return f"<Project {self.name}>"


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    priority = db.Column(db.String(10), default="medium")  # high / medium / low
    status = db.Column(db.String(15), default="pending")  # pending / completed
    category = db.Column(db.String(50), default="general")
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def is_overdue(self):
        if not self.due_date:
            return False
        return self.due_date < date.today() and self.status != "completed"

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "category": self.category,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "project_id": self.project_id,
            "project_name": self.project.name if self.project else None,
            "project_color": self.project.color if self.project else "#6366f1",
            "is_overdue": self.is_overdue(),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
        }

    def __repr__(self):
        return f"<Task {self.title}>"
