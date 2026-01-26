#!/usr/bin/env python3
"""Minimal metadata check for the GX Core container."""
from __future__ import annotations

import sys
from pathlib import Path

metadata_path = Path(__file__).resolve().parent.parent / "container.yaml"
contents = metadata_path.read_text(encoding="utf-8")

if 'slug: "gx-core"' not in contents:
    sys.exit("missing gx-core slug")

print("ok")
