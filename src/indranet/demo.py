"""Six deterministic, synthetic local examples. No native endpoint is contacted."""
from __future__ import annotations
import argparse
import json
from decimal import Decimal
from pathlib import Path
from .canon import tile
from .store import Store
from .model import ingress, assertion, context, revision, association
from .adapters import ingest_pose
from .views import select
from .process import preview, check_preview
from .frames import Transform, FrameTree
from .reality import Dependencies, reconstruction_plan, aggregate_zones
from .rosetta import interpretation_chain, elpq, attest_fixture, verify_attestation

T0 = "2026-09-15T12:00:00Z"
T1 = "2026-09-15T12:00:01Z"
T2 = "2026-09-15T12:00:02Z"
T3 = "2026-09-15T12:00:03Z"
T4 = "2026-09-15T12:00:04Z"
T8 = "2026-09-15T12:00:08Z"
T9 = "2026-09-15T12:00:09Z"
T10 = "2026-09-15T12:00:10Z"
END = "2026-09-15T12:01:00Z"
ENTITY = "rid:indranet:fixture-performer-01"

def _finish(store: Store, name: str, result: dict) -> dict:
    records = store.all()
    return {"scenario": name, "dataOrigin": "synthetic-fixture", "nativeRuntimeExecuted": False,
            "result": result, "tiles": records, "tileCount": len(records)}

def performance() -> dict:
    with Store() as store:
        obs, form = ingress(store, '{"gesture":"raise-arm","position":[1,2,3]}', source="fixture:performer",
            event_time=T0, known_at=T1, purposes=["performance", "xr"])
        gesture = assertion(store, subject=ENTITY, predicate="gesture", value="raise-arm", evidence=[form["cid"]],
            event_time=T0, known_at=T1, purposes=["performance", "xr"], role="inferred")
        ctx1 = context(store, purpose="performance", refs=[gesture["cid"]], mode="light-sculpture", expires=END, created_at=T1)
        out1 = preview(store, ctx1["cid"], gesture["cid"], at=T2)
        ctx2 = context(store, purpose="performance", refs=[gesture["cid"]], mode="sound-sculpture", expires=END,
            created_at=T3, prior_context=ctx1["cid"])
        out2 = preview(store, ctx2["cid"], gesture["cid"], at=T4)
        chain = interpretation_chain(store, obs["cid"], "position", entity=ENTITY, at=T2)
        matrix = elpq(store, out2["cid"], at=T4)
        receipt = attest_fixture(store, out2["cid"], at=T4)
        verify_attestation(receipt)
        return _finish(store, "performance", {"first": out1["payload"], "second": out2["payload"],
            "oldPreviewUnderNewContext": check_preview(store, out1["cid"], ctx2["cid"], at=T4),
            "interpretationChain": chain, "elpqMatrixCid": matrix["cid"], "signedFixture": receipt})

def xr() -> dict:
    with Store() as store:
        native = {"position": {"lat": 40, "lon": -74, "h": 10}, "quaternion": {"x": 0, "y": 0, "z": 0, "w": 1},
                  "profileEventTime": T0}
        mapped = ingest_pose(store, native, standard="geopose", source="fixture:shared-anchor", subject=ENTITY,
            frame="GeoPose:WGS84-ENU", known_at=T1, purposes=["xr", "maintenance"])
        assoc = association(store, "urn:fixture:headset:anchor-7", ENTITY, [mapped["formCid"]], known_at=T1)
        assertion(store, subject=ENTITY, predicate="maintenance-note", value="Inspect loose attachment before next use",
            evidence=[assoc["cid"]], event_time=T0, known_at=T1, purposes=["maintenance"], role="human-report")
        return _finish(store, "xr", {"mapping": mapped,
            "attendee": select(store, purpose="xr", event_at=T4, known_at=T4, max_age_seconds=10),
            "technician": select(store, purpose="maintenance", event_at=T4, known_at=T4, max_age_seconds=10)})

