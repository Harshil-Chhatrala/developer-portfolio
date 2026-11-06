"""
forms.py
Flask-WTF forms with server-side validation for TaskFlow.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField,
    PasswordField,
    TextAreaField,
    SelectField,
    DateField,
    BooleanField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    Email,
    EqualTo,
    Optional,
    ValidationError,
)
from models import User


class RegisterForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=3, max=25)]
    )
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters long."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create Account")

    def validate_password(self, field):
        pwd = field.data
        if not any(c.isupper() for c in pwd):
            raise ValidationError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in pwd):
            raise ValidationError("Password must contain at least one number.")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("That username is already taken.")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("That email is already registered.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Log In")


class TaskForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(min=1, max=200)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    priority = SelectField(
        "Priority",
        choices=[("high", "High"), ("medium", "Medium"), ("low", "Low")],
        default="medium",
    )
    category = StringField("Category", validators=[Optional(), Length(max=50)])
    due_date = DateField("Due Date", validators=[Optional()])
    project_id = SelectField("Project", coerce=int, validators=[Optional()])
    submit = SubmitField("Save Task")


class ProjectForm(FlaskForm):
    name = StringField("Project Name", validators=[DataRequired(), Length(min=1, max=120)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=1000)])
    color = StringField("Color", validators=[Optional(), Length(max=20)], default="#6366f1")
    submit = SubmitField("Save Project")


class ProfileForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=25)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    profile_picture = FileField(
        "Profile Picture", validators=[FileAllowed(["jpg", "jpeg", "png", "gif", "webp"], "Images only!")]
    )
    submit = SubmitField("Update Profile")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField(
        "New Password", validators=[DataRequired(), Length(min=8)]
    )
    confirm_new_password = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(), EqualTo("new_password", message="Passwords must match.")],
    )
    submit = SubmitField("Change Password")


class SettingsForm(FlaskForm):
    theme = SelectField("Theme", choices=[("light", "Light"), ("dark", "Dark")])
    notifications_enabled = BooleanField("Enable Notifications")
    submit = SubmitField("Save Settings")
