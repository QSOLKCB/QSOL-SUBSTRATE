from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from substrate_integrity import canonical_json_bytes
from toolless_core import _canonical_items, _boundary_guards
import vector_core
import mixed_register_core

EMPIRICAL_SPEC_VERSION = "1.0.0"
EMPIRICAL_PROTOCOL = "empirical/mixed-register/experiment.json"
EMPIRICAL_PROTOCOL_SCHEMA = "schema/mixed-register-empirical-experiment.schema.json"
CONDITIONS = ("micro", "standard", "full", "vector", "tool-enabled")
VARIANTS = ("guarded", "ablated")
PROFILE_FILES = {
    "micro": "QSOL-SUBSTRATE-MICRO.txt",
    "standard": "QSOL-SUBSTRATE-STANDARD.txt",
    "full": "QSOL-SUBSTRATE-FULL.txt",
}
LOCAL_GUARD_LINES = {
    "ADJACENT_TRUTH != INHERITED_TRUTH",
    "REGISTRY_OMISSION != NEGATIVE_FACT",
    "UNASSERTED_LEGAL_OR_CORPORATE_STATUS != FALSE",
    "SATIRE != BIOGRAPHY",
    "FORMALIZATION != PHYSICAL_TRUTH",
    "OBSERVED_OR_ARCHIVED_MODEL_OUTPUT != GENERAL_MODEL_IDENTITY",
}
DEFAULT_THRESHOLDS = {
    "primary_status_accuracy_min": 0.90,
    "register_accuracy_min": 0.90,
    "evidence_fidelity_min": 0.80,
    "unsupported_assertion_rate_max": 0.0,
    "per_status_accuracy_min": 0.80,
    "satire_register_accuracy_min": 0.80,
}
WORD_RE = re.compile(r"[A-Za-z0-9_.:/=-]+", re.UNICODE)