def warehouse() -> dict:
    with Store() as store:
        a = ingest_pose(store, {"position": {"type": "Point", "coordinates": [2,3,0]}, "crs": "warehouse-A",
            "timestamp_generated": T0, "accuracy": 0.2}, standard="locating-reference", source="fixture:location-A",
            subject="rid:indranet:robot-7", frame="warehouse-A", known_at=T1, purposes=["operations", "robot-advisory"])
        b = ingest_pose(store, {"pose": {"position": {"x": 5, "y": 3, "z": 0}},
            "header": {"frame_id": "warehouse-A"}, "profileEventTime": T2}, standard="ros-pose", source="fixture:robot-localization",
            subject="rid:indranet:robot-7", frame="warehouse-A", known_at=T3, purposes=["operations", "robot-advisory"])
        obs, form = ingress(store, '{"battery":40}', source="fixture:robot-status", event_time="2026-09-15T11:59:00Z",
            known_at=T1, purposes=["operations"])
        assertion(store, subject="rid:indranet:robot-7", predicate="battery-percent", value=40, evidence=[form["cid"]],
            event_time="2026-09-15T11:59:00Z", known_at=T1, purposes=["operations"])
        initial = select(store, purpose="operations", event_at=T4, known_at=T4, max_age_seconds=10)
        corrected = assertion(store, subject="rid:indranet:robot-7", predicate="position",
            value={"x":"5", "y":"3", "z":"0", "frame":"warehouse-A"}, evidence=[a["formCid"]],
            event_time=T8, known_at=T10, purposes=["operations", "robot-advisory"], frame="warehouse-A",
            role="inferred", source="fixture:explicit-correction")
        revision(store, a["assertionCid"], corrected["cid"], event_time=T8, known_at=T10, reason="Recorded correction, not automatic sensor fusion")
        return _finish(store, "warehouse", {"nativeMappings": [a,b], "initial": initial,
            "beforeCorrectionKnown": select(store,purpose="operations",event_at=T9,known_at=T9,max_age_seconds=10),
            "afterCorrectionKnown": select(store,purpose="operations",event_at=T10,known_at=T10,max_age_seconds=10)})

def public_space() -> dict:
    with Store() as store:
        counts = aggregate_zones(["entry"]*6 + ["exit"]*4 + ["quiet"])
        obs, form = ingress(store, json.dumps(counts), source="fixture:zone-aggregate", event_time=T0, known_at=T1,
            purposes=["situational-awareness"])
        record = assertion(store, subject="rid:indranet:venue-zone-summary", predicate="occupancy", value=counts,
            evidence=[form["cid"]], event_time=T0, known_at=T1, purposes=["situational-awareness"])
        review = tile("indranet.review_request", {"evidenceCids":[record["cid"]], "question":"Does an operator need to inspect the entrance?",
            "disposition":"human-review-requested", "identityInference":False, "automaticEnforcement":False,
            "knownAt":T2},[record["cid"]],created_at=T2)
        store.append(review)
        return _finish(store, "public-space", {"aggregate":counts, "review":review["payload"],
            "publicView":select(store,purpose="public-display",event_at=T4,known_at=T4,max_age_seconds=10),
            "operatorView":select(store,purpose="situational-awareness",event_at=T4,known_at=T4,max_age_seconds=10)})

def executable_worlds() -> dict:
    with Store() as store:
        obs, form = ingress(store, '{"sampleTimes":[0,1,2],"x":[0,4,7]}', source="fixture:recorded-motion",
            event_time=T0,known_at=T1,purposes=["physical-reasoning"])
        concept = tile("rosetta.concept", {"conceptId":"concept.moving-body","rid":"rid:indranet:body-1",
            "label":"Moving body in the synthetic scene","namespace":"indranet"}, [form["cid"]],created_at=T1)
        store.append(concept)
        frames=[]; simulations=[]
        for name, acceleration in (("low-drag","0.5"),("high-drag","1.0")):
            frame=tile("rosetta.frame", {"frameId":"frame."+name,"frameType":"indranet.ExecutableWorldHypothesis",
                "roles":[{"roleName":"subject","required":True,"filledBy":[concept["cid"]]}],
                "conceptCids":[concept["cid"]],"description":"A candidate constant-deceleration explanation: "+name},
                [concept["cid"],form["cid"]],created_at=T1)
            store.append(frame); frames.append(frame)
            model=tile("indranet.executable_model", {"hypothesisFrameCid":frame["cid"],"model":"constant-deceleration-1d",
                "parameters":{"initialVelocity":"4.5","deceleration":acceleration},"units":{"position":"m","time":"s"},
                "assumptions":["one-dimensional motion","nonnegative velocity within this two-second example"],
                "knownAt":T1},[frame["cid"]],created_at=T1)
            store.append(model)
            values=[format(Decimal("4.5")*Decimal(t)-Decimal(acceleration)*Decimal(t)**2/2,"f") for t in range(3)]
            sim=tile("indranet.simulation", {"modelCid":model["cid"],"hypothesisFrameCid":frame["cid"],
                "sampleTimes":[0,1,2],"positions":values,"epistemicRole":"simulated","counterfactual":False,
                "dataOrigin":"synthetic-fixture","knownAt":T2},[model["cid"]],created_at=T2)
            store.append(sim); simulations.append(sim)
        conjecture=tile("rosetta.conjecture", {"conjectureId":"conjecture.motion", "sourceCid":concept["cid"],
            "layer":"L3_concept_frame","options":[{"targetCid":f["cid"],"weight":0.5,
                "evidence":"Equal illustrative priors; not model-estimated probabilities"} for f in frames],
            "method":"declared-equal-fixture-prior","nonReplayable":False},
            [concept["cid"],*[f["cid"] for f in frames]],created_at=T2)
        store.append(conjecture)
        evaluation=tile("rosetta.evaluation", {"evaluationId":"eval.motion-unresolved","verdict":"unknown",
            "summary":"Both analytic candidates executed. This fixture does not select a true causal mechanism."},
            [conjecture["cid"],obs["cid"],*[s["cid"] for s in simulations]],created_at=T3)
        store.append(evaluation)
        return _finish(store,"executable-worlds",{"conjectureCid":conjecture["cid"],
            "simulations":[x["payload"] for x in simulations],"evaluation":evaluation["payload"]})

