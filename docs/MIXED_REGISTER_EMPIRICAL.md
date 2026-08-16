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

The strict default cold-consumer gate requires:

- primary epistemic-status accuracy >= 0.90;
- register accuracy >= 0.90;
- evidence fidelity >= 0.80;
- unsupported-assertion rate == 0;
- accuracy >= 0.80 inside each primary status class;
- satire-register accuracy >= 0.80.

Passing is evidence only for the recorded immutable model digest and run. It is not a claim that all models, prompts, or future revisions behave the same way.

## Local Ollama runner

Build/run:

```bash
ollama pull qwen2.5:1.5b
python tools/run_mixed_register_empirical.py \
  --model qwen2.5:1.5b \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/empirical/mixed-register
```

The runner builds fresh tool-less, vector, and `MIXED-REGISTER/1` bundles from the checked-out commit, resolves the immutable Ollama model digest, performs the ten paired runs, normalises only explicitly visible evidence references, scores each audit with the canonical Phase 9 scorer, and writes `summary.json`.

Generated results are `derived_evaluation`; they do not become canonical `source_refs`.

## Interpreting guard effect

For each condition the summary reports guarded-minus-ablated deltas for status accuracy, register accuracy, and evidence fidelity, plus the reduction in unsupported assertions.

A positive delta is a measured effect for that exact run. It is **not** sufficient by itself to claim statistical significance or cross-model causality. Replication across immutable model revisions is a later empirical step, not something CI is allowed to invent.
