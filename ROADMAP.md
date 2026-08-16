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

Phase 1 establishes the canonical public knowledge layer. The registry is selective rather than exhaustive: absence from the substrate means unavailable, not false.

## Phase 2 — Export pipeline

- [x] Define explicit-allow export policy from private QSOL-CONTEXT.
- [x] Add field-level visibility rules.
- [x] Add redaction and secret scanning.
- [x] Add deterministic canonicalisation.
- [x] Add export manifest and fingerprint.
- [x] Fail closed on unknown visibility or provenance.
- [x] Preserve public/private omission semantics during export.
- [x] Guarantee that generated public records contain no private source references.

The export pipeline treats publication as an explicit act. Private context never becomes public merely because a field was not explicitly marked private. The shipped allowlist contains zero private-to-public publication grants.

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

Validation fails closed when canonical identity, provenance, visibility, relationships, chronology, publication/release identity, or the public boundary cannot be resolved safely. The integrity validator is deliberately network-free: live-source freshness and frozen-snapshot consistency remain separate concerns.

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

Adapters are disposable transport layers. They may change formatting and delivery, but must never redefine canonical substrate facts. Phase 4 generates all adapter knowledge from one byte-identical canonical projection and records snapshot identity, source commit, substrate SHA-256, projection SHA-256, adapter identity, per-file hashes, and an aggregate adapter-bundle fingerprint.

## Phase 5 — Toolless Substrate Capsule

Create a deterministic, self-contained substrate representation for AI systems that have no browsing, retrieval, file-system, repository, or external tool access.

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

- [x] Define a compact LLM-oriented substrate serialization.
- [x] Preserve canonical IDs and aliases.
- [x] Inline important relationships where this improves local comprehension.
- [x] Preserve publication and DOI identity.
- [x] Preserve provenance class and epistemic state.
- [x] Preserve chronology without requiring external lookup.
- [x] Avoid deeply nested structures where they waste context.
- [x] Generate all tool-less artifacts from the canonical substrate rather than maintaining duplicate facts manually.

Generated output:

```text
dist/toolless/
├── QSOL-SUBSTRATE-MICRO.txt
├── QSOL-SUBSTRATE-STANDARD.txt
├── QSOL-SUBSTRATE-FULL.txt
└── manifest.json
```

Phase 5 uses deterministic model-independent `qsol-portable-token-v1` build budgets: `MICRO=8192`, `STANDARD=24576`, and `FULL=131072`. These values control compilation only and are not claims about any vendor/model tokenizer.

Records are admitted only at whole canonical-item boundaries. Admission brings public `source_refs`, relationship endpoints, and other resolvable canonical-ID dependencies with the record, so compact profiles cannot gain space by leaving dangling provenance. Omitted material remains unavailable, not false.

The `FULL` profile must contain the complete canonical payload projection or the build fails closed. `MICRO` deliberately repeats the highest-risk epistemic rules for small-model robustness. Generated artifacts record the exact source commit, snapshot identity, canonical substrate SHA-256, deterministic portable token count, inclusion/omission counts, per-profile hashes, and aggregate capsule-bundle fingerprint.

The tool-less representation behaves as a frozen public context image: one artifact in, no external tools required, no freshness claims beyond the snapshot, and no invented lore to fill omissions.

## Phase 6 — Vector and Latent Substrate Projection

Explore whether the same canonical substrate can be projected into more compact machine representations without modifying the underlying canonical knowledge.

The canonical substrate remains vendor- and model-independent. Vector indexes, prefix states, caches, and learned adapters are disposable model-specific projections.

### Vector substrate

- [x] Define deterministic record chunking.
- [x] Generate deterministic reference embeddings for canonical substrate records.
- [x] Preserve canonical record IDs alongside every vector.
- [x] Preserve provenance and epistemic metadata outside the embedding itself.
- [x] Add deterministic nearest-neighbour retrieval experiments.
- [x] Compare vector-selected context against fixed textual profile budgets.
- [x] Evaluate whether retrieval can reduce prompt size without dropping provenance closure.
- [x] Add fail-closed deterministic rebuild validation for the complete vector bundle.

