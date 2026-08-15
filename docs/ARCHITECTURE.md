# Architecture

QSOL-SUBSTRATE separates canonical meaning from presentation, private-source publication, retrieval indexes, model-specific transport/projection state, and evaluation artifacts.

## Layers

### Human documentation

`README.md` and `docs/` explain the project in ordinary prose. These documents optimise for understanding, examples, rationale, and maintenance.

### Machine contract

`ai/` contains compact, structured instructions for AI consumers. These files define mandatory contract load order, epistemic states, public-boundary behaviour, retrieval precedence, and consumer obligations.

The bootstrap separates **mandatory contract loading** from **selective payload retrieval**. Consumers load the normative machine contract first, then retrieve only the canonical payload records needed for the current task.

### Schema

`schema/` defines structural validation for canonical records, machine contracts, export manifests, validation/fingerprint outputs, adapter/capsule manifests, vector bundles, model-projection compatibility identities, Phase 7 model-run envelopes, probe report cards, and comparison reports.

### Canonical public knowledge payload

The source-of-truth public snapshot lives under:

```text
sources/index.json
identity/public.json
context/public.json
terminology/index.json
projects/index.json
publications/index.json
relationships/graph.json
chronology/current.jsonl
```

The payload is **selective, not exhaustive**. Missing records and relationship edges mean unavailable/unknown from this snapshot, not false.

### Provenance snapshots

`sources/index.json` stores public source locators together with snapshot evidence. First-party repository documents retain exact commit-pinned evidence where available; release records retain release/tag identity.

The frozen substrate can therefore explain what evidence supported a snapshot while still allowing later live primary evidence to supersede stale state.

### Private-to-public export boundary

Phase 2 implements a maintainer-side publication pipeline under:

```text
public_export/
├── policy.json
├── include.json
└── exclude.json

tools/export_public_substrate.py
```

The private source is optional and local. It is not available to public consumers and is never a runtime dependency.

Publication is **explicit allow only**. Each enabled directive selects one exact source object and names every field permitted to cross the boundary. Public provenance must resolve through the existing public source registry.

### Integrity validation

Phase 3 validates schemas, canonical IDs, provenance, visibility, aliases, DOI identity, relationships, chronology, release identity, public-boundary invariants, secret/private-reference leakage, and deterministic canonical substrate identity.

```text
tools/validate_substrate.py
tools/fingerprint_substrate.py
```

The canonical substrate fingerprint covers public payload semantics, not derived transports, projections, or evaluation artifacts.

### Portable adapters

Phase 4 deterministically formats the canonical substrate for target systems under generated `dist/adapters/` output.

Adapters can change transport and formatting. They cannot redefine facts.

### Tool-less capsules

Phase 5 compiles deterministic MICRO/STANDARD/FULL frozen textual context images under `dist/toolless/`.

Capsules may omit whole canonical items according to deterministic profile budgets, but cannot transform included canonical facts. Provenance and relationship dependencies are closed before delivery.

### Vector projection

Phase 6 builds a deterministic retrieval projection under:

```text
dist/vectors/
├── records.jsonl
├── embeddings.f16
├── index.json
├── retrieval-report.json
└── manifest.json
```

`qsol-record-chunk-v1` maps one canonical item to one retrieval chunk. `qsol-hash-embed-v1` provides a dependency-free deterministic reference embedding for network-free CI.

Canonical IDs, source paths, provenance, epistemic labels, and payload objects remain outside embedding coordinates. Vectors are indexes, not truth. The retrieval CLI validates the bundle before rendering records as model context.

### Model-specific latent/prefix projection

Phase 6 also defines reproducible experiment contracts under:

```text
dist/projections/
├── epistemic-prefix.txt
├── projection-recipes.json
├── delivery-matrix.json
└── manifest.json
```

The recipes cover soft-prompt/prefix tuning, virtual tokens, LoRA, KV-cache prefill, reusable prefix state, and hybrid epistemic-prefix + factual-text conditions.

Generic CI validates the recipe and compatibility contract. It does not claim model-specific weights or KV state were created unless an actual model-specific execution produces them.

### Phase 7 evaluation layer

Phase 7 adds deterministic evaluation inputs and scoring contracts without turning the probe into a fact store:

```text
probe/
├── substrate-probe.jsonl
├── yeah-nah-1.jsonl
└── conditions.json

            |
            v

dist/probes/
├── substrate-probe.jsonl
├── yeah-nah-1.jsonl
├── conditions.json
├── scoring-contract.json
└── manifest.json
```

The probe bundle is bound to the exact source substrate identity and is deterministically rebuilt during validation. A model run must bind the same probe-bundle SHA-256 and substrate identity before scoring.

The scorer consumes a strict structured response envelope while retaining raw model prose for audit. Report cards and comparison tables are derived evaluation artifacts, not canonical facts.

