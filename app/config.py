from __future__ import annotations

import os
from datetime import timedelta
from typing import Optional, Type


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)
    REMEMBER_COOKIE_DURATION = timedelta(days=14)


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


def get_config(name: Optional[str]) -> Type[Config]:
    mapping = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
    }
    key = (name or os.environ.get("FLASK_CONFIG") or "development").lower()
    return mapping.get(key, DevelopmentConfig)
