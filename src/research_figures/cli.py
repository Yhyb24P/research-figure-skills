"""Typer command line interface for V2."""
# ruff: noqa: B008

import json
import os
import shutil
import tempfile
from pathlib import Path

import typer

from ._version import __version__
from .agent import install as install_skill
from .agent import status as skill_status
from .agent import uninstall as uninstall_skill
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
from .resources import ROOT as RESOURCE_ROOT
from .resources import read_source_registry, resource_path

app = typer.Typer(no_args_is_help=True, invoke_without_command=True)
policy = typer.Typer(no_args_is_help=True)
agent = typer.Typer(no_args_is_help=True)
config_app = typer.Typer(no_args_is_help=True)
app.add_typer(policy, name="policy")
app.add_typer(agent, name="agent")
app.add_typer(config_app, name="config")


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

    resources_ok = all(
        RESOURCE_ROOT.joinpath(kind).is_dir()
        for kind in ("profiles", "schemas", "references", "skills", "selftest", "templates")
    )
    output_ok = os.access(Path.cwd(), os.W_OK)
    skill_manifest = Path.cwd() / ".agents" / "skills" / "research-figure-install.json"
    try:
        if skill_manifest.is_file():
            json.loads(skill_manifest.read_text(encoding="utf-8"))
        skill_status_value = "PASS"
    except json.JSONDecodeError:
        skill_status_value = "FAIL"
    results = [
        {
            "id": "RF-RESOURCE-001",
            "status": "PASS" if resources_ok else "FAIL",
            "message": "bundled resources available" if resources_ok else "bundled resources incomplete",
        },
        {
            "id": "RF-INSTALL-001",
            "status": "PASS" if output_ok else "FAIL",
            "message": "current output directory is writable" if output_ok else "current output directory is not writable",
        },
        {
            "id": "RF-INSTALL-001",
            "status": skill_status_value,
            "message": "agent Skill manifest valid" if skill_status_value == "PASS" else "agent Skill manifest is invalid",
        },
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
        "status": "FAIL" if any(x["status"] == "FAIL" for x in results) else "PASS",
        "results": results,
        "warnings": [x for x in results if x["status"] == "WARN"],
        "errors": [x for x in results if x["status"] == "FAIL"],
    }
    typer.echo(
        json.dumps(payload)
        if json_output
        else "\n".join(f"{x['status']} {x['id']} {x['message']}" for x in results)
    )


@app.command("self-test")
def self_test():
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
    profile = "generic.high_impact.v2026-09-11" if journal == "generic" else journal
    template = resource_path("templates", "project.toml").read_text(encoding="utf-8")
    (path / "project.toml").write_text(
        template.replace("generic.high_impact.v2026-09-11", profile).replace(
            'phase = "draft"', f'phase = "{phase}"'
        ),
        encoding="utf-8",
    )
    typer.echo(path)


@app.command()
def new(
    figure_id: str,
    type_: str = typer.Option("data", "--type"),
    source: str = typer.Option("", "--source"),
):
    """Create a deliberately incomplete, non-renderable contract draft."""
    target = Path.cwd() / ".rfig" / "figures" / f"{figure_id}.yaml"
    dump_yaml(
        target,
        {
            "schema_version": "2.0",
            "figure_id": figure_id,
            "draft": {
                "type": type_,
                "source": source,
                "todo": "Complete an evidence-backed contract before rendering.",
            },
        },
    )
    typer.echo(target)


def _project_contract(figure_id: str) -> Path:
    candidate = Path.cwd() / ".rfig" / "figures" / f"{figure_id}.yaml"
    if not candidate.is_file():
        raise typer.BadParameter(f"RF-CONTRACT-001 missing project figure: {figure_id}")
    return candidate


@app.command()
def run(figure_id: str, json_output: bool = typer.Option(False, "--json")):
    """Validate, policy-check, render and preflight one project contract."""
    contract_path = _project_contract(figure_id)
    contract = contract_from(contract_path)
    validate_contract(contract, contract_path.parent)
    decisions = policy_check(root(), contract)
    if any(decision.status in {"FAIL", "BLOCKED"} for decision in decisions):
        raise BlockedError("RF-POLICY-001 policy gate blocked figure")
    output = render(contract_path, root())
    report = inspect(output / f"{contract.figure_id}.pdf", contract)
    if report["overall"] != "TECHNICAL_PASS":
        raise RfigError("RF-PREFLIGHT-001 render preflight failed")
    payload = {"schema_version": "1", "command": "run", "status": "PASS", "output": str(output)}
    typer.echo(json.dumps(payload) if json_output else output)


@app.command()
def submit(figure_id: str, json_output: bool = typer.Option(False, "--json")):
    """Create a submission bundle only after technical and policy gates pass."""
    contract_path = _project_contract(figure_id)
    contract = contract_from(contract_path)
    decisions = policy_check(root(), contract)
    if any(decision.status in {"FAIL", "BLOCKED"} for decision in decisions):
        raise BlockedError("RF-POLICY-001 submission blocked")
    target = package(contract_path, root())
    payload = {
        "schema_version": "1",
        "command": "submit",
        "status": "CONDITIONAL",
        "output": str(target),
        "manual_notice": "Scientific and editorial review remain required.",
    }
    typer.echo(json.dumps(payload) if json_output else target)


@app.command()
def completion(shell: str):
    """Emit shell completion for bash, zsh, fish or powershell."""
    if shell not in {"bash", "zsh", "fish", "powershell"}:
        raise typer.BadParameter("shell must be bash, zsh, fish or powershell")
    typer.echo(f"# Use `rfig --install-completion {shell}` to install completion.")


def _config_path() -> Path:
    from platformdirs import user_config_dir

    return Path(user_config_dir("research-figure")) / "config.json"


def _config() -> dict:
    path = _config_path()
    data = (
        json.loads(path.read_text())
        if path.is_file()
        else {"network_policy": "off", "update_check": False}
    )
    return data


@config_app.command("path")
def config_path(json_output: bool = typer.Option(False, "--json")):
    path = _config_path()
    typer.echo(json.dumps({"path": str(path)}) if json_output else path)


@config_app.command("show")
def config_show(json_output: bool = typer.Option(False, "--json")):
    data = _config()
    typer.echo(json.dumps(data) if json_output else json.dumps(data, indent=2))


@config_app.command("set")
def config_set(key: str, value: str, json_output: bool = typer.Option(False, "--json")):
    path = _config_path()
    data = _config()
    path.parent.mkdir(parents=True, exist_ok=True)
    data[key] = value
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    typer.echo(json.dumps(data) if json_output else json.dumps(data, indent=2))


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


@agent.command("detect")
def agent_detect():
    typer.echo(
        json.dumps(
            {
                "supported": ["codex"],
                "detected": ["codex"] if (Path.home() / ".codex").exists() else [],
            }
        )
    )


@agent.command("list")
def agent_list():
    typer.echo("codex")


@agent.command("uninstall")
def agent_uninstall(
    agent_name: str = typer.Option("codex", "--agent"),
    global_: bool = typer.Option(False, "--global"),
    project: Path | None = typer.Option(None, "--project"),
):
    typer.echo(json.dumps(uninstall_skill(agent_name, global_, project)))


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
    except BlockedError as exc:
        typer.echo(f"FAIL_CLOSED: {exc}", err=True)
        raise typer.Exit(3)
    except RfigError as exc:
        typer.echo(f"FAIL_CLOSED: {exc}", err=True)
        raise typer.Exit(4 if str(exc).startswith("RF-PREFLIGHT-") else 2)
