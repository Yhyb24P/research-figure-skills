from pathlib import Path

import pytest

from research_figures.core import (
    BlockedError,
    RfigError,
    contract_from,
    digest,
    graph_from,
    inspect,
    package,
    policy_check,
    primary_integrity,
    render,
    resolve_profile,
    schematic,
    validate_contract,
    validate_graph,
)

ROOT = Path(__file__).resolve().parents[2]
EX = ROOT / "examples/v2"


def contract():
    return contract_from(EX / "figure.contract.yaml")


def test_contract_and_lineage():
    c = contract()
    validate_contract(c, EX)
    out = render(EX / "figure.contract.yaml", ROOT)
    lineage = __import__("yaml").safe_load((out / "data-lineage.yaml").read_text())
    assert lineage["nodes"][0]["sha256"] == digest(EX / "metrics.csv")


def test_no_fabrication_and_missing_data():
    c = contract()
    c.panels[0].plot.uncertainty = "invented"
    with pytest.raises(RfigError, match="missing-statistical"):
        validate_contract(c, EX)
    c = contract()
    c.panels[0].plot.significance = "stars"
    with pytest.raises(RfigError):
        validate_contract(c, EX)


def test_policy_and_profile_isolation():
    c = contract()
    results = policy_check(ROOT, c)
    assert any(r.rule_id == "NATURE-MAIN-WIDTH-001" and r.status == "PASS" for r in results)
    c.journal_context.publisher = "elsevier"
    c.journal_context.journal = "cell"
    assert resolve_profile(ROOT, c.journal_context)["profile_id"].startswith("cell.press")


def test_ai_blocks_and_elsevier_allows_deterministic():
    c = contract()
    c.ai_usage = [{"capability": "generative_image"}]
    assert any(r.status == "BLOCKED" for r in policy_check(ROOT, c))
    c.journal_context.publisher = "elsevier"
    c.journal_context.journal = "cell"
    c.ai_usage = [{"capability": "deterministic_plot"}]
    assert not any(r.status == "BLOCKED" for r in policy_check(ROOT, c))


def test_render_and_preflight():
    out = render(EX / "figure.contract.yaml", ROOT)
    assert all((out / f"Fig1.{x}").is_file() for x in ["pdf", "svg", "png"])
    report = inspect(out / "Fig1.pdf", contract())
    assert report["overall"] == "TECHNICAL_PASS"


def test_schematic_and_edge_evidence():
    graph = graph_from(EX / "semantic-graph.yaml")
    validate_graph(graph)
    assert schematic(EX / "semantic-graph.yaml").is_file()
    graph.edges[0].evidence = []
    with pytest.raises(RfigError):
        validate_graph(graph)


def test_primary_integrity_blocks(tmp_path):
    from PIL import Image

    raw = tmp_path / "raw.png"
    Image.new("RGB", (20, 20)).save(raw)
    assert primary_integrity(raw, [{"op": "crop", "bounds_px": [0, 0, 10, 10]}])["original"][
        "sha256"
    ] == digest(raw)
    with pytest.raises(BlockedError):
        primary_integrity(raw, [{"op": "generative_fill"}])


def test_package():
    render(EX / "figure.contract.yaml", ROOT)
    target = package(EX / "figure.contract.yaml", ROOT)
    assert (target / "manifests/provenance.yaml").is_file() and (
        target / "artwork/Fig1.pdf"
    ).is_file()


def test_preflight_bad_fixtures(tmp_path):
    from PIL import Image

    c = contract()
    bad = tmp_path / "bad.png"
    Image.new("RGB", (20, 20)).save(bad, dpi=(600, 600))
    assert inspect(bad, c)["overall"] == "INCOMPLETE"
    svg = tmp_path / "bad.svg"
    svg.write_text('<svg><image href="https://bad.invalid/x.png"/></svg>')
    assert any(x["status"] == "FAIL" for x in inspect(svg, c)["checks"])


def test_missing_values_and_stale_policy(tmp_path):
    c = contract()
    csv = tmp_path / "x.csv"
    csv.write_text("environment,pcc\nE1,\n")
    c.sources[0].path = str(csv)
    c.export.output_dir = "out"
    contract_path = tmp_path / "c.yaml"
    __import__("yaml").safe_dump(c.model_dump(mode="json"), contract_path.open("w"))
    with pytest.raises(RfigError, match="missing values"):
        render(contract_path, ROOT)
    profile = resolve_profile(ROOT, contract().journal_context)
    profile["verification"]["last_verified"] = "2000-01-01"
    from research_figures.core import fresh, policy_decision

    assert (
        fresh(profile) == "STALE"
        and policy_decision(profile, "data_visualization", "generative_image") == "BLOCKED"
    )
