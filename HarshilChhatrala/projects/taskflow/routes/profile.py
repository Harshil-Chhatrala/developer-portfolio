"""
routes/profile.py
User profile, password change, and settings pages.
"""

import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models import db
from forms import ProfileForm, ChangePasswordForm, SettingsForm

profile_bp = Blueprint("profile", __name__)


def _allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


@profile_bp.route("/profile", methods=["GET", "POST"])
@login_required
def view_profile():
    form = ProfileForm(obj=current_user)
    password_form = ChangePasswordForm()

    if form.validate_on_submit() and form.submit.data:
        current_user.username = form.username.data.strip()
        current_user.email = form.email.data.lower().strip()

        file = form.profile_picture.data
        if file and _allowed_file(file.filename):
            os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
            filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
            file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
            current_user.profile_picture = filename

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile.view_profile"))

    return render_template("profile.html", form=form, password_form=password_form)


@profile_bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Password changed successfully!", "success")
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, "danger")
    return redirect(url_for("profile.view_profile"))


@profile_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    form = SettingsForm(obj=current_user)
    if form.validate_on_submit():
        current_user.theme = form.theme.data
        current_user.notifications_enabled = form.notifications_enabled.data
        db.session.commit()
        flash("Settings saved!", "success")
        return redirect(url_for("profile.settings"))
    return render_template("settings.html", form=form)
