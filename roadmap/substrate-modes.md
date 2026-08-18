# Phase 10 — Substrate Modes and Domain-Admissibility Geometry

Substrate Modes extend QSOL-SUBSTRATE with a public, vendor-neutral policy layer for specialist knowledge domains while preserving the canonical public substrate as the sole source of canonical truth.

## Implemented in Phase 10 bootstrap

- [x] Define Substrate Modes as bounded domain/epistemic contexts rather than personas, permissions, or authority levels.
- [x] Add 19 top-level domain modes covering formal knowledge, natural science, life science, medicine, engineering, computing, security, law, governance, economics, business, social science, history, philosophy, humanities, education, arts/media, environment, and everyday practical knowledge.
- [x] Add 10 cross-cutting activity modes: research, diagnostic, design, decision, educational, forensic, historical, predictive, normative, and creative.
- [x] Define the request composition contract: `DOMAIN_MODE + ACTIVITY_MODE + EPISTEMIC_PROFILE_24D + DECLARED_BRIDGES`.
- [x] Add explicit mode resolution states: `MODE_OK`, `MODE_AMBIGUOUS`, `MODE_CROSSOVER`, `MODE_VIOLATION`, and `MODE_UNRESOLVED`.
- [x] Add a source-admissibility model separating provenance class, publication state, epistemic status, authority class, and claim scope.
- [x] Enforce `CLAIM_STRENGTH <= EVIDENCE_ENTITLEMENT` as the central mode invariant.
- [x] Add claim maturity labels: established, consensus, supported, contested, preliminary, theoretical, proposed, speculative, unknown, hypothetical, counterfactual, fictional, and satirical.
- [x] Preserve preprint status and prevent silent promotion to peer reviewed or established.
- [x] Define repository/DOI semantics so archival identity and persistence cannot be mistaken for peer review, consensus, authority, or truth.
- [x] Permit repository-hosted/DOI material, including Zenodo-style archival records, in theoretical/proposed/speculative/unknown contexts while requiring separate stronger evidence for stronger claim states.
- [x] Add hard Legal mode policy: binding legal claims require resolved primary legal authority; commentary may explain but cannot become final binding authority.
- [x] Add Medical research/clinical separation: preprints and repository material may be used in labelled research contexts but are non-normative for clinical guidance by default.
- [x] Add field-sensitive terminology namespaces for ambiguous terms including evidence, proof, significance, causation, diagnosis, theory, model, test, risk, normal, liability, and validity.
- [x] Add an interpretable 24-dimensional mode-validation geometry.
- [x] Define geometry as structural validation machinery rather than a truth score, embedding oracle, or evidence source.
- [x] Add sparse hard geometry constraints for binding legal claims, clinical guidance, high-safety/low-evidence claims, and material cross-domain dependence.
- [x] Add explicit cross-domain bridges with non-equivalence rules for the highest-value domain crossings.
- [x] Require material cross-domain inference to declare a bridge rather than silently inheriting terminology or authority.
- [x] Add JSON Schema validation for the domain mode registry.
- [x] Add fail-closed `tools/validate_modes.py` validation.
- [x] Add regression tests for mode coverage, 24D geometry, bridge endpoints, high-stakes source guards, and the central evidence-entitlement invariant.
- [x] Run mode validation in the main GitHub Actions validation workflow.
- [x] Load the lightweight mode contract from `ai/bootstrap.json` while leaving detailed mode resources selective/on-demand.
- [x] Extend the canonical epistemic contract with claim maturity states and DOI/preprint/peer-review promotion guards.

## Completed deferred work — QSOL-MODE-POLICY/1

The former deferred list is now implemented as a versioned **derived policy/evaluation surface**. A checked item means the deterministic contract, resolver, runner, validator, or release binding exists. It does not fabricate empirical model results or convert policy into external truth.

