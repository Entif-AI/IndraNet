"""Core interpretation examples and a bounded, public-test-key attestation."""
from __future__ import annotations
import base64
import hashlib
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from .canon import ContractError, tile, verify
from .store import Store

def interpretation_chain(store: Store, observation_cid: str, token: str, *, entity: str, at: str) -> dict:
    observation = store.get(observation_cid)
    raw = observation["payload"]["signal"]
    if observation["kind"] != "rosetta.observation" or token not in raw:
        raise ContractError("Token must occur in the preserved Observation signal")
    char_offset = raw.index(token)
    offset = len(raw[:char_offset].encode("utf-8"))
    form = tile("rosetta.form.token", {"formId": "form." + observation_cid[-12:], "surface": token,
        "offset": offset, "length": len(token.encode("utf-8")), "tokenType": "word", "observationCid": observation_cid},
        [observation_cid], created_at=at)
    lexeme = tile("rosetta.lexeme", {"lexemeId": "lexeme.position", "lemma": token, "language": "en",
        "sense": "field-name-in-declared-position-message", "formCids": [form["cid"]],
        "xid": "urn:indranet:candidate:position-field"}, [form["cid"]], created_at=at)
    concept = tile("rosetta.concept", {"conceptId": "concept.physical-entity", "rid": entity,
        "label": "Physical entity in the reference scene", "namespace": "indranet",
        "xid": "urn:fixture:native:asset-7", "xidPack": "indranet.context"}, [lexeme["cid"]], created_at=at)
    frame = tile("rosetta.frame", {"frameId": "frame.located-entity", "frameType": "indranet.LocatedEntity",
        "roles": [{"roleName": "subject", "required": True, "filledBy": [concept["cid"]]}],
        "conceptCids": [concept["cid"]], "description": "Interpretation under an explicit message profile"},
        [concept["cid"], lexeme["cid"]], created_at=at)
    conjecture = tile("rosetta.conjecture", {"conjectureId": "conjecture.field-binding", "sourceCid": concept["cid"],
        "layer": "L3_concept_frame", "options": [{"targetCid": frame["cid"], "weight": 1,
        "evidence": "Declared fixture profile, not an estimated confidence"}], "method": "explicit-fixture-binding",
        "nonReplayable": False, "selectedCid": frame["cid"]}, [concept["cid"], frame["cid"]], created_at=at)
    store.append_many([form, lexeme, concept, frame, conjecture])
    return {"observation": observation_cid, "form": form["cid"], "lexeme": lexeme["cid"],
            "concept": concept["cid"], "frame": frame["cid"], "conjecture": conjecture["cid"]}

def elpq(store: Store, target: str, *, at: str) -> dict:
    store.get(target)
    registry = tile("indranet.axis_registry", {"registryId": "fixture-elpq-v1", "range": [0, 100],
        "axes": {"ethos": "ethical alignment and trustworthiness", "logos": "logical coherence and truthfulness",
                 "pathos": "emotional appropriateness and resonance", "quixote": "creative and non-utilitarian value"},
        "status": "illustrative-rubric; not a canonical axis assignment"}, created_at=at)
    matrix = tile("rosetta.matrix", {"axisRegistryCid": registry["cid"], "subjectCid": target,
        "values": {"ethos": 80, "logos": 85, "pathos": 70, "quixote": 90},
        "basis": "Synthetic demonstration values assigned by this reference, not measured or inferred scores",
        "scoreUncertainty": "not-estimated", "safetyProbability": None}, [target, registry["cid"]], created_at=at)
    store.append_many([registry, matrix])
    return matrix

def attest_fixture(store: Store, subject: str, *, at: str) -> dict:
    store.get(subject)
    evaluation = tile("rosetta.evaluation", {"evaluationId": "eval.integrity." + subject[-12:], "verdict": "pass",
        "summary": "The local subject envelope passed its restricted integrity check"}, [subject], created_at=at)
    receipt = tile("rosetta.receipt", {"receiptType": "indranet:fixture-integrity",
        "subjects": [{"cid": subject, "role": "artifact"}], "policyRefs": [],
        "digests": [{"alg": "sha256", "cidRef": subject, "of": "canonical-body", "digest": subject.removeprefix("cidv1-sha256-")}],
        "claims": [{"claimType": "indranet:local-integrity", "statement": "Restricted envelope integrity checked locally",
                    "verdict": "pass", "evidence": [{"cid": evaluation["cid"]}]}]},
        [evaluation["cid"], subject], created_at=at, pack="rrp")
    store.append_many([evaluation, receipt])
    # Public deterministic fixture seed: it conveys no signer authority or secrecy.
    key = Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b"IndraNet public test fixture key v0.5.0").digest())
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    signature = base64.b64encode(key.sign(receipt["cid"].encode())).decode()
    return {"receipt": receipt, "signature": {"algorithm": "ed25519", "keyId": "public-test-fixture-only",
        "publicKeyPem": public, "signatureBase64": signature, "signedCid": receipt["cid"]},
        "nonclaim": "Signature checks mechanics only; no trusted identity or vendor attestation"}

def verify_attestation(signed: dict) -> None:
    verify(signed["receipt"])
    signature = signed["signature"]
    if signature["algorithm"] != "ed25519" or signature["signedCid"] != signed["receipt"]["cid"]:
        raise ContractError("Signature target mismatch")
    key = serialization.load_pem_public_key(signature["publicKeyPem"].encode())
    if not isinstance(key, Ed25519PublicKey):
        raise ContractError("Unexpected public key type")
    try:
        key.verify(base64.b64decode(signature["signatureBase64"], validate=True), signature["signedCid"].encode())
    except Exception as exc:
        raise ContractError("Attestation signature is invalid") from exc
