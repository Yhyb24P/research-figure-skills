"""Offline V2 core. Scientific semantics are validated before any rendering occurs."""

from __future__ import annotations

import json
import platform
import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import fitz
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from lxml import etree
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

from .resources import iter_profiles

ARTIFACTS = {
    "data_visualization",
    "primary_research_image",
    "explanatory_schematic",
    "method_architecture",
    "protein_structure",
    "graphical_abstract",
    "cover_art",
    "extended_data",
    "supplementary_figure",
}
PLOTS = {
    "scatter",
    "line",
    "point_range",
    "bar",
    "box",
    "violin",
    "histogram",
    "ecdf",
    "heatmap",
    "roc",
    "pr",
    "calibration",
    "confusion_matrix",
    "forest",
    "volcano",
}
CAPABILITIES = {
    "deterministic_plot",
    "deterministic_vector",
    "traditional_image_processing",
    "llm_code_assist",
    "llm_layout_planning",
    "vlm_visual_critic",
    "generative_image",
    "licensed_asset_library",
}


class RfigError(ValueError):
    pass


class BlockedError(RfigError):
    pass


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RfigError(f"missing input: {path}")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RfigError(f"invalid YAML mapping: {path}")
    return value


def dump_yaml(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    kind: str
    path: str
    sha256: str | None = None
    scientific_role: str | None = None


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statement: str
    scope: str | None = None
    evidence_panel_ids: list[str] = Field(default_factory=list)


class JournalContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    publisher: str
    journal: str
    submission_phase: str
    article_type: str | None = None
    profile_id: str | None = None


class Plot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str
    source: str
    x: str | None = None
    y: str | None = None
    group: str | None = None
    uncertainty: str | None = None
    significance: str | None = None
    smoothing: str | None = None
    interpolation: str | None = None


class Panel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    purpose: str
    plot: Plot
    axes: dict[str, Any] = Field(default_factory=dict)
    encoding: dict[str, Any] = Field(default_factory=dict)
    legend: dict[str, Any] = Field(default_factory=dict)


class Export(BaseModel):
    model_config = ConfigDict(extra="forbid")
    formats: list[str]
    output_dir: str
    width_mm: float
    height_mm: float
    dpi: int = 450


class FigureContract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str
    figure_id: str
    claim: Claim
    journal_context: JournalContext
    artifact_class: str
    sources: list[Source]
    panels: list[Panel]
    export: Export
    title: str | None = None
    transformations: list[dict[str, Any]] = Field(default_factory=list)
    statistics: dict[str, Any] = Field(default_factory=dict)
    layout: dict[str, Any] = Field(default_factory=dict)
    accessibility: dict[str, Any] = Field(default_factory=dict)
    ai_usage: list[dict[str, Any]] = Field(default_factory=list)
    assets: list[dict[str, Any]] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    locator: str


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    label: str
    semantic: bool
    kind: str
    evidence: list[Evidence] = Field(default_factory=list)


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    target: str
    relation: str
    semantic: bool = True
    evidence: list[Evidence] = Field(default_factory=list)


class SemanticGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str
    graph_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]


def contract_from(path: Path) -> FigureContract:
    return FigureContract.model_validate(load_yaml(path))


def graph_from(path: Path) -> SemanticGraph:
    return SemanticGraph.model_validate(load_yaml(path))


def validate_contract(contract: FigureContract, base: Path) -> None:
    if contract.artifact_class not in ARTIFACTS:
        raise RfigError("unsupported artifact class")
    if not contract.sources or not contract.panels:
        raise RfigError("sources and panels are required")
    ids = {s.source_id for s in contract.sources}
    if len(ids) != len(contract.sources):
        raise RfigError("source ids must be unique")
    panel_ids = [p.id for p in contract.panels]
    if len(panel_ids) != len(set(panel_ids)):
        raise RfigError("panel ids must be unique")
    if not ({"pdf", "svg"} & set(contract.export.formats)):
        raise RfigError("vector output required")
    for source in contract.sources:
        if not (base / source.path).is_file():
            raise RfigError(f"missing source: {source.path}")
    for panel in contract.panels:
        if panel.plot.type not in PLOTS or panel.plot.source not in ids:
            raise RfigError("unsupported plot or unresolved panel source")
        if panel.plot.uncertainty and panel.plot.uncertainty not in contract.statistics.get(
            "uncertainty", {}
        ):
            raise RfigError("missing-statistical-evidence")
        if panel.plot.significance:
            raise RfigError("significance requires explicit supported test-result contract")
        if panel.plot.smoothing or panel.plot.interpolation:
            raise RfigError("undeclared transformation requested")
        if not panel.axes.get("x_label") or not panel.axes.get("y_label"):
            raise RfigError("axis labels required")


