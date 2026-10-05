# IndraNet

**IndraNet is the relational fabric among independently bounded cognitive participants in Entif AI's Unified Cognitive Architecture.**

Those participants are called **Jewels**.

A Jewel can be a model runtime, a personal sovereign instance, a server, a specialized service, a robot, a sensor-actuator assembly, or another independently addressable participant. It may have cognition, memory, inference, observation, communication, embodiment, actuation, local policy, or only a subset of them.

Embodiment is optional. The boundary is the point.

One Jewel may itself contain many graph nodes, compute nodes, processes, agents, models, or devices. `Jewel` is therefore a UCA participant-level term, **not a replacement for ordinary technical node terminology and not a new Rosetta Core kind**.

## Why IndraNet?

The design mnemonic comes from the later Buddhist and Huayan image commonly called **Indra's Net**: an immense relational web whose junctions hold multifaceted jewels, each reflecting others while remaining a distinguishable locus in the whole.

IndraNet does not claim to instantiate a religious cosmology. The metaphor is useful because it describes the architecture we actually want better than "a bunch of nodes": locally bounded participants whose relationships can carry information, evidence, cognition, correction, and eventually coordinated action without requiring one central mind to own the network.

## Swarm Gnosis

When useful cognition crosses Jewel boundaries, the architecture calls the larger pattern **Swarm Gnosis**.

The objective is not to upload everyone's private cognition into a giant common context. A Jewel should be able to contribute a bounded artifact while retaining its private memory, internal prompts, local policy, proprietary model state, and unrelated evidence.

What travels should carry enough structure for the receiver to reason about it:

```text
artifact identity
+ provenance
+ evidence / computation lineage
+ qualification and scope
+ rights and purpose limits
+ uncertainty / alternatives
+ correction and invalidation path
+ receiver-local admission decision
```

A laboratory Jewel may contribute an observation. A specialist may contribute a method. Another Jewel may provide an independent witness. A larger model may synthesize what remains unresolved. The participants do not need identical memories or identical ontologies to cooperate on the task.

A remote result imports **work**, not authority.

## Two resolutions of IndraNet

The current repository predates this broader UCA framing and contains a deliberately narrower, concrete specialization.

At the architectural level, **IndraNet is the relational plane among Jewels**: communication, qualified state exchange, coordination, observation, reusable cognition, and, where applicable, interaction with a shared physical world.

At the present reference-implementation level, IndraNet specializes that fabric for **physical context** across spatial twins, embodied AI, XR, robotics, live performance, public-space context, executable-world research, receiver-side reconstruction, sensing, simulation, rendering, and actuation.

The physical-context work is a proving surface of the broader architecture, not a claim that IndraNet exists only in meat-space or that every Jewel has sensors and motors.

## The current physical-context reference

Version 0.5.0 is an author-review candidate. The implementation uses synthetic inputs and reference mappings. It does not claim deployed vendor interoperability, official standards conformance, physical actuation authority, a trained neural decoder, measured bitrate advantage, safety certification, a canonical ROCK identifier, a deployed global Jewel federation, or partner endorsement.

The standalone exchange is independently usable. Its candidate records preserve spatial frame, event and knowledge time, evidence role, quality, revision history, purpose limits, mapping loss, and branchable state without requiring Rosetta.

The optional Rosetta companion maps qualified physical-context exchange into source-linked observations, interpretations, alternatives, evaluations, and receipts. External native bytes remain preserved instead of disappearing into a new identity system.

A digest is not physical truth. A compatible operation is not permission to act. A simulation is not an observation merely because its pixels look convincing.

## What is here

- `src/indranet/`: standalone physical-context records plus the optional Rosetta projection and bounded reference runtime.
- `packs/stdpack-indranet-context/`: candidate Rosetta StdPack schemas, profiles, examples, translators, SHACL subset, migration notes and test vectors.
- `tests/`: fault-detecting tests for the standalone exchange, Rosetta companion and research-reference boundaries.
- `tools/`: candidate validation, native validation, Pack identity and constructor-parity probes.
- `outputs/` and `composition-results/`: deterministic synthetic fixtures used by the validation suite.
- `docs/IndraNet_Manuscript_v0.5.0.md`: the current physical-context manuscript source from the supplied corpus.
- `docs/architecture.md`: repository-oriented architecture map.
- `docs/open-work.md`: unresolved work extracted from the manuscript, validation report and implementation limits.
- `docs/source/`: source-projection and validation receipts retained for provenance.

## Run the reference implementation

Use Python 3.10 or newer and Node.js for the candidate Pack identity check.

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
python -m indranet.demo --out outputs
python -m indranet.scenarios --out composition-results
python tools/validate.py --report outputs/validation.json
python tools/validate_native.py
node tools/rosetta-constructor-probe.mjs
```

The exact observed production environment is recorded in `requirements-observed.txt`. Compatible dependency ranges live in `pyproject.toml`; this repository does not claim bit-for-bit environment reproduction.

## Architectural boundary

`src/indranet/native.py` is independently usable and depends only on the Python standard library. It validates qualified physical-context records, computes an IndraNet-native digest, preserves bitemporal revision history and branches, and produces purpose-limited views.

The candidate can be projected into explicit NGSI-LD and SensorThings selected-field profiles, with GeoPose emitted only for compatible geodetic poses. The locating reference is independently authored and is not claimed as certified omlox interoperability. `src/indranet/native_bridge.py` is the optional Rosetta boundary. External native bytes remain preserved as observations while derived state remains separately typed and attributable.

The richer companion stories cover performance, XR, warehouse operations, public-space context, executable-world hypotheses and Generative Reality reconstruction. They are deterministic synthetic examples. Their signing key is a public fixture used to test mechanics, not an operational identity credential.

## Generative Reality

A related research branch asks whether a receiver can reconstruct an experience from three separable sources:

1. a prepared world prior;
2. changing executable state;
3. selective fresh witnesses for novelty the receiver cannot derive locally.

That could eventually reduce redundant transport while keeping source state and generated appearance distinguishable. The present package defines and simulates contracts around the idea. It does not establish a trained neural receiver, evidence-faithful photorealistic reconstruction, or end-to-end bandwidth savings.

## Source and disclosure boundary

The supplied public-candidate projection contains 187 of 194 source-lock files. Seven private lineage/control records were intentionally omitted from that projection and remain omitted here. Their paths and source-lock hashes are recorded in `docs/source/PROJECTION_SCOPE.json` without reproducing their contents.

The candidate remains classified `screen-before-publication` in the supplied metadata. The repository preserves the public interoperability layer and the explicit non-claims of the source package.

The broader Jewel/Swarm Gnosis framing described here is an architectural interpretation from the Unified Cognitive Architecture. It does not retroactively convert the current physical-context implementation into a deployed global cognitive network.
