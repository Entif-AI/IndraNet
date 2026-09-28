"""Synthetic, deterministic 90-second reference timelines. No physical data."""
from __future__ import annotations
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .native import Ledger, native_digest
from .standards import to_ngsi, from_ngsi, compose, recover, mapping_table
from .native_bridge import project
from .store import Store

BASE = datetime(2026,9,28,12,0,0,tzinfo=timezone.utc)
def time_at(seconds: int) -> str:
    return (BASE + timedelta(seconds=seconds)).isoformat().replace('+00:00','Z')

def sample(index: int = 0, *, scenario: str = 'performance', role: str = 'reported-measurement') -> dict:
    return {'schemaVersion':'0.5.0', 'recordId':f'urn:fixture:{scenario}:{index}',
        'entity':f'urn:fixture:{scenario}:asset-7', 'predicate':'position', 'role':role,
        'eventTime':{'start':time_at(index),'end':None,'basis':'UTC'}, 'knownAt':time_at(index+1),
        'spatial':{'frame':f'urn:frame:{scenario}:stage', 'units':['m','m','m'],
            'position':[str(index),'2','0'], 'orientation':{'x':'0','y':'0','z':'0','w':'1'},
            'transformRefs':['urn:fixture:calibration:v1']},
        'quality':{'kind':'unknown'}, 'sources':['urn:fixture:provider-A'],
        'derivation':{'parents':[], 'method':'synthetic-fixture', 'branch':'historical', 'counterfactual':False},
        'rights':{'purposes':['operations','review','xr'], 'expiresAt':time_at(300),
            'prohibitedInferences':['biometric-identification','actuation-authorization']},
        'lifecycle':{'operation':'assert','target':None,'validUntil':time_at(index+5)},
        'origin':'synthetic-fixture-not-sensor-data'}

def timeline(name: str) -> list[dict]:
    rows = []
    for i in range(90):
        # The missing report is deliberately absent, not filled with an invented measurement.
        if name == 'performance' and 40 <= i < 46:
            continue
        r=sample(i, scenario=name)
        if name == 'warehouse':
            if i >= 45:
                r['sources']=['urn:fixture:provider-B']
                r['spatial']['transformRefs']=['urn:fixture:calibration:v2']
            if 20 <= i <= 25:
                r['quality']={'kind':'bound','value':'2.5','unit':'m','interpretation':'declared-bound-not-calibrated'}
            if i % 15 == 0:
                r['rights']['purposes']=['operations','review']
        if name == 'executable-world':
            r['role']='simulated' if i >= 30 else 'reported-measurement'
            if i >= 60:
                r['derivation']['branch']='counterfactual:B'
                r['derivation']['counterfactual']=True
            elif i >= 30:
                r['derivation']['branch']='predicted:A'
        if i >= 1 and name != 'executable-world':
            # Consecutive independent sensor reports are not causal derivations.
            r['derivation']['method']='fixture-position-report'
        rows.append(r)
    # Two providers disagree about the same event; do not pick a winner.
    conflict=copy.deepcopy(rows[20]); conflict['recordId']+=':alternate'; conflict['sources']=['urn:fixture:provider-alternate']
    conflict['spatial']['position'][0]='-3'; rows.append(conflict)
    # A correction retires one assertion without mutating its bytes.
    correction=copy.deepcopy(rows[10]); correction['recordId']+=':revision'; correction['knownAt']=time_at(13)
    correction['spatial']['position'][1]='3'; correction['derivation']['parents']=[rows[10]['recordId']]
    correction['lifecycle']['operation']='supersede'; correction['lifecycle']['target']=rows[10]['recordId']
    rows.append(correction)
    return rows

def run(out: Path) -> dict:
    out.mkdir(parents=True,exist_ok=True); records=[]; summaries=[]
    for name in ('performance','warehouse','executable-world'):
        rows=timeline(name); ledger=Ledger()
        for row in rows:
            digest=ledger.admit(row)
            if ledger.admit(row)!=digest:
                raise AssertionError('Idempotent admission failed')
            if from_ngsi(to_ngsi(row)) != row or recover(compose(row)) != row:
                raise AssertionError('Declared profile failed semantic round-trip')
        views={purpose:ledger.view(purpose=purpose,event_at=time_at(22),known_at=time_at(95))
               for purpose in ('operations','review','xr')}
        with Store() as store:
            bridge=project(store,rows[0]); bridge['closure']=store.closure([bridge['stateAssertionCid']])
        result={'scenario':name,'durationSeconds':90,'origin':'synthetic-fixture', 'records':rows,
                'views':views,'sharedExample':compose(rows[0]), 'rosettaProjection':bridge}
        (out/(name+'.json')).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        summaries.append({'scenario':name,'records':len(rows),'ngsiProfileRoundTrips':len(rows),
            'compositionProfileRoundTrips':len(rows),'consumerPurposes':list(views),
            'dataOrigin':'synthetic-fixture','fullStandardsExperimentExecuted':False})
        records.extend(rows)
    report={'status':'PASS','version':'0.5.0','scenarios':summaries,'recordCount':len(records),
        'profileRoundTrips':2*len(records), 'digestSetSize':len({native_digest(r) for r in records}),
        'comparisonConclusion':'Both declared profiles preserve the selected native fields. No necessity or performance winner follows.',
        'executed':'Local Python profile codecs, lifecycle, purpose views and optional Rosetta projection.',
        'notExecuted':['NGSI-LD broker','JSON-LD expansion','SensorThings server','omlox Hub or official omlox schema',
            'vendor hardware','neural decoder','human perceptual study','full registered standards-composition experiment'],
        'officialConformance':False,'physicalActuation':False}
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'field-crosswalk.json').write_text(json.dumps(mapping_table(),indent=2)+'\n')
    return report

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    print(json.dumps(run(parser.parse_args().out),indent=2))
