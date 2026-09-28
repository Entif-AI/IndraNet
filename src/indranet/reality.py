"""Prior-state-witness planning, without a neural decoder or bitrate claim."""
from __future__ import annotations
from collections import defaultdict, deque
from .canon import ContractError, CID, timestamp

class Dependencies:
    def __init__(self, graph: dict[str, list[str]]) -> None:
        self.graph = graph
        self.children: dict[str, set[str]] = defaultdict(set)
        for node, parents in graph.items():
            if len(set(parents)) != len(parents):
                raise ContractError("Repeated derivation dependency")
            for parent in parents:
                if parent not in graph:
                    raise ContractError("Undeclared derivation dependency")
                self.children[parent].add(node)
        visiting, done = set(), set()
        def walk(node: str) -> None:
            if node in visiting:
                raise ContractError("Derivation graph contains a cycle")
            if node in done:
                return
            visiting.add(node)
            for parent in graph[node]:
                walk(parent)
            visiting.remove(node); done.add(node)
        for node in graph:
            walk(node)

    def invalidate(self, changed: list[str]) -> list[str]:
        if any(node not in self.graph for node in changed):
            raise ContractError("Changed derivation node is unknown")
        affected = set(changed); queue = deque(changed)
        while queue:
            node = queue.popleft()
            for child in self.children[node]:
                if child not in affected:
                    affected.add(child); queue.append(child)
        return sorted(affected)

def reconstruction_plan(package: dict, state: dict, receiver: dict, *, at: str) -> dict:
    mode = receiver.get("mode")
    if mode not in {"evidence", "perceptual", "creative"}:
        raise ContractError("Unknown reconstruction mode")
    if not CID.fullmatch(package.get("cid", "")):
        raise ContractError("World package requires a content identifier")
    for name in ("eventTime", "validUntil"):
        timestamp(state[name])
    missing_assets = sorted(set(package["requiredAssets"]) - set(receiver["availableAssets"]))
    missing_witnesses = sorted(set(state["requiredWitnesses"]) - set(receiver["availableWitnesses"]))
    reasons = []
    if state["baselineCid"] != package["cid"]:
        reasons.append("baseline-mismatch")
    if receiver["decoderProfile"] != package["decoderProfile"]:
        reasons.append("decoder-profile-mismatch")
    if missing_assets:
        reasons.append("missing-assets")
    if not (timestamp(state["eventTime"]) <= timestamp(at) < timestamp(state["validUntil"])):
        reasons.append("state-outside-validity")
    if receiver["purpose"] not in package["purposes"] or receiver["purpose"] not in state["purposes"]:
        reasons.append("purpose-denied")
    if reasons:
        status = "blocked"
    elif missing_witnesses and mode == "evidence":
        status = "degraded-wireframe"
    elif missing_witnesses:
        status = "synthesis-labeled"
    else:
        status = "ready-for-declared-decoder"
    return {"status": status, "mode": mode, "missingAssets": missing_assets,
        "missingWitnesses": missing_witnesses, "reasons": reasons,
        "appearanceEvidenceComplete": not missing_witnesses and not reasons,
        "generatedAppearanceIsObservation": False, "decoderExecuted": False}

def aggregate_zones(zone_samples: list[str], *, minimum_count: int = 3) -> dict:
    if type(minimum_count) is not int or minimum_count < 1:
        raise ContractError("Aggregation threshold must be a positive integer")
    counts: dict[str, int] = defaultdict(int)
    for zone in zone_samples:
        if not isinstance(zone, str) or not zone:
            raise ContractError("Zone samples contain only nonempty zone identifiers")
        counts[zone] += 1
    return {"zones": [{"zone": zone, "count": count} for zone, count in sorted(counts.items()) if count >= minimum_count],
        "suppressedZones": sum(count < minimum_count for count in counts.values()),
        "privacyGuarantee": "none; illustrative suppression, not differential privacy or anonymity proof"}
