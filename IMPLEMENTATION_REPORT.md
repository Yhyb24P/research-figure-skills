# Research Figure Skills v2.1 Implementation Report

## Status

`IMPLEMENTATION_COMPLETE` for the repository changes and the tested Linux x64 distribution path.
This is **not** `RELEASE_CANDIDATE` or `PUBLIC_RELEASE_READY`: PyPI/npm Trusted Publishing ownership
and registry-side configuration have not been independently confirmed. Those are explicit release
blockers, not inferred completions.

## Product changes

- Runtime profiles, source registry, schemas, bundled Skills, templates, and synthetic self-test
  fixtures are installed package resources accessed through `importlib.resources`.
- The Python wheel exposes `rfig` and `research-figure`; resource smoke works outside the checkout.
- The CLI now provides product commands: `setup`, `doctor`, `self-test`, `init`, `new`, `run`,
  `submit`, `config path/show/set`, completion, and agent detect/install/list/status/uninstall.
- Canonical bundled Skills live in `src/research_figures/resources/skills`; `sync_skills.py`
  synchronizes/checks GitHub-visible `skills/` copies.
- Linux x64 uses a PyApp 0.29.0 launcher with an embedded, locally built 2.1.0rc1 wheel and
  CPython 3.12 managed at first launch. npm is a thin dispatcher only; it has no self-update path.
- `release.toml` centralizes Python/npm/tag version mapping. The release dry-run generates
  checksums, SPDX-shaped dependency inventory, release manifest, wheel/sdist, native launcher,
  and npm tarballs.

## Commands actually executed

```text
uv run ruff check .
uv run pytest -q                         # 12 passed
uv build --no-sources
uv run python scripts/test_wheel.py
uv tool install <built wheel>             # isolated tool install
rfig self-test
rfig agent install/status/uninstall --agent codex --project <tmp>
uv run python scripts/check_case_collisions.py
uv run python scripts/check_versions.py
uv run python scripts/sync_skills.py --check
uv run python scripts/build_native.py --platform linux-x64
<native rfig> --version
<native rfig> doctor --json
<native rfig> self-test
npm pack (wrapper and linux-x64 platform package)
npm install <both tarballs> in a clean temporary directory
<npm-installed rfig> --version / doctor --json / self-test
uv run python scripts/release_dry_run.py
```

## Gate matrix

| Gate | Evidence | Status |
|---|---|---|
| P0 source-tree independence | Built wheel clean-installed outside checkout; `policy list`, doctor JSON, self-test passed. | PASS |
| P1 resource completeness | Wheel inspection includes profiles, schemas, references, Skills, templates and self-test fixtures. | PASS |
| P2 cross-platform path safety | [CI run 34549372343](https://github.com/Yhyb24P/research-figure-skills/actions/runs/34549372343) passed case-collision checks and wheel clean-install smoke on Linux, Windows and macOS for Python 3.11/3.12. | PASS |
| P3 npm wrapper | Packed wrapper + Linux x64 platform tarball clean-install forwards to native launcher. | PASS (Linux x64) |
| P4 no-Python consumer | Source-tree-external PyApp launch with `PYTHONPATH`/`VIRTUAL_ENV` unset bootstrapped managed CPython 3.12 and ran all smoke commands. | PASS (Linux x64) |
| P5 Python-native path | `uv tool install` of the built wheel followed by self-test passed. | PASS |
| P6 Agent installation | Wheel-installed CLI copied bundled Codex Skills, recorded hashes, reported status, and uninstalled safely. | PASS |
| P7 Skills CLI compatibility | Public root Skills are synced from canonical bundled Skills; `sync_skills.py --check` passes. | PASS |
| P8 first-run UX | `rfig setup --yes --agent codex`, config subcommands and completion smoke passed in a temporary directory. | PASS |
| P9 doctor | JSON doctor validates packaged resources, writable output, fonts, profile freshness and malformed local Skill manifests. | PASS |
| P10 machine contract | JSON envelopes parse in smoke tests; documented stable exit-code mapping is implemented. | PASS |
| P11 scientific regression | Existing V2 integrity/no-fabrication regression suite remains green (12 tests total). | PASS |
| P12 release build | wheel/sdist, Linux native launcher, npm tarballs, checksums, SBOM inventory and manifest generated locally. | PASS (Linux x64) |
| P13 supply chain | [Release dry-run 34549653211](https://github.com/Yhyb24P/research-figure-skills/actions/runs/34549653211) generated wheel/sdist/native/npm artifacts, uploaded them, and completed `attest-build-provenance`. REST attestation lookup found one attestation for each downloaded npm tgz SHA-256. | PASS (remote, publish=false) |
| P14 public metadata | README, changelog, security, contributing, citation metadata and Apache-2.0 LICENSE exist. PyPI/npm OIDC ownership setup remains external. | PENDING_OWNER_CONFIGURATION |
| P15 release dry-run | [Release dry-run 34549653211](https://github.com/Yhyb24P/research-figure-skills/actions/runs/34549653211) passed remotely with `publish=false`, including generated npm tgz validation, external npm installation, launcher smoke, artifact upload and provenance attestation. | PASS (remote, publish=false) |

## Linux launcher evidence

`dist/native/linux-x64/launcher-manifest.json` records release version, CPython 3.12 distribution,
wheel filename/SHA-256, build commit/platform, PyApp version, entry point, and the required
`PYAPP_PROJECT_PATH` embedded-local-wheel source. The launcher uses
`research_figures.cli:main`, never resolves the project package from a registry, and may fetch
only CPython runtime and third-party dependencies on first execution.

## Owner actions required before public release

1. Confirm the PyPI distribution and `@yhyb24p` npm scope/package ownership.
2. Configure PyPI/npm Trusted Publishing and protected release environments.

## P13 npm artifact evidence

The remote dry-run generated both package archives in `dist/npm/`, rather than relying on
`npm pack --dry-run` or any local cache. `scripts/package_npm.py` packs the Linux platform
workspace first and the wrapper workspace second with `--pack-destination dist/npm --json`.
`scripts/release_dry_run.py` requires the directory and both non-empty files, reads each embedded
`package/package.json` to verify name/version, and performs a source-tree-external
`npm install <platform.tgz> <wrapper.tgz>` followed by `rfig --version`, `doctor --json`, and
`self-test` with `PYTHONPATH` and `VIRTUAL_ENV` absent.

Remote artifact SHA-256 values from run 34549653211:

- `yhyb24p-research-figure-linux-x64-2.1.0-rc.1.tgz` —
  `1714d34726323911dd55012205cdb4b2e690a7630649d4d590d0a26e5fac5e65`
- `yhyb24p-research-figure-2.1.0-rc.1.tgz` —
  `599b69a145446915f1555d2f2f823571bc739bfe1440260e90f35969e83b6e20`

Both digests returned one GitHub repository attestation through the REST attestations endpoint.
The pack summaries identify `@yhyb24p/research-figure-linux-x64@2.1.0-rc.1` and
`@yhyb24p/research-figure@2.1.0-rc.1`; each has four intended package files. Version validation
maps the distinct release spellings explicitly: Python `2.1.0rc1` → npm `2.1.0-rc.1` → Git tag
`v2.1.0-rc.1`, rather than requiring the Python and npm strings to be identical.

## Scientific and policy limitations

Nature is a dated verified snapshot. Science and Cell snapshots are provisional. No technical
preflight certifies scientific validity, asset rights, causality, statistics, or editorial
acceptance; current publisher instructions must be reviewed before submission.
