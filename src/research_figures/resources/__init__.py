"""Installed, immutable runtime resources shipped in wheels."""

from collections.abc import Iterator
from importlib.resources import as_file, files
from pathlib import Path

import yaml

ROOT = files(__name__)


def resource_path(kind: str, relative_path: str = "") -> Path:
    target = ROOT.joinpath(kind, relative_path)
    with as_file(target) as path:
        return Path(path)


def iter_profiles() -> Iterator[dict]:
    for node in ROOT.joinpath("profiles").rglob("*.yaml"):
        yield yaml.safe_load(node.read_text(encoding="utf-8"))


def read_source_registry() -> dict:
    return yaml.safe_load(ROOT.joinpath("references", "sources.yaml").read_text(encoding="utf-8"))


def iter_bundled_skills() -> Iterator[tuple[str, str]]:
    for node in ROOT.joinpath("skills").rglob("SKILL.md"):
        yield node.parent.name, node.read_text(encoding="utf-8")


def selftest_fixture() -> dict:
    return yaml.safe_load(
        ROOT.joinpath("selftest", "figure.contract.yaml").read_text(encoding="utf-8")
    )
