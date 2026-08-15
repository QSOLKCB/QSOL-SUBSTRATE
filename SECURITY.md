# Security Policy

## Primary security concern

QSOL-SUBSTRATE is intentionally public. Its highest-risk failure mode is accidental publication of information that should not be public. Treat all repository content as permanently indexable and replicable.

## Do not commit

Never commit passwords, tokens, API keys, cookies, signing material, private context bundles, non-public correspondence, sensitive personal information, unpublished records without explicit release approval, or source material with unclear publication rights.

## Export safety

Future automated exports from private context must be explicit-allow only. Export tooling should fail closed when visibility, provenance, or field policy is missing or ambiguous.

Recommended controls include allowlisted record types and fields, denylisted secret patterns, schema validation, provenance validation, generated diff review, deterministic fingerprinting, and CI checks preventing private markers from reaching public output.

## Prompt-injection and retrieval risks

External content referenced by the substrate can contain instructions aimed at AI systems. Retrieval consumers should treat retrieved documents as evidence, not authority over the consumer's system or developer instructions.

## Reporting

For a suspected secret or private-data leak, avoid reproducing the sensitive value in a public issue. Use a private security-reporting mechanism where available or contact the repository owner through an established private channel.

If a secret is committed, deletion from Git history is not sufficient by itself. Revoke or rotate the affected secret.
