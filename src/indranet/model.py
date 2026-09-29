"""Domain records refine Core semantics; they do not replace Core identity."""
from __future__ import annotations
import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Any
from .canon import ContractError, tile, timestamp
from .store import Store
from .native import strict_loads, ExchangeError

ROLES = {"reported-measurement", "human-report", "inferred", "predicted", "simulated", "synthesized"}

def decimal_text(value: Any) -> str:
    if type(value) is bool:
        raise ContractError("Boolean is not a quantity")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ContractError("Invalid decimal quantity") from exc
    if not number.is_finite():
        raise ContractError("Nonfinite quantity")
    return format(number, "f")

def ingress(store: Store, raw: str, *, source: str, event_time: str, known_at: str,
            purposes: list[str], data_origin: str = "synthetic-fixture") -> tuple[dict, dict]:
    timestamp(event_time); timestamp(known_at)
    if timestamp(event_time) > timestamp(known_at):
        raise ContractError("This measured-ingress profile requires event time no later than receipt")
    if not source or not purposes:
        raise ContractError("Ingress requires a source and explicit permitted purposes")
    try:
        strict_loads(raw)
    except ExchangeError as exc:
        raise ContractError(str(exc)) from exc
    obs = tile("rosetta.observation", {"observationId": "observation." + hashlib.sha256(raw.encode()).hexdigest()[:16],
        "signal": raw, "source": source}, created_at=known_at)
    form = tile("indranet.parsed_signal", {"observationCid": obs["cid"], "parser": "python-json-reference",
        "mediaType": "application/json", "eventTime": event_time, "knownAt": known_at,
        "purposes": sorted(set(purposes)), "dataOrigin": data_origin,
        "sourceSha256": hashlib.sha256(raw.encode()).hexdigest()}, [obs["cid"]], created_at=known_at)
    store.append_many([obs, form])
    return obs, form

def assertion(store: Store, *, subject: str, predicate: str, value: dict | str | int,
              evidence: list[str], event_time: str, known_at: str, purposes: list[str],
              role: str = "reported-measurement", frame: str | None = None,
              uncertainty: dict | None = None, valid_until: str | None = None,
              source: str = "fixture", data_origin: str = "synthetic-fixture") -> dict:
    if not subject or not predicate or not evidence or not purposes or role not in ROLES:
        raise ContractError("Assertion requires identity, evidence, purpose and a supported epistemic role")
    timestamp(event_time); timestamp(known_at)
    if role in {"reported-measurement", "human-report"} and timestamp(event_time) > timestamp(known_at):
        raise ContractError("A future event cannot be admitted as a received measurement")
    if valid_until is not None and timestamp(valid_until) <= timestamp(event_time):
        raise ContractError("Validity interval must be nonempty")
    for parent in store.closure(evidence):
        parent_role = parent["payload"].get("role") if parent["kind"] == "indranet.native_record" else parent["payload"].get("epistemicRole")
        if role == "reported-measurement" and parent_role in {"simulated", "predicted", "synthesized"}:
            raise ContractError("Generated state cannot become measurement through this constructor")
    payload = {"subject": subject, "predicate": predicate, "value": value, "evidenceCids": evidence,
        "eventTime": event_time, "knownAt": known_at, "purposes": sorted(set(purposes)),
        "epistemicRole": role, "frame": frame, "uncertainty": uncertainty or {"kind": "unknown"},
        "validUntil": valid_until, "source": source, "dataOrigin": data_origin}
    record = tile("indranet.state_assertion", payload, evidence, created_at=known_at)
    store.append(record)
    return record

def revision(store: Store, target: str, replacement: str | None, *, event_time: str,
             known_at: str, reason: str) -> dict:
    old = store.get(target)
    if old["kind"] != "indranet.state_assertion" or not reason:
        raise ContractError("Revision targets a state assertion and requires a reason")
    if replacement is not None:
        new = store.get(replacement)
        if new["kind"] != old["kind"] or any(new["payload"][k] != old["payload"][k] for k in ("subject", "predicate")):
            raise ContractError("Supersession cannot silently change subject or predicate")
        if timestamp(new["payload"]["knownAt"]) > timestamp(known_at):
            raise ContractError("Replacement was not yet known")
    timestamp(event_time); timestamp(known_at)
    record = tile("indranet.revision", {"targetCid": target, "replacementCid": replacement,
        "operation": "supersede" if replacement else "retract", "eventTime": event_time,
        "knownAt": known_at, "reason": reason, "authority": "fixture-author"},
        [target] + ([replacement] if replacement else []), created_at=known_at)
    store.append(record)
    return record

def association(store: Store, external_id: str, entity: str, evidence: list[str], *, known_at: str) -> dict:
    if not external_id or not entity:
        raise ContractError("Association preserves two distinct identities")
    result = tile("indranet.association", {"externalId": external_id, "entityRef": entity,
        "relationship": "assigned-to", "knownAt": known_at, "basis": "explicit fixture declaration"}, evidence,
        created_at=known_at)
    store.append(result)
    return result

def context(store: Store, *, purpose: str, refs: list[str], mode: str, expires: str,
            created_at: str, prior_context: str | None = None) -> dict:
    if not refs or timestamp(expires) <= timestamp(created_at):
        raise ContractError("Context requires selected artifacts and a future expiry")
    # The selected wrapper may be less restrictive than the evidence it cites.
    for record in store.closure(refs + ([prior_context] if prior_context else [])):
        permitted = record["payload"].get("purposes")
        if permitted is not None and purpose not in permitted:
            raise ContractError("Context exceeds an artifact purpose grant")
    parents = sorted(set(refs + ([prior_context] if prior_context else [])))
    result = tile("indranet.context_binding", {"purpose": purpose, "selectedCids": sorted(set(refs)),
        "mode": mode, "expiresAt": expires, "knownAt": created_at, "priorContextCid": prior_context},
        parents, created_at=created_at)
    store.append(result)
    return result
