"""Offline profile composition using selected published standard fields.

The named source APIs, JSON-LD processor, omlox Hub and vendor runtimes are not
executed. Crosswalk profiles are explicit; this module makes no expressivity
winner or official conformance claim.
"""
from __future__ import annotations
import copy
import json
from .native import validate, ExchangeError

CONTEXT = {
    '@vocab': 'urn:indranet:candidate:0.5:',
    'Property': 'https://uri.etsi.org/ngsi-ld/Property',
    'Relationship': 'https://uri.etsi.org/ngsi-ld/Relationship',
    'GeoProperty': 'https://uri.etsi.org/ngsi-ld/GeoProperty',
}
PROFILE_FIELDS = ('role', 'knownAt', 'quality', 'sources', 'derivation', 'rights', 'lifecycle', 'origin')

def _property(value: object, observed: str | None = None) -> dict:
    result = {'type': 'Property', 'value': copy.deepcopy(value)}
    if observed is not None:
        result['observedAt'] = observed
    return result

def to_ngsi(record: dict) -> dict:
    r = validate(record); t = r['eventTime']; s = r['spatial']
    # Decimal strings live in a declared Property rather than becoming invalid
    # GeoJSON coordinates or undergoing a silent precision conversion.
    entity = {'id': r['entity'], 'type': 'PhysicalContextRecord', '@context': copy.deepcopy(CONTEXT),
        'recordId': _property(r['recordId']), 'schemaVersion': _property(r['schemaVersion']),
        'predicate': _property(r['predicate']), 'eventInterval': _property(t),
        'position': _property(s['position'], t['start']), 'coordinateFrame': _property(s['frame']),
        'coordinateUnits': _property(s['units']), 'orientation': _property(s['orientation']),
        'transformRefs': _property(s['transformRefs'])}
    for field in PROFILE_FIELDS:
        entity[field] = _property(r[field])
    return entity

def from_ngsi(entity: dict) -> dict:
    try:
        required = ['recordId','schemaVersion','predicate','eventInterval','position','coordinateFrame',
                    'coordinateUnits','orientation','transformRefs',*PROFILE_FIELDS]
        if entity['type'] != 'PhysicalContextRecord' or entity['@context'] != CONTEXT:
            raise ExchangeError('This decoder requires the declared candidate JSON-LD context')
        if any(entity[k].get('type') != 'Property' for k in required):
            raise ExchangeError('Expected normalized Property representation')
        r = {'schemaVersion': entity['schemaVersion']['value'], 'recordId': entity['recordId']['value'],
            'entity': entity['id'], 'predicate': entity['predicate']['value'], 'eventTime': entity['eventInterval']['value'],
            'spatial': {'frame':entity['coordinateFrame']['value'], 'units':entity['coordinateUnits']['value'],
                'position':entity['position']['value'], 'orientation':entity['orientation']['value'],
                'transformRefs':entity['transformRefs']['value']}}
        for field in PROFILE_FIELDS:
            r[field] = copy.deepcopy(entity[field]['value'])
        if entity['position'].get('observedAt') != r['eventTime']['start']:
            raise ExchangeError('NGSI observedAt and the interval start disagree')
        return validate(r)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ExchangeError('Incomplete normalized NGSI-LD profile') from exc

def compose(record: dict) -> dict:
    r = validate(record); t = r['eventTime']; s = r['spatial']
    phenomenon = t['start'] if t['end'] is None else t['start'] + '/' + t['end']
    # SensorThings permits a complex result governed by Datastream observationType.
    observation = {'@iot.id':r['recordId'], 'phenomenonTime':phenomenon, 'resultTime':r['knownAt'],
        'result':{'coordinates':copy.deepcopy(s['position']), 'coordinateFrame':s['frame']},
        'parameters':{'profile':'urn:indranet:candidate:position-result-v1'},
        'Datastream':{'@iot.id':r['entity'] + ':position-stream'}}
    if r['lifecycle']['validUntil']:
        observation['validTime'] = t['start'] + '/' + r['lifecycle']['validUntil']
    # resultQuality requires an ISO DQ_Element representation. Candidate bounds
    # remain explicit NGSI profile attributes; they are not relabeled ISO quality.
    geopose = None
    if s['frame'] == 'OGC:CRS84' and len(s['position']) == 3 and s['orientation'] is not None:
        lon,lat,h = s['position']
        geopose = {'position':{'lat':float(lat),'lon':float(lon),'h':float(h)},
                   'quaternion':{k:float(v) for k,v in s['orientation'].items()}}
    return {'profile':'indranet-mature-composition-reference/0.5.0', 'ngsiLd':to_ngsi(r),
        'sensorThings':observation, 'geoPose':geopose,
        'locatingReference':{'trackable':r['entity'],'zone':s['frame'],'locationProvider':r['sources'][0],
            'coordinates':copy.deepcopy(s['position']), 'generatedAt':t['start']},
        'losses':[
            {'surface':'NGSI-LD','status':'Composition','detail':'Explicit candidate attributes; no JSON-LD expansion or live temporal API.'},
            {'surface':'SensorThings','status':'Specialization','detail':'Declared complex-position Datastream; Sensor/ObservedProperty/FoI dereferencing is not executed.'},
            {'surface':'GeoPose','status':'LossyDeclared' if geopose else 'OutOfScope',
             'detail':'Optional binary64 preview only; exact decimals remain in NGSI profile. Local Cartesian frames need an explicit geodetic transform.'},
            {'surface':'omlox','status':'Unsupported','detail':'Official API schema/runtime not retrieved. LocatingReference is independently authored, not an omlox payload.'}],
        'nativeRuntimesExecuted':False, 'officialConformance':False}

def recover(bundle: dict) -> dict:
    if bundle.get('profile') != 'indranet-mature-composition-reference/0.5.0':
        raise ExchangeError('Unknown composition profile')
    r = from_ngsi(bundle['ngsiLd']); obs = bundle['sensorThings']; loc = bundle['locatingReference']
    expected = compose(r)
    for field in ('@iot.id','phenomenonTime','resultTime','result','Datastream','parameters','validTime'):
        if obs.get(field) != expected['sensorThings'].get(field):
            raise ExchangeError(f'Conflicting SensorThings field: {field}')
    if loc != expected['locatingReference']:
        raise ExchangeError('Locating reference disagrees with normalized state')
    if bundle.get('geoPose') != expected['geoPose']:
        raise ExchangeError('GeoPose projection disagrees with the shared record')
    return r

def mapping_table() -> list[dict]:
    return [{'nativeField':field, 'ngsiLd':'Property.value (declared profile)',
             'sensorThings':{'eventTime':'phenomenonTime','knownAt':'resultTime','spatial':'complex result under Datastream profile',
                             'lifecycle':'validTime when present'}.get(field,'profile-carried, not a native SensorThings field'),
             'classification':'Composition', 'silentLossAllowed':False}
            for field in ['recordId','entity','predicate','eventTime','knownAt','spatial',*PROFILE_FIELDS]]