Generated output:

```text
dist/vectors/
├── records.jsonl
├── embeddings.f16
├── index.json
├── retrieval-report.json
└── manifest.json
```

Phase 6 uses `qsol-record-chunk-v1` for one-canonical-item-per-chunk record projection and `qsol-hash-embed-v1` as a dependency-free 256-dimensional float16 reference embedding backend. The reference backend exists to make network-free CI and retrieval contracts reproducible; it is not asserted to be equivalent to a learned semantic embedding model.

Embedding vectors are retrieval indexes, not canonical truth. Raw embedding coordinates must never be treated as meaningful factual context by an LLM without an explicit retrieval/projection mechanism.

Primary vector matches are closed over public provenance references and relationship endpoints before delivery. The reference retrieval report measures context size and expected-ID retrieval hits only; downstream model quality remains a Phase 7 measurement.

### Latent / prefix substrate

Phase 6 implements reproducible **experiment contracts** for model-specific substrate initialization. A checked item below means the recipe, source identity, compatibility requirements, invalidation behavior, and deterministic experiment payload are defined. It does **not** claim that generic repository CI trained model-specific weights or captured a universal KV cache.

- [x] Soft prompt / prefix-tuning experiment recipe.
- [x] Prompt-tuned virtual-token experiment recipe.
- [x] Model-specific epistemic LoRA experiment recipe.
- [x] Prefilled attention/KV-cache experiment recipe.
- [x] Reusable model-specific prefix-state experiment recipe.
- [x] Epistemic-prefix plus factual-text hybrid mode.
- [x] Deterministic regeneration from declared snapshot/version + commit + substrate SHA-256.
- [x] Model/version compatibility manifest schema and compatibility checker.
- [x] Explicit invalidation when model revision, architecture, tokenizer, dimensions, attention layout, or KV layout changes.
- [x] Deterministic validation of the model-projection experiment bundle.

Generated output:

```text
dist/projections/
├── epistemic-prefix.txt
├── projection-recipes.json
├── delivery-matrix.json
└── manifest.json
```

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

A model-specific latent projection must never replace the canonical public substrate or become an independent source of truth.

### Hybrid epistemic projection

Phase 6 fixes a deterministic candidate split:

```text
LATENT / PREFIX EPISTEMIC SUBSTRATE
    UNKNOWN != FALSE
    INFERENCE != FACT
    SATIRE != BIOGRAPHY
    REPLAY != EMPIRICAL VALIDATION
    FORMALIZATION != PHYSICAL_TRUTH
    PRESERVE PROVENANCE
    RESOLVE CANONICAL IDS

            +

TEXTUAL / RETRIEVED FACTUAL SUBSTRATE
    identity
    projects
    publications
    chronology
    relationships

            +

USER TASK
```

- [x] Define deterministic textual, epistemic-prefix, and hybrid delivery conditions for `YEAH-NAH/1`.
- [x] Keep identical pragmatic rule payloads across those Phase 7 comparison conditions.
- [x] Mark actual model-behaviour preservation/uplift measurement as Phase 7 work rather than inferring it from representation plumbing.

This architecture keeps frequently changing public facts inspectable and textual while testing whether stable epistemic behaviour can be efficiently projected into temporary inference state.

## Phase 7 — Substrate Probe

Build a deterministic evaluation suite for measuring whether substrate delivery actually improves model behaviour.

A checked Phase 7 item means the **probe corpus, response contract, scorer, metric, report-card format, or comparison protocol is executable and reproducible**. Generic repository CI does not claim that it ran hosted/open-weight models. Empirical model results require explicit model-run records and are separate evidence.

- [x] Deterministic question set.
- [x] Exact-known-fact tests.
- [x] `unknown`-answer tests.
- [x] Unsupported-assertion tests.
- [x] Provenance preservation tests.
- [x] Entity/alias disambiguation tests.
- [x] Contradiction handling tests.
- [x] Snapshot/freshness tests.
- [x] Satire/fiction boundary tests.
- [x] Formalization-versus-empirical-claim tests.
- [x] Project relationship tests.
- [x] Publication/DOI identity tests.
- [x] Reproducible model-run and report-card formats.
- [x] Fail-closed deterministic probe-bundle validation.
- [x] Scoring-oracle self-test that is mechanically excluded from empirical comparisons.

