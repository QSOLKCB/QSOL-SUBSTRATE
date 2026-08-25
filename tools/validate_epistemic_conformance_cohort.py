from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import FormatChecker

from epistemic_conformance_core import StrictDraft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COHORT = Path("empirical/epistemic-conformance-1/2026-08-25/cohort.json")
COHORT_SCHEMA = Path("schema/epistemic-conformance-cohort.schema.json")


def validate_cohort(root: Path, cohort: Path = DEFAULT_COHORT) -> list[str]:
    cohort_path = cohort if cohort.is_absolute() else root / cohort
    schema_path = root / COHORT_SCHEMA
    try:
        value = json.loads(cohort_path.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"cohort.invalid:{exc}"]

    validator = StrictDraft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(
        validator.iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    findings = []
    for error in errors:
        path = "/".join(str(part) for part in error.absolute_path) or "<root>"
        findings.append(f"cohort.schema:{path}:{error.message}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate EPISTEMIC-CONFORMANCE/1 exploratory cohort metadata"
    )
    parser.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    args = parser.parse_args()
    findings = validate_cohort(ROOT, args.cohort)
    if findings:
        for finding in findings:
            print(finding)
        return 1
    print("epistemic_conformance_cohort_validation=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
