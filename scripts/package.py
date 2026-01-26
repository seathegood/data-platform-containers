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


def compute_resolved_tags(metadata: Dict[str, Any]) -> List[str]:
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
        resolved.append(resolved_tag)

    version = str(metadata.get("version", {}).get("current", "")).strip()
    if version:
        parts = version.split(".")
        if len(parts) >= 3 and all(p.isdigit() for p in parts[:3]):
            major, minor, patch = parts[:3]
            for extra in (major, f"{major}.{minor}", f"{major}.{minor}.{patch}"):
                if extra not in resolved:
                    resolved.append(extra)

    if "latest" not in resolved:
        resolved.append("latest")

    if os.environ.get("PACKAGE_INCLUDE_STABLE"):
        if "stable" not in resolved:
            resolved.append("stable")

    sha = None
    env_sha = os.environ.get("GITHUB_SHA") or os.environ.get("GIT_SHA")
    if env_sha:
        sha = env_sha[:12]
    else:
        try:
            completed = subprocess.run(
                ["git", "rev-parse", "--short=12", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
            sha = completed.stdout.strip()
        except Exception:
            sha = None
    if sha:
        sha_tag = f"sha-{sha}"
        if sha_tag not in resolved:
            resolved.append(sha_tag)

    return resolved


def compute_tags(metadata: Dict[str, Any]) -> List[str]:
    publish = metadata.get("publish", {})
    image = publish.get("image")
    if not image:
        raise SystemExit("publish.image must be set in container.yaml")
    return [f"{image}:{tag}" for tag in compute_resolved_tags(metadata)]


def compute_local_tag(metadata: Dict[str, Any]) -> str:
    publish = metadata.get("publish", {})
    image = publish.get("image")
    if not image:
        raise SystemExit("publish.image must be set in container.yaml")
    base = image.rsplit("/", 1)[-1]
    return f"{base}:local"


def docker_build(package_dir: Path, metadata: Dict[str, Any], args: argparse.Namespace) -> None:
    dockerfile = metadata.get("build", {}).get("dockerfile", "Dockerfile")
    context = metadata.get("build", {}).get("context", ".")
    context_dir = package_dir / context
    if not context_dir.exists():
        raise SystemExit(f"build context not found: {context_dir}")

    tags = compute_tags(metadata)
    local_tag = compute_local_tag(metadata)
    build_args = flatten_build_args(metadata)

    platforms = args.platform or os.environ.get("PACKAGE_PLATFORMS")
    use_buildx = bool(platforms)

    if use_buildx:
        cmd = ["docker", "buildx", "build"]
    else:
        cmd = ["docker", "build"]

    cmd.extend(["-f", str(package_dir / dockerfile)])

    if platforms:
        cmd.extend(["--platform", platforms])

    if use_buildx:
        multi_arch = "," in platforms if platforms else False
        if os.environ.get("PACKAGE_PUSH"):
            cmd.append("--push")
        elif not multi_arch:
            cmd.append("--load")
        else:
            raise SystemExit("Multi-architecture builds require PACKAGE_PUSH=1 to push the image")

    for tag in tags:
        cmd.extend(["-t", tag])
    if local_tag not in tags:
        cmd.extend(["-t", local_tag])

    for key, value in build_args.items():
        cmd.extend(["--build-arg", f"{key}={value}"])

    cmd.append(str(context_dir))

    print("→", " ".join(cmd))
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


def docker_retag(
    metadata: Dict[str, Any],
    source_image: str,
    dry_run: bool,
    skip_missing: bool,
) -> None:
    publish = metadata.get("publish", {})
    dest_image = publish.get("image")
    if not dest_image:
        raise SystemExit("publish.image must be set in container.yaml")

    tags = compute_resolved_tags(metadata)
    for tag in tags:
        source = f"{source_image}:{tag}"
        dest = f"{dest_image}:{tag}"
        cmd = ["docker", "buildx", "imagetools", "create", "--tag", dest, source]
        print("→", " ".join(cmd))
        if not dry_run:
            completed = subprocess.run(cmd, capture_output=True, text=True)
            if completed.returncode != 0:
                stderr = completed.stderr.strip()
                stdout = completed.stdout.strip()
                combined = "\n".join([line for line in (stderr, stdout) if line])
                if skip_missing and "not found" in combined.lower():
                    print(f"→ skipping missing source tag: {source}")
                    continue
                raise SystemExit(combined or f"retag failed for {source}")


def resolve_source_image(metadata: Dict[str, Any], source_image: str | None, source_namespace: str | None) -> str:
    if source_image and source_namespace:
        raise SystemExit("Provide either --source-image or --source-namespace, not both")
    if source_image:
        return source_image
    if source_namespace:
        publish = metadata.get("publish", {})
        dest_image = publish.get("image")
        if not dest_image:
            raise SystemExit("publish.image must be set in container.yaml")
        image_name = dest_image.rsplit("/", 1)[-1]
        return f"{source_namespace}/{image_name}"
    raise SystemExit("Missing source image. Provide --source-image or --source-namespace.")




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

    if strategy == 'pypi':
        package_name = str(version_cfg.get('component') or slug).strip()
        timeout = float(version_cfg.get('timeout', 10))
        if not package_name:
            result['status'] = 'error'
            result['error'] = 'missing PyPI package name'
            print(json.dumps(result))
            return 0
        url = f'https://pypi.org/pypi/{package_name}/json'
        from urllib.request import urlopen
        try:
            with urlopen(url, timeout=timeout) as response:
                payload = json.loads(response.read().decode('utf-8', 'ignore'))
        except Exception as exc:  # pylint: disable=broad-except
            result['status'] = 'error'
            result['error'] = str(exc)
            result['source'] = url
            print(json.dumps(result))
            return 0
        latest = payload.get('info', {}).get('version')
        if not latest:
            result['status'] = 'error'
            result['error'] = 'unable to determine latest PyPI version'
            result['source'] = url
            print(json.dumps(result))
            return 0
        result['latest'] = latest
        result['source'] = url
        if version_key(latest) > version_key(str(current)):
            result['status'] = 'update_available'
            print(json.dumps(result))
            return 2

        result['status'] = 'up_to_date'
        print(json.dumps(result))
        return 0

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
        from urllib.request import urlopen
        import re
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
        if path.name == "_template":
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

    retag_parser = subparsers.add_parser(
        "retag",
        help="Retag an existing image from another namespace without rebuilding",
    )
    retag_parser.add_argument("package", help="Package slug or 'all'")
    retag_parser.add_argument("--source-image", help="Fully-qualified source image name")
    retag_parser.add_argument(
        "--source-namespace",
        help="Source namespace (e.g. ghcr.io/bssprx/data-platform-containers) used with the destination image name",
    )
    retag_parser.add_argument("--dry-run", action="store_true", help="Print commands without pushing")
    retag_parser.add_argument(
        "--skip-missing",
        action="store_true",
        help="Skip tags that do not exist in the source registry",
    )

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

    if args.command == "retag" and getattr(args, "package") == "all":
        packages = list(list_packages())
    else:
        packages = [getattr(args, "package")]

    for package in packages:
        metadata, package_dir = load_metadata(package)
        if args.command == "build":
            docker_build(package_dir, metadata, args)
        elif args.command == "test":
            run_tests(package_dir, metadata, args)
        elif args.command == "publish":
            docker_push(metadata)
        elif args.command == "retag":
            source_image = resolve_source_image(
                metadata, args.source_image, args.source_namespace
            )
            docker_retag(metadata, source_image, args.dry_run, args.skip_missing)
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