Generated protocol bundle:

```text
dist/probes/
├── substrate-probe.jsonl
├── yeah-nah-1.jsonl
├── conditions.json
├── scoring-contract.json
└── manifest.json
```

The reference corpus contains 48 cases: 24 substrate epistemic/factual probes and 24 `YEAH-NAH/1` pragmatic probes. Model runs bind the exact probe-bundle SHA-256 and substrate identity before they can be scored.

### YEAH-NAH/1 — Australian Pragmatic Humour Probe

Build a deterministic cultural-pragmatics stress test for sarcasm, deadpan, understatement, banter, mock hostility, affectionate insult, and polarity reversal in Australian English. The purpose is not to assume that Australian speech is sarcastic; it is to test whether a model can avoid naive literalism without over-classifying ambiguous language as sarcasm or hostility.

- [x] Context-paired literal-versus-sarcastic utterance set.
- [x] Deadpan interpretation tests.
- [x] Understatement tests, including high-severity contexts expressed mildly.
- [x] Mock-hostility versus actual-hostility tests.
- [x] Affectionate-insult and familiar-banter tests.
- [x] Positive/negative polarity-reversal tests.
- [x] Contextual `yeah nah` / `nah yeah` interpretation tests.
- [x] Relationship-familiarity and conversational-context controls.
- [x] Sarcasm-confidence and uncertainty-calibration tests.
- [x] Speaker-confirmed sarcasm controls that distinguish explicit confirmation from model inference.
- [x] Cross-model comparison protocol for small open-weight and hosted models.
- [x] Compare naked, textual-substrate, vector-selected, latent-prefix, hybrid, and tool-enabled conditions.

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

- [x] Sarcasm precision and recall.
- [x] Literal-meaning error rate.
- [x] Banter misclassification rate.
- [x] Hostility false-positive rate.
- [x] Understatement severity-preservation rate.
- [x] Confidence calibration via Brier score.
- [x] Cultural-context dependence and uplift from substrate delivery.

`YEAH-NAH/1` is a pragmatic interpretation probe, not a canonical-fact source. A sarcasm classification remains `inferred` unless the speaker or cited evidence explicitly confirms the intended meaning.

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

- [x] Factual accuracy.
- [x] Unsupported assertion rate.
- [x] `UNKNOWN` precision.
- [x] `UNKNOWN` recall.
- [x] Alias resolution accuracy.
- [x] Provenance fidelity.
- [x] Contradiction handling.
- [x] Claim-boundary preservation.
- [x] Context/token efficiency from the actual runner's tokenizer usage.
- [x] Substrate uplift over the same model's naked baseline.
- [x] Hallucination reduction relative to the same model's naked baseline.
- [x] Reject comparisons across mismatched probe/substrate identities.

A central research question is:

> How much substrate is enough?

A compact, well-structured substrate may outperform a much larger undifferentiated context dump. Phase 7 supplies the machinery to measure that claim; it does not fabricate the empirical answer.

## Phase 8 — Release discipline

- [x] Semantic versioning policy.
- [x] Release manifests.
- [x] Canonical substrate snapshot identity.
- [x] Immutable probe snapshots.
- [x] Release fingerprints.
- [x] Toolless capsule fingerprints.
- [x] Vector-index fingerprints.
- [x] Model-specific projection manifests.
- [x] Compatibility metadata for latent/KV artifacts.
- [x] Reproducible build commands.
- [x] Optional archival DOI workflow.

Phase 8 compiles a deterministic release bill of materials under `dist/release/` and validates it by byte-for-byte rebuild. Release identity binds the exact Git source commit and canonical substrate SHA-256 while retaining separate fingerprints for adapters, tool-less profiles, vectors, projection contracts, and the immutable Phase 7 probe snapshot. CI builds `0.8.0-ci.0` only as a non-publishable integration candidate; a stable version or DOI is never fabricated by validation.

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

