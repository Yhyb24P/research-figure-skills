# Research Figure Skills V2.1 Implementation Report

## Status

PRODUCTIZATION IN PROGRESS — P4/P12 Linux x64 implementation is complete and
verified below. This repository is **not** marked `RELEASE_CANDIDATE` or
`PUBLIC_RELEASE_READY`: the remaining P0–P15 product gates are intentionally
outside this focused launcher closeout.

## Implemented

The V2 package is under `src/research_figures`: typed Pydantic contracts, source hashing and lineage, scoped profile resolution, AI policy routing, deterministic Matplotlib PDF/SVG/PNG rendering, deterministic SVG schematics, primary-image operation manifests, artifact preflight and submission packaging. Eight routing Skills, six dated target profiles, source register, JSON Schemas, examples, CI, and owned synthetic tests are included.

## Commands

`uv sync --all-groups`; `uv run rfig --help`; `uv run pytest -q` (10 passed); `uv run ruff check src tests/v2`; V2 render/schematic/preflight/policy/package commands.

## Profile verification state

Nature profile is a dated verified snapshot. Science and Cell technical snapshots are marked `PROVISIONAL`; current official instructions must be rechecked before submission. No report claims certification or editorial acceptance.

## Manual checks

Scientific validity, causality, statistics appropriateness, asset rights, image-history completeness, and live publisher instructions require human review.

## P4/P12 embedded-project launcher evidence (Linux x64)

The native launcher is PyApp 0.29.0 compiled with these build-time settings:

| Requirement | Implemented value | Evidence |
|---|---|---|
| P4-A no-system-Python bootstrap | PyApp-managed CPython 3.12 | A source-tree-external run with `PYTHONPATH` and `VIRTUAL_ENV` unset bootstrapped `/tmp/.../data/pyapp/.../bin/python3` (Python 3.12). |
| P4-B embedded project wheel | `PYAPP_PROJECT_PATH=dist/research_figure_skills-2.1.0rc1-py3-none-any.whl` | PyApp embeds this exact release wheel and installs it from a temporary embedded archive; it does not resolve `research-figure-skills` from a registry. |
| Entry point | `PYAPP_EXEC_SPEC=research_figures.cli:main` | Native `rfig --version` emitted `2.1.0rc1`. |
| Native smoke | `--version`, `doctor --json`, `self-test` | All three exited successfully outside the source tree; doctor returned JSON `status: PASS` and self-test emitted `PASS`. |
| Launcher manifest | `dist/native/linux-x64/launcher-manifest.json` | Contains release version, CPython distribution, wheel filename/SHA-256, git commit, build platform, PyApp version, embedded source mode, and entry point. |
| P12 npm platform | `@yhyb24p/research-figure-linux-x64@2.1.0-rc.1` | Created only after native smoke and carries the real `rfig` binary plus its manifest. |
| P12 npm E2E | wrapper → platform tarball → native launcher → Python core | A clean temporary npm install of both packed tarballs ran `rfig --version`, `doctor --json`, and `self-test` successfully with `PYTHONPATH`/`VIRTUAL_ENV` unset. |

The npm wrapper is intentionally only a dispatcher. It contains no PyApp
self-update path; npm package versioning remains the update authority.

## Gate matrix

| Gate | Evidence | Status |
|---|---|---|
| A | installable `src` package, CLI, Skills, schemas, profiles, docs | PASS |
| B | Pydantic contract models and strict unknown-field tests | PASS |
| C | missing uncertainty/significance/missing-data fail-closed tests | PASS |
| D | SHA-256 `data-lineage.yaml` emitted and asserted | PASS |
| E | scoped profile selection, explanation, freshness tests | PASS |
| F | Nature and protected-image blocking plus Elsevier deterministic route tests | PASS |
| G | rendered PDF/SVG/PNG and physical-size inspection | PASS |
| H | PDF font/text and SVG editable-text checks | PASS |
| I | small-DPI, bad SVG link and page-size preflight tests | PASS |
| J | semantic-edge evidence validation and deterministic SVG test | PASS |
| K | original image hash / allowed-operation log / blocked AI edit test | PASS |
| L | redundant encoding check and non-certification language | PASS |
| M | manifests and submission bundle test | PASS |
| N | `uv run pytest -q` and CI workflow | PASS |
