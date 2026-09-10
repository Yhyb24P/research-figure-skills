# Research Figure

Evidence-constrained, journal-aware scientific figure compiler and technical auditor.
It renders locally, does not upload research data by default, has no telemetry by default, and
does not claim publisher endorsement or editorial acceptance.

## Install

The consumer front door is npm (Linux x64 is the currently tested native platform):

```bash
npm install -g @yhyb24p/research-figure
rfig setup
```

Python-native users can install the canonical package directly:

```bash
uv tool install research-figure-skills
rfig doctor
```

The package name and registry publishing setup are pending owner confirmation. Until publication,
build local tarballs/wheels with the documented release checks.

## 30-second start

```bash
rfig setup --yes --agent codex
mkdir my-research && cd my-research
rfig init
rfig new Fig1 --type data --source results/metrics.csv
```

`rfig new` makes an intentionally incomplete draft. Complete an evidence-backed contract before
using `rfig run Fig1`; the renderer refuses missing sources, statistics, transformations and
unsupported claims.

## Safety boundary

Research Figure preserves data lineage, requires explicit uncertainty and transformation
contracts, blocks forbidden primary-image operations, and records policy profiles in provenance.
Nature profiles are dated snapshots; Science and Cell profiles are provisional. Technical passes
never replace scientific, rights, or current-journal-instruction review.

## Skills

Install bundled Codex Skills without copying a repository checkout:

```bash
rfig agent install --agent codex --project .
rfig agent status --agent codex --project .
```

The repository-facing `skills/` directory remains compatible with `npx skills add
Yhyb24P/research-figure-skills --all`.

## Development

Developer setup and all release verification commands are in [CONTRIBUTING.md](CONTRIBUTING.md).
See [IMPLEMENTATION_REPORT.md](IMPLEMENTATION_REPORT.md) for tested platforms and release status.

Exit codes are stable: `0` success, `2` invalid contract/input, `3` policy blocked, `4` artifact
preflight failure, `5` runtime environment failure, and `6` unexpected internal failure.
