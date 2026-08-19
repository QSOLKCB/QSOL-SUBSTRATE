from __future__ import annotations

import argparse
import json
from pathlib import Path

from mode_core import ModeError, score_mode_run
from substrate_integrity import canonical_json_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description="Score a frozen MODE-CONFUSION/1 consumer or oracle run")
    parser.add_argument("--bundle", type=Path, default=Path("dist/modes"))
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("mode-report.json"))
    parser.add_argument("--require-perfect-oracle", action="store_true")
    args = parser.parse_args()
    try:
        run = json.loads(args.run.read_text(encoding="utf-8"))
        report = score_mode_run(args.bundle, run)
        if args.require_perfect_oracle:
            if report["execution_kind"] != "scoring_oracle":
                raise ModeError("--require-perfect-oracle refuses non-oracle runs")
            if report["counts"]["correct"] != report["counts"]["total"]:
                raise ModeError("scoring oracle did not classify every case correctly")
        args.output.write_bytes(canonical_json_bytes(report))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ModeError) as exc:
        print(f"MODE RUN SCORING REFUSED: {exc}")
        return 1
    print(f"correct={report['counts']['correct']}/{report['counts']['total']}")
    print(f"empirical_model_result={str(report['empirical_model_result']).lower()}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
