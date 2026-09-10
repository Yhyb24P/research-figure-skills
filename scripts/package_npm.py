#!/usr/bin/env python3
"""Stage a native launcher into its npm platform package after smoke testing."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "dist" / "native" / "linux-x64"
PLATFORM = ROOT / "packages" / "npm" / "platforms" / "linux-x64"


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
    print(destination)


if __name__ == "__main__":
    main()
