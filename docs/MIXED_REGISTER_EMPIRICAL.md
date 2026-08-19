# Phase 9 empirical mixed-register consumer experiment

This experiment operationalises the two remaining Phase 9 empirical questions without promoting model output into canonical substrate truth.

## Questions

1. Do **local nonclaims** plus `ADJACENT_TRUTH != INHERITED_TRUTH` improve classification of the frozen `MIXED-REGISTER/1` corpus?
2. Can a **cold consumer** classify supported, contradicted, unavailable/unverified, and satirical claims without treating plausibility or neighbouring truth as provenance?

## Paired design

Every immutable model revision is run against the same frozen evaluation bundle under five delivery conditions:

- `MICRO`
- `STANDARD`
- `FULL`
- `vector`
- `tool-enabled`

Each condition is executed twice.

`guarded` uses the normal delivery surface. `ablated` removes only the local boundary treatment under test: `BOUNDARY` lines, `ADJACENT_TRUTH != INHERITED_TRUTH`, and the local satire/formalization/legal-status/registry/model-observation guards. General uncertainty semantics such as `UNKNOWN != FALSE` remain in place. This prevents the ablation from becoming “remove all epistemics and see what happens.”

The model receives the full adversarial report plus the exact frozen claim IDs. It never receives the oracle or expected labels.

## Retrieval conditions

`vector` uses the repository's deterministic `qsol-hash-embed-v1` vector substrate. Each frozen claim text is the retrieval query. Retrieved records are provenance-closed before they are rendered.

`tool-enabled` uses deterministic lexical search over the canonical repository records. The harness owns the repository-retrieval tool boundary; it does not consult the oracle or expected answers. This makes the condition reproducible even for local models that do not expose a provider-specific function-calling API.

For guarded retrieval, local `BOUNDARY` semantics are rendered beside the canonical records they constrain. The ablated twin removes only those local guards.

## Cold-consumer rule

A run is cold when the consumer starts with no prior QSOL context and is instructed to use only the supplied carrier/retrieval evidence. The report itself is an evaluation target and may never become evidence.

The original cold-consumer gate requires:

- primary epistemic-status accuracy >= 0.90;
- register accuracy >= 0.90;
- evidence fidelity >= 0.80;
- unsupported-assertion rate == 0;
- accuracy >= 0.80 inside each primary status class;
- satire-register accuracy >= 0.80.

Phase 9 closure adds a targeted adjacency gate rather than relying only on aggregate accuracy. An **adjacency trap** is derived mechanically as any non-supported claim in a paragraph that also contains at least one supported claim. The frozen corpus currently contains 16 such traps.

A guarded condition closes the cold-consumer criterion only when the original gate passes **and**:

- adjacency-trap status accuracy >= 0.80;
- adjacency false-support rate == 0;
- unavailable/unverified status accuracy >= 0.80;
- unavailable/unverified spurious-evidence rate == 0.

This directly tests the failure mode “the sentence beside this one was true, therefore this claim may borrow its provenance.”

Passing is evidence only for the recorded immutable model digest and run. It is not a claim that all models, prompts, or future revisions behave the same way.

## Local Ollama runner

Build/run:

```bash
ollama pull qwen2.5:3b
python tools/run_mixed_register_empirical.py \
  --model qwen2.5:3b \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/empirical/mixed-register

python tools/close_mixed_register_empirical.py \
  --empirical-dir dist/empirical/mixed-register
```

The runner builds fresh tool-less, vector, and `MIXED-REGISTER/1` bundles from the checked-out commit, resolves the immutable Ollama model digest, performs the ten paired runs, normalises only explicitly visible evidence references, scores each audit with the canonical Phase 9 scorer, and writes `summary.json`.

The closure pass writes:

```text
dist/empirical/mixed-register/
├── summary.json
├── closure.json
├── closure.md
├── audits/
├── reports/
├── carriers/
├── prompts/
└── raw/
```

Before deriving any metric, the closure pass verifies every available audit and scored report against `summary.json`: complete evaluation-bundle and substrate identity, immutable provider/model revision, condition and guarded/ablated run identity, plus the recorded prompt, carrier, raw-response, audit, and report hashes. Mixed-run or edited evidence is refused even when each individual JSON file remains schema-shaped.

`closure.json` derives adjacency traps from the frozen corpus, computes targeted guarded-versus-ablated metrics, classifies each condition as `improved`, `neutral`, `degraded`, `mixed`, or `unavailable`, and records whether at least one guarded condition satisfies the stricter cold-consumer criterion.

Generated results are `derived_evaluation`; they do not become canonical `source_refs`.

## Interpreting guard effect

For each condition the original summary reports guarded-minus-ablated deltas for status accuracy, register accuracy, and evidence fidelity, plus the reduction in unsupported assertions.

The closure adds:

- adjacency-trap status-accuracy delta;
- adjacency false-support-rate reduction;
- adjacency evidence-fidelity delta;
- unavailable/unverified status-accuracy delta;
- unavailable/unverified spurious-evidence reduction;
- satire-register and satire-status deltas.

A condition is `improved` when at least one measured delta moves in the desired direction and none move backwards. `degraded` is the inverse, `mixed` records movement in both directions, and `neutral` means the measured deltas are all zero. The repository also records whether improvement is observed in any condition and whether improvement occurs without degradation across the complete five-condition matrix.

These are descriptive paired measurements for one immutable model revision. A positive delta is **not** sufficient by itself to claim statistical significance or cross-model causality. Replication across immutable model revisions remains a separate empirical step.

## CI evidence

The Phase 9 empirical workflow now runs the cold Ollama consumer on pull requests that modify this empirical harness. This keeps the two roadmap exit questions tied to an actual open-weight model execution rather than a scoring oracle.

The workflow binds the evidence to the exact PR head commit and immutable Ollama digest, publishes both the aggregate and adjacency-specific metrics, and uploads the complete prompts, carriers, raw responses, audits, reports, summary, and closure artifacts for inspection.
