#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGES = os.environ.get('PACKAGES_JSON')
if not PACKAGES:
    print('::warning::PACKAGES_JSON not provided; nothing to check')
    sys.exit(0)

packages = json.loads(PACKAGES)
results = []
for pkg in packages:
    cmd = ["./scripts/package.py", "check-upstream", pkg]
    completed = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    stdout = completed.stdout.strip()
    if stdout:
        for line in stdout.splitlines():
            try:
                payload = json.loads(line)
                results.append(payload)
            except json.JSONDecodeError:
                print(line)
    if completed.returncode not in (0, 2):
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        completed.check_returncode()

def head_exists(url: str, timeout: float = 10.0) -> bool:
    req = Request(url, method="HEAD")
    with urlopen(req, timeout=timeout) as response:
        return response.status == 200


def fetch_versions(url: str, timeout: float = 10.0) -> list[str]:
    with urlopen(url, timeout=timeout) as response:
        data = response.read().decode("utf-8", "ignore")
    versions = []
    for line in data.splitlines():
        line = line.strip()
        if line.startswith("<version>") and line.endswith("</version>"):
            versions.append(line[len("<version>") : -len("</version>")])
    return versions


def spark_update_gate(entry: dict) -> None:
    if entry.get("status") != "update_available":
        return
    latest = entry.get("latest")
    if not latest:
        return

    metadata_path = REPO_ROOT / "containers" / "spark" / "container.yaml"
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:
        return
    data = yaml.safe_load(metadata_path.read_text())
    build_args = data.get("build", {}).get("args", {})
    hadoop_version = str(build_args.get("HADOOP_VERSION", "3"))
    hadoop_major = hadoop_version.split(".")[0]

    spark_url = (
        f"https://archive.apache.org/dist/spark/spark-{latest}/"
        f"spark-{latest}-bin-hadoop{hadoop_major}.tgz"
    )
    try:
        if not head_exists(spark_url):
            entry["status"] = "blocked"
            entry["blocked_reason"] = "spark_archive_missing"
            entry["blocked_url"] = spark_url
            return
    except Exception as exc:  # pylint: disable=broad-except
        entry["status"] = "blocked"
        entry["blocked_reason"] = f"spark_archive_check_failed: {exc}"
        entry["blocked_url"] = spark_url
        return

    current_flavor = str(build_args.get("ICEBERG_RUNTIME_FLAVOR", ""))
    scala_suffix = None
    if "_" in current_flavor:
        scala_suffix = current_flavor.split("_", 1)[1]
    if not scala_suffix:
        scala_suffix = "2.13"

    parts = str(latest).split(".")
    if len(parts) < 2:
        return
    candidate_flavor = f"{parts[0]}.{parts[1]}_{scala_suffix}"
    metadata_url = (
        "https://repo1.maven.org/maven2/org/apache/iceberg/"
        f"iceberg-spark-runtime-{candidate_flavor}/maven-metadata.xml"
    )
    try:
        versions = fetch_versions(metadata_url)
    except Exception:  # pylint: disable=broad-except
        entry["status"] = "blocked"
        entry["blocked_reason"] = "iceberg_runtime_flavor_missing"
        entry["blocked_url"] = metadata_url
        return

    if not versions:
        entry["status"] = "blocked"
        entry["blocked_reason"] = "iceberg_runtime_versions_missing"
        entry["blocked_url"] = metadata_url
        return

    entry["iceberg_runtime_flavor"] = candidate_flavor
    entry["iceberg_version"] = versions[-1]


for entry in results:
    if entry.get("package") == "spark":
        spark_update_gate(entry)

updates = [r for r in results if r.get('status') == 'update_available']
print(json.dumps(results, indent=2))

def write_output(name: str, value):
    serialized = json.dumps(value)
    output_path = os.environ.get('GITHUB_OUTPUT')
    if not output_path:
        return
    with open(output_path, 'a', encoding='utf-8') as fh:
        fh.write(f'{name}<<EOF\n{serialized}\nEOF\n')

write_output('results', results)
write_output('updates', updates)
write_output('updates_count', len(updates))
