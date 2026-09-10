test:
	uv run pytest -q

test-wheel:
	uv build --no-sources

test-npm:
	npm test --workspace @yhyb24p/research-figure

release-check:
	uv run python scripts/check_versions.py
	uv run python scripts/check_case_collisions.py
	uv run python scripts/sync_skills.py --check
	uv run python scripts/release_dry_run.py
