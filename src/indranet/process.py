"""Context-bound effect previews. This module has no network or device API."""
from __future__ import annotations
import struct
from .canon import ContractError, tile, timestamp
from .store import Store

# Declared example mappings, not a learned or production show-control policy.
SCENES = {
    "light-sculpture": {"raise-arm": ("/indranet/demo/light/level", 80)},
    "sound-sculpture": {"raise-arm": ("/indranet/demo/sound/send", 35)},
}

def _osc_string(value: str) -> bytes:
    if "\0" in value:
        raise ContractError("OSC strings cannot contain embedded nulls")
    raw = value.encode("utf-8") + b"\0"
    return raw + b"\0" * ((-len(raw)) % 4)

def osc_packet(address: str, integer: int) -> bytes:
    if not address.startswith("/") or type(integer) is not int or not -(2**31) <= integer < 2**31:
        raise ContractError("OSC preview requires an address and signed 32-bit integer")
    return _osc_string(address) + _osc_string(",i") + struct.pack(">i", integer)

def preview(store: Store, context_cid: str, gesture_cid: str, *, at: str) -> dict:
    ctx = store.get(context_cid); gesture = store.get(gesture_cid)
    if ctx["kind"] != "indranet.context_binding" or gesture["kind"] != "indranet.state_assertion":
        raise ContractError("Preview requires a context and gesture assertion")
    c, g = ctx["payload"], gesture["payload"]
    if timestamp(at) >= timestamp(c["expiresAt"]):
        raise ContractError("Context expired before preview")
    if c["purpose"] != "performance" or "performance" not in g["purposes"]:
        raise ContractError("Gesture/context is not permitted for performance")
    if gesture_cid not in c["selectedCids"] or g["predicate"] != "gesture":
        raise ContractError("Gesture must be selected in the bound context")
    if timestamp(g["eventTime"]) > timestamp(at) or timestamp(g["knownAt"]) > timestamp(at):
        raise ContractError("Gesture was not available at the preview time")
    try:
        address, value = SCENES[c["mode"]][g["value"]]
    except (KeyError, TypeError) as exc:
        raise ContractError("No declared example mapping for this mode and gesture") from exc
    run = tile("rosetta.run", {"runId": "demo." + context_cid[-12:], "summary": "Context-bound effect preview",
                              "tags": ["synthetic-fixture", "no-device-execution"]}, created_at=at)
    action = tile("rosetta.action", {"actionId": "action." + context_cid[-12:], "runCid": run["cid"],
        "intent": "Compile a preview packet from an explicitly selected gesture and context"},
        [run["cid"], context_cid, gesture_cid], created_at=at)
    call = tile("rosetta.toolcall", {"tool": "local.osc_packet_preview", "toolCallId": "preview." + action["cid"][-12:],
        "args": {"address": address, "value": value, "contextCid": context_cid}}, [action["cid"]], created_at=at)
    output = tile("indranet.effect_preview", {"contextCid": context_cid, "gestureCid": gesture_cid,
        "address": address, "value": value, "oscHex": osc_packet(address, value).hex(), "mode": c["mode"],
        "eventTime": at, "sent": False, "actuationAuthority": False}, [call["cid"], context_cid, gesture_cid], created_at=at)
    evaluation = tile("rosetta.evaluation", {"evaluationId": "eval." + output["cid"][-12:], "verdict": "pass",
        "summary": "Local packet compilation completed; no endpoint was contacted"}, [output["cid"], action["cid"]], created_at=at)
    store.append_many([run, action, call, output, evaluation])
    return output

def check_preview(store: Store, preview_cid: str, current_context_cid: str, *, at: str) -> dict:
    record = store.get(preview_cid)
    ctx = store.get(current_context_cid)
    reasons = []
    if record["kind"] != "indranet.effect_preview" or ctx["kind"] != "indranet.context_binding":
        raise ContractError("Unexpected preview/context kinds")
    if record["payload"]["contextCid"] != current_context_cid:
        reasons.append("context-changed")
    if timestamp(at) >= timestamp(ctx["payload"]["expiresAt"]):
        reasons.append("context-expired")
    return {"status": "refused" if reasons else "preview-current", "reasons": reasons,
            "actuationAuthority": False, "sent": False}
