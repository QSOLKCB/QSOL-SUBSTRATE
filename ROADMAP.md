# QSOL-SUBSTRATE Roadmap

## Phase 0 — Documentation contract

- [x] Human-facing README and conceptual documentation.
- [x] Machine bootstrap and epistemic contracts.
- [x] Public/private boundary contract.
- [x] Initial JSON schema.
- [x] Agent guidance.
- [x] Generic, Grok, Sider, and Ollama adapter documentation.

## Phase 1 — Canonical public substrate

- [x] Add public identity/context records.
- [x] Add canonical QSOL terminology and aliases.
- [x] Add active public project registry.
- [x] Add publication and DOI registry.
- [x] Add project/research relationship graph.
- [x] Add chronology for materially relevant public events.

Phase 1 establishes the canonical public knowledge layer. The registry is
selective rather than exhaustive: absence from the substrate means unavailable,
not false.

## Phase 2 — Export pipeline

- [x] Define explicit-allow export policy from private QSOL-CONTEXT.
- [x] Add field-level visibility rules.
- [x] Add redaction and secret scanning.
- [x] Add deterministic canonicalisation.
- [x] Add export manifest and fingerprint.
- [x] Fail closed on unknown visibility or provenance.
- [x] Preserve public/private omission semantics during export.
- [x] Guarantee that generated public records contain no private source references.

The export pipeline treats publication as an explicit act. Private context
never becomes public merely because a field was not explicitly marked private.
The shipped allowlist contains zero private-to-public publication grants.

## Phase 3 — Validation and CI

- [x] JSON Schema validation.
- [x] Referential-integrity validation.
- [x] Provenance validation.
- [x] Alias collision checks.
- [x] DOI uniqueness checks.
- [x] Relationship endpoint validation.
- [x] Chronology ordering validation.
- [x] Public-boundary checks.
- [x] Secret/private-reference scanning.
- [x] SHA-256 substrate fingerprint.
- [x] GitHub Actions validation workflow.

Validation fails closed when canonical identity, provenance, visibility,
relationships, chronology, publication/release identity, or the public boundary
cannot be resolved safely. The integrity validator is deliberately network-free:
live-source freshness and frozen-snapshot consistency remain separate concerns.

## Phase 4 — Portable model adapters

- [x] Generic single-file substrate bundle.
- [x] Grok chat bootstrap.
- [x] xAI retrieval export.
- [x] Grok Build project rules/skill export.
- [x] Sider prompt/knowledge-base bundle.
- [x] Ollama Modelfile/system-context bundle.
- [x] OpenAI-compatible API bundle.
- [x] Anthropic-compatible context bundle.
- [x] Model-independent adapter manifest.
- [x] Record exact substrate version, commit, and adapter identity for reproducible runs.

Adapters are disposable transport layers. They may change formatting and
delivery, but must never redefine canonical substrate facts. Phase 4 generates
all adapter knowledge from one byte-identical canonical projection and records
snapshot identity, source commit, substrate SHA-256, projection SHA-256, adapter
identity, per-file hashes, and an aggregate adapter-bundle fingerprint.

## Phase 5 — Toolless Substrate Capsule

Create a deterministic, self-contained substrate representation for AI systems
that have no browsing, retrieval, file-system, repository, or external tool
access.

### Profiles

- [x] `MICRO` tool-less profile for small-context and 4B–8B class models.
- [x] `STANDARD` tool-less profile for general-purpose local and hosted models.
- [x] `FULL` tool-less profile for large-context models.
- [x] Deterministic token-budgeted compilation.
- [x] Priority-aware truncation that preserves epistemic rules before optional detail.
- [x] Strategic semantic redundancy for small models.
- [x] Inline critical claim boundaries with high-risk project records.

### Toolless cold boot

- [x] Add a compact cold-boot header declaring that the model has no tools.
- [x] Declare substrate snapshot date prominently.
- [x] Declare substrate version and SHA-256 fingerprint.
- [x] Require `UNKNOWN != FALSE`.
- [x] Require `INFERENCE != FACT`.
- [x] Require `SATIRE != BIOGRAPHY`.
- [x] Require `FORMALIZATION != PHYSICAL_TRUTH`.
- [x] Require models not to claim freshness beyond the substrate snapshot.
- [x] Require models to state snapshot limitations when current state cannot be verified.

Example invariant:

```text
IF_CURRENT_STATE_REQUIRED
AND_TOOLS_UNAVAILABLE
THEN:
    use snapshot only if sufficient;
    state snapshot date;
    do not claim currentness beyond snapshot;
    return UNKNOWN for unresolved post-snapshot state.
```

### Toolless serialization

* [x] Define a compact LLM-oriented substrate serialization.
* [x] Preserve canonical IDs and aliases.
* [x] Inline important relationships where this improves local comprehension.
* [x] Preserve publication and DOI identity.
* [x] Preserve provenance class and epistemic state.
* [x] Preserve chronology without requiring external lookup.
* [x] Avoid deeply nested structures where they waste context.
* [x] Generate all tool-less artifacts from the canonical substrate rather than maintaining duplicate facts manually.

