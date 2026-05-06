"""
Demo seeding orchestration.

Invoked from the app factory for non-testing configs so demo deployments (including production)
get the `localdev` admin and sample data.
"""

from __future__ import annotations

from app.seed.demo_assets import ensure_demo_assets
from app.seed.localdev import ensure_localdev_admin

__all__ = ["ensure_demo_assets", "ensure_localdev_admin"]
