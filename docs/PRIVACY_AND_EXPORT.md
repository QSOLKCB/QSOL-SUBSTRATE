# Privacy and Public Export

QSOL-SUBSTRATE is public-facing by construction. It should never be treated as a convenient mirror of private context.

## Explicit-allow publication

The safest export rule is:

```text
not explicitly approved for public export -> do not export
```

This is stronger than a denylist. A forgotten privacy marker must not cause publication.

## Omission semantics

A public substrate is intentionally incomplete. Therefore:

```text
absent != false
absent != nonexistent
absent == unavailable from this public substrate
```

AI systems must not infer that omitted personal, project, relationship, or historical information does not exist.

## Field-level export

A record may be public while one of its fields is not. Future export tooling should support field-level policies and strip non-public fields before canonicalisation.

## Fail-closed conditions

Automated export should fail when visibility is unspecified, provenance is ambiguous where required, a secret pattern is detected, a private-source reference would leak access details, a record type has no export policy, or a field is unknown to the export schema.

## No reconstruction of private context

Public records should not contain clues deliberately designed to let models reconstruct excluded private information. The purpose is useful public context, not reversible redaction.

## Publication review

Generated public diffs should be human-reviewable before release, especially when identity, correspondence, collaboration, health, credentials, or security-related fields are involved.
