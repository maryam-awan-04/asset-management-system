"""Shared literals for development seeding."""

from __future__ import annotations

import os

LOCALDEV_USERNAME = "localdev"
LOCALDEV_EMAIL = "localdev@gmail.com"

SEED_SERIAL_MARKER = "IT-LP-24-00891"
SEED_USER_PASSWORD = os.environ.get("SEED_USER_PASSWORD", "SeedDemo1!")

SEED_EMAIL_DOMAIN = "demo.com"

_DEMO_ASSET_SERIALS = frozenset(
    {
        "IT-LP-24-00891",
        "LEN-PF4ZK9Q2",
        "DELL-U3223QE-4KQ2N1",
        "DELL-P2723DE-8MZ3K9",
        "LOG-MXK-BKEY-00221",
        "APL-FVFK71Q9Q05D",
        "MSFT-SL5-9K2M4410",
        "DELL-U2424H-3N8KQ7",
        "LOG-MXM3S-11K882",
        "LOG-MXA3S-44B901",
        "JBR-EV275-QP93L2",
        "POL-P15-UK90M1",
        "ELG-FCPRO-7HX22",
        "SHR-MV7-USB-44102",
        "MSFT-M365-E5-SN8841201",
        "ADOBE-CC-TM-2025-77102",
        "DELL-P2422H-EOL-1993",
        "KEY-Q6PRO-BK88",
    },
)
