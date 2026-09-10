#!/usr/bin/env python3
"""Clean-install smoke for the wheel, usable by Linux/macOS/Windows CI."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def main() -> None:
    wheel = next((ROOT / "dist").glob("research_figure_skills-*-py3-none-any.whl"), None)
    if wheel is None:
        raise SystemExit("wheel is missing; run `uv build --no-sources` first")
    with tempfile.TemporaryDirectory(prefix="rfig-wheel-") as temporary:
        base = Path(temporary)
        venv = base / "venv"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("VIRTUAL_ENV", None)
        run(["uv", "venv", str(venv)], base, env)
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        rfig = venv / ("Scripts/rfig.exe" if os.name == "nt" else "bin/rfig")
        run(["uv", "pip", "install", "--python", str(python), str(wheel)], base, env)
        for command in (
            [str(rfig), "policy", "list"],
            [str(rfig), "doctor", "--json"],
            [str(rfig), "self-test"],
        ):
            run(command, base, env)
    print("PASS wheel clean-install")


if __name__ == "__main__":
    main()
