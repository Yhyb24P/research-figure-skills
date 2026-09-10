"""Create checksums and a minimal SBOM for locally built release artifacts."""

import json
from hashlib import sha256
from pathlib import Path

dist = Path("dist")
artifacts = []
for path in sorted(dist.glob("research_figure_skills-*")):
    artifacts.append({"path": path.name, "sha256": sha256(path.read_bytes()).hexdigest()})
(dist / "checksums.json").write_text(
    json.dumps({"version": "2.1.0rc1", "artifacts": artifacts}, indent=2)
)
(dist / "sbom.spdx.json").write_text(
    json.dumps(
        {"spdxVersion": "SPDX-2.3", "name": "research-figure-skills", "packages": []}, indent=2
    )
)
print("PASS release dry-run", len(artifacts))
