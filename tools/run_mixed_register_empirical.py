#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from mixed_register_core import MixedRegisterError, build_mixed_register_bundle, score_claim_audit
from mixed_register_empirical import (
    CONDITIONS,
    EmpiricalError,
    OllamaClient,
    build_claim_audit,
    build_prompt,
    carrier_text,
    cold_consumer_gate,
    constrain_evidence_refs,
    experiment_summary,
    parse_consumer_output,
)
from substrate_integrity import canonical_json_bytes
from toolless_core import CapsuleError, build_toolless_bundle
from vector_core import VectorError, build_vector_bundle

ROOT = Path(__file__).resolve().parents[1]


def _source_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    if len(value) != 40:
        raise EmpiricalError("git HEAD did not resolve to a full commit")
    return value


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run paired guarded/ablated MIXED-REGISTER/1 cold-consumer measurements against a local Ollama model."
    )
    parser.add_argument("--model", default="qwen2.5:1.5b")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--num-ctx", type=int, default=32768)
    parser.add_argument("--seed", type=int, default=18437)
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument(
        "--conditions",
        default=",".join(CONDITIONS),
        help="Comma-separated subset of: " + ",".join(CONDITIONS),
    )
    parser.add_argument("--source-commit", default=None)
    parser.add_argument("--work-dir", type=Path, default=Path("/tmp/qsol-mixed-register-empirical"))
    parser.add_argument("--output", type=Path, default=Path("dist/empirical/mixed-register"))
    args = parser.parse_args()

    try:
        source_commit = args.source_commit or _source_commit()
        selected = tuple(item.strip() for item in args.conditions.split(",") if item.strip())
        unknown = sorted(set(selected) - set(CONDITIONS))
        if unknown:
            raise EmpiricalError("unknown conditions: " + ", ".join(unknown))
        if set(selected) != set(CONDITIONS):
            raise EmpiricalError(
                "the canonical Phase 9 empirical run requires all five conditions; "
                "use tests/helpers for partial matrices"
            )

        if args.work_dir.exists():
            shutil.rmtree(args.work_dir)
        args.work_dir.mkdir(parents=True)
        toolless_dir = args.work_dir / "toolless"
        vector_dir = args.work_dir / "vectors"
        mixed_dir = args.work_dir / "mixed-register-1"
        build_toolless_bundle(ROOT, toolless_dir, source_commit)
        build_vector_bundle(ROOT, vector_dir, source_commit)
        mixed_manifest = build_mixed_register_bundle(ROOT, mixed_dir, source_commit)
        built_claims = json.loads("[" + ",".join(
            line for line in (mixed_dir / "claims.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()
        ) + "]")
        report_text = (mixed_dir / "report.md").read_text(encoding="utf-8")

        client = OllamaClient(args.ollama_url, args.model, num_ctx=args.num_ctx, seed=args.seed)
        identity = client.identity()

        if args.output.exists():
            shutil.rmtree(args.output)
        args.output.mkdir(parents=True)

        results = []
        for condition in CONDITIONS:
            for variant in ("guarded", "ablated"):
                carrier = carrier_text(
                    ROOT, condition, variant, toolless_dir, vector_dir, built_claims, top_k=args.top_k
                )
                prompt = build_prompt(report_text, built_claims, carrier, condition, variant)
                raw_payload, provider_meta = client.generate(prompt)
                parsed_claims = parse_consumer_output(raw_payload, built_claims)
                constrained_claims, evidence_violations = constrain_evidence_refs(
                    ROOT, parsed_claims, carrier
                )
                audit = build_claim_audit(
                    mixed_manifest,
                    identity,
                    condition,
                    variant,
                    constrained_claims,
                    hashlib.sha256(carrier.encode("utf-8")).hexdigest(),
                    str(provider_meta["raw_response_sha256"]),
                )
                audit["artifact_hashes"]["empirical_prompt"] = hashlib.sha256(
                    prompt.encode("utf-8")
                ).hexdigest()
                report = score_claim_audit(ROOT, mixed_dir, audit)
                gate = cold_consumer_gate(built_claims, audit, report)
                stem = f"{condition}.{variant}"
                (args.output / "prompts").mkdir(exist_ok=True)
                (args.output / "carriers").mkdir(exist_ok=True)
                (args.output / "raw").mkdir(exist_ok=True)
                (args.output / "audits").mkdir(exist_ok=True)
                (args.output / "reports").mkdir(exist_ok=True)
                (args.output / "prompts" / f"{stem}.txt").write_text(prompt, encoding="utf-8")
                (args.output / "carriers" / f"{stem}.txt").write_text(carrier, encoding="utf-8")
                _write_json(args.output / "raw" / f"{stem}.json", {
                    "consumer_output": raw_payload,
                    "provider_metadata": provider_meta,
                    "evidence_ref_violations": evidence_violations,
                })
                _write_json(args.output / "audits" / f"{stem}.json", audit)
                _write_json(args.output / "reports" / f"{stem}.json", report)
                results.append({
                    "condition": condition,
                    "variant": variant,
                    "audit": audit,
                    "report": report,
                    "cold_consumer_gate": gate,
                    "evidence_ref_violation_count": len(evidence_violations),
                })
                print(
                    f"{condition}/{variant}: "
                    f"status={report['metrics']['primary_status_accuracy']} "
                    f"register={report['metrics']['register_accuracy']} "
                    f"unsupported={report['metrics']['unsupported_assertion_rate']} "
                    f"cold_pass={gate['passed']}"
                )

        summary = experiment_summary(results, mixed_manifest, identity)
        summary["source_commit"] = source_commit
        summary["seed"] = args.seed
        summary["num_ctx"] = args.num_ctx
        summary["top_k"] = args.top_k
        summary["run_count"] = len(results)
        _write_json(args.output / "summary.json", summary)
        print(f"cold_consumer_demonstrated={summary['cold_consumer_demonstrated']}")
        print("passing_guarded_conditions=" + ",".join(summary["passing_guarded_conditions"]))
        print(f"output={args.output.resolve()}")
        return 0
    except (
        OSError,
        ValueError,
        subprocess.CalledProcessError,
        CapsuleError,
        VectorError,
        MixedRegisterError,
        EmpiricalError,
    ) as exc:
        print(f"EMPIRICAL RUN REFUSED: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