## Phase 9 — Mixed-register adversarial evaluation and consumer audit integrity

Turn the first external cold-consumer review of QSOL-SUBSTRATE into reproducible defensive machinery without promoting the review itself into canonical truth.

The motivating stress test mixed supported substrate facts, directly contradicted claims, plausible-but-unverified biography/legal/financial claims, and obvious satire inside one coherent long-form report. The consumer successfully respected the public-boundary and provenance rules, but its derived report also exposed a separate integrity risk: summary totals can drift from the underlying claim objects even when the artifact hashes are valid.

Phase 9 therefore treats **consumer epistemics** and **consumer-report integrity** as separate validation surfaces.

### Epistemic guard extension

- [x] Add `ADJACENT_TRUTH != INHERITED_TRUTH` as a normative epistemic guard.
- [x] Require every substantive claim in mixed-register material to stand on its own evidence rather than inheriting credibility from neighbouring supported claims.
- [x] Preserve the distinction between `CONTRADICTED` and `UNAVAILABLE / UNVERIFIED`; absence or non-assertion must never be silently converted into falsity.
- [x] Preserve satire/fiction/register classification independently from factual epistemic status so humorous framing cannot become biography.
- [x] Propagate the new guard through the canonical epistemic contract, tool-less capsules, adapters, probe conditions, and any stable epistemic-prefix payload.

Normative extension:

```text
UNKNOWN != FALSE
INFERENCE != FACT
SATIRE != BIOGRAPHY
FORMALIZATION != PHYSICAL_TRUTH
ADJACENT_TRUTH != INHERITED_TRUTH
```

### Claim-audit interchange contract

- [x] Define a machine-readable claim-audit schema for external and internal consumer evaluations.
- [x] Require stable claim IDs, verbatim-or-hashed claim text, evidence refs, rationale, source substrate identity, and evaluator/run identity.
- [x] Separate primary epistemic classification from secondary register/style annotations.
- [x] Define deterministic classification-summary generation from claim objects rather than accepting hand-maintained totals.
- [x] Reject audit artifacts whose summary totals do not exactly match the underlying claim records.
- [x] Reject ambiguous counting schemes unless each dimension is explicitly named, for example `primary_class_counts` versus `register_counts`.
- [x] Require the total number of primary classifications to equal the number of auditable claim records.
- [x] Freeze the expected claim-ID set in the evaluation-bundle manifest and require one-to-one audit coverage of that exact set.
- [x] Reject missing, extra, or duplicate claim IDs even when submitted summary totals are internally consistent.

Example integrity invariant:

```text
summary.SUPPORTED == count(claims where epistemic_status == SUPPORTED)
summary.CONTRADICTED == count(claims where epistemic_status == CONTRADICTED)
summary.UNAVAILABLE_UNVERIFIED == count(claims where epistemic_status == UNAVAILABLE_UNVERIFIED)
sum(primary_class_counts) == auditable_claim_count
set(claims[].claim_id) == set(manifest.expected_claim_ids)
count(claims[].claim_id) == count(distinct(claims[].claim_id))
```

A valid SHA-256 only proves that an artifact is unchanged. It does not prove that the artifact's derived arithmetic, completeness, or interpretation is correct.

### MIXED-REGISTER/1 adversarial corpus

- [x] Add a frozen long-form adversarial corpus specifically for truth-by-proximity and register contamination.
- [x] Include supported facts immediately adjacent to invented claims.
- [x] Include directly contradicted claims about registry completeness, private/public boundaries, and canonical authority.
- [x] Include plausible but unsupported biography, legal status, corporate status, education, employment, financial, and ownership claims.
- [x] Include satire and obviously fictional claims as controls.
- [x] Include DOI, release, version, alias, chronology, and provenance traps.
- [x] Include compound paragraphs where only some clauses are supported.
- [x] Require claim-local classification rather than paragraph-level truth labelling.
- [x] Ship a deterministic oracle and scorer with the corpus.
- [x] Build one deterministic evaluation bundle containing the corpus, expected claim IDs/answers, oracle, scorer, scoring contract, and manifest.
- [x] Bind every run to the complete `MIXED-REGISTER/1` bundle fingerprint and substrate identity; a corpus-text hash alone is insufficient.
- [x] Reject scoring or comparison when the evaluation-bundle fingerprint differs, even if the corpus text is byte-identical.
- [x] Mark all adversarial fixtures as evaluation-only and mechanically prevent them from becoming canonical `source_refs`.

