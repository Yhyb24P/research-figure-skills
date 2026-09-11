#!/usr/bin/env python3
"""Stage a native launcher into its npm platform package after smoke testing."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "dist" / "native" / "linux-x64"
PLATFORM = ROOT / "packages" / "npm" / "platforms" / "linux-x64"
NPM_DIST = ROOT / "dist" / "npm"
PACKAGES = (
    "@yhyb24p/research-figure-linux-x64",
    "@yhyb24p/research-figure",
)


def main() -> None:
    launcher = NATIVE / "rfig"
    manifest_file = NATIVE / "launcher-manifest.json"
    if not launcher.is_file() or not manifest_file.is_file():
        raise SystemExit("native launcher and manifest must exist before npm platform packaging")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("project_source") != "embedded local wheel via PYAPP_PROJECT_PATH":
        raise SystemExit("refusing to package a launcher without an embedded local project wheel")
    if b"RF1004 native PyApp launcher not bundled" in launcher.read_bytes():
        raise SystemExit("refusing to package a placeholder launcher")
    destination = PLATFORM / "bin" / "rfig"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(launcher, destination)
    destination.chmod(0o755)
    shutil.copy2(manifest_file, PLATFORM / "launcher-manifest.json")

    NPM_DIST.mkdir(parents=True, exist_ok=True)
    for stale_tarball in NPM_DIST.glob("*.tgz"):
        stale_tarball.unlink()
    summaries = []
    for package in PACKAGES:
        result = subprocess.run(
            [
                "npm",
                "pack",
                "--workspace",
                package,
                "--pack-destination",
                str(NPM_DIST),
                "--json",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        summary = json.loads(result.stdout)
        if not isinstance(summary, list) or len(summary) != 1:
            raise SystemExit(f"unexpected npm pack --json output for {package}: {result.stdout}")
        summaries.append(summary[0])
    (NPM_DIST / "npm-pack-summary.json").write_text(
        json.dumps(summaries, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summaries, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
