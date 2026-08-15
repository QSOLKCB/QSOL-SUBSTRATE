# Substrate Probe

Phase 7 turns QSOL-SUBSTRATE from a context-delivery system into a deterministic evaluation protocol.

The central question is:

> **How much substrate is enough?**

The probe measures whether a model behaves better when the same canonical public substrate is delivered through different representations. It does not assume that more context is better, and it does not treat a successful build, retrieval hit, prefix recipe, or scoring self-test as evidence of improved model behaviour.

## Scientific boundary

```text
PROBE HARNESS != MODEL RESULT
SCORING ORACLE != EMPIRICAL EVIDENCE
RETRIEVAL HIT != ANSWER QUALITY
LATENT RECIPE != EXECUTED LATENT ARTIFACT
SAME SNAPSHOT IS REQUIRED FOR COMPARABLE UPLIFT
```

Repository CI builds and validates the probe and runs a deterministic **scoring oracle**. The oracle reads the declared expected answers directly. Its only purpose is to prove that the scorer can recover the declared ground truth and that all metrics are operational.

The oracle is explicitly marked `execution_kind=scoring_oracle` and comparison tooling refuses to treat oracle reports as empirical model results.

## Probe corpus

Phase 7 contains 48 deterministic cases:

```text
24 substrate probes
24 YEAH-NAH/1 pragmatic probes
48 total
```

The substrate probe covers:

- exact known facts;
- unknown answers and unsupported assertions;
- public provenance;
- entity and alias resolution;
- contradiction handling;
- snapshot/freshness limits;
- satire versus biography;
- formalization versus empirical claims;
- project relationships;
- publication and DOI identity;
- omission semantics (`absence != false`).

The source files are:

```text
probe/substrate-probe.jsonl
probe/yeah-nah-1.jsonl
probe/conditions.json
```

Generated deterministic output is:

```text
dist/probes/
├── substrate-probe.jsonl
├── yeah-nah-1.jsonl
├── conditions.json
├── scoring-contract.json
└── manifest.json
```

The generated manifest records the exact substrate snapshot, source commit, canonical substrate SHA-256, probe counts, condition identities, per-file hashes, and aggregate probe-bundle fingerprint.

## Comparison conditions

The same model can be evaluated under eight declared conditions:

```text
naked
micro
standard
full
vector
latent-prefix
hybrid
tool-enabled
```

They correspond to:

1. **naked** — no QSOL substrate context;
2. **micro** — Phase 5 MICRO text capsule;
3. **standard** — Phase 5 STANDARD text capsule;
4. **full** — Phase 5 FULL text capsule;
5. **vector** — Phase 6 provenance-closed vector-selected context;
6. **latent-prefix** — a real model-specific latent/KV/prefix projection execution;
7. **hybrid** — model-specific epistemic prefix plus inspectable factual text;
8. **tool-enabled** — bootstrap contract plus live repository/retrieval access.

A textual copy of `epistemic-prefix.txt` is not a substitute for a real latent-prefix experiment. Runners claiming `latent-prefix` or `hybrid` should preserve the Phase 6 model compatibility identity and record the actual model-specific projection used.

## Build and validate the probe

```bash
python tools/build_probes.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/probes

python tools/validate_probe_bundle.py --bundle dist/probes
```

Validation recompiles the bundle from the source probe corpus and requires deterministic equality. Symlinks, undeclared files, malformed manifests, changed test cases, changed scoring contracts, or mismatched source identities fail closed.

## Model-run contract

Real model runners produce one `qsol-probe-model-run` JSON document conforming to:

```text
schema/model-run.schema.json
```

Every response preserves the raw model answer for audit, but scoring is based on a small structured envelope:

```text
probe_id
raw_answer
epistemic_state
answer
canonical_ids
provenance_refs
classification
sarcasm
hostility
intent_polarity
severity
confidence
freshness_limited
```

This avoids using a second LLM as an unversioned subjective grader.

The run also records:

```text
run_id
execution_kind
model id / revision / provider
condition
probe_bundle_sha256
substrate identity
input/output token usage
tokenizer identity
```

A run bound to a different probe fingerprint or substrate snapshot is rejected.

## Score a real model run

```bash
python tools/score_probe_run.py \
  --bundle dist/probes \
  --run runs/qwen3-8b-micro.json \
  --output reports/qwen3-8b-micro.json \
  --markdown reports/qwen3-8b-micro.md
```

