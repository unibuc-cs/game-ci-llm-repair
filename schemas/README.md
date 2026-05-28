# Schemas

These JSON Schema files document the release-facing data structures used by the
offline prototype:

- `policy.schema.json`: T0-T3 repair policies.
- `architecture_card.schema.json`: reusable project constraints.
- `symptom_card.schema.json`: defect-specific evidence.
- `code_context.schema.json`: prompt-visible file scope and one-hop neighbors.

The runtime currently uses Python validation and deterministic tests rather
than a JSON Schema dependency, so these schemas are documentation and artifact
review aids.
