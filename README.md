# IndraNet

IndraNet is a candidate physical-context exchange architecture for spatial twins, embodied AI, XR, robotics, live performance, public-space context, executable-world research and receiver-side reconstruction.

Version 0.5.0 is an author-review candidate. The implementation uses synthetic inputs and reference mappings. It does not claim deployed vendor interoperability, official standards conformance, physical actuation authority, a trained neural decoder, measured bitrate advantage, safety certification, a canonical ROCK identifier or partner endorsement.

## What is here

- `src/indranet/`: standalone physical-context records plus the optional Rosetta projection and bounded reference runtime.
- `packs/stdpack-indranet-context/`: candidate Rosetta StdPack schemas, profiles, examples, translators, SHACL subset, migration notes and test vectors.
- `tests/`: fault-detecting tests for the standalone exchange, Rosetta companion and research-reference boundaries.
- `tools/`: candidate validation, native validation, Pack identity and constructor-parity probes.
- `outputs/` and `composition-results/`: deterministic synthetic fixtures used by the validation suite.
- `docs/IndraNet_Manuscript_v0.5.0.md`: the current manuscript source from the supplied corpus.
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

## Source and disclosure boundary

The supplied public-candidate projection contains 187 of 194 source-lock files. Seven private lineage/control records were intentionally omitted from that projection and remain omitted here. Their paths and source-lock hashes are recorded in `docs/source/PROJECTION_SCOPE.json` without reproducing their contents.

The candidate remains classified `screen-before-publication` in the supplied metadata. The repository preserves the public interoperability layer and the explicit non-claims of the source package.
