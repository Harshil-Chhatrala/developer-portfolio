"""
app.py
Application entry point for TaskFlow.
Run with: python app.py
"""

import os
from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf import CSRFProtect

from config import Config
from models import db, User

# Blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.tasks import tasks_bp
from routes.projects import projects_bp
from routes.profile import profile_bp
from routes.api import api_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure instance & upload folders exist
    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    CSRFProtect(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(api_bp)

    # Make current year & helper available in all templates
    @app.context_processor
    def inject_globals():
        from datetime import date
        return {"current_year": date.today().year}

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
