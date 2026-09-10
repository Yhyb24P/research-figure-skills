#!/usr/bin/env python3
"""Copy the repository license into each independently packed npm package."""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [ROOT / "packages/npm/cli/LICENSE", ROOT / "packages/npm/platforms/linux-x64/LICENSE"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    source = (ROOT / "LICENSE").read_bytes()
    mismatches = [
        target for target in TARGETS if not target.is_file() or target.read_bytes() != source
    ]
    if args.check and mismatches:
        raise SystemExit(
            "npm package license copies are out of sync: " + ", ".join(map(str, mismatches))
        )
    if not args.check:
        for target in mismatches:
            target.write_bytes(source)
    print("PASS license sync")


if __name__ == "__main__":
    main()
