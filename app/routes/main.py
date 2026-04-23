from flask import Blueprint, jsonify

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return jsonify(
        name="IT Asset Management System",
        status="ok",
    )


@bp.get("/health")
def health():
    return jsonify(healthy=True), 200
