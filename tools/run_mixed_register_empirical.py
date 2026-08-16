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
    load_empirical_protocol,
    parse_consumer_output,
)
from substrate_integrity import canonical_json_bytes
from toolless_core import CapsuleError, build_toolless_bundle
from vector_core import VectorError, build_vector_bundle

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (ROOT / "dist/empirical/mixed-register").resolve()
WORK_MARKER = ".qsol-mixed-register-empirical-workdir"
OUTPUT_MARKER = ".qsol-mixed-register-empirical-output"


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


def _resolved(path: Path) -> Path:
    return (ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def _reject_destructive_target(path: Path, label: str) -> Path:
    if path.exists() and path.is_symlink():
        raise EmpiricalError(f"{label} may not be a symlink")
    resolved = _resolved(path)
    if resolved == ROOT or resolved in ROOT.parents:
        raise EmpiricalError(f"{label} may not be the repository root or one of its ancestors")
    return resolved


def _prepare_work_dir(path: Path) -> Path:
    resolved = _reject_destructive_target(path, "work directory")
    if ROOT in resolved.parents:
        raise EmpiricalError("work directory must live outside the repository checkout")
    if resolved.exists():
        if not resolved.is_dir():
            raise EmpiricalError("work directory must be a directory")
        marker = resolved / WORK_MARKER
        if not marker.is_file():
            raise EmpiricalError("refusing to recursively delete an unmarked existing work directory")
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)
    (resolved / WORK_MARKER).write_text("dedicated Phase 9 empirical scratch directory\n", encoding="utf-8")
    return resolved


def _prepare_output_dir(path: Path) -> Path:
    resolved = _reject_destructive_target(path, "output directory")
    inside_repo = ROOT in resolved.parents
    if inside_repo and resolved != DEFAULT_OUTPUT:
        raise EmpiricalError("in-repository output is restricted to dist/empirical/mixed-register")
    if resolved.exists():
        if not resolved.is_dir():
            raise EmpiricalError("output directory must be a directory")
        marker = resolved / OUTPUT_MARKER
        if resolved != DEFAULT_OUTPUT and not marker.is_file():
            raise EmpiricalError("refusing to recursively delete an unmarked custom output directory")
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)
    (resolved / OUTPUT_MARKER).write_text("dedicated Phase 9 empirical evidence directory\n", encoding="utf-8")
    return resolved


def _protocol_failure_gate(message: str) -> dict[str, object]:
    return {
        "passed": False,
        "checks": {"consumer_protocol_integrity": False},
        "protocol_error": message,
        "interpretation": (
            "The consumer response violated the empirical output contract. "
            "This is a measured consumer failure, not a harness or infrastructure failure."
        ),
    }


def _metric_delta(
    guarded: dict[str, object] | None,
    ablated: dict[str, object] | None,
    key: str,
    *,
    reverse: bool = False,
) -> float | None:
    if guarded is None or ablated is None:
        return None
    gv = guarded.get(key)
    av = ablated.get(key)
    if not isinstance(gv, (int, float)) or not isinstance(av, (int, float)):
        return None
    value = av - gv if reverse else gv - av
    return round(float(value), 6)


