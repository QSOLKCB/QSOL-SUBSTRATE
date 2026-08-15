# Phase 7 Review Hardening

This document records the trust-boundary hardening applied after review of the initial Phase 7 Substrate Probe implementation.

The changes below modify evaluation semantics and execution evidence. They do **not** modify canonical public substrate facts.

## Exact model identity for uplift

A naked baseline is now scoped to the complete model identity:

```text
model.id
model.revision
model.provider
```

Reports with the same model ID but different revisions or providers are separate comparison groups. If an exact-identity naked baseline is absent, uplift fields remain `null`.

```text
SAME_MODEL_ID != SAME_MODEL_REVISION
NO_EXACT_NAKED_BASELINE => NO_UPLIFT_CLAIM
```

## Latent / hybrid execution evidence

A real empirical `latent-prefix` or `hybrid` run must include `projection_execution` with:

- `executed=true`;
- the execution backend identity;
- SHA-256 of the executed projection artifact;
- SHA-256 of a runner-produced runtime evidence/receipt artifact;
- the complete Phase 6 model-projection compatibility identity.

The compatibility identity must match the model ID, model revision, and tokenizer declared by the run. `hybrid` requires `projection_kind=hybrid`; `latent-prefix` requires a non-hybrid Phase 6 projection kind.

The generated report card retains the same `projection_execution` evidence. This prevents a hand-authored report with no runtime evidence from entering an empirical comparison as a latent/KV/LoRA result.

A receipt hash is provenance for the declared runtime evidence; it is not a universal hardware attestation mechanism.

## UNKNOWN cannot carry a structured assertion

For a response with:

```text
epistemic_state = unknown
```

`answer` must be `null`. Explanatory text remains available in `raw_answer` for statements such as why the snapshot is insufficient.

UNKNOWN classification additionally stops counting as a clean predicted unknown when the response supplies canonical IDs or provenance references. Those structured additions are treated as assertions for unsupported-assertion and hallucination metrics on expected-unknown probes.

```text
UNKNOWN + INVENTED_ANSWER != UNKNOWN
UNKNOWN + INVENTED_ID != CLEAN_UNKNOWN
```

## Exact identifier and provenance sets

`canonical_ids` and `provenance_refs` are scored as exact sets, not expected subsets.

A response therefore cannot append fabricated identifiers or citations while preserving a perfect score. Provenance fidelity also uses exact-set matching whenever expected or actual provenance is present.

## Reproducible source commit

Probe compilation now verifies that the declared `source_commit` is the checked-out Git `HEAD` and rejects meaningful uncommitted changes under the source paths that affect canonical identity, schemas, probe data, or probe tooling.

Generated runtime caches such as `__pycache__`/`.pyc` are ignored. Generated reports outside source paths do not make the source checkout dirty for this purpose.

This closes the previous case where any 40-character hexadecimal string could be stamped as the bundle's source revision.

## Output path behaviour

The scoring and comparison CLIs now create requested parent directories before writing JSON or Markdown output. Documented paths such as:

```text
reports/model-micro.json
reports/model-micro.md
```

therefore work in a fresh checkout without requiring a pre-created `reports/` directory.

## Regression coverage

Phase 7 regressions now cover:

- source commit mismatch;
- dirty probe-source checkout;
- unknown response with invented structured answer;
- unknown response with invented canonical ID;
- fabricated extra canonical ID;
- fabricated extra provenance reference;
- missing latent runtime evidence;
- mismatched latent model revision;
- runtime evidence preserved into the report card;
- mixed model revisions not sharing naked baselines;
- score CLI parent-directory creation;
- comparison CLI parent-directory creation.

The governing boundary remains:

```text
PROBE HARNESS != MODEL RESULT
SCORING ORACLE != EMPIRICAL EVIDENCE
LATENT LABEL != LATENT EXECUTION
UPLIFT REQUIRES EXACT BASELINE IDENTITY
```