def validate_graph(graph: SemanticGraph) -> None:
    ids = [n.id for n in graph.nodes]
    if len(ids) != len(set(ids)):
        raise RfigError("node ids must be unique")
    known = set(ids)
    for n in graph.nodes:
        if n.semantic and not n.evidence:
            raise RfigError(f"semantic node lacks evidence: {n.id}")
    for e in graph.edges:
        if e.source not in known or e.target not in known:
            raise RfigError("edge points to missing node")
        if e.semantic and (not e.evidence or not e.relation.strip()):
            raise RfigError("semantic edge lacks evidence")


@dataclass
class RuleResult:
    rule_id: str
    status: str
    expected: Any
    observed: Any
    source_id: str
    verification_status: str


def profiles(root: Path | None = None) -> list[dict[str, Any]]:
    """Return profiles bundled with the installed Python distribution."""
    return list(iter_profiles())


def resolve_profile(
    root: Path, context: JournalContext, artifact_class: str = "data_visualization"
) -> dict[str, Any]:
    candidates = []
    for profile in profiles(root):
        scope = profile["scope"]
        if (
            profile["publisher"] == context.publisher
            and profile["journal"] == context.journal
            and scope["submission_phase"] == context.submission_phase
        ):
            score = sum(
                [
                    scope.get("article_type") == context.article_type,
                    scope["artifact_class"] == artifact_class,
                ]
            )
            candidates.append((score, profile))
    if not candidates:
        raise RfigError("no scoped journal profile")
    return max(candidates, key=lambda x: x[0])[1]


def fresh(profile: dict[str, Any]) -> str:
    v = profile.get("verification", {})
    last = v.get("last_verified")
    ttl = int(v.get("stale_after_days", 90))
    if not last:
        return "UNVERIFIED"
    return (
        "STALE"
        if (datetime.now(UTC).date() - date.fromisoformat(str(last))).days > ttl
        else v.get("status", "UNVERIFIED")
    )


def policy_decision(profile: dict[str, Any], artifact: str, capability: str) -> str:
    if capability not in CAPABILITIES:
        raise RfigError("unknown capability")
    ai = profile.get("ai_policy", {})
    decision = ai.get(artifact, {}).get(capability, "UNKNOWN")
    if capability == "generative_image" and (
        decision == "UNKNOWN" or fresh(profile) in {"STALE", "UNVERIFIED"}
    ):
        return "BLOCKED"
    return decision


def policy_check(root: Path, contract: FigureContract) -> list[RuleResult]:
    profile = resolve_profile(root, contract.journal_context, contract.artifact_class)
    results = []
    for rule in profile["rules"]:
        prop = rule["property"]
        observed = (
            contract.export.width_mm
            if prop == "export.width_mm"
            else contract.export.height_mm
            if prop == "export.height_mm"
            else None
        )
        op = rule["operator"]
        value = rule["value"]
        good = (
            (op == "in" and observed in value)
            or (op == "lte" and observed <= value)
            or (op == "forbid" and True)
        )
        results.append(
            RuleResult(
                rule["rule_id"],
                "PASS" if good else "FAIL",
                value,
                observed,
                rule["source_id"],
                fresh(profile),
            )
        )
    for use in contract.ai_usage:
        decision = policy_decision(profile, contract.artifact_class, use["capability"])
        if decision in {"FORBID", "BLOCKED"}:
            results.append(
                RuleResult(
                    "AI-POLICY", "BLOCKED", decision, use["capability"], "policy", fresh(profile)
                )
            )
    return results


def _data(contract: FigureContract, base: Path, source_id: str) -> pd.DataFrame:
    source = next(s for s in contract.sources if s.source_id == source_id)
    path = base / source.path
    if source.kind != "csv":
        raise RfigError("V2 deterministic core currently supports csv sources")
    return pd.read_csv(path)


