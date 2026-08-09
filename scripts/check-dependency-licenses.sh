#!/usr/bin/env bash
set -euo pipefail

review="specs/001-user-auth/dependency-licenses.md"
backend="apps/api/pyproject.toml"
frontend="apps/web/package.json"

for required_file in "$review" "$backend" "$frontend"; do
  test -f "$required_file" || { echo "Missing dependency evidence: $required_file" >&2; exit 1; }
done

mapfile -t dependencies < <(
  python3 -c 'import tomllib; p=tomllib.load(open("apps/api/pyproject.toml", "rb")); values=p["build-system"]["requires"]+p["project"]["dependencies"]+sum(p["project"]["optional-dependencies"].values(), []); print("\n".join(v.split("[")[0].split("=")[0].lower() for v in values))'
  node -e 'const p=require("./apps/web/package.json"); console.log(Object.keys({...p.dependencies,...p.devDependencies}).join("\n"))'
)

for dependency in "${dependencies[@]}"; do
  grep -Fq "| ${dependency} |" "$review" || {
    echo "Dependency lacks reviewed SPDX evidence: $dependency" >&2
    exit 1
  }
done

if grep -Eq '"(latest|next|\*)"|==[[:space:]]*$' "$backend" "$frontend"; then
  echo "Dependency manifests contain an unpinned version" >&2
  exit 1
fi

echo "Dependency license review passed for ${#dependencies[@]} direct dependencies."