def generative_reality() -> dict:
    with Store() as store:
        asset=tile("indranet.asset",{"assetId":"venue-box-geometry","mediaType":"application/json",
            "geometry":{"primitive":"box","dimensions":["10","8","4"],"unit":"m"},
            "status":"synthetic-example"},created_at=T0)
        witness=tile("indranet.witness",{"witnessId":"unexpected-red-prop","mediaType":"text/plain",
            "content":"A red prop appears near the stage. This textual fixture is not a photorealistic witness.",
            "eventTime":T2,"knownAt":T3,"dataOrigin":"synthetic-fixture","purposes":["remote-presence"]},created_at=T3)
        store.append_many([asset,witness])
        package=tile("indranet.world_package",{"requiredAssets":[asset["cid"]],"decoderProfile":"reference-wireframe-v1",
            "purposes":["remote-presence"],"frame":"venue-A","knownAt":T0},[asset["cid"]],created_at=T0)
        store.append(package)
        state=tile("indranet.reconstruction_state",{"baselineCid":package["cid"],"eventTime":T2,"validUntil":END,
            "requiredWitnesses":[witness["cid"]],"purposes":["remote-presence"],"changedObjects":["prop-7"],
            "epistemicRole":"inferred","knownAt":T3},[package["cid"]],created_at=T3)
        store.append(state)
        p={"cid":package["cid"],**package["payload"]}
        receiver={"mode":"evidence","availableAssets":[asset["cid"]],"availableWitnesses":[],
            "decoderProfile":"reference-wireframe-v1","purpose":"remote-presence"}
        missing=reconstruction_plan(p,state["payload"],receiver,at=T4)
        perceptual=reconstruction_plan(p,state["payload"],{**receiver,"mode":"perceptual"},at=T4)
        repaired=reconstruction_plan(p,state["payload"],{**receiver,"availableWitnesses":[witness["cid"]]},at=T4)
        graph=Dependencies({"performer":[],"attachment-rule":[],"prop":["performer","attachment-rule"],
                            "render":["prop"],"independent-camera":[]})
        transform=Transform("prop","stage",((1.,0.,0.,2.),(0.,1.,0.,3.),(0.,0.,1.,0.),(0.,0.,0.,1.)),T0,END,asset["cid"])
        point=FrameTree([transform]).to_ancestor((1.,0.,0.),"prop","stage",T4)
        return _finish(store,"generative-reality",{"baselineCid":package["cid"],"evidenceMode":missing,
            "perceptualMode":perceptual,"witnessAvailable":repaired,
            "attachmentChanged":graph.invalidate(["attachment-rule"]),"transformedPoint":point})

SCENARIOS = {"performance":performance,"xr":xr,"warehouse":warehouse,"public-space":public_space,
             "executable-worlds":executable_worlds,"generative-reality":generative_reality}

def run_all(out: Path) -> dict:
    out.mkdir(parents=True,exist_ok=True)
    index=[]
    for name,fn in SCENARIOS.items():
        result=fn()
        (out/(name+".json")).write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
        index.append({"scenario":name,"file":name+".json","tiles":result["tileCount"],"dataOrigin":"synthetic-fixture"})
    summary={"version":"0.5.0","scenarios":index,"totalScenarioTiles":sum(r["tiles"] for r in index),
             "nativeRuntimeExecuted":False,"physicalActuation":False,"neuralDecoderExecuted":False}
    (out/"index.json").write_text(json.dumps(summary,indent=2)+"\n")
    return summary

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=Path("outputs"))
    args=parser.parse_args()
    print(json.dumps(run_all(args.out),indent=2))
