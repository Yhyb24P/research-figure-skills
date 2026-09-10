# Research Figure Skills V2 Implementation Report

## Status

COMPLETE

## Implemented

The V2 package is under `src/research_figures`: typed Pydantic contracts, source hashing and lineage, scoped profile resolution, AI policy routing, deterministic Matplotlib PDF/SVG/PNG rendering, deterministic SVG schematics, primary-image operation manifests, artifact preflight and submission packaging. Eight routing Skills, six dated target profiles, source register, JSON Schemas, examples, CI, and owned synthetic tests are included.

## Commands

`uv sync --all-groups`; `uv run rfig --help`; `uv run pytest -q` (10 passed); `uv run ruff check src tests/v2`; V2 render/schematic/preflight/policy/package commands.

## Profile verification state

Nature profile is a dated verified snapshot. Science and Cell technical snapshots are marked `PROVISIONAL`; current official instructions must be rechecked before submission. No report claims certification or editorial acceptance.

## Manual checks

Scientific validity, causality, statistics appropriateness, asset rights, image-history completeness, and live publisher instructions require human review.

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
