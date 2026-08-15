# Usage

QSOL-SUBSTRATE can be consumed in several ways depending on the model or agent environment.

## Minimal use

For a capable model with repository access: provide the repository, instruct the model to read `ai/bootstrap.json` first, allow it to retrieve only context relevant to the current task, and require it to preserve the epistemic states defined in `ai/epistemic-contract.json`.

## File-upload / no-tools use

For chat systems that accept files but cannot browse repositories, use a deterministic Phase 5 tool-less capsule rather than an unversioned copy/paste subset:

```bash
python tools/build_toolless.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/toolless
```

Choose MICRO, STANDARD, or FULL according to the target context budget. Omitted facts remain unavailable, not false.

## Portable adapter use

For vendor/runner-specific transport, build the Phase 4 adapter bundle:

```bash
python tools/build_adapters.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/adapters
```

Adapters may reformat delivery but cannot redefine canonical facts.

## RAG / vector retrieval use

**Load `ai/bootstrap.json` first and follow its mandatory contract `load_order` before supplying any retrieved payload to a model.** Vector-selected context supplements the machine contract; it does not replace the epistemic, public-boundary, retrieval, or consumer contracts.

Build the deterministic Phase 6 reference index:

```bash
python tools/build_vectors.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/vectors
```

Retrieve provenance-closed context with:

```bash
python tools/retrieve_vector_context.py \
  "your query" \
  --bundle dist/vectors \
  --top-k 5
```

The retrieval CLI validates the complete vector bundle against the canonical substrate before emitting any payload. A tampered, stale, malformed, symlinked, or otherwise non-reproducible bundle is refused rather than treated as canonical context. Empty or featureless queries are also refused instead of returning arbitrary tie-broken records.

Every rendered context carries the substrate snapshot version, snapshot date, exact source commit, and canonical substrate SHA-256. If a context is saved inside this repository, `--output` is restricted to the dedicated `dist/retrieved/` subtree so retrieval output cannot overwrite vector, projection, adapter, or capsule artifacts.

The reference index keeps canonical IDs, provenance, epistemic state, visibility, and payload objects outside embedding coordinates. Similarity score is retrieval rank, not factual confidence.

If a learned embedding backend is introduced later, pin its exact model/revision/preprocessing identity. Do not silently swap embedding models while claiming the same derived artifact identity.

## Local model / latent-prefix experiments

Phase 6 supplies deterministic model-projection experiment recipes:

```bash
python tools/build_projections.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/projections
```

The recipes cover soft prompts/prefix tuning, virtual tokens, LoRA, KV-cache prefill, reusable prefix states, and hybrid epistemic-prefix + factual-text conditions.

Any actual model-specific artifact must have a compatibility identity matching `schema/model-projection-compatibility.schema.json`. A model revision, architecture, tokenizer, dimension, attention, KV-layout, tensor dtype, KV-cache dtype, or quantization change invalidates the artifact.

Use:

```bash
python tools/check_projection_compatibility.py \
  --expected previous-model-identity.json \
  --actual current-model-identity.json
```

A compatibility match does not make a latent artifact a factual source. Mutable facts should remain textual or retrieval-selected when practical.

## Phase 7 — deterministic model evaluation

Build and validate the probe bundle:

```bash
python tools/build_probes.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/probes

python tools/validate_probe_bundle.py --bundle dist/probes
```

The Phase 7 bundle contains 24 substrate epistemic/factual cases plus 24 `YEAH-NAH/1` Australian pragmatic-humour cases. It defines eight comparison conditions: naked, MICRO, STANDARD, FULL, vector-selected, latent-prefix, hybrid, and tool-enabled.

A real model runner emits one strict `qsol-probe-model-run` document conforming to `schema/model-run.schema.json`. Preserve the raw answer for audit, but also provide the structured scoring fields declared by the schema. This lets the deterministic scorer operate without using a second unversioned LLM as a subjective judge.

Score a run with:

```bash
python tools/score_probe_run.py \
  --bundle dist/probes \
  --run runs/model-micro.json \
  --output reports/model-micro.json \
  --markdown reports/model-micro.md
```

Compare empirical report cards with:

```bash
python tools/compare_probe_reports.py \
  reports/model-naked.json \
  reports/model-micro.json \
  reports/model-vector.json \
  --output reports/model-comparison.json \
  --markdown reports/model-comparison.md
```

Comparison requires an identical probe-bundle fingerprint and substrate identity. Uplift is computed against the same model's naked baseline; the tool does not borrow a baseline from another model.

CI also runs a deterministic scoring oracle. The oracle is a scorer self-test only: it reads declared ground truth, is marked `execution_kind=scoring_oracle`, and is mechanically rejected by the empirical comparison tool.

See `docs/SUBSTRATE_PROBE.md` for the full experimental contract, metrics, YEAH-NAH/1 interpretation rules, and real-run provenance requirements.

## Reproducible evaluation

Record at least:

```text
model identifier
model revision
provider/runtime
tokenizer identity
substrate snapshot/version
substrate commit
substrate SHA-256
probe bundle SHA-256
derived artifact kind
derived artifact SHA-256
adapter/capsule/vector/projection identity
comparison condition
input/output token usage
raw outputs
execution date
```

For latent-prefix, KV-cache, LoRA, or hybrid conditions, also retain the exact Phase 6 compatibility identity/fingerprint. For comparisons, keep the substrate and probe snapshot identical unless substrate sensitivity itself is the experiment.

## Expected benefit

The substrate can reduce errors caused by missing QSOL-specific context, ambiguous names, stale project relationships, unsupported inference, and naive pragmatic interpretation. It cannot guarantee correctness, fix unrelated world knowledge, or prevent every hallucination.

Phase 6 establishes transport/retrieval efficiency. Phase 7 provides the protocol that measures whether a real model actually behaves better under those delivery conditions.
