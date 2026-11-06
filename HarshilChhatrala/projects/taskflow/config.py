"""
config.py
Central configuration for the TaskFlow application.
Values can be overridden via environment variables in a real deployment.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Secret key used to sign session cookies / CSRF tokens.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # SQLite database stored inside the /instance folder.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "instance", "taskflow.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File uploads (profile pictures)
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB max upload size

    # Flask-WTF CSRF protection
    WTF_CSRF_ENABLED = True
