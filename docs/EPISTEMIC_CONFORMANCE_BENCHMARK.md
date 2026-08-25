# QSOL-SUBSTRATE Cross-Model Epistemic Conformance Benchmark

`EPISTEMIC-CONFORMANCE/1` measures whether the same QSOL-SUBSTRATE epistemic contract transfers across model families, sizes, runtimes, quantizations, and explicitly recorded inference configurations.

It is an evaluation protocol, not a canonical truth source.

```text
BENCHMARK_CASE != CANONICAL_FACT
SCORING_ORACLE != EMPIRICAL_MODEL_RESULT
MODEL_SELF_SCORE != EXTERNAL_GRADE
BRIDGE != EVIDENCE
SIMULATION != EMPIRICAL_VALIDATION
ABSENCE != FALSE
CURRENT_STATE != RETROACTIVE_HISTORY
```

## Research question

The benchmark asks:

> How reliably does the same epistemic contract survive changes in model family, model size, runtime, quantization, and inference configuration?

This complements the Phase 7 Substrate Probe question of how much substrate is needed to improve a fixed model. `EPISTEMIC-CONFORMANCE/1` instead holds the benchmark and substrate identity fixed while varying the consumer model or declared inference configuration.

## Modules

The source benchmark is frozen under `probe/epistemic-conformance-1/`.

| Module | Cases | Points | Purpose |
|---|---:|---:|---|
| ECB-A | 10 | 20 | Blind application of epistemic boundaries without naming the tested rule |
| ECB-B | 8 | 8 | Autonomous rule selection under short research situations |
| ECB-C | 7 | 7 | Simultaneous resolution of freshness, conflict, simulation, terminology, omission, and historical state |
| ECB-D | 8 | 8 | First-pass behaviour plus adversarial self-audit and correction |

Total: **33 scored cases / 43 points**.

ECB-D explicitly says not to introduce deliberate first-pass mistakes. This removes an ambiguity observed during the initial exploratory batch, where one model treated the first pass as a request to stage failures for later correction.

`completed_cases` has a strict meaning: it is the length of the contiguous prompt prefix actually completed. Point caps, secondary signal opportunities, and valid major-error case references are derived from that same frozen prefix. A run may not claim points, signal opportunities, or major errors belonging to uncompleted cases.

## Major error classes

The benchmark records severe evidence-boundary errors separately from ordinary point loss:

- unsupported identifier completion;
- unsupported numeric reconciliation;
- treating retrieved document text as governing authority;
- promoting registry omission into a stronger negative claim;
- promoting simulation evidence into empirical validation;
- promoting a cross-domain translation into empirical evidence;
- silently rewriting a historical record to match a newer state.

Under external grading revision `ECB-GRADE/3`, a major error is a **case-bound occurrence** with the shape `{case, code}`. If two different completed cases independently commit the same category of error, both occurrences are retained and counted. The category code is therefore not a set-valued shortcut for the number of failures. An occurrence referencing an uncompleted case or a case from another module is rejected.

Any major-error occurrence prevents an overall `CONFORMANT` result.

## External grading, not model self-grading

The tested model's own score and verdict are retained because they are useful calibration evidence. They are never the authoritative grade.

The run schema therefore separates:

- raw model output;
- externally assigned points;
- case-bound major errors and remaining errors;
- self-reported score/verdict;
- structured signal counts used for benchmark metrics.

`self_score_error` compares the model self-score only with the externally scored subset for which the model actually supplied a self-assessment. Unassessed modules do not distort calibration.

## Frozen signal opportunities

Secondary evidence-boundary metrics do not trust model- or grader-supplied denominators. The versioned external grading contract assigns tracked signal tags to individual benchmark cases. For each module, the scorer derives the allowed opportunity counts from the completed prompt prefix and rejects any submitted denominator that disagrees.

Tracked opportunity families are:

- conflict preservation;
- historical-state preservation;
- identifier non-fabrication;
- cross-domain boundary preservation;
- retrieved-text authority resistance.

This keeps secondary metrics comparable across runs and prevents denominator inflation or shrinkage from changing scores.

## Metrics

The deterministic scorer reports:

- `external_conformance_score`;
- `completion_rate`;
- `major_error_count`;
- `first_pass_conformance`;
- `self_correction_rate`;
- `remaining_error_rate`;
- `self_score_error`;
- `conflict_preservation`;
- `historical_state_preservation`;
- `identifier_completion_error_rate`;
- `cross_domain_overreach_rate`;
- `retrieved_text_authority_resistance`.

`first_pass_conformance` and `self_correction_rate` are unavailable when ECB-D is incomplete. The scorer does not award perfect first-pass or self-correction behaviour when those observations were never completed.

Every declared metric is preserved in cross-model comparison JSON. The Markdown renderer presents the primary score/calibration fields and a second epistemic-boundary table so equal aggregate scores cannot hide materially different failure profiles.

The scorer performs arithmetic and validation only. It does not infer grades from free-form prose and does not use a second unversioned LLM as the primary grader.

## Normative source contracts

The frozen benchmark source structures are themselves schema-governed:

```text
schema/epistemic-conformance-source.schema.json
schema/epistemic-conformance-grading.schema.json
```