def render(contract_path: Path, root: Path) -> Path:
    contract = contract_from(contract_path)
    base = contract_path.parent
    validate_contract(contract, base)
    results = policy_check(root, contract)
    if any(r.status == "BLOCKED" for r in results):
        raise BlockedError("policy gate blocked requested backend")
    out = base / contract.export.output_dir
    out.mkdir(parents=True, exist_ok=True)
    profile = resolve_profile(root, contract.journal_context, contract.artifact_class)
    uppercase = any(
        rule["property"] == "typography.panel_labels"
        and isinstance(rule["value"], dict)
        and rule["value"].get("case") == "uppercase"
        for rule in profile["rules"]
    )
    n = len(contract.panels)
    fig, axes = plt.subplots(
        1,
        n,
        figsize=(contract.export.width_mm / 25.4, contract.export.height_mm / 25.4),
        squeeze=False,
    )
    plt.rcParams.update(
        {"font.size": 6, "font.family": "DejaVu Sans", "pdf.fonttype": 42, "svg.fonttype": "none"}
    )
    for ax, panel in zip(axes.ravel(), contract.panels):
        data = _data(contract, base, panel.plot.source)
        x, y = panel.plot.x, panel.plot.y
        if not x or not y or x not in data or y not in data:
            raise RfigError("panel variable missing")
        if data[[x, y]].isna().any().any():
            raise RfigError("missing values require an explicit declared transformation")
        groups = (
            [(None, data)]
            if not panel.plot.group
            else list(data.groupby(panel.plot.group, sort=False))
        )
        for i, (name, frame) in enumerate(groups):
            kw = {
                "label": str(name) if name is not None else None,
                "marker": ["o", "s", "^"][i % 3],
            }
            if panel.plot.type in {"line", "roc", "pr", "calibration"}:
                ax.plot(frame[x], frame[y], lw=1, ms=3, **kw)
            elif panel.plot.type == "ecdf":
                values = frame[y].sort_values().to_numpy()
                ax.step(values, np.arange(1, len(values) + 1) / len(values), where="post", **kw)
            elif panel.plot.type in {"bar", "forest"}:
                ax.bar(frame[x], frame[y], hatch=["/", "\\", "x"][i % 3], label=kw["label"])
            elif panel.plot.type == "histogram":
                ax.hist(frame[y], alpha=0.65, label=kw["label"], hatch=["/", "\\", "x"][i % 3])
            elif panel.plot.type in {"box", "violin"}:
                values = [f[y].to_numpy() for _, f in frame.groupby(x, sort=False)]
                (ax.boxplot if panel.plot.type == "box" else ax.violinplot)(values)
            elif panel.plot.type in {"heatmap", "confusion_matrix"}:
                matrix = frame.pivot_table(index=y, columns=x, aggfunc="size", fill_value=0)
                ax.imshow(matrix, aspect="auto")
            else:
                ax.scatter(frame[x], frame[y], s=18, **kw)
        if len(groups) > 1:
            ax.legend(frameon=False, fontsize=6)
        ax.set_xlabel(panel.axes["x_label"])
        ax.set_ylabel(panel.axes["y_label"])
        ax.text(
            -0.13,
            1.04,
            panel.id.upper() if uppercase else panel.id.lower(),
            transform=ax.transAxes,
            fontweight="bold",
            fontsize=8,
        )
    fig.subplots_adjust(left=0.13, right=0.98, bottom=0.20, top=0.90, wspace=0.35)
    for fmt in contract.export.formats:
        fig.savefig(out / f"{contract.figure_id}.{fmt}", format=fmt, dpi=contract.export.dpi)
    plt.close(fig)
    shutil.copy2(contract_path, out / "figure.contract.yaml")
    lineage = {
        "nodes": [
            {"id": s.source_id, "type": "source", "path": s.path, "sha256": digest(base / s.path)}
            for s in contract.sources
        ],
        "transformations": contract.transformations,
        "panel_sources": {p.id: p.plot.source for p in contract.panels},
    }
    dump_yaml(out / "data-lineage.yaml", lineage)
    dump_yaml(out / "ai-usage.yaml", {"ai_usage": contract.ai_usage})
    dump_yaml(out / "asset-manifest.yaml", {"assets": contract.assets})
    dump_yaml(
        out / "provenance.yaml",
        {
            "contract_sha256": digest(contract_path),
            "sources": lineage["nodes"],
            "renderer_version": "2.0.0",
            "python": platform.python_version(),
            "generated_at": datetime.now(UTC).isoformat(),
            "profile_id": profile["profile_id"],
        },
    )
    return out


