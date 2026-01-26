#!/usr/bin/env python3
"""Basic sanity checks for devpi-server container metadata."""
from __future__ import annotations

import sys
from pathlib import Path

metadata_path = Path(__file__).resolve().parent.parent / "container.yaml"
text = metadata_path.read_text(encoding="utf-8")

if 'slug: "devpi-server"' not in text:
    sys.exit("missing devpi-server slug")

print("ok")
