"""Optional Rosetta projection. Standalone producers do not import this module."""
from __future__ import annotations
import json
from .native import validate, native_digest
from .model import ingress, assertion
from .canon import tile
from .store import Store

def project(store: Store, native_record: dict) -> dict:
    r = validate(native_record)
    raw = json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    obs, form = ingress(store, raw, source=r['sources'][0], event_time=r['knownAt'],
        known_at=r['knownAt'], purposes=r['rights']['purposes'], data_origin=r['origin'])
    native = tile('indranet.native_record', r, [form['cid']], created_at=r['knownAt'])
    store.append(native)
    state = assertion(store, subject=r['entity'], predicate=r['predicate'], value=r['spatial'],
        evidence=[native['cid']], event_time=r['eventTime']['start'], known_at=r['knownAt'],
        purposes=r['rights']['purposes'], role=r['role'], frame=r['spatial']['frame'],
        uncertainty=r['quality'], valid_until=r['lifecycle']['validUntil'],
        source=r['sources'][0], data_origin=r['origin'])
    return {'nativeDigest':native_digest(r), 'observationCid':obs['cid'], 'nativeRecordCid':native['cid'],
            'stateAssertionCid':state['cid'], 'externalRefsPreserved':r['sources'],
            'integrationStatus':'local projection of an independently authored native profile',
            'officialConformance':False, 'nativeRuntimeExecuted':False}
