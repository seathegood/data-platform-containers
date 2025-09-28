#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

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
