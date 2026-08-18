# QSOL-MODE-POLICY/1

`QSOL-MODE-POLICY/1` completes the first versioned Substrate Modes policy surface. It is a **derived, noncanonical policy layer** over QSOL-SUBSTRATE. It constrains how evidence may be interpreted and moved across domains; it does not create factual, legal, clinical, scientific, or professional authority.

## Core boundary

```text
CLAIM_STRENGTH <= EVIDENCE_ENTITLEMENT

MODE != AUTHORITY
GEOMETRY != TRUTH
BRIDGE != EVIDENCE
DOI != VALIDATION
```

The policy fingerprint is intentionally separate from the canonical substrate fingerprint. A canonical substrate snapshot can remain byte-identical while the noncanonical mode policy changes, and empirical mode comparisons are valid only when the exact mode-policy fingerprint also matches.

## Versioned resources

The versioned policy surface is indexed by `dist/modes/policy-index.json` and includes:

- `ai/mode-contract.json` and `ai/mode-delivery.json`
- domain/activity registries and source admissibility policy
- 24D validation geometry
- field terminology namespace and ontology resources
- jurisdiction-specific Legal resolver profiles
- specialty-specific Medical profiles
- authoritative-source resolver contracts
- claim-relative freshness policy
- explicit conflict-resolution contracts
- declared cross-domain bridges
- finite machine-checkable mode-separation witnesses
- the deterministic `MODE-CONFUSION/1` corpus

`tools/build_modes.py` fingerprints those resources into `dist/modes/`. `tools/validate_mode_bundle.py` rebuilds the bundle byte-for-byte.

## MODE-CONFUSION/1

`MODE-CONFUSION/1` is a deterministic 30-case stress suite covering:

- accidental terminology transfer
- undeclared bridge use
- authority escalation
- jurisdiction and scope confusion
- currentness/version failures
- Medical preprint-to-guidance promotion
- DOI and peer-review promotion
- claim-strength inflation
- high-safety/low-evidence uncertainty
- register loss
- scenario-to-observation promotion
- unresolved co-primary conflicts

The repository ships a deterministic scoring oracle only as an implementation self-test. Oracle output is mechanically labelled non-empirical and the geometry calibration tool refuses oracle reports.

Empirical runs use `schema/mode-run.schema.json`, bind the exact source commit, canonical substrate SHA-256, mode-policy SHA-256, mode-bundle SHA-256, delivery condition, model ID, and immutable model revision, and are scored by `tools/score_mode_run.py`.

## Calibration

`tools/calibrate_mode_geometry.py` accepts only empirical consumer reports. It requires:

- at least two distinct immutable model revisions
- complete coverage of naked, MICRO, STANDARD, FULL, vector, latent-prefix, hybrid, and tool-enabled conditions
- one exact frozen substrate and mode-policy identity

Calibration output is recommendation-only. It never rewrites `geometry/mode-space-v1.json`. This prevents an evaluation script from silently turning observed model behaviour into a claim that an alternative threshold is epistemically truer.

The deterministic structural reference benchmark compares the sparse 24D guard set with a rule-only baseline before any learned classifier is considered.

## Legal resolution

`modes/legal-jurisdictions.json` defines fail-closed jurisdiction profiles for:

- `AU-COMMONWEALTH`
- `AU-SA`

`modes/authority-resolvers.json` defines metadata contracts for legislation, case law, and regulator sources. These resolver records classify source identity and applicability. They are **not legal authority themselves** and do not decide the legal conclusion.

For a material binding Legal-mode claim:

1. jurisdiction must be resolved;
2. primary legal authority must be resolved;
3. temporal/version scope must be resolved;
4. conflicting co-primary authorities must remain conflict/unresolved until the controlling relationship is established.

No Australian jurisdiction is silently generalized into another.

## Medical resolution

`modes/medical-specialties.json` defines initial profiles for general clinical medicine, emergency medicine, cardiology, oncology, psychiatry, pharmacology/medicines, and public health.

Current clinical-guidance claims require a resolved applicable scope, current regulator/guideline source, version or effective date, retrieval date, and provenance. Preprints and repository artifacts remain research evidence and are non-normative for clinical guidance by default.

The profiles are policy constraints, not treatment instructions or a frozen medical knowledge base.

## Freshness and conflicts

`modes/freshness-policy.json` uses claim-relative freshness classes rather than a universal time-to-live. Current Security, Governance, clinical, regulator, and other volatile claims can require live primary-source resolution, while version-bound or historical questions can be answered from exact dated/versioned material.

`modes/conflict-policy.json` prevents a common failure mode: synthesizing incompatible authorities into an invented compromise. Evidence is partitioned by domain, jurisdiction/scope, authority class, version, and applicable time before a conflict is resolved.

## Delivery compatibility

The source contract `ai/mode-delivery.json` is part of the normative machine-file projection, so generated adapters carry the mode guard.

`tools/bind_mode_delivery.py` then produces `dist/mode-delivery/`:

- token-budgeted mode-aware MICRO/STANDARD/FULL tool-less capsules;
- a vector retrieval mode prefix;
- a stable latent epistemic-mode prefix;
- a hybrid mode prefix;
- a manifest binding all of those surfaces to the exact mode policy and canonical substrate.

`tools/retrieve_mode_context.py` is the mode-aware vector retrieval entry point and prepends the mode contract to every returned context.

Mutable authority, regulator, guideline, and freshness facts are deliberately **not** baked into a stable latent state.

## Formal witness boundary

`formal/mode-separation.json` and the mode bundle build perform finite machine checks for selected internal invariants, including claim-strength monotonicity, bridge non-authority, geometry non-evidentiary behavior, high-stakes fail-closed behavior, and conflict preservation.

These checks prove only properties of the finite policy model.

```text
FORMALIZATION != PHYSICAL_OR_LEGAL_OR_CLINICAL_TRUTH
```

A future Lean 4 formalization may strengthen the proof machinery, but it must not erase that boundary.

## Release identity

Phase 8 release manifests now bind both:

- the canonical substrate identity, and
- the versioned mode-policy bundle plus its `mode_policy_sha256`.

The release build also validates the deterministic mode-delivery binding. This keeps canonical truth identity separate from policy identity while making the complete consumer contract reproducible.

## What remains empirical

The implementation is complete, but cross-model performance remains evidence-bearing work. No repository CI run is described as a hosted/open-weight model result.

Real claims such as “24D performs better than rule-only” or “local negative-boundary guards improve a specific model” require frozen empirical consumer runs. The tooling for those experiments is complete; the results must come from actual executions.
