from __future__ import annotations

import argparse
import json
from pathlib import Path

from epistemic_conformance_core import EpistemicConformanceError, canonical_json_bytes, report_markdown, score_run

ROOT = Path(__file__).resolve().parents[1]


def _prepare_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Score an EPISTEMIC-CONFORMANCE/1 empirical run")
    parser.add_argument("--bundle", type=Path, default=Path("dist/epistemic-conformance-1"))
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown")
    args = parser.parse_args()
    try:
        run = json.loads(args.run.read_text(encoding="utf-8"))
        report = score_run(ROOT, args.bundle, run)
        _prepare_parent(args.output)
        args.output.write_bytes(canonical_json_bytes(report))
        if args.markdown:
            markdown = Path(args.markdown)
            _prepare_parent(markdown)
            markdown.write_text(report_markdown(report), encoding="utf-8")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, EpistemicConformanceError) as exc:
        print(f"EPISTEMIC CONFORMANCE SCORE REFUSED: {exc}")
        return 1
    print(f"external_conformance_score={report['metrics']['external_conformance_score']}")
    print(f"completion_rate={report['metrics']['completion_rate']}")
    print(f"major_error_count={report['metrics']['major_error_count']}")
    print(f"verdict={report['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
