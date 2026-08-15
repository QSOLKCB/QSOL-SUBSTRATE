from __future__ import annotations

import argparse
import json
from pathlib import Path

from projection_core import (
    compatibility_fingerprint,
    compatibility_mismatches,
    validate_compatibility_manifest,
)


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Check exact model compatibility for a QSOL model-specific projection")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--actual", type=Path, required=True)
    args = parser.parse_args()

    try:
        expected = _read(args.expected)
        actual = _read(args.actual)
    except Exception as exc:
        print(f"COMPATIBILITY REFUSED: {exc}")
        return 1

    expected_schema = validate_compatibility_manifest(args.root, expected)
    actual_schema = validate_compatibility_manifest(args.root, actual)
    if expected_schema or actual_schema:
        print("COMPATIBILITY REFUSED: schema validation failed")
        for pointer in expected_schema:
            print(f"- expected:{pointer}")
        for pointer in actual_schema:
            print(f"- actual:{pointer}")
        return 1

    mismatches = compatibility_mismatches(expected, actual)
    if mismatches:
        print("COMPATIBILITY INVALIDATED: " + ",".join(mismatches))
        return 1

    print("COMPATIBLE")
    print(f"compatibility_sha256={compatibility_fingerprint(actual)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
