#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from substrate_integrity import canonical_json_bytes, validate_repository


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed validator for the canonical QSOL-SUBSTRATE public substrate.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json-report", type=Path)
    args = parser.parse_args()

    report = validate_repository(args.root)
    payload = report.to_dict()
    if args.json_report:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_bytes(canonical_json_bytes(payload))

    if report.valid:
        print(f"VALID records={report.record_count} sources={report.source_count} relationships={report.relationship_count} publications={report.publication_count} events={report.event_count}")
        print(f"substrate_sha256={report.substrate_sha256}")
        return 0

    print(f"VALIDATION REFUSED: {len(report.findings)} finding(s)", file=sys.stderr)
    for finding in report.findings:
        print(f"- [{finding.code}] {finding.path}: {finding.message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