## Information flow

```text
private canonical context (optional, local)
              |
              | explicit field-level allowlist
              | + secret/private-reference scan
              v
       reviewable export staging
              |
              | deterministic canonicalisation
              | + manifest + fingerprint
              v
      QSOL-SUBSTRATE public records
              |
              | Phase 3 fail-closed validation
              v
       canonical public snapshot
              |
       +------+------+----------------+
       |             |                |
       v             v                v
 adapters       tool-less text    vector index
       |             |                |
       |             |          provenance closure
       |             |                |
       +------+------+----------------+
              |
              v
        factual context delivery
              |
              +----------------------+
              |                      |
              v                      v
        ordinary model       model-specific prefix/
                              LoRA/KV experiment
              |                      |
              +----------+-----------+
                         |
                         v
                 Phase 7 model run
                         |
                         v
             deterministic report card
                         |
                         v
             same-snapshot comparison
```

The canonical payload remains the only public truth store in this graph.

## Retrieval flow

Canonical retrieval:

```text
ai/bootstrap.json
       |
       v
mandatory machine contracts
       |
       v
identify task-relevant records
       |
       v
selective canonical payload retrieval
       |
       +--> sources/index.json for provenance
```

Phase 6 vector retrieval:

```text
user/query text
       |
       v
validate vector bundle
       |
       v
qsol-hash-embed-v1 query vector
       |
       v
normalized-dot nearest neighbours
       |
       v
canonical IDs
       |
       v
source_ref + relationship endpoint closure
       |
       v
render canonical payload objects + source identity
```

Nearest-neighbour score is retrieval rank, not factual confidence.

## Export flow

```text
QSOL-CONTEXT checkout
       |
       v
verify source protocol
       |
       v
load existing public payload baseline
       |
       v
apply enabled explicit grants only
       |
       +--> directive visibility == public
       +--> exported field visibility == public
       +--> public source_ref already registered
       +--> no source-path escape
       +--> no private source-registry mutation
       |
       v
scan selected values and complete output
       |
       v
canonicalise JSON / JSONL
       |
       v
export-manifest.json + bundle SHA-256
       |
       v
human review
```

Failure at any boundary produces `EXPORT REFUSED`; there is no fallback publication path.

## Projection compatibility flow

A model-specific latent artifact is valid only for its declared compatibility identity:

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

Any mismatch invalidates the artifact. A tokenizer, architecture, precision, quantization, or KV-layout change is not a warning; it means regenerate.

## Hybrid epistemic projection

Phase 6 fixes the delivery architecture; Phase 7 measures behaviour:

```text
stable epistemic/pragmatic rules
           |
           v
 model-specific prefix recipe
           |
           +
           |
mutable canonical facts
           |
           v
 textual capsule or vector-selected context
           |
           +
           |
        user task
           |
           v
      model response
           |
           v
 Phase 7 structured run + scorer
```

The YEAH-NAH/1 textual/prefix/hybrid rule payload is held constant so delivery effects can be measured rather than inferred from representation plumbing.

## Probe and comparison flow

```text
probe source cases
       |
       v
deterministic probe build
       |
       v
probe-bundle SHA + substrate identity
       |
       +----------------------------+
       |                            |
       v                            v
 model condition A             model condition B
       |                            |
       v                            v
 strict model-run JSON         strict model-run JSON
       |                            |
       +-------------+--------------+
                     |
                     v
          deterministic scorer
                     |
                     v
           schema-valid reports
                     |
                     v
       same-model naked baseline
                     |
                     v
 uplift / hallucination / YEAH-NAH
          comparison metrics
```

A scoring oracle follows the same scorer path to test the metric plumbing, but its `execution_kind=scoring_oracle` is mechanically rejected by empirical comparison tooling.

## Trust precedence

The substrate is a cache of public context, not a replacement for current primary evidence. A current repository commit, release, DOI record, or other primary source can supersede a stale substrate entry.

Derived artifacts sit **below** canonical structured records in factual authority. Neither embedding proximity, latent-state activation, nor a high probe score can overrule canonical evidence.

Private context does not outrank public provenance merely because it is canonical inside QSOL-CONTEXT. A private candidate fact requires explicit publication authority and public source references before it can enter the public substrate.

## Determinism

Deterministic identities are layered:

- canonical JSON/JSONL rules define public payload semantics;
- Phase 3 fingerprints the canonical payload;
- Phase 4 fingerprints adapter projections;
- Phase 5 fingerprints tool-less textual projections;
- Phase 6 fingerprints vector bundles and model-projection experiment bundles;
- Phase 7 fingerprints deterministic probe bundles and binds model runs/reports to probe + substrate identity;
- every derived artifact records the exact source commit plus canonical substrate SHA-256.

Model inference itself need not be deterministic for the substrate, its generated artifacts, and its evaluation inputs to be version-identifiable.
