"""Explicit bitemporal, purpose-scoped views. No inferred trust ranking."""
from __future__ import annotations
from collections import defaultdict
from .canon import ContractError, canonical, timestamp
from .store import Store

def select(store: Store, *, purpose: str, event_at: str, known_at: str,
           max_age_seconds: int, subject: str | None = None) -> dict:
    if not purpose or type(max_age_seconds) is not int or max_age_seconds < 0:
        raise ContractError("View requires a purpose and nonnegative integer freshness budget")
    event = timestamp(event_at); knowledge = timestamp(known_at)
    retired = set()
    for row in store.all("indranet.revision"):
        p = row["payload"]
        if timestamp(p["eventTime"]) <= event and timestamp(p["knownAt"]) <= knowledge:
            retired.add(p["targetCid"])
    groups: dict[tuple, list] = defaultdict(list)
    omitted = 0
    for row in store.all("indranet.state_assertion"):
        p = row["payload"]
        if subject is not None and p["subject"] != subject:
            continue
        if timestamp(p["knownAt"]) > knowledge or timestamp(p["eventTime"]) > event or row["cid"] in retired:
            continue
        if p["validUntil"] is not None and event >= timestamp(p["validUntil"]):
            continue
        grants = [r["payload"].get("purposes") for r in store.closure([row["cid"]])]
        if purpose not in p["purposes"] or any(g is not None and purpose not in g for g in grants):
            omitted += 1
            continue
        age = int((event - timestamp(p["eventTime"])).total_seconds())
        groups[(p["subject"], p["predicate"])].append({"cid": row["cid"], "value": p["value"],
            "frame": p["frame"], "epistemicRole": p["epistemicRole"], "uncertainty": p["uncertainty"],
            "eventTime": p["eventTime"], "source": p["source"], "ageSeconds": age,
            "stale": age > max_age_seconds, "dataOrigin": p["dataOrigin"]})
    result = []
    for (entity, predicate), candidates in sorted(groups.items()):
        # Frame differences are unresolved correspondence, not numeric disagreement.
        frames = {candidate["frame"] for candidate in candidates}
        values = {canonical(candidate["value"]) for candidate in candidates}
        status = "frame-unresolved" if len(frames) > 1 else ("contested" if len(values) > 1 else "available")
        if all(candidate["stale"] for candidate in candidates):
            status = "stale"
        result.append({"subject": entity, "predicate": predicate, "status": status,
            "candidates": sorted(candidates, key=lambda r: r["cid"])})
    return {"purpose": purpose, "eventAt": event_at, "knownAt": known_at,
            "groups": result, "omittedCount": omitted, "actuationAuthority": False}
