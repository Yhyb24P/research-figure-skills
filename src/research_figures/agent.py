"""Copy-based agent Skill installation from bundled package resources."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ._version import __version__
from .resources import iter_bundled_skills


def target(agent: str, global_: bool, project: Path | None) -> Path:
    if agent != "codex":
        raise ValueError("RF-INSTALL-001 unsupported agent: " + agent)
    return (
        (Path.home() / ".codex" / "skills")
        if global_
        else ((project or Path.cwd()) / ".agents" / "skills")
    )


def install(agent: str, global_: bool, project: Path | None, force: bool = False) -> dict:
    dest = target(agent, global_, project)
    dest.mkdir(parents=True, exist_ok=True)
    skills = {}
    for name, content in iter_bundled_skills():
        path = dest / name / "SKILL.md"
        value = hashlib.sha256(content.encode()).hexdigest()
        if path.exists() and path.read_text(encoding="utf-8") != content and not force:
            raise ValueError("RF-INSTALL-002 local skill modified: " + name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        skills[name] = {"sha256": value, "source": "bundled"}
    manifest = {
        "schema_version": "1",
        "product": "research-figure-skills",
        "product_version": __version__,
        "agent": agent,
        "scope": "global" if global_ else "project",
        "skills": skills,
    }
    (dest / "research-figure-install.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest


def status(agent: str, global_: bool, project: Path | None) -> dict:
    path = target(agent, global_, project) / "research-figure-install.json"
    return {
        "installed": path.exists(),
        "manifest": json.loads(path.read_text()) if path.exists() else None,
    }


def uninstall(agent: str, global_: bool, project: Path | None) -> dict:
    """Remove only Skills recorded by this product's installation manifest."""
    dest = target(agent, global_, project)
    manifest_path = dest / "research-figure-install.json"
    if not manifest_path.is_file():
        return {"removed": [], "status": "NOT_INSTALLED"}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    removed = []
    for name, entry in manifest.get("skills", {}).items():
        skill = dest / name / "SKILL.md"
        expected = entry.get("sha256")
        actual = hashlib.sha256(skill.read_bytes()).hexdigest() if skill.is_file() else None
        if actual and actual != expected:
            raise ValueError("RF-INSTALL-002 local skill modified: " + name)
        if skill.is_file():
            skill.unlink()
        try:
            (dest / name).rmdir()
        except OSError:
            pass
        removed.append(name)
    manifest_path.unlink()
    return {"removed": removed, "status": "PASS"}