The goal is not to teach a model which jokes are jokes by keyword. The goal is to test whether it can preserve provenance and epistemic boundaries when true, false, unknown, and satirical material is deliberately interleaved.

### Local negative-boundary reinforcement

- [x] Preserve critical `nonclaims` beside the records they constrain when building compact adapters and tool-less capsules.
- [x] Keep `selective_not_exhaustive` semantics locally visible beside project/publication registries where practical.
- [x] Keep identity/legal-status non-assertions locally visible when identity records are projected without the full surrounding context.
- [x] Add validation that compact projections cannot strip a required local negative-boundary guard while retaining the higher-risk positive claim.
- [x] Add probe cases for long-context drift where a correct global disclaimer appears far away from a tempting unsupported claim.

This is controlled semantic redundancy: a small amount of repeated boundary information is preferable to a compact projection that makes a downstream model over-generalise.

### QSOL-SUBSTRATE publication and DOI closure

- [x] Add the QSOL-SUBSTRATE archival release/DOI to the canonical publication registry once its first-party release identity and provenance are resolved.
- [x] Keep README badge, `CITATION.cff`, `.zenodo.json`, release manifest, canonical publication registry, and source registry consistent.
- [x] Add a validator for self-publication metadata drift across those surfaces.
- [x] Fail closed on conflicting DOI/version/release identity rather than selecting whichever representation was loaded first.

A DOI appearing in human-facing metadata must not silently become a canonical publication fact until the canonical record and provenance closure exist.

### Consumer-evaluation provenance boundary

- [x] Define first-class metadata for external consumer evaluations: `execution_kind`, evaluator/provider, model ID, immutable model revision, tool mode, run date, source commit, source substrate SHA-256, prompt/test identity, complete evaluation-bundle fingerprint, artifact hashes, and classification contract version.
- [x] Require provider, model ID, and immutable model revision as separate fields; mutable provider aliases alone are not reproducible model identity.
- [x] Reject cross-condition empirical comparisons when the immutable model revision differs, so provider drift cannot be misreported as substrate uplift or regression.
- [x] Require an `execution_kind` discriminator such as `scoring_oracle`, `empirical_consumer`, or another explicitly defined non-empirical mode.
- [x] Mechanically exclude `scoring_oracle` and other non-empirical execution kinds from empirical result aggregation and cross-model performance claims.
- [x] Mark consumer reviews, model reports, scorecards, PDFs, and generated analyses as `derived_evaluation`, never canonical evidence by default.
- [x] Prevent canonical `source_refs` from targeting evaluation-only artifacts unless an explicit future policy permits a narrowly defined use.
- [x] Preserve evaluation artifacts for reproducibility without allowing them to launder their own claims back into the substrate.
- [x] Add a validation rule that an evaluator report cannot cite itself as evidence for the factual claims it is auditing.

### Follow-on consumer ergonomics

These are useful but lower priority than the integrity gates above.

- [x] Add optional retrieval hints that help tool-enabled consumers locate the smallest sufficient canonical evidence set without changing canonical facts.
- [x] Define freshness recipes for facts whose current state is expected to require live primary-source verification.
- [x] Add a first-class conflict-record shape for genuine public-source disagreements rather than forcing conflict state into prose.
- [ ] Measure whether local nonclaims and adjacency guards improve mixed-register performance across MICRO, STANDARD, FULL, vector-selected, and tool-enabled conditions.

### Phase 9 exit criteria

Phase 9 is complete only when:

