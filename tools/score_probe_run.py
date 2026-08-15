from __future__ import annotations

import argparse
import json
from pathlib import Path

from probe_core import ProbeError, report_markdown, score_probe_run, validate_probe_bundle
from substrate_integrity import canonical_json_bytes

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Score a structured model run against the deterministic Phase 7 probe")
    parser.add_argument("--bundle", type=Path, default=Path("dist/probes"))
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown")
    parser.add_argument("--require-perfect-oracle", action="store_true")
    args = parser.parse_args()
    try:
        findings = validate_probe_bundle(ROOT, args.bundle)
        if findings:
            raise ProbeError("probe bundle failed deterministic validation before scoring")
        run = json.loads(args.run.read_text(encoding="utf-8"))
        report = score_probe_run(ROOT, args.bundle, run)
        args.output.write_bytes(canonical_json_bytes(report))
        if args.markdown:
            Path(args.markdown).write_text(report_markdown(report), encoding="utf-8")
        if args.require_perfect_oracle:
            if report["execution_kind"] != "scoring_oracle" or report["metrics"]["overall_accuracy"] != 1.0:
                raise ProbeError("perfect scoring-oracle check failed")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ProbeError) as exc:
        print(f"PROBE SCORE REFUSED: {exc}")
        return 1
    print(f"probe_score={report['counts']['correct']}/{report['counts']['total']}")
    print(f"overall_accuracy={report['metrics']['overall_accuracy']}")
    print(f"yeah_nah_1_accuracy={report['yeah_nah_1']['overall_accuracy']}")
    print(f"execution_kind={report['execution_kind']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
