#!/usr/bin/env bash
set -euo pipefail

review="specs/001-user-auth/dependency-licenses.md"
backend="apps/api/pyproject.toml"
frontend="apps/web/package.json"
lockfile="apps/api/requirements.lock"

for required_file in "$review" "$backend" "$frontend" "$lockfile"; do
  test -f "$required_file" || { echo "Missing dependency evidence: $required_file" >&2; exit 1; }
done

for parser_pin in \
  "pypdf==6.14.2" \
  "python-docx==1.2.0" \
  "python-multipart==0.0.32" \
  "lxml==6.1.1"; do
  grep -Fxq "$parser_pin" "$lockfile" || {
    echo "Reviewed parser dependency is not pinned in the backend lock: $parser_pin" >&2
    exit 1
  }
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
