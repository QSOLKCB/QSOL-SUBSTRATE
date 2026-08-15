# Vector and Latent Substrate Projection

Phase 6 explores compact machine projections of QSOL-SUBSTRATE without changing the canonical public knowledge layer.

The governing rule is simple:

```text
CANONICAL SUBSTRATE = SOURCE OF TRUTH
VECTOR INDEX        = RETRIEVAL PROJECTION
PREFIX / KV / LORA  = MODEL-SPECIFIC PROJECTION
```

Derived projections are disposable. They may select, encode, cache, or transport canonical material, but they do not acquire independent factual authority.

## Vector substrate

Build and validate the deterministic reference vector bundle:

```bash
python tools/build_vectors.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/vectors

python tools/validate_vector_bundle.py --bundle dist/vectors
```

Generated layout:

```text
dist/vectors/
├── records.jsonl
├── embeddings.f16
├── index.json
├── retrieval-report.json
└── manifest.json
```

### Deterministic record chunking

`qsol-record-chunk-v1` uses one canonical substrate item as one retrieval chunk. It does not split a record into partial factual fragments.

Each `records.jsonl` row contains:

- a stable chunk ID;
- canonical record ID;
- record type;
- canonical source path;
- vector index;
- canonical payload SHA-256;
- deterministic search text;
- the canonical payload object;
- public `source_refs`;
- epistemic state;
- visibility.

The provenance and epistemic metadata remain outside embedding coordinates. A vector therefore cannot silently replace the record it indexes.

### Reference embedding backend

CI uses `qsol-hash-embed-v1`, a deterministic dependency-free feature-hashing backend.

Contract:

```text
normalization = Unicode NFKC + casefold
features      = token unigrams + adjacent token bigrams
hash          = SHA-256 feature hashing
vectors       = 256 dimensions
normalization = L2
disk dtype    = little-endian float16
```

This backend is intentionally a **reference retrieval embedding**, not a claim that feature hashing is equivalent to a modern learned semantic embedding model.

Its purpose is to make the Phase 6 index reproducible in network-free CI and to establish the artifact/metadata/retrieval contracts. Future learned embedding backends may be added only when their exact model ID, revision, dimension, preprocessing/tokenizer identity, and other compatibility requirements are recorded.

Embedding coordinates are not canonical truth.

## Deterministic retrieval

A model consumer must load `ai/bootstrap.json` and its mandatory contract `load_order` before using retrieved payloads. Vector retrieval selects canonical evidence; it is not a substitute for the epistemic/public-boundary/consumer contracts.

Retrieve context with:

```bash
python tools/retrieve_vector_context.py \
  "publication:uff-v5.2.0 10.5281/zenodo.21911644" \
  --bundle dist/vectors \
  --top-k 5
```

Before reading or rendering payloads, the CLI runs the deterministic vector-bundle validator. A modified, stale, malformed, symlinked, or externally supplied bundle that cannot be reproduced from the canonical substrate is refused.

Empty, whitespace-only, or otherwise featureless queries are also refused. They do not fall through to all-zero similarity scores and alphabetical tie-breaking.

Nearest neighbours use normalized dot product, equivalent to cosine similarity for the normalized vectors. Ties are resolved by canonical ID ascending.

Primary vector matches are not immediately treated as a complete answer context. The retriever closes the selected set over:

- public `source_refs`;
- both endpoints of included relationships.

Every rendered retrieval context carries:

```text
SUBSTRATE_VERSION
SNAPSHOT_DATE
SOURCE_COMMIT
SUBSTRATE_SHA256
```

A saved/copied context can therefore still be traced to the exact substrate state that produced it.

If retrieval output is written inside the repository, the destination is restricted to `dist/retrieved/`. Generated vector/projection/adapter/capsule bundles are not valid retrieval-output targets.

The rendered context therefore carries evidence needed to interpret retrieved canonical items instead of saving prompt space by dropping provenance.

## Reference retrieval-size experiment

`retrieval-report.json` runs a fixed deterministic query set against the reference index and records:

- top-K canonical IDs;
- expected-ID hit status;
- provenance-closed delivered IDs;
- delivered item count;
- `qsol-portable-token-v1` context size;
- aggregate hit rate;
- average provenance-closed context size;
- reduction relative to the fixed MICRO/STANDARD/FULL build budgets.

This is a **retrieval-size experiment**, not a downstream model-quality benchmark. It can establish that a retrieval condition is smaller and provenance-closed; Phase 7 must determine whether a model actually answers better under that condition.

## Vector validation

The validator does not trust manifest hashes alone. It rebuilds the complete vector bundle from the canonical substrate and the recorded source commit and requires deterministic file equality.

