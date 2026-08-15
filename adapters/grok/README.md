# Grok Adapter

QSOL-SUBSTRATE can be supplied to Grok through whatever public context mechanism is available in the chosen xAI product surface: repository/project context, file upload, knowledge retrieval, project rules, or reusable agent skills.

Adapter rules:

- keep the bootstrap compact;
- retrieve larger public records selectively;
- do not ask Grok to treat substrate content as higher priority than xAI system or safety instructions;
- preserve unknown/conflict responses rather than rewarding confident guessing;
- record the substrate commit and model identifier during evaluations.

Future work may add generated Grok Build project rules and a retrieval-collection export.
