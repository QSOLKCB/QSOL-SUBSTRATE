from __future__ import annotations

import argparse
from pathlib import Path

from probe_core import validate_probe_bundle

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deterministic QSOL-SUBSTRATE Phase 7 probe bundle")
    parser.add_argument("--bundle", type=Path, default=Path("dist/probes"))
    args = parser.parse_args()
    findings = validate_probe_bundle(ROOT, args.bundle)
    if findings:
        for finding in findings:
            print(f"{finding.code}: {finding.path}: {finding.message}")
        return 1
    print(f"VALID probe_bundle={args.bundle.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