def _summary_with_protocol_failures(
    results: list[dict[str, object]],
    manifest: dict[str, object],
    identity,
    protocol: dict[str, object],
) -> dict[str, object]:
    indexed = {(str(row["condition"]), str(row["variant"])): row for row in results}
    rows: list[dict[str, object]] = []
    protocol_failure_count = 0
    for condition in CONDITIONS:
        guarded = indexed.get((condition, "guarded"))
        ablated = indexed.get((condition, "ablated"))
        if guarded is None or ablated is None:
            raise EmpiricalError(f"missing paired empirical result for {condition}")
        guarded_report = guarded.get("report")
        ablated_report = ablated.get("report")
        gm = guarded_report.get("metrics") if isinstance(guarded_report, dict) else None
        am = ablated_report.get("metrics") if isinstance(ablated_report, dict) else None
        gm = gm if isinstance(gm, dict) else None
        am = am if isinstance(am, dict) else None
        guarded_error = guarded.get("protocol_error")
        ablated_error = ablated.get("protocol_error")
        protocol_failure_count += int(bool(guarded_error)) + int(bool(ablated_error))
        rows.append({
            "condition": condition,
            "guarded": gm,
            "ablated": am,
            "guarded_protocol_error": guarded_error,
            "ablated_protocol_error": ablated_error,
            "guard_effect": {
                "primary_status_accuracy_delta": _metric_delta(gm, am, "primary_status_accuracy"),
                "register_accuracy_delta": _metric_delta(gm, am, "register_accuracy"),
                "evidence_fidelity_delta": _metric_delta(gm, am, "evidence_fidelity"),
                "unsupported_assertion_rate_reduction": _metric_delta(
                    gm, am, "unsupported_assertion_rate", reverse=True
                ),
            },
            "cold_consumer_gate": guarded["cold_consumer_gate"],
        })
    passing = [
        row["condition"]
        for row in rows
        if isinstance(row["cold_consumer_gate"], dict)
        and row["cold_consumer_gate"].get("passed") is True
    ]
    return {
        "type": "qsol-mixed-register-empirical-summary",
        "schema_version": "1.0.0",
        "empirical_spec_version": protocol["empirical_spec_version"],
        "artifact_class": "derived_evaluation",
        "canonical_truth_authority": False,
        "evaluation_bundle_sha256": manifest["bundle_sha256"],
        "substrate": manifest["substrate"],
        "model": {
            "provider": identity.provider,
            "model_id": identity.model_id,
            "immutable_model_revision": identity.immutable_revision,
        },
        "conditions": list(CONDITIONS),
        "variants": ["guarded", "ablated"],
        "rows": rows,
        "consumer_protocol_failure_count": protocol_failure_count,
        "cold_consumer_demonstrated": bool(passing),
        "passing_guarded_conditions": passing,
        "interpretation": (
            "Consumer protocol violations are retained as empirical failures and do not make the harness fail. "
            "Guard deltas are null where a paired quantitative score is unavailable."
        ),
    }


def _summarize_results(
    results: list[dict[str, object]],
    manifest: dict[str, object],
    identity,
    protocol: dict[str, object],
) -> dict[str, object]:
    if any(row.get("protocol_error") for row in results):
        return _summary_with_protocol_failures(results, manifest, identity, protocol)
    return experiment_summary(results, manifest, identity)


