#!/usr/bin/env python3
"""Synchronize public Skills from the canonical packaged resource source."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/research_figures/resources/skills"
DESTINATION = ROOT / "skills"


def main() -> None:
    check = argparse.ArgumentParser()
    check.add_argument("--check", action="store_true")
    args = check.parse_args()
    mismatches = []
    for source in sorted(SOURCE.glob("*/SKILL.md")):
        target = DESTINATION / source.parent.name / "SKILL.md"
        if not target.is_file() or target.read_bytes() != source.read_bytes():
            mismatches.append(target)
            if not args.check:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
    if mismatches and args.check:
        print("Skill copies are out of sync:", *mismatches, sep="\n", file=sys.stderr)
        raise SystemExit(1)
    print("PASS skill sync")


if __name__ == "__main__":
    main()
