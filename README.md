# IT Asset Management System

A Flask web app for tracking hardware and software assets, assignments, and user-driven asset requests. Admins manage assets, users, and approvals; standard users see their assigned assets, submit requests, and record returns.

---

## Contents

[Developer Guide](#developer-guide) · [Admin Guide](#admin-guide) · [User Guide](#user-guide)

# Developer Guide

[App Features](#app-features) ~ [Quick start](#quick-start) ~ [Configuration and Environment](#configuration-environment) ~ [SQLite Database](#sqlite-database) ~ [Demo data and local admin](#demo-data-and-local-admin-account) ~ [URLs](#urls) ~ [Project Layout](#project-layout) ~ [Testing](#testing)

## App Features

- 📦 Assets — Laptops, monitors, peripherals, licenses, etc., with serials, status, dates, and notes.
- 🔗 Assignments — Link assets to people; return due dates; tracking.
- 📝 Requests — Users ask for an asset type; admins approve (and select inventory) or reject.
- 👥 Roles — Admin (full catalog + users + requests) vs User (my assets, requests, returns).
- 📜 Audit trail — Key actions logged (logins, asset changes, assignments, requests, etc.).

Stack: Python 3.10+, Flask, Flask-SQLAlchemy (SQLite), Flask-Login, Flask-WTF, Flask-Limiter, bcrypt, python-dotenv.

---

## Quick start

1. Clone the repo and open a terminal in the project root.

2. Virtual environment (Windows PowerShell):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```

4. Run (loads `.env` if present):

   ```bash
   python run.py
   ```

5. Open http://127.0.0.1:5000/ — you will be redirected to sign-in.

In DEBUG mode, the app seeds demo data and ensures a `localdev` admin account (see [Demo data and local admin](#demo-data-and-local-admin-account)).

---

## Configuration & Environment

Environment variables

| Variable | Purpose |
|:---------|:--------|
| `SECRET_KEY` | Session signing. Set in production; defaults to a dev placeholder. |
| `FLASK_CONFIG` | `development` (default) or `production`. |
| `LOCALDEV_ADMIN_PASSWORD` | Password for seeded user `localdev` (default in code if unset). |

Optional `.env` in the project root:

```env
SECRET_KEY=random-string
FLASK_CONFIG=development
LOCALDEV_ADMIN_PASSWORD=YourSecurePassword1!
```

`run.py` loads `.env` via `python-dotenv`.

---

## SQLite Database

- Location: `instance/app.db` (created on first run).
- Schema: `db.create_all()` on startup. — If you change models and see errors like 'no such column', stop the app, delete `instance/app.db`, and start again.

### Demo data and local admin account

When `DEBUG` is true (`FLASK_CONFIG=development`):

- `ensure_localdev_admin()` — Ensures user `localdev` exists with email `localdev@gmail.com`, role Admin, password from `LOCALDEV_ADMIN_PASSWORD` or a documented default.
- `ensure_demo_assets()` — Seeds sample users, assets, assignments, and requests if the catalog marker is absent (orchestrated from the `app/seed/` package).

---

## URLs

| Prefix | Blueprint | Who |
|:-------|:----------|:----|
| `/` | `main` | Dashboard, my assets, requests, admin request review, health |
| `/auth` | `auth` | Login, register, logout |
| `/assets` | `assets` | Admin asset list, create, edit, view, delete |
| `/users` | `users` | Admin user list, edit, delete, view user’s assets |

---

## Project Layout

```text
app/
  __init__.py       # App factory
  config.py         # Dev / prod config classes
  enums.py
  extensions.py     # db, login_manager, csrf, limiter
  models.py         # User, Asset, Assignment, AssetRequest, AuditLog
  passwords.py      # bcrypt hash / verify
  audit.py          # record_audit helper
  util_enum.py      # util for URL filters
  util_search.py    # util for search
  access.py         # @admin_required, @standard_user_required
  forms/            # WTForms
  routes/
    auth.py         # Login, register, logout + audits + rate limits
    main/           # Dashboard, admin requests, user CRUD
      __init__.py   # Exports blueprint; loads route modules
      ...
    assets.py       # Admin asset CRUD
    users.py        # Admin user CRUD
  seed/             # DEBUG-only demo data
    __init__.py
    ...
  static/css/
  templates/        # Jinja2
run.py              # load_dotenv + create_app + app.run
wsgi.py             # WSGI entry for production servers
requirements.txt
```

## Testing

There is no automated test suite in this repo yet; manual checks should cover admin vs user routes and CSRF on POST actions.

---

# Admin Guide

### Signing in

1. Use an Admin account.
2. After login you land on the Dashboard with key KPIs.

### Navigation

| Link | Purpose |
|:-----|:------------------|
| Dashboard | Overview metrics; links into filtered requests and overdue asset list. |
| Assets | Full inventory: filter by type, status, overdue; open row to view/edit. |
| Users | Directory: filter department, role, search username; edit or delete users. |
| Requests | All asset requests; filter by type/status; open one to approve or reject. |

### Assets Workflow

- List (`/assets/`) — Filter asset type, status, overdue (active assignment with return due in the past). Table shows return-due for assigned items where applicable.
- Create (`/assets/new`) — Name, serial (unique), type, status, purchase/expiry dates, notes.
- View (`/assets/<id>/view`) — Detail + assignment history + recent audit lines mentioning that serial.
- Edit (`/assets/<id>/edit`) — Change fields; for Assigned status, assign or reassign user (searchable), set optional return due (not before today); for Returned status, record return date and close open assignments.
- Delete (`/assets/<id>/delete`) — Only if the asset is not currently Assigned (POST + CSRF).

### Users Workflow

- List (`/users/`) — Filter by department, role; search username.
- Edit (`/users/<id>/edit`) — Username, role, department (not email/password here).
- User’s assets (`/users/<id>/assets`) — Current and past assignments for support.
- Delete — Blocked if the user has open assignments, if the target is yourself, or if deleting the last admin.

### Asset Requests

1. Open Requests → pick a Pending row → Review.
2. For Approve:
   - Choose one available asset of the requested type.
   - Optional return due date.
   - Optional asset notes (syncs from selected row; editable; saved on the asset when you approve).
3. Approve and assign — Sets asset to Assigned, creates an Assignment, marks the request Approved, writes audit.
4. Reject — Marks the request Rejected, clears any linked asset on the request, audit logged.

---

# User Guide

### Signing In & Registering

- Register (`/auth/register`) — Choose username, email, department, password. New accounts are User role.
- Login (`/auth/login`). After login you will land on a page showing the assets assigned to you.

### Navigation

| Link | Purpose |
|:-----|:------------------|
| My Assets | Everything currently assigned to you; Return per item when you hand it back. |
| My Requests | Your asset requests and statuses; create, edit note, or delete pending only. |
| Asset History | Past assignments (including returned items). |

### Request an Asset

1. My Requests → flow to request (or go to Request asset from the UI).
2. Pick asset type (laptop, monitor, license, etc.) and add a note (why you need it).
3. Submit — Request will be sent to IT admins.

### Pending Requests

- Edit note — Clarify or update your message.
- Delete — Withdraw the request (recorded in audit).

You cannot edit or delete approved/rejected requests.

### Returns

- From My Assets, use Return on an item when you have physically returned it.
- The app records the return and updates asset status.
