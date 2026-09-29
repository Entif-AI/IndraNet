# Architecture

IndraNet v0.5.0 separates an independently usable physical-context exchange from an optional Rosetta representation layer.

## Native exchange

`src/indranet/native.py` defines the standalone record contract. Records carry source identity, event time, knowledge time, spatial frame and units, quality, derivation, purpose and lifecycle constraints. The local ledger preserves append-only history and bitemporal revision behavior. A native digest identifies the restricted JSON representation without claiming Rosetta CID or RFC 8785 equivalence.

`src/indranet/standards.py` composes the native record into selected NGSI-LD, SensorThings, locating-reference and GeoPose surfaces. The implementation treats mapping loss as data. It does not infer missing altitude, frame conversions, covariance, vendor certification or complete standards-runtime conformance.

## Optional Rosetta projection

`src/indranet/native_bridge.py` projects a validated native record into the candidate Rosetta companion. Received source bytes are preserved in an Observation. Derived native/state artifacts are distinct records with explicit epistemic roles and provenance.

The candidate Pack at `packs/stdpack-indranet-context/` uses Rosetta Core meaning where available and namespaced `indranet.*` kinds for domain structures. The Pack is compatible with Rosetta v3.x by declaration, remains draft, and has no assigned canonical ROCK identifier.

## Context runtime

The reference runtime is intentionally bounded:

- `model.py` creates parsed signals, assertions, revisions, contexts and associations.
- `store.py` provides local append-only SQLite artifact history.
- `views.py` constructs bitemporal, purpose-scoped views without inferred trust ranking.
- `frames.py` provides bounded rigid SE(3) frame transforms without covariance fusion.
- `process.py` produces context-bound OSC effect previews without sending device commands.
- `reality.py` handles prior-state/witness reconstruction planning and derivation invalidation.
- `rosetta.py` demonstrates interpretation chains and a public-fixture attestation path.
- `research_reference.py` keeps seven upstream research-system references inert and explicitly simulated.

## Scenario families

The repository preserves six deterministic contextual stories: performance, XR, warehouse, public space, executable worlds and Generative Reality. Separate composition timelines exercise native profile round trips and conflict/revision behavior.

These examples are evidence about the candidate contract and its local mechanics. They are not evidence that a live broker, headset, robot, safety controller, research model or neural receiver has been exercised.
