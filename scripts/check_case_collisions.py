import subprocess
import sys

paths = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
seen = {}
bad = []
for path in paths:
    key = path.casefold()
    if key in seen:
        bad.append((seen[key], path))
    seen[key] = path
if bad:
    print("case collisions:", bad)
    sys.exit(1)
print("PASS case collision check")