The scorer validates the probe bundle before reading its ground truth, validates the model-run schema, requires exactly one response per probe ID, and validates the generated report card against `schema/probe-report.schema.json`.

## Compare conditions and models

```bash
python tools/compare_probe_reports.py \
  reports/qwen3-8b-naked.json \
  reports/qwen3-8b-micro.json \
  reports/qwen3-8b-vector.json \
  --output reports/qwen3-8b-comparison.json \
  --markdown reports/qwen3-8b-comparison.md
```

Comparison requires an identical probe bundle fingerprint and substrate identity across all supplied reports.

Uplift is computed against the **same model's naked baseline**. If no naked baseline exists for a model, uplift fields remain null instead of borrowing another model's baseline.

## General metrics

Phase 7 computes:

- overall accuracy;
- factual accuracy;
- unsupported assertion rate;
- `UNKNOWN` precision;
- `UNKNOWN` recall;
- alias resolution accuracy;
- provenance fidelity;
- contradiction handling;
- claim-boundary preservation;
- context/token efficiency;
- hallucination rate;
- substrate uplift over naked baseline;
- hallucination reduction relative to naked baseline.

Token efficiency uses the tokenizer usage reported by the actual model runner. It is therefore model/run-specific and is not confused with the portable build-budget tokenization used by Phase 5.

## YEAH-NAH/1 — Australian Pragmatic Humour Probe

YEAH-NAH/1 is a deterministic cultural-pragmatics stress test. It is not a claim that Australian English is always sarcastic, hostile, or culturally uniform.

Its purpose is to test whether models can use conversational context without either:

1. naively taking every surface form literally; or
2. over-classifying ambiguous language as sarcasm or hostility.

The suite includes:

- literal controls;
- paired literal/sarcastic uses of `Nice one, mate`;
- deadpan;
- high-severity understatement;
- mock hostility;
- actual-hostility controls;
- affectionate insults;
- familiar banter;
- self-deprecation;
- positive/negative polarity reversal;
- `yeah nah` and `nah yeah`;
- context-free uncertainty controls;
- relationship-familiarity controls;
- speaker-confirmed sarcasm.

Normative interpretation guards:

```text
SURFACE_MEANING != NECESSARILY_INTENDED_MEANING
SARCASM = INFERRED UNLESS SPEAKER_CONFIRMED
UNCERTAIN != SARCASTIC
BANTER != HOSTILITY
UNDERSTATEMENT != LOW_SEVERITY
CONTEXT > TOKEN_POLARITY
```

Unconfirmed pragmatic classifications use epistemic state `inferred`. The explicit speaker-confirmed sarcasm control uses `known`.

YEAH-NAH/1 metrics are:

- overall pragmatic accuracy;
- sarcasm precision;
- sarcasm recall;
- literal-meaning error rate on literal-trap cases;
- banter misclassification rate;
- hostility false-positive rate;
- understatement severity-preservation rate;
- confidence Brier score;
- cultural-context uplift over the same model's naked baseline.

## CI scoring oracle

CI runs:

```bash
python tools/build_probe_oracle.py \
  --bundle dist/probes \
  --output probe-oracle-run.json

python tools/score_probe_run.py \
  --bundle dist/probes \
  --run probe-oracle-run.json \
  --output probe-oracle-report.json \
  --markdown probe-oracle-report.md \
  --require-perfect-oracle
```

A passing `48/48` oracle score means:

> the declared ground truth, response contract, scorer, metric implementation, report schema, and CI plumbing agree.

It does **not** mean:

> any real model achieved 48/48.

The comparison engine refuses oracle reports to make this boundary mechanical rather than rhetorical.

## Reproducible empirical runs

For a publishable comparison, preserve at least:

```text
model ID
model revision
provider/runtime
quantization or tensor precision where applicable
tokenizer identity
substrate source commit
substrate SHA-256
probe bundle SHA-256
condition
adapter/capsule/vector/projection identity
input/output token counts
raw model outputs
structured response envelope
report-card JSON
execution date
```

For latent-prefix, KV-cache, LoRA, or hybrid conditions, also retain the Phase 6 compatibility manifest/fingerprint.

## Interpretation boundary

A high score does not make the probe a source of canonical facts. The canonical public substrate remains the truth store.

The probe is an evaluation artifact that asks whether a model preserves those facts and epistemic boundaries under different delivery conditions.

The research target is not merely:

> Which model scored highest?

It is also:

> Which model needed the least substrate to stop inventing the lore?
