"""
Development seeding orchestration.

Invokes `ensure_localdev_admin` and `ensure_demo_assets` from the app factory when DEBUG is enabled.
"""

from __future__ import annotations

from app.seed.demo_assets import ensure_demo_assets
from app.seed.localdev import ensure_localdev_admin

__all__ = ["ensure_demo_assets", "ensure_localdev_admin"]