def main() -> int:
    try:
        protocol = load_empirical_protocol(ROOT)
    except EmpiricalError as exc:
        print(f"EMPIRICAL RUN REFUSED: {exc}")
        return 2

    runner_defaults = protocol["default_local_runner"]
    canonical_top_k = int(protocol["retrieval"]["vector"]["top_k"])
    parser = argparse.ArgumentParser(
        description="Run paired blinded guarded/ablated MIXED-REGISTER/1 cold-consumer measurements against a local Ollama model."
    )
    parser.add_argument("--model", default=runner_defaults["model"])
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--num-ctx", type=int, default=int(runner_defaults["num_ctx"]))
    parser.add_argument("--seed", type=int, default=int(runner_defaults["seed"]))
    parser.add_argument("--top-k", type=int, default=canonical_top_k)
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
        if args.top_k != canonical_top_k:
            raise EmpiricalError(
                f"canonical empirical run requires top_k={canonical_top_k}; protocol and executable settings must not drift"
            )
        source_commit = args.source_commit or _source_commit()
        selected = tuple(item.strip() for item in args.conditions.split(",") if item.strip())
        unknown = sorted(set(selected) - set(CONDITIONS))
        if unknown:
            raise EmpiricalError("unknown conditions: " + ", ".join(unknown))
        if selected != CONDITIONS:
            raise EmpiricalError(
                "the canonical Phase 9 empirical run requires all five conditions in protocol order; "
                "use tests/helpers for partial matrices"
            )

        work_dir = _prepare_work_dir(args.work_dir)
        toolless_dir = work_dir / "toolless"
        vector_dir = work_dir / "vectors"
        mixed_dir = work_dir / "mixed-register-1"
        build_toolless_bundle(ROOT, toolless_dir, source_commit)
        build_vector_bundle(ROOT, vector_dir, source_commit)
        mixed_manifest = build_mixed_register_bundle(ROOT, mixed_dir, source_commit)
        built_claims = json.loads("[" + ",".join(
            line for line in (mixed_dir / "claims.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()
        ) + "]")
        report_text = (mixed_dir / "report.md").read_text(encoding="utf-8")

        client = OllamaClient(args.ollama_url, args.model, num_ctx=args.num_ctx, seed=args.seed)
        identity = client.identity()
        output_dir = _prepare_output_dir(args.output)

        results: list[dict[str, object]] = []
        for condition in CONDITIONS:
            for variant in ("guarded", "ablated"):
                carrier = carrier_text(
                    ROOT, condition, variant, toolless_dir, vector_dir, built_claims, top_k=args.top_k
                )
                prompt = build_prompt(report_text, built_claims, carrier, condition, variant)
                stem = f"{condition}.{variant}"
                for name in ("prompts", "carriers", "raw", "audits", "reports"):
                    (output_dir / name).mkdir(exist_ok=True)
                (output_dir / "prompts" / f"{stem}.txt").write_text(prompt, encoding="utf-8")
                (output_dir / "carriers" / f"{stem}.txt").write_text(carrier, encoding="utf-8")

                raw_payload, provider_meta, raw_text = client.generate(prompt)
                raw_path = output_dir / "raw" / f"{stem}.response.json"
                raw_path.write_bytes(raw_text.encode("utf-8"))

                try:
                    parsed_claims = parse_consumer_output(raw_payload, built_claims)
                except EmpiricalError as exc:
                    protocol_error = str(exc)
                    gate = _protocol_failure_gate(protocol_error)
                    _write_json(output_dir / "raw" / f"{stem}.metadata.json", {
                        "consumer_output": raw_payload,
                        "provider_metadata": provider_meta,
                        "raw_response_path": raw_path.name,
                        "raw_response_sha256": provider_meta["raw_response_sha256"],
                        "consumer_protocol_error": protocol_error,
                    })
                    results.append({
                        "condition": condition,
                        "variant": variant,
                        "report": None,
                        "cold_consumer_gate": gate,
                        "protocol_error": protocol_error,
                        "evidence_ref_violation_count": None,
                    })
                    print(
                        f"{condition}/{variant}: consumer_protocol_error={protocol_error!r} "
                        "cold_pass=False"
                    )
                    continue

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
                gate = cold_consumer_gate(
                    built_claims,
                    audit,
                    report,
                    evidence_ref_violations=evidence_violations,
                )
                _write_json(output_dir / "raw" / f"{stem}.metadata.json", {
                    "consumer_output": raw_payload,
                    "provider_metadata": provider_meta,
                    "raw_response_path": raw_path.name,
                    "raw_response_sha256": provider_meta["raw_response_sha256"],
                    "evidence_ref_violations": evidence_violations,
                })
                _write_json(output_dir / "audits" / f"{stem}.json", audit)
                _write_json(output_dir / "reports" / f"{stem}.json", report)
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
                    f"evidence_violations={len(evidence_violations)} "
                    f"cold_pass={gate['passed']}"
                )

        summary = _summarize_results(results, mixed_manifest, identity, protocol)
        summary["source_commit"] = source_commit
        summary["seed"] = args.seed
        summary["num_ctx"] = args.num_ctx
        summary["top_k"] = args.top_k
        summary["run_count"] = len(results)
        summary["protocol_sha256"] = hashlib.sha256(
            (ROOT / "empirical/mixed-register/experiment.json").read_bytes()
        ).hexdigest()
        _write_json(output_dir / "summary.json", summary)
        print(f"cold_consumer_demonstrated={summary['cold_consumer_demonstrated']}")
        print("passing_guarded_conditions=" + ",".join(summary["passing_guarded_conditions"]))
        print(f"consumer_protocol_failures={summary.get('consumer_protocol_failure_count', 0)}")
        print(f"output={output_dir}")
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
