# Acceptance boundary

Local acceptance requires schema parsing and fixture validation; deterministic scenario replay;
content digest and parent closure verification; source-span parity; explicit conflict and stale state;
refusal of context-purpose escalation; refusal of expired or changed process context; witness-aware
receiver modes; derivation-cycle detection; signed fixture verification; and current Pack ID.

Negative vectors must fail for digest tampering, unknown Core kinds, unsupported canonical values,
missing evidence, generated-state laundering, frame cycles, reflection, invalid validity intervals,
unauthorized views and invalid signatures. The API remains read-only and local by default.

Release remains blocked on author review, licensing and disclosure decisions. Live standards/runtime
acceptance, independent implementation, full SHACL and full Rosetta Profile conformance are separate
gates. Local success is not a safety, privacy, accuracy, bitrate, latency or causality certificate.
