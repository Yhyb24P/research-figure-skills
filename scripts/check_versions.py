#!/usr/bin/env python3
"""Reject version drift across Python, npm and release metadata."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def python_to_npm(version: str) -> str:
    """Map the supported PEP 440 RC spelling to npm semver prerelease syntax."""
    match = re.fullmatch(r"(\d+\.\d+\.\d+)(?:(a|b|rc)(\d+))?", version)
    if match is None:
        raise SystemExit(f"unsupported Python release version: {version}")
    base, phase, serial = match.groups()
    if phase is None:
        return base
    npm_phase = {"a": "alpha", "b": "beta", "rc": "rc"}[phase]
    return f"{base}-{npm_phase}.{serial}"


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
    if release["npm_version"] != python_to_npm(release["python_version"]):
        failures.append("release.toml python/npm mapping")
    if release["git_tag"] != f"v{release['npm_version']}":
        failures.append("release.toml git_tag")
    if failures:
        raise SystemExit("version mismatch: " + ", ".join(failures))
    print(
        "PASS version parity "
        f"(Python={release['python_version']}, npm={release['npm_version']}, "
        f"tag={release['git_tag']})"
    )


if __name__ == "__main__":
    main()
