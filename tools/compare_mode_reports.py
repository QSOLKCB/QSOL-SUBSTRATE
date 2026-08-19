from __future__ import annotations

import argparse
import json
from pathlib import Path

from mode_core import ModeError, compare_mode_reports
from substrate_integrity import canonical_json_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two frozen MODE-CONFUSION/1 reports for the exact same model revision")
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--output", type=Path, default=Path("mode-comparison.json"))
    args = parser.parse_args()
    try:
        left = json.loads(args.left.read_text(encoding="utf-8"))
        right = json.loads(args.right.read_text(encoding="utf-8"))
        result = compare_mode_reports(left, right)
        args.output.write_bytes(canonical_json_bytes(result))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ModeError) as exc:
        print(f"MODE REPORT COMPARISON REFUSED: {exc}")
        return 1
    print(f"left={result['left_condition']} right={result['right_condition']}")
    print(f"accuracy_delta={result['delta']['accuracy']}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
