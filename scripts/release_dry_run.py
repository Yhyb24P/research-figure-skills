#!/usr/bin/env python3
"""Verify locally built release artifacts without pretending to publish them."""

from __future__ import annotations

import json
import subprocess
import tomllib
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def record(path: Path) -> dict[str, str]:
    return {"path": str(path.relative_to(DIST)), "sha256": sha256(path.read_bytes()).hexdigest()}


def main() -> None:
    release = tomllib.loads((ROOT / "release.toml").read_text())["release"]
    artifacts = sorted(
        path
        for path in DIST.rglob("*")
        if path.is_file()
        and not path.name.startswith(".")
        and path.name
        not in {"checksums.json", "checksums-sha256.txt", "sbom.spdx.json", "release-manifest.json"}
    )
    wheel = DIST / f"research_figure_skills-{release['python_version']}-py3-none-any.whl"
    sdist = DIST / f"research_figure_skills-{release['python_version']}.tar.gz"
    native = DIST / "native/linux-x64/rfig"
    npm = sorted((DIST / "npm").glob("*.tgz"))
    required = [wheel, sdist, native]
    if any(not path.is_file() for path in required) or len(npm) < 2:
        raise SystemExit(
            "release artifacts missing; build wheel, native launcher, and npm tarballs first"
        )
    checks = [record(path) for path in artifacts]
    (DIST / "checksums.json").write_text(
        json.dumps({"version": release["python_version"], "artifacts": checks}, indent=2) + "\n"
    )
    (DIST / "checksums-sha256.txt").write_text(
        "".join(f"{item['sha256']}  {item['path']}\n" for item in checks)
    )
    dependencies = subprocess.check_output(
        ["uv", "export", "--no-dev", "--no-hashes"], cwd=ROOT, text=True
    )
    (DIST / "sbom.spdx.json").write_text(
        json.dumps(
            {
                "spdxVersion": "SPDX-2.3",
                "name": "research-figure-skills",
                "packages": dependencies.splitlines(),
            },
            indent=2,
        )
        + "\n"
    )
    manifest = {
        "schema_version": "1",
        "version": release["python_version"],
        "git_tag": release["git_tag"],
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "python_distribution": "research-figure-skills",
        "npm_distribution": release["npm_package"],
        "artifacts": checks,
        "policy_snapshots": [
            profile.name
            for profile in (ROOT / "src/research_figures/resources/profiles").rglob("*.yaml")
        ],
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (DIST / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"PASS release dry-run ({len(checks)} artifacts)")


if __name__ == "__main__":
    main()