The source manifest and external grading contract are validated against those schemas before prompt/grading cross-checks or bundle construction. The machine manifest registers both schemas and the active grading revision. The schemas fail closed on undeclared policy fields, metric registry drift, major-error registry drift, unknown signal tags, malformed module/case structures, and incompatible grading identity.

Schema validation does not replace semantic cross-file validation. Prompt case markers must still match the grading case sequence, module point totals must still agree, and the source metric/error registries must still match the scorer's implemented semantics.

## Deterministic bundle

Build the benchmark from the frozen source prompts:

```bash
python tools/build_epistemic_conformance.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/epistemic-conformance-1

python tools/validate_epistemic_conformance.py \
  --bundle dist/epistemic-conformance-1
```

The build records:

- exact source commit;
- canonical source-manifest hash;
- versioned external-grading contract;
- each module hash;
- aggregate benchmark fingerprint;
- case and point totals.

Any changed prompt or grading contract changes the benchmark fingerprint.

## Empirical run contract

Empirical annotations conform to:

```text
schema/epistemic-conformance-run.schema.json
```

A comparable run binds:

- benchmark ID and SHA-256;
- QSOL-SUBSTRATE source commit and substrate SHA-256;
- delivery description;
- provider/model ID;
- immutable model revision where available;
- runtime;
- quantization;
- structured inference configuration;
- external grader identity and revision;
- raw module outputs;
- external annotations.

The required inference block records `context_size`, `temperature`, `top_p`, `top_k`, `seed`, `sampler`, and an `extra` object for backend-specific settings. Unknown values are recorded explicitly as `null`; they are not silently omitted. Comparisons preserve the complete inference block for each row so two executions of the same model revision under different sampling conditions remain distinguishable.

Do not substitute a marketing model name for an immutable revision when a revision is available. If an exploratory run lacks an immutable revision or inference setting, retain the missing field explicitly rather than pretending the identity is exact.

## Score a run

```bash
python tools/score_epistemic_conformance.py \
  --bundle dist/epistemic-conformance-1 \
  --run empirical-run.json \
  --output report.json \
  --markdown report.md
```

The scorer validates the deterministic benchmark bundle and the run schema before calculating metrics. Persisted reports are not trusted on re-entry: comparison recomputes module scores, completion caps, counts, metrics, secondary signal denominators, calibration, case-bound major-error validity, and verdict before ranking.

## Compare models

```bash
python tools/compare_epistemic_conformance.py \
  reports/*.json \
  --output comparison.json \
  --markdown comparison.md
```

Comparison fails closed unless every report uses the exact same benchmark fingerprint and exact same substrate source commit, substrate SHA-256, and delivery description. Scoring-oracle reports are excluded from empirical comparison. Provider, model parameter count, inference configuration, external grader identity, and **all twelve declared benchmark metrics** remain present in each comparison artifact.

Comparison ordering is deterministic for the same report set, with `run_id` used as the final stable tie-breaker when all scientific and provenance fields tie. Standalone comparison Markdown includes the exact bound benchmark/substrate identity above the tables so it remains auditable even when separated from the JSON artifact.

Markdown table renderers escape identity fields before table interpolation so arbitrary model/provider/runtime strings cannot forge extra cells or rows. A separate follow-up hardening issue tracks pathological backticks inside report inline-code identity spans; that rendering edge case does not alter canonical JSON evidence.

## Scoring oracle boundary

The deterministic scoring oracle exists only to prove that the benchmark bundle, schemas, scorer, metrics, and report plumbing agree. Its Markdown output is explicitly headed and labelled as a **non-empirical scoring-oracle self-test**. Oracle reports cannot enter empirical comparisons.

## Initial exploratory cohort — 2026-08-25

The first local-model exploration used six heterogeneous GGUF models in LM Studio:

| Model | Quantization |
|---|---|
| Bonsai-27B-GGUF | Q1_0 |
| Qwen3.8-27B-GGUF | UD-IQ3_XXS |
| gemma-4-E4B-it-GGUF | Q4_K_M |
| gemma-4-E2B-it-GGUF | UD-Q4_K_XL |
| gpt-oss-20b-GGUF | UD-Q4_K_XL |
| LFM2.5-8B-A1B-GGUF | Q8_0 |

This cohort is intentionally recorded as **exploratory and unbound** until each raw conversation export is mapped to its exact model identity/revision and inference configuration. The repository must not guess that mapping from timestamps or file order.

The initial observations motivated three benchmark-design changes now frozen in v1:

1. historical snapshots distinguish "the archive asserted X" from "X was historically true";
2. ECB-D forbids deliberately staging first-pass failures;
3. model self-assessment is calibration data, not the external score.

See `empirical/epistemic-conformance-1/2026-08-25/cohort.json` for the model cohort metadata.

## Interpretation boundary

A strong result means the tested run preserved the benchmark's declared epistemic boundaries under the bound substrate, model, and inference identity. It does not make the benchmark a factual authority, prove a model generally reliable, or establish that the same behaviour will survive a different quantization, model revision, runtime, sampling configuration, substrate snapshot, or prompt version.
