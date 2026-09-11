#!/usr/bin/env python3
"""Verify locally built release artifacts without pretending to publish them."""

from __future__ import annotations

import json
import os
import subprocess
import tarfile
import tempfile
import tomllib
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def record(path: Path) -> dict[str, str]:
    return {"path": str(path.relative_to(DIST)), "sha256": sha256(path.read_bytes()).hexdigest()}


def npm_filename(name: str, version: str) -> str:
    return f"{name.removeprefix('@').replace('/', '-')}-{version}.tgz"


def verify_npm_tarball(path: Path, expected_name: str, expected_version: str) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"missing or empty npm artifact: {path}")
    with tarfile.open(path, "r:gz") as archive:
        try:
            member = archive.extractfile("package/package.json")
        except KeyError as exc:
            raise SystemExit(f"npm artifact lacks package/package.json: {path}") from exc
        if member is None:
            raise SystemExit(f"npm artifact has unreadable package/package.json: {path}")
        metadata = json.load(member)
    if metadata.get("name") != expected_name or metadata.get("version") != expected_version:
        raise SystemExit(
            f"npm artifact metadata mismatch in {path}: "
            f"expected {expected_name}@{expected_version}, got "
            f"{metadata.get('name')}@{metadata.get('version')}"
        )


def npm_external_smoke(platform_tgz: Path, wrapper_tgz: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="rfig-npm-release-") as temp:
        temp_dir = Path(temp)
        subprocess.run(
            ["npm", "install", "--no-audit", "--no-fund", str(platform_tgz), str(wrapper_tgz)],
            cwd=temp_dir,
            check=True,
        )
        launcher = temp_dir / "node_modules" / ".bin" / "rfig"
        if not launcher.is_file():
            raise SystemExit("npm external smoke did not install the rfig launcher")
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "VIRTUAL_ENV"}
        }
        for arguments in (("--version",), ("doctor", "--json"), ("self-test",)):
            subprocess.run([str(launcher), *arguments], cwd=temp_dir, env=env, check=True)


def main() -> None:
    release = tomllib.loads((ROOT / "release.toml").read_text())["release"]
    npm_version = release["npm_version"]
    npm_dir = DIST / "npm"
    if not npm_dir.is_dir():
        raise SystemExit(f"npm artifact directory is missing: {npm_dir}")
    package_names = (
        "@yhyb24p/research-figure-linux-x64",
        "@yhyb24p/research-figure",
    )
    npm_artifacts = [npm_dir / npm_filename(name, npm_version) for name in package_names]
    for path, name in zip(npm_artifacts, package_names, strict=True):
        verify_npm_tarball(path, name, npm_version)
    npm_external_smoke(npm_artifacts[0], npm_artifacts[1])
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
    npm = sorted(npm_dir.glob("*.tgz"))
    required = [wheel, sdist, native]
    if any(not path.is_file() for path in required) or len(npm) != len(npm_artifacts):
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