def schematic(graph_path: Path) -> Path:
    graph = graph_from(graph_path)
    validate_graph(graph)
    out = graph_path.parent / f"{graph.graph_id}.svg"
    positions = {
        n.id: (100 + 190 * (i % 4), 90 + 120 * (i // 4)) for i, n in enumerate(graph.nodes)
    }
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="350" viewBox="0 0 800 350"><defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0 0 L0 6 L8 3z"/></marker></defs>'
    ]
    for e in graph.edges:
        a, b = positions[e.source], positions[e.target]
        parts.append(
            f'<line x1="{a[0] + 65}" y1="{a[1]}" x2="{b[0] - 65}" y2="{b[1]}" stroke="black" marker-end="url(#a)"/><text x="{(a[0] + b[0]) / 2}" y="{(a[1] + b[1]) / 2 - 8}" font-size="10">{e.relation}</text>'
        )
    for n in graph.nodes:
        x, y = positions[n.id]
        parts.append(
            f'<rect x="{x - 65}" y="{y - 24}" width="130" height="48" rx="5" fill="white" stroke="black"/><text x="{x}" y="{y + 4}" text-anchor="middle" font-size="12">{n.label}</text>'
        )
    out.write_text("".join(parts) + "</svg>", encoding="utf-8")
    return out


def inspect(path: Path, contract: FigureContract | None = None) -> dict[str, Any]:
    checks = []
    add = lambda status, msg: checks.append({"status": status, "message": msg})
    if path.suffix == ".pdf":
        doc = fitz.open(path)
        page = doc[0]
        spans = [
            s
            for b in page.get_text("dict")["blocks"]
            if "lines" in b
            for l in b["lines"]
            for s in l["spans"]
        ]
        add("PASS" if doc.page_count == 1 else "FAIL", "PDF page count")
        add("PASS" if spans else "FAIL", "PDF text objects")
        add("PASS" if doc.get_page_fonts(0) else "WARN", "PDF fonts")
        add("PASS" if min((s["size"] for s in spans), default=0) >= 5 else "FAIL", "minimum font")
        if contract:
            width, height = page.rect.width * 25.4 / 72, page.rect.height * 25.4 / 72
            add(
                "PASS"
                if abs(width - contract.export.width_mm) < 0.5
                and abs(height - contract.export.height_mm) < 0.5
                else "FAIL",
                "physical page size",
            )
    if path.suffix == ".svg":
        try:
            root = etree.parse(str(path)).getroot()
        except etree.XMLSyntaxError:
            add("FAIL", "SVG parseability")
            root = None
        if root is not None:
            texts = root.xpath("//*[local-name()='text']")
            add("PASS" if texts else "FAIL", "SVG editable text")
            add(
                "FAIL"
                if any(
                    str(k).endswith("href") and str(v).startswith("http")
                    for e in root.iter()
                    for k, v in e.attrib.items()
                )
                else "PASS",
                "external SVG links",
            )
    if path.suffix.lower() in {".png", ".tif", ".tiff"}:
        with Image.open(path) as im:
            dpi = im.info.get("dpi", (0, 0))
            effective = im.width / (contract.export.width_mm / 25.4) if contract else min(dpi)
            add(
                "PASS" if effective >= (contract.export.dpi if contract else 300) else "FAIL",
                f"effective DPI {effective:.0f}",
            )
            add("PASS" if im.mode in {"RGB", "RGBA"} else "WARN", "raster color mode")
    if contract:
        add(
            "WARN" if not contract.accessibility.get("redundant_group_encoding") else "PASS",
            "non-color encoding",
        )
        add("PASS" if (path.parent / "provenance.yaml").is_file() else "FAIL", "provenance")
    overall = (
        "TECHNICAL_PASS"
        if all(c["status"] == "PASS" for c in checks)
        else "CONDITIONAL"
        if not any(c["status"] in {"FAIL", "BLOCKED"} for c in checks)
        else "INCOMPLETE"
    )
    return {
        "artifact": str(path),
        "checks": checks,
        "overall": overall,
        "manual_notice": "Automated checks do not certify editorial acceptance or scientific validity; re-check current journal instructions before upload.",
    }


def primary_integrity(original: Path, operations: list[dict[str, Any]]) -> dict[str, Any]:
    forbidden = {
        "healing",
        "clone",
        "content_aware",
        "object_removal",
        "generative_fill",
        "ai_denoising",
        "ai_super_resolution",
    }
    if not original.is_file():
        raise RfigError("missing primary image")
    if any(op.get("op") in forbidden for op in operations):
        raise BlockedError("protected primary image operation blocked")
    with Image.open(original) as im:
        size = [im.width, im.height]
    return {
        "original": {"path": str(original), "sha256": digest(original), "size_px": size},
        "operations": operations,
        "ai": {"used": False},
    }


def package(contract_path: Path, root: Path) -> Path:
    contract = contract_from(contract_path)
    out = contract_path.parent / contract.export.output_dir
    target = contract_path.parent / "submission" / contract.figure_id
    if not out.is_dir():
        raise RfigError("render before package")
    for folder in ["artwork", "source-data", "manifests", "audit", "source-code"]:
        (target / folder).mkdir(parents=True, exist_ok=True)
    for f in out.glob(f"{contract.figure_id}.*"):
        shutil.copy2(f, target / "artwork" / f.name)
    for s in contract.sources:
        shutil.copy2(contract_path.parent / s.path, target / "source-data" / Path(s.path).name)
    for name in ["provenance.yaml", "data-lineage.yaml", "ai-usage.yaml", "asset-manifest.yaml"]:
        shutil.copy2(out / name, target / "manifests" / name)
    if any(not a.get("publication_rights_verified", True) for a in contract.assets):
        raise RfigError("asset license evidence incomplete")
    report = inspect(out / f"{contract.figure_id}.pdf", contract)
    (target / "audit" / "preflight.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (target / "README.md").write_text(
        "Submission-oriented technical bundle; not a journal certification.\n", encoding="utf-8"
    )
    return target
