# MIXED-REGISTER/1 and Consumer Audit Integrity

Phase 9 adds a deterministic adversarial evaluation for material in which supported facts, contradictions, unavailable claims, and satire are deliberately interleaved.

## Core rule

`ADJACENT_TRUTH != INHERITED_TRUTH`

A supported sentence does not lend evidence to the next sentence. Every substantive claim is audited against claim-local evidence.

## Two independent classification dimensions

MIXED-REGISTER/1 does not use `fiction` or `satire` as a replacement for factual status.

Primary epistemic status is one of:

- `SUPPORTED`
- `CONTRADICTED`
- `UNAVAILABLE_UNVERIFIED`

Register is recorded separately, for example `literal` or `satire`.

This avoids the counting ambiguity that occurs when a humorous claim is simultaneously treated as both a truth-status category and a style/register category.

## Frozen evaluation bundle

`tools/build_mixed_register.py` compiles:

```text
dist/mixed-register-1/
├── report.md
├── claims.jsonl
├── oracle.json
├── scoring-contract.json
├── scorer.py
├── mixed_register_core.py
├── substrate_integrity.py
├── substrate_integrity_core.py
├── toolless_core.py
└── manifest.json
```

The manifest binds the exact source substrate commit/SHA-256, expected claim-ID set, each file hash, and one complete evaluation-bundle fingerprint. The scorer CLI, scoring implementation, and its internal repository dependencies are packaged and fingerprinted so scorer-semantic changes necessarily change bundle identity. A corpus-text hash alone is not sufficient identity.

The source fixtures under `probe/` and all generated Phase 9 artifacts are evaluation material. They are never canonical source evidence.

## Claim-audit contract

A consumer response can be normalized into the strict `schema/claim-audit.schema.json` envelope. Every run records:

- `execution_kind`;
- provider, model ID, and immutable model revision separately;
- tool mode and run date;
- prompt/test identity;
- classification-contract version;
- complete evaluation-bundle SHA-256;
- exact substrate identity;
- artifact hashes;
- one result for every frozen claim ID;
- mechanically derived summary counts.

Validation rejects missing, extra, and duplicate claim IDs; altered claim hashes; mismatched bundle/substrate identity; self-referential evaluation evidence; and hand-maintained summary totals that do not match the claim objects.

## Oracle boundary

`tools/build_mixed_register_oracle.py` produces an `execution_kind=scoring_oracle` self-test. It proves only that the deterministic scorer can recover frozen expected answers.

Oracle and other non-empirical execution kinds are mechanically forbidden from empirical comparisons.

## Reproducible empirical comparison

`tools/compare_mixed_register_reports.py` accepts only `empirical_consumer` reports and requires identical:

- complete evaluation-bundle fingerprint;
- source substrate identity;
- provider;
- model ID;
- immutable model revision.

This prevents provider/model drift from being misreported as substrate uplift or regression. Empirical `latent-prefix` and `hybrid` audits additionally require a Phase 6 compatibility identity, its fingerprint, the exact executed projection artifact SHA-256, and runtime evidence proving that the declared artifact actually ran; textual simulations cannot use those condition labels.

## Local negative boundaries

Compact tool-less projections preserve selected negative-boundary semantics beside the records they constrain:

- selective project/publication registries emit `REGISTRY_OMISSION != NEGATIVE_FACT`;
- the QSOL-IMC legal/corporate nonclaim emits `UNASSERTED_LEGAL_OR_CORPORATE_STATUS != FALSE`;
- project-tag-derived satire/formalization/model-observation boundaries remain local;
- `MICRO` repeats the core epistemic guards, including `ADJACENT_TRUTH != INHERITED_TRUTH`.

This is deliberate semantic redundancy. Compactness may not be purchased by separating a tempting positive claim from the boundary that prevents over-generalisation.

## Self-publication closure

QSOL-SUBSTRATE v1.0.0 is closed through one canonical chain:

```text
src:qsol-substrate-v1.0.0-release
        |
        v
publication:qsol-substrate-v1.0.0
        ^
        |
rel:qsol-substrate-publishes-qsol-substrate-v1.0.0
        ^
        |
project:qsol-substrate
```

`tools/validate_self_publication.py` checks that this chain agrees with README DOI metadata, `CITATION.cff`, and `.zenodo.json` for DOI `10.5281/zenodo.21959180`, v1.0.0, and the pinned release commit.

## Consumer ergonomics

`ai/retrieval-hints.json` and `ai/freshness-recipes.json` are noncanonical navigation/verification aids. `schema/conflict-record.schema.json` provides a first-class shape for unresolved source disagreement. None of these surfaces can create a canonical fact.

## What CI can and cannot prove

CI can prove deterministic bundle identity, schema validity, exact claim coverage, summary arithmetic, oracle separation, projection propagation, provenance closure, and metadata consistency.

CI does **not** prove that a real model behaves better. Cross-model or cross-delivery uplift remains empirical evidence and must be backed by immutable model-run records.
