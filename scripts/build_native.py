#!/usr/bin/env python3
"""Build the Linux PyApp launcher from the release wheel, never from a registry.

PyApp has no separate "pack" executable: it is a Rust binary configured at
compile time.  PYAPP_PROJECT_PATH causes its build script to embed the exact
wheel named below, and makes the runtime install that embedded archive instead
of resolving ``research-figure-skills`` from an index.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYAPP_VERSION = "0.29.0"


def release_version() -> str:
    return tomllib.loads((ROOT / "release.toml").read_text())["release"]["python_version"]


def pyapp_manifest() -> Path:
    candidates = sorted(Path.home().glob(f".cargo/registry/src/*/pyapp-{PYAPP_VERSION}/Cargo.toml"))
    if len(candidates) != 1:
        raise SystemExit(
            "PyApp 0.29.0 source is required exactly once in Cargo's local "
            "registry; run `cargo install pyapp --version 0.29.0 --locked` first."
        )
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", default="linux-x64")
    args = parser.parse_args()
    if (
        args.platform != "linux-x64"
        or platform.system() != "Linux"
        or platform.machine() != "x86_64"
    ):
        raise SystemExit("this builder currently supports only native Linux x64")

    version = release_version()
    wheel = ROOT / "dist" / f"research_figure_skills-{version}-py3-none-any.whl"
    if not wheel.is_file():
        raise SystemExit(f"release wheel is missing: {wheel}; run `uv build --no-sources` first")

    target = ROOT / "build" / "pyapp-target"
    env = os.environ | {
        "PYAPP_PROJECT_PATH": str(wheel),
        "PYAPP_EXEC_SPEC": "research_figures.cli:main",
        "PYAPP_PYTHON_VERSION": "3.12",
        "CARGO_TARGET_DIR": str(target),
    }
    subprocess.run(
        ["cargo", "build", "--release", "--manifest-path", str(pyapp_manifest())],
        check=True,
        cwd=ROOT,
        env=env,
    )
    binary = target / "release" / "pyapp"
    if not binary.is_file():
        raise SystemExit(f"PyApp did not create {binary}")
    output = ROOT / "dist" / "native" / args.platform / "rfig"
    output.parent.mkdir(parents=True, exist_ok=True)
    staged_output = output.with_name(f".{output.name}.new")
    shutil.copy2(binary, staged_output)
    os.replace(staged_output, output)
    output.chmod(0o755)

    manifest = {
        "release_version": version,
        "python_distribution": "CPython 3.12 (PyApp managed)",
        "wheel_filename": wheel.name,
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "build_platform": f"{platform.system().lower()}-{platform.machine()}",
        "pyapp_version": PYAPP_VERSION,
        "project_source": "embedded local wheel via PYAPP_PROJECT_PATH",
        "entry_point": "research_figures.cli:main",
    }
    (output.parent / "launcher-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(output)


if __name__ == "__main__":
    main()
