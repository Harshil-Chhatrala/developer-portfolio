# TaskFlow — Flask Task & Project Management App

A web application for managing projects and tasks, with user accounts and a dashboard.

## Features represented in the source
- User registration and login using Flask-Login
- Project and task management routes
- Profile and dashboard pages
- SQLite persistence through Flask-SQLAlchemy
- Forms and JSON API routes
- Front-end templates, CSS, and JavaScript

## Tech Stack
Python, Flask, Flask-Login, Flask-WTF, Flask-SQLAlchemy, SQLite, HTML, CSS, JavaScript.

## Setup
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open the local address printed by Flask in your browser.

## Repository hygiene
The local SQLite database and runtime uploads are not included. The application should create/use its database according to its configuration. Review `config.py` and use environment variables for any secret values before deploying.

## Screenshots
Add screenshots of the login, dashboard, project list, and task views here.
