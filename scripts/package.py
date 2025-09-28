#!/usr/bin/env python3
"""Helper CLI for building, testing, and publishing upstream container packages."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
CONTAINERS_DIR = ROOT / "containers"


def load_metadata(slug: str) -> Tuple[Dict[str, Any], Path]:
    package_dir = CONTAINERS_DIR / slug
    metadata_path = package_dir / "container.yaml"
    if not metadata_path.exists():
        raise SystemExit(f"container metadata not found: {metadata_path}")
    metadata = _load_yaml(metadata_path)
    return metadata, package_dir


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:
        raise SystemExit("Install pyyaml (pip install pyyaml) to use this script.")

    return yaml.safe_load(path.read_text())


def resolve_token(metadata: Dict[str, Any], value: Any) -> Any:
    if isinstance(value, str) and value.startswith("!"):
        path = value[1:]
        return resolve_path(metadata, path)
    return value


def resolve_path(metadata: Dict[str, Any], path: str) -> Any:
    parts = path.split(".")
    node: Any = metadata
    for part in parts:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            raise SystemExit(f"unable to resolve token '!{path}' in metadata")
    return node


def flatten_build_args(metadata: Dict[str, Any]) -> Dict[str, str]:
    args = metadata.get("build", {}).get("args", {})
    resolved = {}
    for key, value in args.items():
        resolved[key] = str(resolve_token(metadata, value))
    return resolved


def compute_tags(metadata: Dict[str, Any]) -> List[str]:
    publish = metadata.get("publish", {})
    image = publish.get("image")
    if not image:
        raise SystemExit("publish.image must be set in container.yaml")
    tags = publish.get("tags", [])
    if not tags:
        raise SystemExit("publish.tags must contain at least one entry")
    resolved: List[str] = []
    for tag in tags:
        resolved_tag = str(resolve_token(metadata, tag))
        resolved.append(f"{image}:{resolved_tag}")
    return resolved


def docker_build(package_dir: Path, metadata: Dict[str, Any], args: argparse.Namespace) -> None:
    dockerfile = metadata.get("build", {}).get("dockerfile", "Dockerfile")
    context = metadata.get("build", {}).get("context", ".")
    context_dir = package_dir / context
    if not context_dir.exists():
        raise SystemExit(f"build context not found: {context_dir}")

    tags = compute_tags(metadata)
    build_args = flatten_build_args(metadata)

    cmd = ["docker", "build", str(context_dir), "-f", str(package_dir / dockerfile)]

    for tag in tags:
        cmd.extend(["-t", tag])

    if args.platform:
        cmd.extend(["--platform", args.platform])

    for key, value in build_args.items():
        cmd.extend(["--build-arg", f"{key}={value}"])

    print("→ docker", " ".join(cmd[1:]))
    subprocess.run(cmd, check=True, cwd=package_dir)


def run_tests(package_dir: Path, metadata: Dict[str, Any], args: argparse.Namespace) -> None:
    tests = metadata.get("tests", [])
    if not tests:
        print("no tests defined; skipping")
        return

    env = os.environ.copy()
    venv_bin = ROOT / ".venv" / "bin"
    if venv_bin.is_dir():
        path = env.get("PATH", "")
        path_entries = [p for p in path.split(os.pathsep) if p]
        venv_str = str(venv_bin)
        if venv_str not in path_entries:
            env["PATH"] = os.pathsep.join([venv_str, *path_entries]) if path_entries else venv_str
        env.setdefault("VIRTUAL_ENV", str(venv_bin.parent))

    for test in tests:
        name = test.get("name") or "unnamed"
        command = test.get("command")
        if not command:
            print(f"Skipping test '{name}' with no command")
            continue
        print(f"→ running test '{name}'")
        subprocess.run(["bash", "-c", command], check=True, cwd=package_dir, env=env)


def docker_push(metadata: Dict[str, Any]) -> None:
    tags = compute_tags(metadata)
    for tag in tags:
        print(f"→ docker push {tag}")
        subprocess.run(["docker", "push", tag], check=True)


def show_info(metadata: Dict[str, Any]) -> None:
    print(json.dumps(metadata, indent=2))


def check_upstream(metadata, package_dir):
    def version_key(value: str):
        parts = []
        for token in str(value).replace('-', '.').split('.'):
            if token.isdigit():
                parts.append(int(token))
            else:
                parts.append(token)
        return tuple(parts)

    slug = metadata.get('slug') or package_dir.name
    version_cfg = metadata.get('version', {})
    strategy = version_cfg.get('strategy', 'manual')
    current = version_cfg.get('current')
    if not current:
        raise SystemExit('version.current must be set for upstream checks')

    result = {
        'package': slug,
        'strategy': strategy,
        'current': current,
        'status': 'skipped',
    }

    if strategy == 'http-directory':
        source = version_cfg.get('source', {}) or {}
        url = source.get('url')
        pattern = source.get('regex') or source.get('pattern')
        timeout = float(source.get('timeout', 10))
        if not url or not pattern:
            result['status'] = 'error'
            result['error'] = 'missing http-directory configuration'
            print(json.dumps(result))
            return 0
        import re
        from urllib.request import urlopen

        try:
            with urlopen(url, timeout=timeout) as response:
                payload = response.read().decode('utf-8', 'ignore')
        except Exception as exc:  # pylint: disable=broad-except
            result['status'] = 'error'
            result['error'] = str(exc)
            result['source'] = url
            print(json.dumps(result))
            return 0

        matches = re.findall(pattern, payload, flags=re.IGNORECASE)
        if not matches:
            result['status'] = 'error'
            result['error'] = 'no matches from http-directory source'
            result['source'] = url
            print(json.dumps(result))
            return 0
        if isinstance(matches[0], tuple):
            matches = [m[0] for m in matches]
        latest = max(matches, key=version_key)
        result['latest'] = latest
        result['source'] = url
        if version_key(latest) > version_key(str(current)):
            result['status'] = 'update_available'
            print(json.dumps(result))
            return 2

        result['status'] = 'up_to_date'
        print(json.dumps(result))
        return 0

    component = version_cfg.get('component')
    candidates = []
    if component:
        component_key = str(component).lower()
        candidates.append(component_key)
        candidates.append(component_key.replace('-', '_'))
    if slug:
        slug_key = str(slug).lower()
        candidates.append(slug_key)
        candidates.append(slug_key.replace('-', '_'))
        candidates.append(slug_key.split('-')[0])

    versions_file = package_dir / 'versions.json'
    latest = None
    if versions_file.exists():
        data = json.loads(versions_file.read_text())
        for key in candidates:
            if key and key in data and isinstance(data[key], dict):
                try:
                    latest = max(data[key].keys(), key=version_key)
                except ValueError:
                    latest = None
                break

    if latest is None:
        print(json.dumps(result))
        return 0

    result['latest'] = latest
    if version_key(latest) > version_key(str(current)):
        result['status'] = 'update_available'
        print(json.dumps(result))
        return 2

    result['status'] = 'up_to_date'
    print(json.dumps(result))
    return 0
def detect_version(metadata: Dict[str, Any]) -> None:
    version = metadata.get("version", {})
    strategy = version.get("strategy")
    current = version.get("current")
    notes = version.get("notes")
    print(f"Strategy: {strategy}")
    print(f"Current: {current}")
    if notes:
        print(f"Notes: {notes}")
    if strategy != "manual":
        print("Implement automated detection by extending scripts/package.py")


def list_packages() -> Iterable[str]:
    for path in sorted(CONTAINERS_DIR.iterdir()):
        if path.name.startswith("."):
            continue
        if (path / "container.yaml").exists():
            yield path.name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")


    build_parser = subparsers.add_parser("build", help="Build the container image")
    build_parser.add_argument("package", help="Package slug")
    build_parser.add_argument("--platform", help="Target platform for buildx (e.g. linux/amd64)")

    test_parser = subparsers.add_parser("test", help="Run package tests")
    test_parser.add_argument("package", help="Package slug")

    push_parser = subparsers.add_parser("publish", help="Push image tags to a registry")
    push_parser.add_argument("package", help="Package slug")

    show_parser = subparsers.add_parser("show", help="Pretty-print package metadata")
    show_parser.add_argument("package", help="Package slug")

    detect_parser = subparsers.add_parser("detect-version", help="Display version strategy information")
    detect_parser.add_argument("package", help="Package slug")

    check_parser = subparsers.add_parser("check-upstream", help="Check upstream for new versions")
    check_parser.add_argument("package", help="Package slug")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.command:
        print("Available packages:")
        for slug in list_packages():
            print(f"- {slug}")
        return

    metadata, package_dir = load_metadata(getattr(args, "package"))

    if args.command == "build":
        docker_build(package_dir, metadata, args)
    elif args.command == "test":
        run_tests(package_dir, metadata, args)
    elif args.command == "publish":
        docker_push(metadata)
    elif args.command == "show":
        show_info(metadata)
    elif args.command == "check-upstream":
        sys.exit(check_upstream(metadata, package_dir))
    elif args.command == "detect-version":
        detect_version(metadata)
    else:
        raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
