"""Restricted JSON parity with the inspected Rosetta constructor body.

This subset excludes floats except exact quarter fractions, and integer-looking/non-ASCII keys.
Native input bytes belong in Observation.signal, not in this canonicalizer.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Iterable

CORE = frozenset({"rosetta.run", "rosetta.action", "rosetta.toolcall", "rosetta.observation",
    "rosetta.evaluation", "rosetta.receipt", "rosetta.concept", "rosetta.frame",
    "rosetta.conjecture", "rosetta.matrix", "rosetta.policy", "rosetta.lattice_edge",
    "rosetta.form.token", "rosetta.lexeme"})
CID = re.compile(r"^cidv1-sha256-[0-9a-f]{64}$")
KEY = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$.:/-]*$")
MAX_INT = 2**53 - 1

class ContractError(ValueError):
    """A local candidate contract was violated."""

def check_json(value: Any) -> None:
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if abs(value) > MAX_INT:
            raise ContractError("Integer exceeds the cross-language safe range")
        return
    if type(value) is float and value in {0.25, 0.5, 0.75}:
        return
    if type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ContractError("Unpaired Unicode surrogate") from exc
        return
    if type(value) is list:
        for item in value:
            check_json(item)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str or not KEY.fullmatch(key):
                raise ContractError("Object keys must use the restricted ASCII identifier grammar")
            check_json(item)
        return
    raise ContractError("Only restricted JSON values are accepted; encode decimal quantities explicitly")

def canonical(value: Any) -> str:
    check_json(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

def content_id(value: Any) -> str:
    return "cidv1-sha256-" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ContractError("Timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("Invalid ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise ContractError("Timestamp requires an explicit timezone")
    return parsed.astimezone(timezone.utc)

def tile(kind: str, payload: dict, parents: Iterable[str] = (), *,
         created_at: str = "2026-09-15T00:00:00Z", pack: str | None = None) -> dict:
    if not (kind in CORE or kind.startswith("indranet.")):
        raise ContractError("Unknown kind: no new Core term may be minted here")
    timestamp(created_at)
    refs = sorted(parents)
    if len(set(refs)) != len(refs) or any(not CID.fullmatch(x) for x in refs):
        raise ContractError("Parents require unique content identifiers")
    body = {"kind": kind, "pack": pack or ("rosetta.core" if kind in CORE else "indranet.context"),
            "version": "0.1.0" if kind in CORE else "0.5.0", "parents": refs, "payload": payload}
    encoded = canonical(body)
    return {**body, "canonical": encoded, "cid": content_id(body), "createdAt": created_at}

def verify(record: dict) -> None:
    expected_keys = {"kind", "pack", "version", "parents", "payload", "cid", "createdAt", "canonical"}
    if set(record) != expected_keys:
        raise ContractError("Envelope fields differ from the inspected subset")
    timestamp(record["createdAt"])
    refs = record["parents"]
    if not isinstance(refs, list) or refs != sorted(set(refs)) or any(not CID.fullmatch(x) for x in refs):
        raise ContractError("Noncanonical parent set")
    body = {key: record[key] for key in ("kind", "pack", "version", "parents", "payload")}
    if canonical(body) != record["canonical"] or content_id(body) != record["cid"]:
        raise ContractError("Canonical body or content digest mismatch")
    if not (record["kind"] in CORE or record["kind"].startswith("indranet.")):
        raise ContractError("Unsupported Core/domain kind")
