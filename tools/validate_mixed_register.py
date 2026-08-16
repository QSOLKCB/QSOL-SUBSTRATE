#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from mixed_register_core import validate_mixed_register_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deterministic MIXED-REGISTER/1 evaluation bundle.")
    parser.add_argument("--bundle", default="dist/mixed-register-1")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    findings = validate_mixed_register_bundle(root, Path(args.bundle))
    if findings:
        for finding in findings:
            print(f"{finding.code}\t{finding.path}\t{finding.message}")
        return 1
    print("VALID MIXED-REGISTER/1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
