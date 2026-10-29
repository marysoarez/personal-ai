#!/usr/bin/env python3
"""Deterministic, offline evaluations of toolkit rules and harness behavior."""
from __future__ import annotations

import argparse
import json
import hashlib
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from toolkit.scripts import ai_toolkit as core


def evaluate(case: dict) -> dict:
    kind = case.get("kind")
    content = case.get("input", "")
    evidence = []
    if kind == "spec":
        observed = core.validate_spec(Path("<eval>"), content)["status"]
        evidence = core.validate_spec(Path("<eval>"), content)["errors"]
    elif kind == "architecture-rules":
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ai-toolkit.json").write_text(json.dumps(case["rules"]), encoding="utf-8")
            for rel, body in case.get("fixture_files", {}).items():
                target = root / rel; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(body, encoding="utf-8")
            architecture = core.architecture_check(root)
        observed = architecture["status"]
        evidence = architecture["findings"]
    elif kind in ("architecture", "security", "privacy", "review"):
        if kind == "security" and isinstance(content, str):
            content = content.replace("{{PRIVATE_KEY_HEADER}}", "-----BEGIN " + "PRIVATE KEY-----")
        patterns = case.get("rules", {}).get("forbidden_patterns", [])
        hits = [pattern for pattern in patterns if re.search(pattern, content, re.I | re.M)]
        secrets = core.scan_secret_text(content) if kind in ("security", "review") else []
        observed = "failed" if hits or secrets else "passed"
        evidence = [{"rule": hit, "value": "matched (value omitted)"} for hit in hits] + [{"line": finding["line"], "kind": finding["kind"], "message": finding["message"]} for finding in secrets]
    elif kind == "testing-traceability":
        criteria = case.get("rules", {}).get("criteria_ids", [])
        tests = case.get("rules", {}).get("test_content", "")
        missing = [criterion for criterion in criteria if criterion not in tests]
        observed = "failed" if missing else "passed"
        evidence = [f"Critério sem referência textual em teste: {item}" for item in missing] or ["Todos IDs configurados aparecem no texto de teste"]
    elif kind == "workflow-order":
        order = case.get("rules", {}).get("required_order", [])
        steps = case.get("rules", {}).get("observed_steps", [])
        positions = [steps.index(step) for step in order if step in steps]
        observed = "passed" if len(positions) == len(order) and positions == sorted(positions) else "failed"
        evidence = [f"Etapas requeridas: {order}; observadas: {steps}"]
    elif kind == "stack-detection":
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            for name, value in case.get("input", {}).get("files", {}).items():
                target = Path(directory) / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(value, encoding="utf-8")
            detected = core.inspect(Path(directory))
        ok = detected["project_type"] == case.get("expected_project_type") and detected["stack"] == case.get("expected_stacks")
        observed = "passed" if ok else "failed"
        evidence = [{"project_type": detected["project_type"], "stack": detected["stack"], "checks": [item.get("availability") or item.get("status") or "catalogued" for item in detected["checks_available"]]}]
    else:
        observed = "error"
        evidence = [f"Tipo de eval desconhecido: {kind}"]
    passed = observed == case.get("expected_status")
    safe_input = {"sha256": hashlib.sha256(content.encode()).hexdigest(), "bytes": len(content.encode()), "content": "omitted (secret-sensitive eval)"} if kind in ("security", "review") else content
    return {"id": case.get("id"), "name": case.get("name"), "category": case.get("category"), "objective": case.get("objective"), "input": safe_input, "expected": case.get("expected_status"), "observed": observed, "status": "passed" if passed else "failed", "evidence": evidence, "limitations": case.get("limitations", "Heurística determinística; não substitui revisão humana/contextual.")}


def run(cases_dir: Path) -> dict:
    cases = sorted(cases_dir.glob("*.json"))
    results = []
    for path in cases:
        case = json.loads(path.read_text(encoding="utf-8"))
        result = evaluate(case)
        result["case_file"] = str(path)
        results.append(result)
    return {"suite": "AI Engineering Toolkit deterministic evals", "method": "deterministic/offline", "case_count": len(results), "passed": sum(item["status"] == "passed" for item in results), "failed": sum(item["status"] == "failed" for item in results), "results": results}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(Path(__file__).parent / "cases"))
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    report = run(Path(args.cases).resolve())
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).resolve().write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