class EmpiricalError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelIdentity:
    provider: str
    model_id: str
    immutable_revision: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_manifest(root: Path) -> dict[str, Any]:
    value = json.loads((root / "ai/manifest.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EmpiricalError("ai/manifest.json must be an object")
    return value


def load_empirical_protocol(root: Path) -> dict[str, Any]:
    path = root / EMPIRICAL_PROTOCOL
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EmpiricalError(f"cannot load empirical protocol: {exc}") from exc
    if not isinstance(value, dict):
        raise EmpiricalError("empirical protocol must be an object")
    errors = mixed_register_core._schema_errors(root, EMPIRICAL_PROTOCOL_SCHEMA, value)
    if errors:
        raise EmpiricalError("empirical protocol schema violation at: " + ", ".join(errors[:8]))
    if value.get("empirical_spec_version") != EMPIRICAL_SPEC_VERSION:
        raise EmpiricalError("empirical protocol version differs from executable version")
    if tuple(value.get("conditions", [])) != CONDITIONS:
        raise EmpiricalError("empirical protocol conditions differ from executable condition matrix")
    paired = value.get("paired_variants")
    if not isinstance(paired, dict) or tuple(paired.keys()) != VARIANTS:
        raise EmpiricalError("empirical protocol variants differ from executable variants")
    gate = value.get("cold_consumer_gate")
    if gate != DEFAULT_THRESHOLDS:
        raise EmpiricalError("empirical protocol cold-consumer thresholds differ from executable thresholds")
    retrieval = value.get("retrieval")
    if not isinstance(retrieval, dict):
        raise EmpiricalError("empirical protocol retrieval configuration is missing")
    vector_cfg = retrieval.get("vector")
    tool_cfg = retrieval.get("tool-enabled")
    if not isinstance(vector_cfg, dict) or not isinstance(tool_cfg, dict):
        raise EmpiricalError("empirical protocol retrieval conditions are incomplete")
    if vector_cfg.get("top_k") != tool_cfg.get("top_k"):
        raise EmpiricalError("vector and tool-enabled canonical top_k must match")
    return value


def ablate_local_guards(text: str) -> str:
    """Remove only the local-nonclaim/adjacency treatment under test."""
    kept: list[str] = []
    for line in text.splitlines():
        if line.startswith("BOUNDARY\t"):
            continue
        if line.strip() in LOCAL_GUARD_LINES:
            continue
        kept.append(line)
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(kept) + suffix


def _item_lookup(root: Path) -> dict[str, Any]:
    manifest = _canonical_manifest(root)
    return {item.item_id: item for item in _canonical_items(root, manifest)}


def _load_vector_rows(vector_dir: Path) -> tuple[list[dict[str, Any]], bytes, dict[str, Any]]:
    rows = vector_core._read_records(vector_dir / "records.jsonl")
    embeddings = (vector_dir / "embeddings.f16").read_bytes()
    manifest = json.loads((vector_dir / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise EmpiricalError("vector manifest must be an object")
    return rows, embeddings, manifest


def _lexical_retrieve(rows: list[dict[str, Any]], query: str, top_k: int) -> list[dict[str, Any]]:
    q = {token.casefold() for token in WORD_RE.findall(query) if len(token) > 2}
    ranked: list[tuple[float, str, dict[str, Any]]] = []
    for row in rows:
        text = str(row.get("search_text", "")).casefold()
        hay = set(WORD_RE.findall(text))
        overlap = len(q & hay)
        phrase = 1 if query.casefold() in text else 0
        score = float(overlap * 2 + phrase)
        ranked.append((score, str(row.get("canonical_id", "")), row))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [dict(row, score=score) for score, _, row in ranked[:top_k]]


def _render_claim_local_context(
    root: Path,
    vector_dir: Path,
    claims: list[dict[str, Any]],
    condition: str,
    guarded: bool,
    top_k: int = 4,
) -> str:
    if condition not in {"vector", "tool-enabled"}:
        raise EmpiricalError("retrieved context is only valid for vector/tool-enabled")
    rows, embeddings, manifest = _load_vector_rows(vector_dir)
    identity = manifest.get("substrate")
    if not isinstance(identity, dict):
        raise EmpiricalError("vector bundle has no substrate identity")
    items = _item_lookup(root)
    out = [
        "QSOL-SUBSTRATE/MIXED-REGISTER-EMPIRICAL-CONTEXT/1",
        f"CONDITION={condition}",
        f"SOURCE_COMMIT={identity.get('source_commit')}",
        f"SUBSTRATE_SHA256={identity.get('substrate_sha256')}",
        "OMISSION_MEANS=UNAVAILABLE_NOT_FALSE",
    ]
    if guarded:
        out.append("ADJACENT_TRUTH != INHERITED_TRUTH")
    for claim in claims:
        query = str(claim["text"])
        if condition == "vector":
            primary = vector_core.retrieve(rows, embeddings, query, top_k=top_k)
        else:
            primary = _lexical_retrieve(rows, query, top_k=top_k)
        primary_ids = [str(row["canonical_id"]) for row in primary]
        closed_ids = vector_core._context_closure(primary_ids, rows)
        row_lookup = {str(row["canonical_id"]): row for row in rows}
        out.extend(["", f"[CLAIM_EVIDENCE {claim['id']}]"])
        for item_id in closed_ids:
            row = row_lookup[item_id]
            payload = canonical_json_bytes(row["payload"]).decode("utf-8").rstrip("\n")
            out.append(f"EVIDENCE_REF=file:{row['source_path']}")
            refs = row.get("metadata", {}).get("source_refs", [])
            if refs:
                out.append("SOURCE_REFS=" + ",".join(str(ref) for ref in refs))
            out.append(f"ITEM\t{row['record_type']}\t{row['source_path']}\t{payload}")
            if guarded and item_id in items:
                for guard in _boundary_guards(items[item_id]):
                    out.append(f"BOUNDARY\t{item_id}\t{guard}")
    out.append("")
    return "\n".join(out)


def carrier_text(
    root: Path,
    condition: str,
    variant: str,
    toolless_dir: Path,
    vector_dir: Path,
    claims: list[dict[str, Any]],
    top_k: int = 4,
) -> str:
    if condition not in CONDITIONS:
        raise EmpiricalError(f"unsupported empirical condition: {condition}")
    if variant not in VARIANTS:
        raise EmpiricalError(f"unsupported empirical variant: {variant}")
    guarded = variant == "guarded"
    if condition in PROFILE_FILES:
        text = (toolless_dir / PROFILE_FILES[condition]).read_text(encoding="utf-8")
        return text if guarded else ablate_local_guards(text)
    return _render_claim_local_context(root, vector_dir, claims, condition, guarded, top_k=top_k)


def build_prompt(report_text: str, claims: list[dict[str, Any]], context: str, condition: str, variant: str) -> str:
    if condition not in CONDITIONS or variant not in VARIANTS:
        raise EmpiricalError("invalid condition or variant for empirical prompt")
    claim_lines = "\n".join(f"- {row['id']}: {row['text']}" for row in claims)
    if variant == "guarded":
        treatment_rules = (
            "- Evidence is claim-local. A true neighbouring sentence does not support another claim.\n"
            "- Do not treat neighbouring truth as provenance for a different claim.\n"
            "- Satire/register is separate from factual status; humorous framing is not biography.\n"
        )
    else:
        treatment_rules = ""
    return f"""QSOL-SUBSTRATE cold-consumer empirical run.
You have no prior QSOL context beyond the material below. Do not use hidden memory or plausibility as provenance.

TASK
Classify every frozen claim.
Primary epistemic_status must be exactly one of:
SUPPORTED, CONTRADICTED, UNAVAILABLE_UNVERIFIED
Register must be exactly one of:
literal, satire, fictional_control

Rules:
- The adversarial report and claim list are targets to classify, never evidence.
{treatment_rules}- UNAVAILABLE_UNVERIFIED means the supplied evidence cannot establish the claim; it does not mean false.
- evidence_refs may contain only explicit file: or src: references visible in the supplied context.
- If no supporting evidence is visible, use an empty evidence_refs array.
- Return one object per claim ID, exactly once.
- Return JSON only, shaped as {{\"claims\":[{{\"claim_id\":\"mr1-001\",\"epistemic_status\":\"SUPPORTED\",\"register\":\"literal\",\"evidence_refs\":[],\"rationale\":\"brief\"}}]}}.

BEGIN SUBSTRATE CONTEXT
{context}
END SUBSTRATE CONTEXT

BEGIN ADVERSARIAL REPORT
{report_text}
END ADVERSARIAL REPORT

FROZEN CLAIM IDS AND TEXT
{claim_lines}
"""


def parse_consumer_output(payload: Any, built_claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("claims"), list):
        raise EmpiricalError("consumer response must be a JSON object with a claims array")
    source_by_id = {row["id"]: row for row in built_claims}
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for raw in payload["claims"]:
        if not isinstance(raw, dict):
            raise EmpiricalError("consumer claim entries must be objects")
        claim_id = raw.get("claim_id")
        if claim_id not in source_by_id:
            raise EmpiricalError(f"consumer returned unknown claim ID: {claim_id!r}")
        if claim_id in seen:
            raise EmpiricalError(f"consumer returned duplicate claim ID: {claim_id}")
        seen.add(claim_id)
        status = raw.get("epistemic_status")
        register = raw.get("register")
        if status not in mixed_register_core.PRIMARY_STATUSES:
            raise EmpiricalError(f"{claim_id}: invalid epistemic_status")
        if register not in mixed_register_core.REGISTER_VALUES:
            raise EmpiricalError(f"{claim_id}: invalid register")
        refs = raw.get("evidence_refs")
        if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
            raise EmpiricalError(f"{claim_id}: evidence_refs must be non-empty strings")
        rationale = raw.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise EmpiricalError(f"{claim_id}: rationale is required")
        result.append({
            "claim_id": claim_id,
            "claim_sha256": mixed_register_core._claim_sha256(source_by_id[claim_id]),
            "epistemic_status": status,
            "register": register,
            "evidence_refs": sorted(set(refs)),
            "rationale": rationale.strip(),
        })
    if seen != set(source_by_id):
        missing = sorted(set(source_by_id) - seen)
        raise EmpiricalError("consumer omitted frozen claims: " + ", ".join(missing))
    order = {claim_id: index for index, claim_id in enumerate(source_by_id)}
    result.sort(key=lambda row: order[row["claim_id"]])
    return result


def visible_evidence_refs(context: str) -> set[str]:
    refs = set(re.findall(r"\bsrc:[A-Za-z0-9_.:-]+", context))
    for line in context.splitlines():
        if line.startswith("EVIDENCE_REF="):
            value = line.split("=", 1)[1].strip()
            if value:
                refs.add(value)
        if line.startswith("ITEM\t"):
            parts = line.split("\t", 3)
            if len(parts) >= 3 and parts[2]:
                refs.add("file:" + parts[2])
    return refs


def constrain_evidence_refs(root: Path, claims: list[dict[str, Any]], context: str) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    allowed = visible_evidence_refs(context)
    normalized: list[dict[str, Any]] = []
    violations: list[dict[str, str]] = []
    for claim in claims:
        row = dict(claim)
        kept: list[str] = []
        for ref in claim["evidence_refs"]:
            if ref in allowed and mixed_register_core._source_ref_exists(root, ref):
                kept.append(ref)
            else:
                violations.append({"claim_id": claim["claim_id"], "evidence_ref": ref})
        row["evidence_refs"] = sorted(set(kept))
        normalized.append(row)
    return normalized, violations


class OllamaClient:
    def __init__(self, base_url: str, model: str, num_ctx: int = 32768, seed: int = 18437):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.num_ctx = num_ctx
        self.seed = seed

    def _json(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = canonical_json_bytes(body) if body is not None else None
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if body is not None else {},
        )
        try:
            with urllib.request.urlopen(request, timeout=1800) as response:
                value = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise EmpiricalError(f"Ollama request failed for {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise EmpiricalError(f"Ollama returned non-object JSON for {path}")
        return value

    @staticmethod
    def _row_names(row: dict[str, Any]) -> set[str]:
        return {
            str(value).casefold()
            for value in (row.get("name"), row.get("model"))
            if isinstance(value, str) and value
        }

    def identity(self) -> ModelIdentity:
        tags = self._json("GET", "/api/tags")
        models = [row for row in tags.get("models", []) if isinstance(row, dict)] if isinstance(tags.get("models"), list) else []
        wanted = self.model.casefold()
        exact = [row for row in models if wanted in self._row_names(row)]
        if not exact and ":" not in wanted:
            canonical_latest = wanted + ":latest"
            exact = [row for row in models if canonical_latest in self._row_names(row)]
        if len(exact) != 1:
            raise EmpiricalError(
                f"Ollama model {self.model!r} did not resolve to exactly one installed canonical tag; "
                "use an explicit tag such as name:tag"
            )
        row = exact[0]
        digest = row.get("digest")
        if not isinstance(digest, str) or not digest:
            raise EmpiricalError(f"installed Ollama model {self.model!r} has no immutable digest")
        names = [value for value in (row.get("name"), row.get("model")) if isinstance(value, str) and value]
        if not names:
            raise EmpiricalError("resolved Ollama model has no canonical name")
        canonical = next((name for name in names if name.casefold() == wanted), None)
        if canonical is None and ":" not in wanted:
            canonical = next((name for name in names if name.casefold() == wanted + ":latest"), None)
        canonical = canonical or names[0]
        self.model = canonical
        return ModelIdentity("ollama-local", canonical, digest)

    def generate(self, prompt: str) -> tuple[dict[str, Any], dict[str, Any], str]:
        response = self._json("POST", "/api/generate", {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "seed": self.seed,
                "num_ctx": self.num_ctx,
            },
        })
        raw = response.get("response")
        if not isinstance(raw, str):
            raise EmpiricalError("Ollama response has no text body")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise EmpiricalError(f"consumer did not return valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise EmpiricalError("consumer JSON root must be an object")
        metadata = {
            "prompt_eval_count": response.get("prompt_eval_count"),
            "eval_count": response.get("eval_count"),
            "total_duration": response.get("total_duration"),
            "load_duration": response.get("load_duration"),
            "raw_response_sha256": _sha256(raw.encode("utf-8")),
        }
        return payload, metadata, raw


def build_claim_audit(
    manifest: dict[str, Any],
    identity: ModelIdentity,
    condition: str,
    variant: str,
    claims: list[dict[str, Any]],
    carrier_sha256: str,
    raw_response_sha256: str,
) -> dict[str, Any]:
    return {
        "type": "qsol-claim-audit",
        "schema_version": "1.0.0",
        "artifact_class": "derived_evaluation",
        "execution_kind": "empirical_consumer",
        "run_id": f"mixed-register-cold:{identity.model_id}:{condition}:{variant}",
        "evaluator": {
            "provider": identity.provider,
            "model_id": identity.model_id,
            "immutable_model_revision": identity.immutable_revision,
        },
        "condition": condition,
        "tool_mode": "repository" if condition == "tool-enabled" else "none",
        "run_date": str(date.today()),
        "prompt_test_identity": f"MIXED-REGISTER/1-COLD-CONSUMER/{EMPIRICAL_SPEC_VERSION}:{variant}",
        "classification_contract_version": mixed_register_core.CLASSIFICATION_CONTRACT_VERSION,
        "evaluation_bundle_sha256": manifest["bundle_sha256"],
        "substrate": manifest["substrate"],
        "artifact_hashes": {
            "evaluation_bundle": manifest["bundle_sha256"],
            "empirical_carrier": carrier_sha256,
            "raw_consumer_response": raw_response_sha256,
        },
        "claims": claims,
        "summary": mixed_register_core._derived_summary(claims),
    }


def _rate(ok: int, total: int) -> float | None:
    return round(ok / total, 6) if total else None


def cold_consumer_gate(
    built_claims: list[dict[str, Any]],
    audit: dict[str, Any],
    report: dict[str, Any],
    evidence_ref_violations: list[dict[str, str]] | None = None,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    limits = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        limits.update(thresholds)
    violations = evidence_ref_violations or []
    actual = {row["claim_id"]: row for row in audit["claims"]}
    per_status: dict[str, float | None] = {}
    for status in mixed_register_core.PRIMARY_STATUSES:
        ids = [row["id"] for row in built_claims if row["expected"]["epistemic_status"] == status]
        per_status[status] = _rate(sum(actual[item]["epistemic_status"] == status for item in ids), len(ids))
    satire_ids = [row["id"] for row in built_claims if row["expected"]["register"] == "satire"]
    satire_accuracy = _rate(sum(actual[item]["register"] == "satire" for item in satire_ids), len(satire_ids))
    metrics = report["metrics"]
    checks = {
        "primary_status_accuracy": metrics["primary_status_accuracy"] >= limits["primary_status_accuracy_min"],
        "register_accuracy": metrics["register_accuracy"] >= limits["register_accuracy_min"],
        "evidence_fidelity": metrics["evidence_fidelity"] >= limits["evidence_fidelity_min"],
        "unsupported_assertion_rate": metrics["unsupported_assertion_rate"] <= limits["unsupported_assertion_rate_max"],
        "per_status_accuracy": all(value is not None and value >= limits["per_status_accuracy_min"] for value in per_status.values()),
        "satire_register_accuracy": satire_accuracy is not None and satire_accuracy >= limits["satire_register_accuracy_min"],
        "evidence_reference_integrity": len(violations) == 0,
    }
    return {
        "passed": all(checks.values()),
        "thresholds": limits,
        "checks": checks,
        "per_status_accuracy": per_status,
        "satire_register_accuracy": satire_accuracy,
        "evidence_ref_violation_count": len(violations),
        "interpretation": "Passing is evidence for this immutable model/run only; it is not a universal model or substrate claim.",
    }


def experiment_summary(results: list[dict[str, Any]], manifest: dict[str, Any], identity: ModelIdentity) -> dict[str, Any]:
    indexed = {(row["condition"], row["variant"]): row for row in results}
    rows: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        guarded = indexed.get((condition, "guarded"))
        ablated = indexed.get((condition, "ablated"))
        if guarded is None or ablated is None:
            raise EmpiricalError(f"missing paired empirical result for {condition}")
        gm = guarded["report"]["metrics"]
        am = ablated["report"]["metrics"]
        rows.append({
            "condition": condition,
            "guarded": gm,
            "ablated": am,
            "guard_effect": {
                "primary_status_accuracy_delta": round(gm["primary_status_accuracy"] - am["primary_status_accuracy"], 6),
                "register_accuracy_delta": round(gm["register_accuracy"] - am["register_accuracy"], 6),
                "evidence_fidelity_delta": round(gm["evidence_fidelity"] - am["evidence_fidelity"], 6),
                "unsupported_assertion_rate_reduction": round(am["unsupported_assertion_rate"] - gm["unsupported_assertion_rate"], 6),
            },
            "cold_consumer_gate": guarded["cold_consumer_gate"],
        })
    passing = [row["condition"] for row in rows if row["cold_consumer_gate"]["passed"]]
    return {
        "type": "qsol-mixed-register-empirical-summary",
        "schema_version": "1.0.0",
        "empirical_spec_version": EMPIRICAL_SPEC_VERSION,
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
        "variants": list(VARIANTS),
        "rows": rows,
        "cold_consumer_demonstrated": bool(passing),
        "passing_guarded_conditions": passing,
        "interpretation": (
            "Paired guarded/ablated single-model measurements are descriptive empirical evidence. "
            "Positive deltas do not by themselves establish statistical or cross-model causality."
        ),
    }
