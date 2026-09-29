"""Explicit native-field mapping subsets, not complete standards implementations."""
from __future__ import annotations
import json
from .canon import ContractError
from .model import assertion, decimal_text, ingress
from .store import Store

def _xyz(values: list, frame: str) -> dict:
    if len(values) not in (2, 3):
        raise ContractError("Position requires two or three components")
    # A missing altitude stays absent, never silently promoted to zero.
    result = {"x": decimal_text(values[0]), "y": decimal_text(values[1]), "frame": frame}
    if len(values) == 3:
        result["z"] = decimal_text(values[2])
    return result

def ingest_pose(store: Store, native: dict, *, standard: str, source: str,
                subject: str, frame: str, known_at: str, purposes: list[str]) -> dict:
    loss = []
    uncertainty = {"kind": "unknown"}
    if standard == "sensorthings":
        event = native["phenomenonTime"]
        if "/" in event:
            raise ContractError("Interval phenomenonTime needs an interval-specific profile")
        position = _xyz(native["result"], frame)
        loss = ["Datastream, FeatureOfInterest and Sensor resources require separate dereferencing",
                "Result is interpreted as a position only under this declared location Datastream profile"]
        if "resultQuality" in native:
            uncertainty = {"kind": "native-quality-reference", "encoded": json.dumps(native["resultQuality"], sort_keys=True)}
    elif standard == "ngsi-ld":
        location = native["location"]
        if location.get("type") != "GeoProperty" or location["value"].get("type") != "Point":
            raise ContractError("This NGSI-LD subset requires a Point GeoProperty")
        if frame != "OGC:CRS84":
            raise ContractError("NGSI-LD GeoJSON point profile requires declared CRS84")
        event = location["observedAt"]
        position = _xyz(location["value"]["coordinates"], frame)
        loss = ["JSON-LD context expansion is not executed", "Entity relationship and temporal API behavior are not implemented"]
    elif standard == "geopose":
        p = native["position"]
        position = {"latitude": decimal_text(p["lat"]), "longitude": decimal_text(p["lon"]),
                    "height": decimal_text(p["h"]), "frame": frame, "orientation": native["quaternion"]}
        # Quaternion decimals become text in this candidate payload; the native bytes remain intact.
        position["orientation"] = {k: decimal_text(v) for k, v in native["quaternion"].items()}
        event = native["profileEventTime"]
        loss = ["profileEventTime is sidecar metadata, not a Basic GeoPose field", "Orientation/frame conversion is not inferred"]
    elif standard == "ros-pose":
        p = native["pose"]["position"]
        position = _xyz([p["x"], p["y"], p["z"]], frame)
        if native["header"]["frame_id"] != frame:
            raise ContractError("ROS frame identifier disagrees with adapter binding")
        event = native["profileEventTime"]
        loss = ["ROS clock-to-UTC binding is supplied by the caller", "DDS and tf2 runtime are not executed",
                "Native orientation is preserved in signal but omitted from this position-only projection"]
    elif standard == "locating-reference":
        if native.get("crs") != frame:
            raise ContractError("Locating report requires an explicit matching CRS")
        position = _xyz(native["position"]["coordinates"], frame)
        event = native["timestamp_generated"]
        if "accuracy" in native:
            uncertainty = {"kind": "vendor-estimate", "value": decimal_text(native["accuracy"]),
                           "unit": "m", "distribution": "not-specified"}
        loss = ["Independently authored locating subset, not official omlox certification",
                "Provider association and zone calibration require separate evidence"]
    else:
        raise ContractError("Unsupported native mapping")
    obs, form = ingress(store, json.dumps(native, ensure_ascii=False, separators=(",", ":")),
        source=source, event_time=event, known_at=known_at, purposes=purposes)
    state = assertion(store, subject=subject, predicate="position", value=position,
        evidence=[form["cid"]], event_time=event, known_at=known_at, purposes=purposes,
        frame=frame, uncertainty=uncertainty, source=source)
    return {"standard": standard, "observationCid": obs["cid"], "formCid": form["cid"],
            "assertionCid": state["cid"], "loss": loss, "nativeRuntimeExecuted": False}
