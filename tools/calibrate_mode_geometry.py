from __future__ import annotations

import argparse
import json
from pathlib import Path

from mode_core import ModeError, calibrate_reports
from substrate_integrity import canonical_json_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate frozen empirical MODE-CONFUSION/1 reports into a non-mutating geometry calibration recommendation")
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=Path("mode-calibration.json"))
    args = parser.parse_args()
    try:
        reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.reports]
        result = calibrate_reports(reports)
        args.output.write_bytes(canonical_json_bytes(result))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ModeError) as exc:
        print(f"MODE CALIBRATION REFUSED: {exc}")
        return 1
    print(f"empirical_reports={result['report_count']}")
    print(f"model_revisions={result['model_revision_count']}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
