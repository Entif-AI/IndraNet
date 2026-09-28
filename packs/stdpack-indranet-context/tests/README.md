# Candidate acceptance tests

Run `PYTHONPATH=src python -m unittest discover -s tests -v` from the repository root.
Run `PYTHONPATH=src python tools/validate.py` for payload schemas, RDF constraint subset,
scenario replay and Pack identity. The parent repository's tests own executable behavior.

The SHACL file is standards-shaped. The included local evaluator implements only the
explicitly listed constraint subset. Run a full SHACL engine before claiming broader conformance.
The code does not claim native vendor runtime interoperability or full Rosetta Profile certification.
