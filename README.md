# Research Figure Skills V2

An offline, evidence-constrained figure compiler: typed contracts, dated Nature/Science/Cell-aware policy profiles, deterministic rendering, primary-image integrity manifests, artifact preflight, and submission bundles. It is not publisher-endorsed and never guarantees editorial acceptance.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Or run `pip install -r requirements.txt`.

## Examples

```bash
uv sync --all-groups
uv run rfig validate examples/v2/figure.contract.yaml
uv run rfig render examples/v2/figure.contract.yaml
uv run rfig schematic examples/v2/semantic-graph.yaml
uv run rfig preflight examples/v2/outputs/Fig1/Fig1.pdf --contract examples/v2/figure.contract.yaml
uv run rfig package examples/v2/figure.contract.yaml --submission
uv run pytest -q
```

`examples/sensitivity/data.csv` is a **synthetic test fixture, not scientific evidence**. Replace it with traceable source data and a claim-specific figure contract for research use.

## Skills

Project-local installation is preferred: copy this repository's `nature-figure/`, `scientific-schematic/`, and `figure-preflight/` folders into `.agents/skills/`. A user-level installation may use `~/.codex/skills/`; paths vary across platforms.

The V2 skills under `skills/` route to the deterministic CLI: data figures, schematics, structures, primary images, graphical abstracts, profiles, and preflight. Renderers never infer statistics, groups, missing-data handling, smoothing, interpolation, mechanisms, or causal relations. Primary image generative editing is blocked.

Profiles are curated dated snapshots with rule-level source IDs. Run `rfig policy list`, `rfig policy explain RULE_ID`, `rfig policy check CONTRACT`, and `rfig policy freshness`; re-check target-journal instructions before submission.