Generated output:

```text
dist/toolless/
├── QSOL-SUBSTRATE-MICRO.txt
├── QSOL-SUBSTRATE-STANDARD.txt
├── QSOL-SUBSTRATE-FULL.txt
└── manifest.json
```

Phase 5 uses deterministic model-independent `qsol-portable-token-v1` build
budgets: `MICRO=8192`, `STANDARD=24576`, and `FULL=131072`. These values control
compilation only and are not claims about any vendor/model tokenizer.

Records are admitted only at whole canonical-item boundaries. Admission brings
public `source_refs`, relationship endpoints, and other resolvable canonical-ID
dependencies with the record, so compact profiles cannot gain space by leaving
dangling provenance. Omitted material remains unavailable, not false.

The `FULL` profile must contain the complete canonical payload projection or the
build fails closed. `MICRO` deliberately repeats the highest-risk epistemic
rules for small-model robustness. Generated artifacts record the exact source
commit, snapshot identity, canonical substrate SHA-256, deterministic portable
token count, inclusion/omission counts, per-profile hashes, and aggregate
capsule-bundle fingerprint.

The tool-less representation behaves as a frozen public context image: one
artifact in, no external tools required, no freshness claims beyond the
snapshot, and no invented lore to fill omissions.

## Phase 6 — Vector and Latent Substrate Projection

Explore whether the same canonical substrate can be projected into more compact
machine representations without modifying the underlying canonical knowledge.

The canonical substrate remains vendor- and model-independent. Vector indexes,
prefix states, caches, and learned adapters are disposable model-specific
projections.

### Vector substrate

* [ ] Define deterministic record chunking.
* [ ] Generate embeddings for canonical substrate records.
* [ ] Preserve canonical record IDs alongside every vector.
* [ ] Preserve provenance and epistemic metadata outside the embedding itself.
* [ ] Add deterministic nearest-neighbour retrieval experiments.
* [ ] Compare vector-selected context against fixed textual profiles.
* [ ] Evaluate whether semantic retrieval can reduce prompt size without losing provenance.

Proposed output:

```text
dist/vectors/
├── records.jsonl
├── embeddings.f16
├── index.json
└── manifest.json
```

Embedding vectors are retrieval indexes, not canonical truth.

Raw embedding coordinates must never be treated as meaningful context by an LLM
without an explicit retrieval or projection mechanism.

### Latent / prefix substrate

Investigate model-specific substrate initialization mechanisms including:

* [ ] Soft prompt / prefix tuning.
* [ ] Prompt-tuned virtual tokens.
* [ ] Model-specific adapter or LoRA experiments.
* [ ] Prefilled attention/KV-cache substrate images.
* [ ] Reusable model-specific prefix states.
* [ ] Epistemic-prefix plus factual-text hybrid mode.
* [ ] Deterministic regeneration from a declared substrate release.
* [ ] Model/version compatibility manifests.
* [ ] Explicit invalidation when model architecture or tokenizer changes.

Conceptual architecture:

```text
QSOL-SUBSTRATE
      |
      v
canonical public records
      |
      +--------------------+
      |                    |
      v                    v
 textual capsule      model-specific projection
      |                    |
      v                    v
 factual context      latent/prefix/KV state
      \                    /
       \                  /
        +------ model ----+
```

A model-specific latent projection must never replace the canonical public
substrate or become an independent source of truth.

### Hybrid epistemic projection

Investigate whether model-specific latent state is more useful for carrying
stable interpretation rules than mutable factual information.

Candidate split:

```text
LATENT EPISTEMIC SUBSTRATE
    UNKNOWN != FALSE
    SATIRE != BIOGRAPHY
    REPLAY != EMPIRICAL VALIDATION
    FORMALIZATION != PHYSICAL TRUTH
    PRESERVE PROVENANCE
    RESOLVE CANONICAL IDS

            +

TEXTUAL FACTUAL SUBSTRATE
    identity
    projects
    publications
    chronology
    relationships

            +

USER TASK
```

* [ ] Test whether stable cultural-pragmatic interpretation rules such as
  `YEAH-NAH/1` are better preserved in an epistemic prefix, textual context, or
  hybrid delivery mode.

This architecture keeps frequently changing public facts inspectable and textual
while testing whether stable epistemic behaviour can be efficiently projected
into temporary inference state.

## Phase 7 — Substrate Probe

Build a deterministic evaluation suite for measuring whether substrate delivery
actually improves model behaviour.

