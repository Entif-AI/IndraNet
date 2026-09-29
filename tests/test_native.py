"""Fault-detecting tests for standalone exchange, not vendor certification."""
import copy
import json
import unittest
from indranet.native import Ledger, ExchangeError, strict_loads, validate, native_digest
from indranet.scenarios import sample, time_at, timeline
from indranet.standards import compose, recover, to_ngsi, from_ngsi
from indranet.native_bridge import project
from indranet.store import Store
from indranet.canon import ContractError, tile
from indranet.model import ingress, context, assertion
from indranet.views import select

class NativeTests(unittest.TestCase):
    def test_valid(self): self.assertEqual(validate(sample()),sample())
    def test_digest_distinct_namespace(self): self.assertTrue(native_digest(sample()).startswith('indranet-json-sha256:'))
    def test_digest_key_order(self): self.assertEqual(native_digest(sample()),native_digest(dict(reversed(list(sample().items())))))
    def test_digest_includes_knowledge_time(self):
        a=sample(); b=copy.deepcopy(a);b['knownAt']=time_at(2)
        self.assertNotEqual(native_digest(a),native_digest(b))
    def test_duplicate_key(self):
        with self.assertRaises(ExchangeError): strict_loads('{"x":1,"x":2}')
    def test_nested_duplicate_key(self):
        with self.assertRaises(ExchangeError): strict_loads('{"x":{"y":1,"y":2}}')
    def test_nan(self):
        with self.assertRaises(ExchangeError): strict_loads('{"x":NaN}')
    def test_overflow(self):
        with self.assertRaises(ExchangeError): strict_loads('{"x":1e999}')
    def test_invalid_utf8_surrogate(self):
        with self.assertRaises(ExchangeError): strict_loads('{"x":"\\ud800"}')
    def test_unknown_fields(self):
        a=sample();a['truth']=True
        with self.assertRaises(ExchangeError): validate(a)
    def test_naive_time(self):
        a=sample();a['knownAt']='2026-09-28T12:00:01'
        with self.assertRaises(ExchangeError): validate(a)
    def test_reversed_interval(self):
        a=sample(3);a['eventTime']['end']=time_at(1)
        with self.assertRaises(ExchangeError): validate(a)
    def test_interval_accepted(self):
        a=sample();a['eventTime']['end']=time_at(1);self.assertEqual(validate(a),a)
    def test_future_measurement(self):
        a=sample();a['eventTime']['end']=time_at(2)
        with self.assertRaises(ExchangeError): validate(a)
    def test_future_prediction(self):
        a=sample(role='predicted');a['eventTime']['start']=time_at(2);self.assertEqual(validate(a),a)
    def test_decimal_number_not_string(self):
        a=sample();a['spatial']['position'][0]=1.5
        with self.assertRaises(ExchangeError): validate(a)
    def test_negative_bound(self):
        a=sample();a['quality']={'kind':'bound','value':'-1','unit':'m','interpretation':'declared-bound-not-calibrated'}
        with self.assertRaises(ExchangeError): validate(a)
    def test_missing_z_is_not_zero(self):
        a=sample();a['spatial']['position']=a['spatial']['position'][:2];a['spatial']['units']=['m','m']
        self.assertEqual(len(validate(a)['spatial']['position']),2)
    def test_quaternion_zero(self):
        a=sample();a['spatial']['orientation']['w']='0'
        with self.assertRaises(ExchangeError): validate(a)
    def test_frame_missing(self):
        a=sample();a['spatial']['frame']=''
        with self.assertRaises(ExchangeError): validate(a)
    def test_unit_mismatch(self):
        a=sample();a['spatial']['units']=['m']
        with self.assertRaises(ExchangeError): validate(a)
    def test_geodetic_range(self):
        a=sample();a['spatial'].update(frame='OGC:CRS84',units=['deg','deg','m'],position=['181','0','0'])
        with self.assertRaises(ExchangeError): validate(a)
    def test_counterfactual_not_measured(self):
        a=sample();a['derivation']['counterfactual']=True
        with self.assertRaises(ExchangeError): validate(a)
    def test_expired_rights(self):
        a=sample();a['rights']['expiresAt']=time_at(0)
        with self.assertRaises(ExchangeError): validate(a)
    def test_idempotent(self):
        l=Ledger();a=sample();self.assertEqual(l.admit(a),l.admit(a))
    def test_collision(self):
        l=Ledger();a=sample();l.admit(a);a['spatial']['position'][0]='4'
        with self.assertRaises(ExchangeError): l.admit(a)
    def test_detached_get(self):
        l=Ledger();a=sample();l.admit(a);l.get(a['recordId'])['entity']='other'
        self.assertEqual(l.get(a['recordId'])['entity'],a['entity'])
    def child(self, parent):
        a=sample(1);a['derivation']['parents']=[parent['recordId']];return a
    def test_missing_parent(self):
        l=Ledger();a=sample();a['derivation']['parents']=['missing']
        with self.assertRaises(ExchangeError): l.admit(a)
    def test_transitive_purpose(self):
        l=Ledger();a=sample();a['rights']['purposes']=['review'];l.admit(a);b=self.child(a)
        with self.assertRaises(ExchangeError): l.admit(b)
    def test_expiry_cannot_expand(self):
        l=Ledger();a=sample();l.admit(a);b=self.child(a);b['rights']['expiresAt']=None
        with self.assertRaises(ExchangeError): l.admit(b)
    def test_prohibited_inferences_inherited(self):
        l=Ledger();a=sample();l.admit(a);b=self.child(a);b['rights']['prohibitedInferences']=[]
        with self.assertRaises(ExchangeError): l.admit(b)
    def test_simulation_laundering(self):
        l=Ledger();a=sample(role='simulated');l.admit(a);b=self.child(a)
        with self.assertRaises(ExchangeError): l.admit(b)
    def test_conflict_retained(self):
        l=Ledger();a=sample();l.admit(a);b=copy.deepcopy(a);b['recordId']+=':other';b['spatial']['position'][0]='8';l.admit(b)
        v=l.view(purpose='review',event_at=time_at(2),known_at=time_at(3))
        self.assertEqual(len(v['states']),2);self.assertFalse(v['physicalActuationAuthority'])
    def test_bitemporal_revision(self):
        l=Ledger();a=sample();l.admit(a);b=self.child(a);b['knownAt']=time_at(4);b['lifecycle'].update(operation='supersede',target=a['recordId']);l.admit(b)
        self.assertEqual(l.view(purpose='review',event_at=time_at(2),known_at=time_at(3))['states'][0]['recordId'],a['recordId'])
        self.assertEqual(l.view(purpose='review',event_at=time_at(2),known_at=time_at(4))['states'][0]['recordId'],b['recordId'])
    def test_three_purposes_and_three_timelines(self):
        for name in ('performance','warehouse','executable-world'):
            l=Ledger()
            for a in timeline(name):l.admit(a)
            for purpose in ('operations','review','xr'):
                self.assertIn('states',l.view(purpose=purpose,event_at=time_at(22),known_at=time_at(95)))

