# Phase 2 Export Pipeline

QSOL-SUBSTRATE Phase 2 provides a fail-closed publication pipeline for producing a reviewable public bundle from a local private QSOL-CONTEXT checkout.

The exporter is a **publication boundary**, not a mirror.

```text
private QSOL-CONTEXT
        |
        | explicit field-by-field grants only
        v
public staging bundle
        |
        | human review
        v
QSOL-SUBSTRATE canonical payload
```

## Safety invariant

```text
not explicitly allowed -> not exported
```

The repository ships with `public_export/include.json` containing **zero publication grants**. This is intentional. A missing rule, forgotten marker, new field, unknown source reference, or ambiguous directive never becomes an implicit approval.

The exporter first canonicalises the already-public QSOL-SUBSTRATE payload into a staging directory. It then applies only enabled allowlist directives.

## Files

```text
public_export/
├── policy.json
├── include.json
└── exclude.json

tools/
└── export_public_substrate.py

tests/
└── test_export_public_substrate.py
```

`policy.json` defines the publication model and deterministic output rules.

`include.json` is the only authority that can grant private-to-public publication. Each enabled directive must explicitly declare `visibility: "public"` and every exported field must independently declare `visibility: "public"`.

`exclude.json` defines paths, field names, secret patterns, and private-reference patterns that cause export to stop.

## Running the exporter

Use local checkouts. The private repository does not need to be reachable from the public repository or from an AI consumer.

```bash
python3 tools/export_public_substrate.py \
  --source-root ../QSOL-CONTEXT \
  --output /tmp/qsol-substrate-export
```

The default output location should be outside the public repository. Writing under the QSOL-SUBSTRATE checkout requires the explicit `--allow-output-inside-repo` switch.

Replacing an existing output requires `--force`.

## Explicit publication grants

An enabled allowlist entry identifies:

- one private source JSON file;
- one exact object, either by JSON Pointer or exact match inside a selected collection;
- one canonical public target collection;
- whether creation of a previously absent public record is allowed;
- the public record ID, record type, and epistemic state;
- one or more already-public `src:*` provenance references;
- every field that may cross the boundary.

Conceptual example:

```json
{
  "id": "example-public-project",
  "enabled": true,
  "visibility": "public",
  "source": {
    "path": "path/to/source.json",
    "collection_pointer": "/records",
    "match": {
      "pointer": "/id",
      "equals": "private-source-id"
    }
  },
  "target": {
    "path": "projects/index.json",
    "collection_pointer": "/projects",
    "allow_create": false,
    "sort_by": "/id"
  },
  "record": {
    "id": "project:example",
    "record_type": "project",
    "epistemic_state": "known",
    "public_source_refs": ["src:example-readme"],
    "fields": [
      {
        "from": "/name",
        "to": "/name",
        "visibility": "public"
      }
    ]
  }
}
```

This example is illustrative only and is not a publication grant.

Unselected source fields are never copied. Private provenance arrays are never copied. Public `source_refs` are supplied by the allowlist and must resolve through the existing public `sources/index.json` registry.

`sources/index.json` is immutable to the private exporter. New public evidence must first be added from public evidence through ordinary review.

## Field-level visibility

There is no default public field.

Each exported field requires:

```json
{
  "from": "/source/pointer",
  "to": "/public/field",
  "visibility": "public"
}
```

A field can also use an explicit constant:

```json
{
  "value": "public constant",
  "to": "/metadata/classification",
  "visibility": "public"
}
```

If `visibility` is absent, misspelled, ambiguous, or anything other than `public`, export stops.

## Redaction

Explicit redaction is supported:

```json
{
  "redact_from": "/nonpublic/detail",
  "to": "/metadata/detail",
  "visibility": "public",
  "replacement": "[REDACTED]"
}
```

Redaction is not a credential-sanitisation escape hatch. Selected source material is still scanned for secret patterns before a redaction is accepted. If a credential-like secret is detected, the exporter fails instead of publishing a placeholder and pretending the incident is solved.

Prefer omission over redaction when the existence of a private field is itself sensitive.

## Secret and private-reference scanning

The deny policy rejects configured classes including:

- common GitHub, API, cloud, bearer, and private-key credential patterns;
- secret-bearing field names;
- `.env`, secret, and credential source paths;
- local filesystem references;
- localhost URLs;
- direct URLs or Git references to the private QSOL-CONTEXT repository.

Scanning is performed on selected source values and again over the complete generated public payload.

A hit stops the export.

## Provenance

Private provenance is not public provenance.

Every generated public record must declare a non-empty list of `public_source_refs`. Every reference must already exist in the public source registry.

Therefore:

```text
private source evidence
    !=
public citation authority
```

The private source can supply candidate facts. Publication still requires independently declared public provenance.

## Deterministic canonicalisation

Phase 2 defines:

### `qsol-canonical-json-v1`

- UTF-8;
- lexicographically sorted object keys;
- no NaN or Infinity;
- compact separators `,` and `:`;
- Unicode preserved rather than ASCII-escaped;
- exactly one trailing newline.

### `qsol-canonical-jsonl-v1`

Each non-empty record is canonicalised using `qsol-canonical-json-v1`. Declared record order is preserved.

The exporter re-canonicalises the complete public baseline before applying private export directives. The same source snapshot, public baseline, and export configuration therefore produce the same payload bytes and hashes.

## Export manifest and fingerprint

The staging directory includes:

```text
export-manifest.json
```

It records:

- export policy;
- source protocol, but no private source URL;
- canonicalisation contract;
- omission semantics;
- configuration SHA-256;
- applied public directive IDs;
- SHA-256 and byte length for every canonical payload file;
- bundle SHA-256.

The bundle fingerprint is derived from the ordered public path/hash/length table. It does **not** hash private source material into the public manifest.

## Optional private audit manifest

For local/private auditing:

```bash
python3 tools/export_public_substrate.py \
  --source-root ../QSOL-CONTEXT \
  --output /tmp/qsol-substrate-export \
  --audit-manifest /private/path/qsol-export-audit.json
```

The audit manifest may contain private source paths and source-file hashes. For that reason the tool refuses to write it inside the public output directory.

Do not commit the private audit manifest to QSOL-SUBSTRATE.

## Omission semantics

The exporter never converts omission into a negative fact.

```text
not selected -> unavailable from this public export
not selected != false
not selected != nonexistent
```

This applies equally to records, fields, relationships, projects, publications, and chronology.

## Failure model

Export is refused when, among other conditions:

- the source root does not identify itself as QSOL-CONTEXT;
- an enabled directive lacks explicit public visibility;
- an exported field lacks explicit public visibility;
- source selection is ambiguous or matches zero/multiple records;
- a source path escapes the declared private root;
- a target is not an existing canonical payload file;
- a directive attempts to mutate the public source registry;
- public provenance is missing or unknown;
- a secret pattern is found;
- a forbidden field or private reference is found;
- output would be written into the public repo without explicit permission;
- a private audit manifest would land in the public bundle.

The correct failure mode is:

```text
EXPORT REFUSED
```

not best-effort publication.

## Review discipline

The generated bundle is a candidate for review. It is not self-authorising publication.

A maintainer should diff the generated canonical payload against the repository, inspect provenance and omissions, and only then commit approved public changes.

Phase 3 will add repository-wide schema, referential, provenance, boundary, fingerprint, and CI enforcement around this pipeline.