Validation rejects:

- altered canonical payload rows;
- changed search text;
- changed vector bytes;
- changed index metadata;
- changed retrieval report results;
- forged manifest metadata;
- symlinked bundle files;
- undeclared files;
- unsafe in-repository output paths.

`dist/vectors` is the only permitted in-repository vector-build destination. Retrieved text uses the separate `dist/retrieved/` subtree.

## Latent / prefix projection experiments

Build the Phase 6 experiment contract bundle:

```bash
python tools/build_projections.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/projections

python tools/validate_projection_bundle.py --bundle dist/projections
```

Generated layout:

```text
dist/projections/
├── epistemic-prefix.txt
├── projection-recipes.json
├── delivery-matrix.json
└── manifest.json
```

The bundle defines reproducible experiment recipes for:

1. soft-prompt / prefix tuning;
2. prompt-tuned virtual tokens;
3. a model-specific LoRA epistemic adapter;
4. prefilled attention/KV-cache state;
5. reusable model-specific prefix state;
6. hybrid epistemic-prefix + factual-text delivery.

These are **experiment recipes**. Generic repository CI does not claim to have trained model-specific weights, tuned virtual tokens, or captured a universal KV cache. Such claims require an actual model-specific execution record.

## Why stable rules are the preferred latent payload

Mutable facts are easier to inspect, update, cite, and invalidate when they remain textual.

Phase 6 therefore treats stable interpretation rules as the most promising latent/prefix payload:

```text
UNKNOWN != FALSE
INFERENCE != FACT
SATIRE != BIOGRAPHY
REPLAY != EMPIRICAL_VALIDATION
FORMALIZATION != PHYSICAL_TRUTH
PRESERVE_PROVENANCE
RESOLVE_CANONICAL_IDS_BEFORE_ALIASES
```

The reference prefix explicitly states that it is an interpretation carrier, not a canonical fact store.

## YEAH-NAH/1 delivery matrix

Phase 6 also freezes three delivery conditions for the future Australian pragmatic-humour probe:

```text
TEXTUAL
EPISTEMIC PREFIX
HYBRID PREFIX + FACTUAL TEXT
```

The experimental pragmatic rules are identical across those conditions:

```text
SURFACE_MEANING != NECESSARILY_INTENDED_MEANING
SARCASM = INFERRED UNLESS SPEAKER_CONFIRMED
UNCERTAIN != SARCASTIC
BANTER != HOSTILITY
UNDERSTATEMENT != LOW_SEVERITY
CONTEXT > TOKEN_POLARITY
```

Phase 6 guarantees deterministic rule payloads and delivery definitions. **Phase 7 remains responsible for measuring which condition actually improves model behaviour.**

## Model compatibility and invalidation

Model-specific projection artifacts must carry a compatibility identity matching `schema/model-projection-compatibility.schema.json`.

The conservative Phase 6 compatibility key includes:

```text
projection_kind
model_id
model_revision
architecture
tokenizer_id
tokenizer_sha256
context_length
hidden_size
num_hidden_layers
num_attention_heads
kv_layout_version
tensor_dtype
kv_cache_dtype
quantization_id
```

`tensor_dtype` records the relevant model/projection tensor precision, `kv_cache_dtype` records the cache precision (or an explicit not-applicable value when no KV state exists), and `quantization_id` records the exact quantization identity or `none`.

The compatibility checker is intentionally fail-closed. A tokenizer, architecture, model revision, dimensional, KV-layout, tensor precision, cache precision, or quantization change invalidates the model-specific projection.

Example check:

```bash
python tools/check_projection_compatibility.py \
  --expected previous-model-identity.json \
  --actual current-model-identity.json
```

A compatible result means only that the declared model identities match the projection compatibility contract. It does not make the projection a source of factual authority.

## Reproducible source identity

Both vector and latent/prefix experiment bundles record:

```text
substrate snapshot version
exact source commit
canonical substrate SHA-256
projection specification version
per-file SHA-256
aggregate bundle SHA-256
```

Until Phase 8 introduces formal release SemVer, `snapshot-YYYY-MM-DD` plus the full Git commit and canonical substrate SHA-256 identifies the source substrate state.

## Trust boundary

A model may use a vector index to find canonical records or a model-specific prefix to carry stable interpretation rules.

It must not treat:

- nearest-neighbour score as factual confidence;
- embedding coordinates as facts;
- a soft prompt as a citation;
- a KV cache as currentness evidence;
- a LoRA adapter as publication authority;
- absence from a retrieved top-K result as evidence that a fact is false.

The canonical public substrate remains the source of truth.
