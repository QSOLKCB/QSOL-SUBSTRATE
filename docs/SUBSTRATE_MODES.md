# QSOL-SUBSTRATE Modes

Substrate Modes are a public, vendor-neutral policy layer for applying the same canonical substrate safely across specialist knowledge domains.

They are **not** personas, permissions, professional credentials, or independent sources of truth. Canonical public substrate records remain the source of truth. Modes determine how terminology, source admissibility, authority, uncertainty, and cross-domain translation are handled for a task.

## Composition

A resolved request is represented as:

```text
KNOWLEDGE_REQUEST
  = DOMAIN_MODE
  + ACTIVITY_MODE
  + EPISTEMIC_PROFILE_24D
  + DECLARED_BRIDGES
```

The machine entrypoint is `ai/mode-contract.json`.

## Domain modes

The initial registry contains 19 top-level modes:

- FORMAL
- SCIENCE
- LIFE_SCIENCE
- MEDICAL
- ENGINEERING
- COMPUTING
- SECURITY
- LEGAL
- GOVERNANCE
- ECONOMICS
- BUSINESS
- SOCIAL_SCIENCE
- HISTORY
- PHILOSOPHY
- HUMANITIES
- EDUCATION
- ARTS_MEDIA
- ENVIRONMENT
- EVERYDAY

Subfields remain submodes rather than top-level modes unless a future boundary requires materially different source or inference rules.

## Activity modes

Activities describe what the consumer is doing with knowledge, independently from the domain:

`RESEARCH`, `DIAGNOSTIC`, `DESIGN`, `DECISION`, `EDUCATIONAL`, `FORENSIC`, `HISTORICAL`, `PREDICTIVE`, `NORMATIVE`, and `CREATIVE`.

Activity modes cannot weaken a domain's source requirements or upgrade authority.

## Source admissibility and epistemic maturity

The central invariant is:

```text
CLAIM_STRENGTH <= EVIDENCE_ENTITLEMENT
```

Every source can be described independently by provenance class, publication state, claim maturity, scenario status, register, authority class, and claim scope. Source preferences are likewise keyed to the axis they constrain; a label from one axis must never be interpreted as a value on another.

This prevents common category errors:

```text
PEER_REVIEWED != ESTABLISHED
PREPRINT != PEER_REVIEWED
DOI != PEER_REVIEW
DOI != CLAIM_VALIDITY
ARCHIVED != VALIDATED
UNKNOWN != FALSE
FORMALIZATION != PHYSICAL_TRUTH
```

Claim maturity labels are `ESTABLISHED`, `CONSENSUS`, `SUPPORTED`, `CONTESTED`, `PRELIMINARY`, `THEORETICAL`, `PROPOSED`, `SPECULATIVE`, and `UNKNOWN`.

Scenario status is a separate axis: `ACTUAL`, `HYPOTHETICAL`, or `COUNTERFACTUAL`.

Register is also separate: `LITERAL`, `FICTIONAL`, or `SATIRICAL`.

This separation is deliberate. A satirical passage can still contain an auditable factual assertion that is independently supported, contradicted, or unavailable. Register must not erase claim-local evidence classification, and evidence classification must not erase register.

A consumer may weaken a claim when evidence is insufficient. It must not silently strengthen a claim without stronger evidence.

## Repository and DOI policy

A DOI or repository record can establish artifact identity, persistence, version identity, and resolvable metadata when those facts are verified.

It does not by itself establish peer review, independent validation, consensus, clinical effectiveness, binding legal authority, or truth of the claims inside the artifact.

Accordingly, repository-hosted material such as Zenodo records is admissible in theoretical, proposed, speculative, and unknown contexts. It may support a stronger claim maturity only when separate stronger evidence independently entitles that status.

## Legal mode

For claims presented as binding law, the default policy requires resolved **primary legal authority** appropriate to the jurisdiction. Commentary and scholarship may explain or help locate authority, but they do not become the final support for a binding claim merely by being persuasive or well cited.

Examples of protected distinctions:

