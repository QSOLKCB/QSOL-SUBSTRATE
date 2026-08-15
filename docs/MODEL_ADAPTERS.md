# Model Adapters

Model adapters translate QSOL-SUBSTRATE into a form a particular model ecosystem can consume efficiently. They are transport layers, not alternate truth sources.

## Adapter invariants

Every adapter should preserve canonical entity identifiers, epistemic state, public/private boundary semantics, source precedence, `unknown` behaviour, provenance references, and substrate version identity.

An adapter may compress, reorder, chunk, embed, or reformat content. It may not strengthen a claim merely because a target model prefers confident prose.

## Generic adapter

The generic path should work with any system capable of reading text or JSON. A future exporter can produce a canonical single-file bundle plus a compact bootstrap.

## Grok

Potential transports include chat file upload, repository/project context, agent project rules, reusable skills, or xAI retrieval collections depending on the product surface in use.

## Sider

Potential transports include reusable custom prompts and indexed knowledge material. The persistent bootstrap should remain compact while larger records are retrieved selectively.

## Ollama and local models

A local adapter can combine a short system bootstrap with a local RAG store or generated context bundle. Model-specific token budgets should affect chunking, not truth semantics.

## Future adapters

Adapters for OpenAI-compatible APIs, Anthropic-compatible APIs, Gemini, Qwen tooling, DeepSeek tooling, and other agent systems can be added without changing canonical records.
