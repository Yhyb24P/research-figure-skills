#!/usr/bin/env python3
"""Reject version drift across Python, npm and release metadata."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    release = tomllib.loads((ROOT / "release.toml").read_text())["release"]
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    packages = [ROOT / "packages/npm/cli/package.json"] + sorted(
        (ROOT / "packages/npm/platforms").glob("*/package.json")
    )
    failures = []
    if pyproject["version"] != release["python_version"]:
        failures.append("pyproject.toml")
    if json.loads((ROOT / "package.json").read_text())["version"] != release["npm_version"]:
        failures.append("package.json")
    for package in packages:
        if json.loads(package.read_text())["version"] != release["npm_version"]:
            failures.append(str(package.relative_to(ROOT)))
    if release["git_tag"] != f"v{release['npm_version']}":
        failures.append("release.toml git_tag")
    if failures:
        raise SystemExit("version mismatch: " + ", ".join(failures))
    print("PASS version parity")


if __name__ == "__main__":
    main()