```text
BILL != ACT
CONSULTATION != REGULATION
COMMENTARY != JUDGMENT
DRAFT_STANDARD != BINDING_REQUIREMENT
HISTORICAL_PRECEDENT != LEGAL_PRECEDENT
```

This architecture improves provenance discipline; it is not a guarantee of legal correctness and does not itself constitute legal advice.

## Medical mode

Medical research and clinical guidance are separate profiles.

Preprints and repository material may be used in research mode when their status is retained. They are non-normative for clinical guidance by default. Clinical guidance prefers current regulator material, current clinical guidelines, systematic evidence, and appropriately established consensus.

Protected distinctions include:

```text
IN_VITRO != CLINICAL_EFFICACY
ANIMAL_RESULT != HUMAN_RECOMMENDATION
SINGLE_STUDY != AUTOMATIC_GUIDELINE_OVERRIDE
BIOLOGICAL_PLAUSIBILITY != CLINICAL_EFFECTIVENESS
```

## Terminology namespaces

Field-sensitive words must not silently inherit a meaning from the wrong mode. Examples include:

```text
LEGAL:evidence
MEDICAL:evidence
SCIENCE:evidence

FORMAL:proof
LEGAL:proof

FORMAL:statistical_significance
MEDICAL:clinical_significance

LEGAL:causation
SCIENCE:causation
MEDICAL:causation
```

If a bare term is materially ambiguous, resolve the namespace before using it to justify a substantive inference.

## 24D mode geometry

`geometry/mode-space-v1.json` defines a 24-dimensional, interpretable validation space covering empirical/formal dependence, observational/experimental evidence, causality, prediction, normativity, individual/population specificity, jurisdiction, temporal sensitivity, uncertainty, evidentiary strength, reproducibility, source authority, provenance completeness, safety criticality, terminology rigidity, and cross-domain dependence.

The geometry is deliberately **not** an embedding-based truth score.

```text
COORDINATES != EVIDENCE
MODE_GEOMETRY != TRUTH
```

Sparse hard constraints detect structurally incompatible configurations. For example, a high-confidence binding legal claim with weak authority, or clinical guidance supported only by weak preliminary evidence, should fail mode validation rather than acquire invented evidence. Each hard constraint has a stable ID, explicit threshold axes, and a policy reference; the validator fails if those definitions drift or disappear.

## Bridges

Material cross-domain inference requires a declared bridge. A bridge is a translation contract, not evidence.

Examples:

```text
SCIENCE -> MEDICAL
LIFE_SCIENCE -> MEDICAL
MEDICAL -> LEGAL
FORMAL -> SCIENCE
FORMAL -> COMPUTING
COMPUTING -> SECURITY
ECONOMICS -> GOVERNANCE
ENVIRONMENT -> GOVERNANCE
```

Each bridge records non-equivalences that must survive translation. For example:

```text
medical causation != legal causation
statistical significance != clinical significance
formal consistency != empirical truth
functional != secure
historical analogy != prediction
```

If a task materially spans modes and no bridge is resolved, the correct result is `MODE_UNRESOLVED`, `MODE_AMBIGUOUS`, or `MODE_VIOLATION` rather than silent semantic crossover.

## Portable consumers

`ai/mode-contract.json` is part of `ai/manifest.json:normative_machine_files`. Portable adapters therefore carry the lightweight mode contract whenever their bootstrap tells a consumer to load it. Detailed mode registries, bridge data, and geometry remain selective resources rather than canonical facts.

## Validation

Run:

```bash
python tools/validate_modes.py
python -m unittest tests.test_substrate_modes -v
```

CI runs the mode validator alongside canonical substrate validation. It schema-validates the epistemic contract, checks mode/source-axis agreement, rejects untyped source preferences, validates the exact hard-constraint set and threshold axes, and verifies bridge/domain consistency.

## Boundary

Substrate Modes are a machine policy surface over canonical public knowledge. They must never become a back door for changing canonical facts, bypassing provenance, weakening uncertainty, or overriding model safety controls.
