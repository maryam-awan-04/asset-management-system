from flask import Blueprint, jsonify, redirect, render_template, url_for
from flask_login import login_required

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    """Landing URL redirects to login (no separate marketing homepage)."""
    return redirect(url_for("auth.login"))


@bp.get("/dashboard")
@login_required
def dashboard():
    return render_template("main/dashboard.html")


@bp.get("/health")
def health():
    return jsonify(healthy=True), 200
