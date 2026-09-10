"""Typer command line interface for V2."""

import json
from pathlib import Path

import typer

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

app = typer.Typer(no_args_is_help=True)
policy = typer.Typer(no_args_is_help=True)
app.add_typer(policy, name="policy")


def root() -> Path:
    return Path(__file__).resolve().parents[2]


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
    path = root() / "references" / "sources.yaml"
    typer.echo(path.read_text(encoding="utf-8") if show else str(path))


def main() -> None:
    try:
        app()
    except (RfigError, BlockedError) as exc:
        typer.echo(f"FAIL_CLOSED: {exc}", err=True)
        raise typer.Exit(2)
