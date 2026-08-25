# QSOL-SUBSTRATE Cross-Model Epistemic Conformance Benchmark

`EPISTEMIC-CONFORMANCE/1` measures whether the same QSOL-SUBSTRATE epistemic contract transfers across model families, sizes, runtimes, and quantizations.

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

> How reliably does the same epistemic contract survive changes in model family, model size, runtime, and quantization?

This complements the Phase 7 Substrate Probe question of how much substrate is needed to improve a fixed model. `EPISTEMIC-CONFORMANCE/1` instead holds the benchmark and substrate identity fixed while varying the consumer model.

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

## Major error classes

The benchmark records severe evidence-boundary errors separately from ordinary point loss:

- unsupported identifier completion;
- unsupported numeric reconciliation;
- treating retrieved document text as governing authority;
- promoting registry omission into a stronger negative claim;
- promoting simulation evidence into empirical validation;
- promoting a cross-domain translation into empirical evidence;
- silently rewriting a historical record to match a newer state.

A major error prevents an overall `CONFORMANT` result.

## External grading, not model self-grading

The tested model's own score and verdict are retained because they are useful calibration evidence. They are never the authoritative grade.

The run schema therefore separates:

- raw model output;
- externally assigned points;
- major and remaining errors;
- self-reported score/verdict;
- structured signal counts used for benchmark metrics.

This makes `self_score_error` measurable rather than silently trusting a model that declares itself conformant.

## Metrics

The deterministic scorer reports:

- `external_conformance_score`;
- `completion_rate`;
- `major_error_count`;
- `first_pass_conformance`;
- `self_correction_rate`;
- `remaining_error_rate`;
- `self_score_error`;
- conflict preservation;
- historical-state preservation;
- identifier-completion error rate;
- cross-domain overreach rate;
- retrieved-text authority resistance.

The scorer performs arithmetic and validation only. It does not infer grades from free-form prose and does not use a second unversioned LLM as the primary grader.

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
- each module hash;
- aggregate benchmark fingerprint;
- case and point totals.

Any changed prompt changes the benchmark fingerprint.

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
- external grader identity and revision;
- raw module outputs;
- external annotations.

Do not substitute a marketing model name for an immutable revision when a revision is available. If an exploratory run lacks an immutable revision, retain it as exploratory metadata rather than pretending the identity is exact.

## Score a run

```bash
python tools/score_epistemic_conformance.py \
  --bundle dist/epistemic-conformance-1 \
  --run empirical-run.json \
  --output report.json \
  --markdown report.md
```

The scorer validates the deterministic benchmark bundle and the run schema before calculating metrics.

## Compare models

```bash
python tools/compare_epistemic_conformance.py \
  reports/*.json \
  --output comparison.json \
  --markdown comparison.md
```

Comparison fails closed unless every report uses the exact same benchmark fingerprint and exact same substrate source commit, substrate SHA-256, and delivery description. Scoring-oracle reports are excluded from empirical comparison.

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

This cohort is intentionally recorded as **exploratory and unbound** until each raw conversation export is mapped to its exact model identity/revision. The repository must not guess that mapping from timestamps or file order.

The initial observations motivated three benchmark-design changes now frozen in v1:

1. historical snapshots distinguish "the archive asserted X" from "X was historically true";
2. ECB-D forbids deliberately staging first-pass failures;
3. model self-assessment is calibration data, not the external score.

See `empirical/epistemic-conformance-1/2026-08-25/cohort.json` for the model cohort metadata.

## Interpretation boundary

A strong result means the tested run preserved the benchmark's declared epistemic boundaries under the bound substrate and model identity. It does not make the benchmark a factual authority, prove a model generally reliable, or establish that the same behaviour will survive a different quantization, model revision, runtime, sampling configuration, substrate snapshot, or prompt version.