- [x] Implement an empirical 24D calibration contract tied to frozen source commit, canonical substrate SHA-256, mode-policy SHA-256, exact model revision, and all delivery conditions. `tools/calibrate_mode_geometry.py` rejects scoring-oracle reports and never mutates thresholds automatically.
- [x] Build deterministic `MODE-CONFUSION/1` with 30 cases covering terminology transfer, bridge omission, authority escalation, jurisdiction/scope confusion, currentness, claim-strength inflation, DOI/peer-review promotion, high-safety/low-evidence uncertainty, register loss, and unresolved authority conflict.
- [x] Add scoring, condition comparison, and frozen cross-model calibration tooling for MICRO, STANDARD, FULL, vector-selected, latent-prefix, hybrid, tool-enabled, and naked conditions.
- [x] Propagate `QSOL-MODE-POLICY/1` through generated adapters and deterministic mode-bound delivery surfaces. Adapters embed `ai/mode-delivery.json`; `dist/mode-delivery/` supplies token-budgeted mode-aware tool-less capsules, vector retrieval prefixes, latent prefixes, and hybrid prefixes.
- [x] Define jurisdiction-specific Legal profiles and primary-authority resolver contracts for `AU-COMMONWEALTH` and `AU-SA`, with fail-closed jurisdiction/scope/time handling.
- [x] Define specialty-specific Medical policy profiles for general clinical medicine, emergency medicine, cardiology, oncology, psychiatry, pharmacology/medicines, and public health, with explicit current guideline/regulator resolution requirements.
- [x] Define claim-relative update/freshness policies for Medical, Legal, Engineering, Security, Computing, Governance, and Environment modes.
- [x] Expand the bridge registry only with concrete non-equivalence contracts, including Engineering→Legal, Security→Legal, Computing→Governance, and Medical→Governance.
- [x] Add a field-level terminology ontology for the highest-risk cross-domain collisions while retaining explicit namespace resolution.
- [x] Add authoritative-source resolver contracts for legislation, case law, regulators, clinical guidelines, standards bodies, security advisories, versioned computing documentation, official statistics, and primary datasets.
- [x] Add conflict-resolution contracts that partition sources by domain, jurisdiction/scope, authority, version, and time and preserve unresolved co-primary conflicts.
- [x] Add machine-checkable finite policy witnesses for claim-strength monotonicity, bridge non-authority, geometry non-evidentiary behavior, high-stakes fail-closed behavior, and conflict preservation. These prove internal policy properties only.
- [x] Add a deterministic sparse-24D versus rule-only structural benchmark before any learned classifier. The benchmark is mechanically labelled non-empirical; cross-model superiority still requires actual frozen consumer runs.
- [x] Add `mode_policy_sha256`, policy version, `MODE-CONFUSION/1` identity, and deterministic mode-delivery binding to the release bill of materials.

See [`docs/MODE_POLICY_V1.md`](../docs/MODE_POLICY_V1.md) for the executable contract and the empirical/non-empirical boundary.

## Empirical completion semantics

The implementation no longer has deferred **code** work in this Phase 10 list. Empirical claims remain run artifacts rather than repository checkboxes.

The following statements require real frozen consumer reports before they may be asserted:

- that one numeric 24D threshold is better calibrated than another;
- that sparse 24D constraints outperform rule-only policy on a particular model population;
- that one delivery condition improves a specific model;
- that a resolver has identified currently controlling legal authority or current clinical guidance.

The repository supplies the deterministic machinery to collect and compare that evidence. It does not substitute an oracle self-test for it.

## Exit principle

A mode implementation is acceptable only if it increases specialist usefulness without allowing a weaker evidence regime in one field to leak into another.

```text
DOMAIN_BOUNDARY != SILO
BRIDGE != EVIDENCE
DOI != VALIDATION
MODE != AUTHORITY
GEOMETRY != TRUTH
CLAIM_STRENGTH <= EVIDENCE_ENTITLEMENT
```