- [x] CI mechanically rejects inconsistent claim-audit summary totals.
- [x] CI rejects audits with missing, extra, or duplicate claim IDs relative to the frozen evaluation-bundle manifest.
- [x] `MIXED-REGISTER/1` has a frozen deterministic corpus, expected claim-ID/answer set, oracle, scorer, scoring contract, manifest, and complete bundle fingerprint.
- [x] Every evaluation run binds the exact complete `MIXED-REGISTER/1` bundle fingerprint and substrate identity.
- [x] empirical comparisons require identical immutable model revisions across the compared conditions.
- [x] `scoring_oracle` runs are mechanically excluded from empirical aggregates and performance comparisons.
- [x] `ADJACENT_TRUTH != INHERITED_TRUTH` survives every relevant deterministic delivery projection.
- [x] compact projections retain required local negative-boundary guards.
- [x] QSOL-SUBSTRATE's own publication identity is provenance-closed across canonical and human-facing metadata.
- [x] evaluation artifacts are reproducibly identifiable as derived/noncanonical and cannot become canonical evidence by accident.
- [ ] a cold consumer can classify mixed supported, contradicted, unavailable, and satirical claims without treating plausibility or neighbouring truth as provenance.

Phase 9 deliberately does **not** expand the substrate into a complete biography. Better uncertainty handling is preferred over filling public omissions with additional personal data.

## Phase 10 — Substrate Modes and Domain-Admissibility Geometry

Add a public, vendor-neutral specialist-policy layer over the canonical substrate without turning domain policy into canonical facts.

- [x] Add 19 top-level domain modes and 10 cross-cutting activity modes.
- [x] Add explicit mode-resolution states and fail-closed ambiguity handling.
- [x] Define `CLAIM_STRENGTH <= EVIDENCE_ENTITLEMENT`.
- [x] Separate provenance class, publication state, epistemic status, authority class, and claim scope.
- [x] Add preliminary/theoretical/proposed/speculative/unknown/hypothetical/counterfactual/fictional/satirical claim labels alongside stronger supported states.
- [x] Define preprint and repository/DOI promotion guards.
- [x] Require primary legal authority for binding Legal-mode claims.
- [x] Separate Medical research evidence from normative clinical guidance.
- [x] Add field-sensitive terminology namespaces.
- [x] Add interpretable 24D validation geometry with sparse hard constraints.
- [x] Add declared cross-domain bridges and non-equivalence contracts.
- [x] Add schema, fail-closed validator, regression tests, and CI integration.
- [x] Load the lightweight mode contract from the AI bootstrap while keeping detailed mode resources selective.

Detailed implementation and deferred work are tracked in [`roadmap/substrate-modes.md`](roadmap/substrate-modes.md).

### Deferred Phase 10 work

- [ ] **DEFERRED:** Empirically calibrate 24D thresholds against frozen cross-model runs.
- [ ] **DEFERRED:** Build `MODE-CONFUSION/1` and measure cross-mode contamination under multiple delivery conditions.
- [ ] **DEFERRED:** Propagate mode policy into every tool-less, adapter, vector, and latent projection only after deterministic compatibility rules are specified.
- [ ] **DEFERRED:** Add jurisdiction-specific Legal primary-authority resolvers.
- [ ] **DEFERRED:** Add specialty-specific, freshness-aware Medical guideline/regulator bindings.
- [ ] **DEFERRED:** Expand terminology ontologies, authoritative-source resolvers, conflict contracts, and justified bridge coverage by submode.
- [ ] **DEFERRED:** Explore formal proofs of selected mode-separation invariants without confusing formal policy consistency with legal, clinical, or empirical truth.
- [ ] **DEFERRED:** Compare sparse 24D constraints against simpler rule-only policies before adopting any learned classifier.

The roadmap is intentionally incremental.

A substrate should become more portable, more compact, and more useful without becoming less inspectable or less trustworthy.

The canonical public substrate remains the source of truth.

Everything else — prose bundles, vector indexes, adapters, soft prompts, KV caches, model-specific latent projections, probe/report artifacts, consumer evaluations, and substrate-mode policy — is a reproducible projection, policy, or evaluation of that source.
