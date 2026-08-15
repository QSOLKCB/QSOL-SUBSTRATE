# Privacy and Public Export

QSOL-SUBSTRATE is public-facing by construction. It must never be treated as a convenient mirror of private context.

## Explicit-allow publication

The export rule is:

```text
not explicitly approved for public export -> do not export
```

This is stronger than a denylist. A forgotten privacy marker, a newly added source field, or an unrecognised record does not cause publication.

Phase 2 implements this rule with `public_export/policy.json`, `public_export/include.json`, `public_export/exclude.json`, and `tools/export_public_substrate.py`.

The shipped allowlist contains **zero publication grants**. Private-to-public publication begins only when a maintainer adds and reviews an enabled field-by-field directive.

## Omission semantics

A public substrate is intentionally incomplete. Therefore:

```text
absent != false
absent != nonexistent
absent == unavailable from this public substrate
```

AI systems must not infer that omitted personal, project, relationship, or historical information does not exist.

The exporter preserves this rule: an unselected record or field is omitted, not converted into a negative assertion.

## Field-level export

A record may contain both public and non-public material. Phase 2 does not copy whole private records.

Every field crossing the boundary requires an explicit allowlist rule with `visibility: "public"`. Missing, ambiguous, or non-public visibility fails closed.

Unselected fields are not copied. The private record's provenance array is not copied either; generated public records must cite already-public `src:*` entries from `sources/index.json`.

## Redaction

Explicit redaction is available for deliberately reviewed fields, but omission is preferred when the existence of a private field is itself sensitive.

Secret detection still runs against selected source material before redaction. Redaction therefore cannot be used to turn a detected credential into an apparently safe public artifact.

## Secret and private-reference scanning

`public_export/exclude.json` defines fail-closed checks for credential-like values, secret-bearing field names, secret/config paths, local filesystem references, localhost endpoints, and direct references to the private QSOL-CONTEXT repository.

Scanning occurs on selected source values and again over the generated public payload.

A hit causes `EXPORT REFUSED`.

## Provenance boundary

Private provenance is not automatically suitable for a public substrate.

Every generated record must declare non-empty public `source_refs`, and every reference must already exist in the public source registry. The private exporter is not allowed to modify `sources/index.json`.

New public evidence should be added from public primary evidence through ordinary repository review before it can authorise private-to-public export.

## Public and private manifests

The generated public `export-manifest.json` contains public payload hashes, the export configuration hash, applied directive IDs, canonicalisation identity, and a bundle fingerprint. It does not contain private source paths or private source hashes.

An optional private audit manifest can record internal source paths and hashes for local auditing. The exporter refuses to write this audit file inside the public output directory.

Do not commit a private audit manifest to QSOL-SUBSTRATE.

## Fail-closed conditions

Automated export fails when visibility is unspecified, provenance cannot be resolved through the public registry, source selection is ambiguous, a source path escapes its declared root, a secret pattern is detected, a private-source reference would leak access details, a target is outside the canonical payload, a directive attempts to mutate the public source registry, or a private audit artifact would land in public output.

The pipeline has no wildcard-copy or "best effort" publication mode.

## No reconstruction of private context

Public records should not contain clues deliberately designed to let models reconstruct excluded private information. The purpose is useful public context, not reversible redaction.

## Publication review

Generated public bundles are **staging artifacts**, not self-authorising publication.

A maintainer should diff the generated payload against QSOL-SUBSTRATE and review identity, correspondence, collaboration, health, credentials, security-related material, provenance, and omission semantics before committing any generated change.

See [`EXPORT_PIPELINE.md`](EXPORT_PIPELINE.md) for the Phase 2 command, allowlist format, deterministic canonicalisation contract, fingerprints, tests, and failure behaviour.