class CodecTests(unittest.TestCase):
    def test_ngsi_roundtrip(self):self.assertEqual(from_ngsi(to_ngsi(sample())),sample())
    def test_composition_roundtrip(self):self.assertEqual(recover(compose(sample())),sample())
    def test_ngsi_role_preserved(self):
        a=sample(role='simulated');self.assertEqual(from_ngsi(to_ngsi(a))['role'],'simulated')
    def test_intervals(self):
        a=sample();a['eventTime']['end']=time_at(1)
        self.assertEqual(recover(compose(a)),a)
    def test_ngsi_context_unknown(self):
        a=to_ngsi(sample());a['@context']='https://example.invalid/unknown'
        with self.assertRaises(ExchangeError):from_ngsi(a)
    def test_ngsi_observedat_conflict(self):
        a=to_ngsi(sample());a['position']['observedAt']=time_at(5)
        with self.assertRaises(ExchangeError):from_ngsi(a)
    def test_sensor_conflict(self):
        a=compose(sample());a['sensorThings']['result']['coordinates'][0]='200'
        with self.assertRaises(ExchangeError):recover(a)
    def test_locating_conflict(self):
        a=compose(sample());a['locatingReference']['zone']='other'
        with self.assertRaises(ExchangeError):recover(a)
    def test_local_pose_not_geopose(self):self.assertIsNone(compose(sample())['geoPose'])
    def test_geopose_separate_sidecar(self):
        a=sample();a['spatial'].update(frame='OGC:CRS84',units=['deg','deg','m'],position=['-73','41','100'])
        b=compose(a);self.assertEqual(set(b['geoPose']),{'position','quaternion'});self.assertEqual(recover(b),a)
    def test_missing_height_not_geopose(self):
        a=sample();a['spatial'].update(frame='OGC:CRS84',units=['deg','deg'],position=['-73','41'])
        self.assertIsNone(compose(a)['geoPose'])
    def test_bridge_native_role(self):
        with Store() as s:
            a=sample(role='simulated');b=project(s,a)
            self.assertEqual(s.get(b['stateAssertionCid'])['payload']['epistemicRole'],'simulated')
            self.assertEqual(json.loads(s.get(b['observationCid'])['payload']['signal']),a)
    def test_bridge_requires_no_native_change(self):
        a=sample();d=native_digest(a)
        with Store() as s:project(s,a)
        self.assertEqual(native_digest(a),d)

class RepairTests(unittest.TestCase):
    def test_ingress_rejects_ambiguous_source(self):
        with Store() as s:
            with self.assertRaises(ContractError):ingress(s,'{"a":1,"a":2}',source='s',event_time=time_at(0),known_at=time_at(1),purposes=['p'])
            self.assertEqual(s.all(),[])
    def test_context_wrapper_cannot_hide_restricted_parent(self):
        with Store() as s:
            o,f=ingress(s,'{}',source='s',event_time=time_at(0),known_at=time_at(1),purposes=['private'])
            wrap=tile('indranet.wrapper',{'purposes':['public']},[f['cid']],created_at=time_at(1));s.append(wrap)
            with self.assertRaises(ContractError):context(s,purpose='public',refs=[wrap['cid']],mode='m',expires=time_at(10),created_at=time_at(2))
    def test_view_follows_evidence_grant(self):
        with Store() as s:
            o,f=ingress(s,'{}',source='s',event_time=time_at(0),known_at=time_at(1),purposes=['private'])
            assertion(s,subject='s',predicate='p',value='v',evidence=[f['cid']],event_time=time_at(0),known_at=time_at(1),purposes=['public'])
            self.assertEqual(select(s,purpose='public',event_at=time_at(2),known_at=time_at(3),max_age_seconds=5)['groups'],[])

if __name__=='__main__':unittest.main()
