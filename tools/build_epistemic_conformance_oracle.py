from __future__ import annotations

import argparse
import json
from pathlib import Path

from epistemic_conformance_core import EpistemicConformanceError, canonical_json_bytes

_SIGNAL_TAGS = {
    "conflict_opportunities": "conflict_preservation",
    "historical_opportunities": "historical_preservation",
    "identifier_opportunities": "identifier_nonfabrication",
    "cross_domain_opportunities": "cross_domain_boundary",
    "retrieved_text_opportunities": "retrieved_text_authority",
}


def _oracle_signals(cases: list[dict]) -> dict[str, int]:
    opportunities = {key: 0 for key in _SIGNAL_TAGS}
    for case in cases:
        tags = case.get("signals", [])
        for key, tag in _SIGNAL_TAGS.items():
            if tag in tags:
                opportunities[key] += 1
    return {
        **opportunities,
        "conflict_preserved": opportunities["conflict_opportunities"],
        "historical_preserved": opportunities["historical_opportunities"],
        "identifier_errors": 0,
        "cross_domain_errors": 0,
        "retrieved_text_errors": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a non-empirical EPISTEMIC-CONFORMANCE/1 scoring-oracle run"
    )
    parser.add_argument("--bundle", type=Path, default=Path("dist/epistemic-conformance-1"))
    parser.add_argument("--substrate-sha256", required=True)
    parser.add_argument("--delivery", default="oracle")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads((args.bundle / "manifest.json").read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise EpistemicConformanceError("benchmark manifest must be a JSON object")
        grading = json.loads(
            (args.bundle / manifest["grading"]["file"]).read_text(encoding="utf-8")
        )
        if not isinstance(grading, dict) or not isinstance(grading.get("modules"), dict):
            raise EpistemicConformanceError("grading contract must be a JSON object")
        if len(args.substrate_sha256) != 64 or any(
            ch not in "0123456789abcdef" for ch in args.substrate_sha256
        ):
            raise EpistemicConformanceError(
                "--substrate-sha256 must be 64 lowercase hex characters"
            )
        modules = []
        for row in manifest["modules"]:
            cases = grading["modules"][row["id"]]
            modules.append(
                {
                    "module_id": row["id"],
                    "raw_output": f"deterministic scoring-oracle annotation for {row['id']}",
                    "completed_cases": row["case_count"],
                    "earned_points": row["max_points"],
                    "max_points": row["max_points"],
                    "major_errors": [],
                    "remaining_errors": 0,
                    "initial_errors": 0,
                    "corrected_errors": 0,
                    "model_self_assessment": {
                        "score_fraction": 1.0,
                        "verdict": "CONFORMANT",
                    },
                    "signals": _oracle_signals(cases),
                }
            )
        run = {
            "type": "qsol-epistemic-conformance-run",
            "schema_version": "1.0.0",
            "run_id": "qsol:epistemic-conformance-scoring-oracle",
            "execution_kind": "scoring_oracle",
            "benchmark": {
                "id": manifest["benchmark_id"],
                "sha256": manifest["benchmark_sha256"],
            },
            "substrate": {
                "protocol": "QSOL-SUBSTRATE",
                "source_commit": manifest["source_commit"],
                "substrate_sha256": args.substrate_sha256,
                "delivery": args.delivery,
            },
            "model": {
                "id": "qsol/scoring-oracle",
                "revision": "EPISTEMIC-CONFORMANCE/1",
                "provider": "QSOL-SUBSTRATE",
                "runtime": "deterministic-oracle",
                "quantization": "none",
                "parameter_count_billion": None,
            },
            "inference": {
                "context_size": None,
                "temperature": None,
                "top_p": None,
                "top_k": None,
                "seed": None,
                "sampler": "deterministic-oracle",
                "extra": {},
            },
            "grader": {
                "id": "qsol/scoring-oracle",
                "revision": "1.0.0",
                "method": "deterministic_oracle",
            },
            "modules": modules,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_json_bytes(run))
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        EpistemicConformanceError,
        KeyError,
        TypeError,
    ) as exc:
        print(f"EPISTEMIC CONFORMANCE ORACLE BUILD REFUSED: {exc}")
        return 1
    print("execution_kind=scoring_oracle")
    print("empirical_model_result=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
