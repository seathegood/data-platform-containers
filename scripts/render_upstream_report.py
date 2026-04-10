#!/usr/bin/env python3
"""Render an upstream check report suitable for issue or PR bodies."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def _load_json_env(name: str) -> list[dict]:
    raw = os.environ.get(name, "")
    if not raw:
        return []
    value = json.loads(raw)
    if isinstance(value, list):
        return value
    return []


def _fmt_update(entry: dict) -> str:
    pkg = entry.get("package", "unknown")
    current = entry.get("current", "unknown")
    latest = entry.get("latest", "unknown")
    extra = ""
    if pkg == "spark":
        flavor = entry.get("iceberg_runtime_flavor")
        iceberg = entry.get("iceberg_version")
        if flavor or iceberg:
            extra = f" (iceberg {iceberg or 'unknown'}, flavor {flavor or 'unknown'})"
    return f"- **{pkg}**: {current} -> {latest}{extra}"


def _fmt_problem(entry: dict) -> str:
    pkg = entry.get("package", "unknown")
    status = entry.get("status", "unknown")
    reason = entry.get("blocked_reason") or entry.get("error") or "n/a"
    source = entry.get("blocked_url") or entry.get("source")
    line = f"- **{pkg}**: {status} ({reason})"
    if source:
        line += f" - `{source}`"
    return line


def _fmt_result(entry: dict) -> str:
    pkg = entry.get("package", "unknown")
    status = entry.get("status", "unknown")
    current = entry.get("current", "unknown")
    latest = entry.get("latest")
    if latest:
        return f"- **{pkg}**: {status} (current `{current}`, latest `{latest}`)"
    return f"- **{pkg}**: {status} (current `{current}`)"


def main() -> None:
    results = _load_json_env("RESULTS_JSON")
    updates = _load_json_env("UPDATES_JSON")
    blocked_or_error = [r for r in results if r.get("status") in {"blocked", "error"}]
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    lines = [
        "## Upstream Check Report",
        "",
        f"- Checked at: `{checked_at}`",
        f"- Packages evaluated: `{len(results)}`",
        f"- Updates available: `{len(updates)}`",
        f"- Blocked or errored: `{len(blocked_or_error)}`",
        "",
    ]

    lines.append("### Updates Ready For Validation")
    if updates:
        lines.extend(_fmt_update(entry) for entry in updates)
    else:
        lines.append("- None")
    lines.append("")

    lines.append("### Blocked / Errors")
    if blocked_or_error:
        lines.extend(_fmt_problem(entry) for entry in blocked_or_error)
    else:
        lines.append("- None")
    lines.append("")

    lines.append("### Full Results")
    if results:
        lines.extend(_fmt_result(entry) for entry in results)
    else:
        lines.append("- No results")
    lines.append("")

    lines.append(
        "_This is an issue-first upstream check. No automatic version PR is opened on schedule._"
    )

    print("\n".join(lines))


if __name__ == "__main__":
    main()