* [ ] Deterministic question set.
* [ ] Exact-known-fact tests.
* [ ] `unknown`-answer tests.
* [ ] Unsupported-assertion tests.
* [ ] Provenance preservation tests.
* [ ] Entity/alias disambiguation tests.
* [ ] Contradiction handling tests.
* [ ] Snapshot/freshness tests.
* [ ] Satire/fiction boundary tests.
* [ ] Formalization-versus-empirical-claim tests.
* [ ] Project relationship tests.
* [ ] Publication/DOI identity tests.
* [ ] Reproducible model report-card format.

### YEAH-NAH/1 — Australian Pragmatic Humour Probe

Build a deterministic cultural-pragmatics stress test for sarcasm, deadpan,
understatement, banter, mock hostility, affectionate insult, and polarity
reversal in Australian English. The purpose is not to assume that Australian
speech is sarcastic; it is to test whether a model can avoid naive literalism
without over-classifying ambiguous language as sarcasm or hostility.

* [ ] Context-paired literal-versus-sarcastic utterance set.
* [ ] Deadpan interpretation tests.
* [ ] Understatement tests, including high-severity contexts expressed mildly.
* [ ] Mock-hostility versus actual-hostility tests.
* [ ] Affectionate-insult and familiar-banter tests.
* [ ] Positive/negative polarity-reversal tests.
* [ ] Contextual `yeah nah` / `nah yeah` interpretation tests.
* [ ] Relationship-familiarity and conversational-context controls.
* [ ] Sarcasm-confidence and uncertainty-calibration tests.
* [ ] Speaker-confirmed sarcasm controls that distinguish explicit confirmation
  from model inference.
* [ ] Cross-model comparison for small open-weight and hosted models.
* [ ] Compare naked, textual-substrate, vector-selected, latent-prefix, hybrid,
  and tool-enabled conditions.

Normative interpretation guards for the probe:

```text
SURFACE_MEANING != NECESSARILY_INTENDED_MEANING
SARCASM = INFERRED UNLESS SPEAKER_CONFIRMED
UNCERTAIN != SARCASTIC
BANTER != HOSTILITY
UNDERSTATEMENT != LOW_SEVERITY
CONTEXT > TOKEN_POLARITY
```

Measure at least:

* [ ] Sarcasm precision and recall.
* [ ] Literal-meaning error rate.
* [ ] Banter misclassification rate.
* [ ] Hostility false-positive rate.
* [ ] Understatement severity-preservation rate.
* [ ] Confidence calibration.
* [ ] Cultural-context dependence and uplift from substrate delivery.

`YEAH-NAH/1` is a pragmatic interpretation probe, not a canonical-fact source.
A sarcasm classification remains `inferred` unless the speaker or cited evidence
explicitly confirms the intended meaning.

### Comparison matrix

Compare the same models under:

```text
NAKED MODEL
vs
MICRO TEXT CAPSULE
vs
STANDARD TEXT CAPSULE
vs
FULL TEXT CAPSULE
vs
VECTOR-SELECTED CONTEXT
vs
LATENT / KV-PREFIX SUBSTRATE
vs
EPISTEMIC PREFIX + FACTUAL TEXT
vs
TOOL-ENABLED RETRIEVAL
```

Measure:

* [ ] Factual accuracy.
* [ ] Unsupported assertion rate.
* [ ] `UNKNOWN` precision.
* [ ] `UNKNOWN` recall.
* [ ] Alias resolution accuracy.
* [ ] Provenance fidelity.
* [ ] Contradiction handling.
* [ ] Claim-boundary preservation.
* [ ] Context/token efficiency.
* [ ] Substrate uplift over naked-model baseline.
* [ ] Hallucination reduction relative to baseline.

A central research question is:

> How much substrate is enough?

A compact, well-structured substrate may outperform a much larger undifferentiated
context dump.

## Phase 8 — Release discipline

* [ ] Semantic versioning policy.
* [ ] Release manifests.
* [ ] Canonical substrate snapshot identity.
* [ ] Immutable probe snapshots.
* [ ] Release fingerprints.
* [ ] Toolless capsule fingerprints.
* [ ] Vector-index fingerprints.
* [ ] Model-specific projection manifests.
* [ ] Compatibility metadata for latent/KV artifacts.
* [ ] Reproducible build commands.
* [ ] Optional archival DOI workflow.

Canonical substrate releases and derived projections must remain distinguishable.

Example:

```text
Canonical substrate:
QSOL-SUBSTRATE v1.2.0
commit=<git-sha>
sha256=<canonical-fingerprint>

Derived artifact:
profile=toolless-standard
or
projection=qwen3-8b-kv-prefix
source_substrate=v1.2.0
source_sha256=<canonical-fingerprint>
artifact_sha256=<derived-artifact-fingerprint>
```

The roadmap is intentionally incremental.

A substrate should become more portable, more compact, and more useful without
becoming less inspectable or less trustworthy.

The canonical public substrate remains the source of truth.

Everything else — prose bundles, vector indexes, adapters, soft prompts,
KV caches, and model-specific latent projections — is a reproducible projection
of that source.
