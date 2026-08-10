#!/usr/bin/env python3
"""Enforce statement, branch, line, and function execution from coverage.py JSON."""

from __future__ import annotations

import ast
import json
from pathlib import Path


def main() -> None:
    report_path = Path(".coverage-backend.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    totals = report["totals"]
    if totals["percent_covered"] != 100 or totals["num_partial_branches"] != 0:
        raise SystemExit("Backend line/statement/branch coverage is below 100%")

    missing_functions: list[str] = []
    for filename, details in report["files"].items():
        source_path = Path(filename)
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=filename)
        executed = set(details["executed_lines"])
        protocol_declarations = {
            method.lineno
            for item in tree.body
            if isinstance(item, ast.ClassDef)
            and any(isinstance(base, ast.Name) and base.id == "Protocol" for base in item.bases)
            for method in item.body
            if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.lineno not in executed
                and node.lineno not in protocol_declarations
            ):
                missing_functions.append(f"{filename}:{node.lineno}:{node.name}")

    if missing_functions:
        raise SystemExit("Unexecuted backend functions:\n" + "\n".join(missing_functions))

    print("Backend lines, branches, functions, and statements meet 100%.")


if __name__ == "__main__":
    main()
