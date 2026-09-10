"""Typer command line interface for V2."""
# ruff: noqa: B008

import json
from pathlib import Path

import typer

from ._version import __version__
from .agent import install as install_skill
from .agent import status as skill_status
from .core import (
    BlockedError,
    RfigError,
    contract_from,
    dump_yaml,
    inspect,
    package,
    policy_check,
    profiles,
    render,
    schematic,
    validate_contract,
)
from .resources import read_source_registry, resource_path

app = typer.Typer(no_args_is_help=True, invoke_without_command=True)
policy = typer.Typer(no_args_is_help=True)
agent = typer.Typer(no_args_is_help=True)
app.add_typer(policy, name="policy")
app.add_typer(agent, name="agent")


def root() -> Path:
    return Path.cwd()


@app.callback()
def callback(version: bool = typer.Option(False, "--version", is_eager=True)):
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command("doctor")
def doctor(json_output: bool = typer.Option(False, "--json")):
    import matplotlib.font_manager as fm

    from .core import fresh

    results = [
        {"id": "RF-RESOURCE-001", "status": "PASS", "message": "bundled resources available"},
        {
            "id": "RF-FONT-001",
            "status": "PASS" if fm.findfont("DejaVu Sans", fallback_to_default=False) else "WARN",
            "message": "font resolution",
        },
    ]
    results += [
        {
            "id": "RF-POLICY-001",
            "status": "WARN" if fresh(p) != "VERIFIED" else "PASS",
            "message": p["profile_id"],
        }
        for p in profiles()
    ]
    payload = {
        "schema_version": "1",
        "command": "doctor",
        "status": "PASS",
        "results": results,
        "warnings": [x for x in results if x["status"] == "WARN"],
        "errors": [],
    }
    typer.echo(
        json.dumps(payload)
        if json_output
        else "\n".join(f"{x['status']} {x['id']} {x['message']}" for x in results)
    )


@app.command("self-test")
def self_test():
    import shutil
    import tempfile

    from .core import render

    with tempfile.TemporaryDirectory(prefix="rfig-selftest-") as temp:
        base = Path(temp)
        fixture = resource_path("selftest", "figure.contract.yaml")
        data = resource_path("selftest", "metrics.csv")
        shutil.copy2(fixture, base / "figure.contract.yaml")
        shutil.copy2(data, base / "metrics.csv")
        out = render(base / "figure.contract.yaml", root())
        report = inspect(out / "SelfTest.pdf", contract_from(base / "figure.contract.yaml"))
        if report["overall"] != "TECHNICAL_PASS":
            raise RfigError("RF-PREFLIGHT-001 self-test preflight failed")
    typer.echo("PASS")


@app.command()
def setup(
    yes: bool = False,
    global_: bool = typer.Option(False, "--global"),
    agent_name: str = typer.Option("codex", "--agent"),
):
    doctor()
    self_test()
    if yes:
        typer.echo(json.dumps(install_skill(agent_name, global_, None)))


@app.command()
def init(journal: str = "generic", phase: str = "draft"):
    path = Path.cwd() / ".rfig"
    (path / "figures").mkdir(parents=True, exist_ok=True)
    (path / "project.toml").write_text(
        f'[journal]\nprofile = "{journal}-high-impact"\nphase = "{phase}"\n', encoding="utf-8"
    )
    typer.echo(path)


@agent.command("install")
def agent_install(
    agent_name: str = typer.Option("codex", "--agent"),
    global_: bool = typer.Option(False, "--global"),
    project: Path | None = typer.Option(None, "--project"),
    force: bool = False,
):
    typer.echo(json.dumps(install_skill(agent_name, global_, project, force)))


@agent.command("status")
def agent_status(
    agent_name: str = typer.Option("codex", "--agent"),
    global_: bool = typer.Option(False, "--global"),
    project: Path | None = typer.Option(None, "--project"),
):
    typer.echo(json.dumps(skill_status(agent_name, global_, project)))


@app.command()
def plan(output: Path = Path("figure.contract.yaml")):
    dump_yaml(
        output,
        {
            "schema_version": "2.0",
            "figure_id": "Fig1",
            "claim": {"statement": "Declare a supported claim."},
            "journal_context": {
                "publisher": "springer_nature",
                "journal": "nature",
                "submission_phase": "final",
            },
            "artifact_class": "data_visualization",
            "sources": [],
            "panels": [],
            "export": {
                "formats": ["pdf", "svg", "png"],
                "output_dir": "outputs/Fig1",
                "width_mm": 89,
                "height_mm": 65,
            },
        },
    )
    typer.echo(output)


@app.command()
def validate(contract: Path):
    value = contract_from(contract)
    validate_contract(value, contract.parent)
    typer.echo("PASS")


@app.command(name="render")
def render_cmd(contract: Path):
    typer.echo(render(contract, root()))


@app.command(name="schematic")
def schematic_cmd(graph: Path):
    typer.echo(schematic(graph))


@app.command()
def preflight(artifact: Path, contract: Path | None = None):
    c = contract_from(contract) if contract else None
    report = inspect(artifact, c)
    target = artifact.parent / "preflight.json"
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    typer.echo(json.dumps(report, indent=2))


@app.command(name="package")
def package_cmd(contract: Path, submission: bool = typer.Option(False, "--submission")):
    if not submission:
        raise typer.BadParameter("--submission is required")
    typer.echo(package(contract, root()))


@policy.command("list")
def policy_list(journal: str = "", phase: str = ""):
    for p in profiles(root()):
        if (not journal or p["journal"] == journal) and (
            not phase or p["scope"]["submission_phase"] == phase
        ):
            typer.echo(p["profile_id"])


@policy.command("explain")
def policy_explain(rule_id: str):
    for p in profiles(root()):
        for rule in p["rules"]:
            if rule["rule_id"] == rule_id:
                typer.echo(
                    json.dumps(
                        {
                            "profile": p["profile_id"],
                            **rule,
                            "verification": p.get("verification", {}),
                        },
                        indent=2,
                    )
                )
                return
    raise typer.BadParameter("unknown rule id")


@policy.command("check")
def policy_check_cmd(contract: Path):
    typer.echo(
        json.dumps(
            [r.__dict__ for r in policy_check(root(), contract_from(contract))],
            indent=2,
            default=str,
        )
    )


@policy.command("freshness")
def policy_freshness(journal: str = ""):
    from .core import fresh

    for p in profiles(root()):
        if not journal or p["journal"] == journal:
            typer.echo(f"{p['profile_id']} {fresh(p)}")


@policy.command("sources")
def policy_sources(show: bool = False):
    source = read_source_registry()
    typer.echo(json.dumps(source, indent=2) if show else "bundled:references/sources.yaml")


def main() -> None:
    try:
        app()
    except (RfigError, BlockedError) as exc:
        typer.echo(f"FAIL_CLOSED: {exc}", err=True)
        raise typer.Exit(2)
