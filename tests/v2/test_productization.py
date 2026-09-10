from pathlib import Path

from typer.testing import CliRunner

from research_figures.cli import app
from research_figures.resources import ROOT, iter_bundled_skills, iter_profiles, resource_path


def test_packaged_resource_surface():
    assert list(iter_profiles())
    assert list(iter_bundled_skills())
    assert resource_path("schemas", "figure-contract.schema.json").is_file()
    assert ROOT.joinpath("templates", "project.toml").is_file()


def test_product_commands_are_discoverable(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ["--version"]).exit_code == 0
    assert runner.invoke(app, ["doctor", "--json"]).exit_code == 0
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["new", "Fig1", "--source", "data.csv"]).exit_code == 0
    result = runner.invoke(app, ["agent", "install", "--project", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / ".agents/skills/research-figure-install.json").is_file()
