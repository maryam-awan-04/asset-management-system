# IT Asset Management System

A web-based asset management app for tracking hardware and software assignments. Administrators will manage assets and assignments; standard users will see what is assigned to them.

## Stack

- Python 3.10+
- Flask
- Flask-SQLAlchemy (SQLite)
- Flask-Login (sessions and protected routes)
- Flask-WTF / WTForms (forms and CSRF)
- bcrypt (password hashing)
- python-dotenv

Schema changes are applied with SQLAlchemy `create_all()` on startup. For local development, if you change models after tables already exist, delete `instance/app.db` and restart so tables are recreated.

## Setup

1. Clone the repository and open a terminal in the project root.

2. Create and activate a virtual environment:

   **Windows (PowerShell)**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Linting Git Hooks

```bash
pip install -r requirements-dev.txt
```

```bash
pre-commit install
```

Run all hooks on the whole repo without committing:

```bash
pre-commit run --all-files
```

## Configuration

- `SECRET_KEY`: Flask session signing key. Set in production; defaults to a dev value in code if unset.
- `FLASK_CONFIG`: `development` (default) or `production`. Controls debug mode and stricter cookie settings in production.

Optional: create a `.env` file in the project root (this file is ignored by git):

```env
SECRET_KEY=random-string
FLASK_CONFIG=development
```

`run.py` loads `.env` automatically via `python-dotenv`. The Flask CLI also reads `.flaskenv` for `FLASK_APP` when you use `flask run`.

## Running the app

```bash
python run.py
```

Then open `http://127.0.0.1:5000/` in a browser.

## SQLite database

- The database file is created at **`instance/app.db`**.
- Tables are created on application startup for all registered models.
- **`create_all()` does not add or rename columns** on tables that already exist. If you change models and SQLite reports errors such as `no such column`, stop the app and Flask shell, delete **`instance/app.db`**, then start again so the schema is recreated.

## Project layout

```text
app/
  __init__.py      # Application factory, extension wiring, db.create_all()
  config.py        # Development / production settings
  extensions.py    # db, login_manager, csrf
  forms/           # WTForms (auth, CSRF helpers)
  models.py        # Database models
  passwords.py     # bcrypt hash / verify helpers
  routes/
    auth.py        # Login, register, logout
    main.py        # Home, dashboard
  static/css/
  templates/       # Jinja2
run.py             # Local dev entrypoint
wsgi.py            # WSGI entry
requirements.txt
```
