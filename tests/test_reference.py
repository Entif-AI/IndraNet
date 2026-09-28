"""Behavioral tests for the local candidate subset."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from indranet.canon import ContractError, canonical, tile, verify, timestamp
from indranet.store import Store
from indranet.model import ingress, assertion, revision, context, decimal_text
from indranet.frames import Transform, FrameTree
from indranet.views import select
from indranet.process import osc_packet, preview, check_preview
from indranet.reality import Dependencies, reconstruction_plan, aggregate_zones
from indranet.rosetta import attest_fixture, verify_attestation, interpretation_chain
from indranet.adapters import ingest_pose
from indranet.demo import SCENARIOS, T0,T1,T2,T3,T4,T8,T9,T10,END,performance,xr,warehouse,executable_worlds,generative_reality

class CanonTests(unittest.TestCase):
    def test_key_order(self):
        self.assertEqual(canonical({"b":2,"a":1}),'{"a":1,"b":2}')
    def test_numeric_key_rejected(self):
        with self.assertRaises(ContractError): canonical({"2":0,"10":0})
    def test_non_ascii_key_rejected(self):
        with self.assertRaises(ContractError): canonical({"\u00e9":0})
    def test_unicode_value(self):
        self.assertEqual(canonical({"a":"\u00e9"}),'{"a":"\u00e9"}')
    def test_surrogate_rejected(self):
        with self.assertRaises(ContractError): canonical({"a":"\ud800"})
    def test_unsafe_integer_rejected(self):
        with self.assertRaises(ContractError): canonical({"a":2**53})
    def test_arbitrary_float_rejected(self):
        with self.assertRaises(ContractError): canonical({"a":0.1})
    def test_exact_quarters(self):
        self.assertEqual(canonical([0.25,0.5,0.75]),'[0.25,0.5,0.75]')
    def test_nonfinite_rejected(self):
        for x in (float('nan'),float('inf')):
            with self.assertRaises(ContractError): canonical({"a":x})
    def test_tamper_detected(self):
        t=tile('rosetta.run',{"runId":"a","summary":"b","tags":[]})
        t['payload']['summary']='c'
        with self.assertRaises(ContractError): verify(t)
    def test_created_at_not_hashed(self):
        a=tile('rosetta.run',{"a":1},created_at=T0)
        b=tile('rosetta.run',{"a":1},created_at=T1)
        self.assertEqual(a['cid'],b['cid'])
    def test_no_new_core_kind(self):
        with self.assertRaises(ContractError): tile('rosetta.position',{})
    def test_naive_time_rejected(self):
        with self.assertRaises(ContractError): timestamp('2026-09-15T12:00:00')
    def test_offset_equivalence(self):
        self.assertEqual(timestamp(T0),timestamp('2026-09-15T08:00:00-04:00'))
    def test_quantity_bool_rejected(self):
        with self.assertRaises(ContractError): decimal_text(True)

class StoreTests(unittest.TestCase):
    def test_duplicate_is_idempotent(self):
        with Store() as s:
            r=tile('rosetta.run',{"a":1});s.append(r);s.append(r)
            self.assertEqual(len(s.all()),1)
    def test_batch_allows_forward_parent(self):
        with Store() as s:
            p=tile('rosetta.run',{"a":1});c=tile('indranet.example',{"a":2},[p['cid']])
            s.append_many([c,p]);self.assertEqual(len(s.closure([c['cid']])),2)
    def test_batch_rollback(self):
        with Store() as s:
            good=tile('rosetta.run',{"a":1})
            bad=tile('indranet.example',{"a":2},['cidv1-sha256-'+'a'*64])
            with self.assertRaises(ContractError): s.append_many([good,bad])
            self.assertEqual(s.all(),[])
    def test_append_only_trigger(self):
        with Store() as s:
            s.append(tile('rosetta.run',{"a":1}))
            with self.assertRaises(sqlite3.IntegrityError): s.db.execute('DELETE FROM artifacts')
            with self.assertRaises(sqlite3.IntegrityError): s.db.execute("UPDATE artifacts SET kind='x'")
    def test_disk_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'store.sqlite';r=tile('rosetta.run',{"a":1})
            with Store(path) as s: s.append(r)
            with Store(path) as s: self.assertEqual(s.get(r['cid']),r)
    def test_returned_value_is_detached(self):
        with Store() as s:
            r=tile('rosetta.run',{"a":1});s.append(r)
            s.get(r['cid'])['payload']['a']=2
            self.assertEqual(s.get(r['cid'])['payload']['a'],1)

class DomainTests(unittest.TestCase):
    def setUp(self):
        self.s=Store()
        self.obs,self.form=ingress(self.s,'{"position":[1,2,3]}',source='fixture',event_time=T0,known_at=T1,purposes=['p','performance'])
    def tearDown(self): self.s.close()
    def make(self, value='a', purposes=None, event=T0, known=T1, role='reported-measurement',frame='f'):
        return assertion(self.s,subject='rid:fixture:a',predicate='location',value=value,evidence=[self.form['cid']],event_time=event,
                         known_at=known,purposes=purposes or ['p'],role=role,frame=frame)
    def view(self, at=T4, known=T4):
        return select(self.s,purpose='p',event_at=at,known_at=known,max_age_seconds=5)
    def test_raw_signal_preserved(self):
        self.assertEqual(self.s.get(self.obs['cid'])['payload']['signal'],'{"position":[1,2,3]}')
    def test_future_measurement_rejected(self):
        with self.assertRaises(ContractError): self.make(event=T4,known=T1)
    def test_unknown_role_rejected(self):
        with self.assertRaises(ContractError): self.make(role='truth')
    def test_missing_evidence_rejected(self):
        with self.assertRaises(ContractError): assertion(self.s,subject='s',predicate='p',value='v',evidence=[],event_time=T0,known_at=T1,purposes=['p'])
    def test_unauthorized_not_returned(self):
        self.make(purposes=['secret']);v=self.view()
        self.assertEqual(v['groups'],[]);self.assertEqual(v['omittedCount'],1)
    def test_conflict_retained(self):
        self.make('a');self.make('b');g=self.view()['groups'][0]
        self.assertEqual(g['status'],'contested');self.assertEqual(len(g['candidates']),2)
    def test_frame_difference_not_numeric_conflict(self):
        self.make('a',frame='one');self.make('a',frame='two')
        self.assertEqual(self.view()['groups'][0]['status'],'frame-unresolved')
    def test_stale_visible(self):
        self.make();self.assertEqual(self.view(at=T10,known=T10)['groups'][0]['status'],'stale')
    def test_knowledge_time(self):
        self.make(known=T10)
        self.assertEqual(self.view()['groups'],[])
    def test_retraction_is_bitemporal(self):
        a=self.make();revision(self.s,a['cid'],None,event_time=T2,known_at=T10,reason='explicit withdrawal')
        self.assertEqual(len(self.view(known=T9)['groups']),1)
        self.assertEqual(self.view(known=T10)['groups'],[])
    def test_supersession_keeps_history(self):
        a=self.make('a');b=self.make('b',event=T2,known=T3)
        revision(self.s,a['cid'],b['cid'],event_time=T2,known_at=T3,reason='correction')
        self.assertEqual(self.view()['groups'][0]['candidates'][0]['value'],'b')
        self.assertTrue(self.s.has(a['cid']))
    def test_simulation_cannot_be_measurement_evidence(self):
        simulated=self.make(role='simulated')
        with self.assertRaises(ContractError):
            assertion(self.s,subject='s',predicate='p',value=1,evidence=[simulated['cid']],event_time=T0,known_at=T1,purposes=['p'])
    def test_context_purpose_escalation_rejected(self):
        a=self.make()
        with self.assertRaises(ContractError): context(self.s,purpose='secret',refs=[a['cid']],mode='m',expires=END,created_at=T2)
    def test_empty_context_rejected(self):
        with self.assertRaises(ContractError): context(self.s,purpose='p',refs=[],mode='m',expires=END,created_at=T2)
    def test_utf8_token_span(self):
        obs,form=ingress(self.s,'{"label":"\u00e9","position":1}',source='fixture',event_time=T0,known_at=T1,purposes=['p'])
        chain=interpretation_chain(self.s,obs['cid'],'position',entity='rid:fixture:a',at=T2)
        token=self.s.get(chain['form'])['payload'];raw=obs['payload']['signal'].encode()
        self.assertEqual(raw[token['offset']:token['offset']+token['length']].decode(),'position')
    def test_receipt_signature(self):
        signed=attest_fixture(self.s,self.obs['cid'],at=T2);verify_attestation(signed)
        signed['signature']['signedCid']='cidv1-sha256-'+'0'*64
        with self.assertRaises(ContractError): verify_attestation(signed)

class FrameTests(unittest.TestCase):
    def edge(self,child='a',parent='b',matrix=None):
        m=matrix or ((1.,0.,0.,2.),(0.,1.,0.,3.),(0.,0.,1.,0.),(0.,0.,0.,1.))
        return Transform(child,parent,m,T0,END,'cidv1-sha256-'+'1'*64)
    def test_translation(self):
        self.assertEqual(FrameTree([self.edge()]).to_ancestor((1,0,0),'a','b',T2)['point'],['3.0','3.0','0.0'])
    def test_composition(self):
        self.assertEqual(FrameTree([self.edge(),self.edge('b','c')]).to_ancestor((1,0,0),'a','c',T2)['point'],['5.0','6.0','0.0'])
    def test_cycle_rejected(self):
        with self.assertRaises(ContractError): FrameTree([self.edge(),self.edge('b','a')])
    def test_multiple_parents_rejected(self):
        with self.assertRaises(ContractError): FrameTree([self.edge(),self.edge('a','c')])
    def test_expiry(self):
        with self.assertRaises(ContractError): FrameTree([self.edge()]).to_ancestor((0,0,0),'a','b',END)
    def test_missing_path(self):
        with self.assertRaises(ContractError): FrameTree([self.edge()]).to_ancestor((0,0,0),'a','c',T2)
    def test_reflection_rejected(self):
        with self.assertRaises(ContractError): self.edge(matrix=((-1.,0.,0.,0.),(0.,1.,0.,0.),(0.,0.,1.,0.),(0.,0.,0.,1.)))
    def test_scale_rejected(self):
        with self.assertRaises(ContractError): self.edge(matrix=((2.,0.,0.,0.),(0.,1.,0.,0.),(0.,0.,1.,0.),(0.,0.,0.,1.)))

class ScenarioTests(unittest.TestCase):
    def test_all_replay_deterministically(self):
        for name,fn in SCENARIOS.items():
            self.assertEqual(fn(),fn(),name)
    def test_gesture_different_meaning(self):
        r=performance()['result'];self.assertNotEqual(r['first']['address'],r['second']['address'])
        self.assertFalse(r['first']['sent'])
    def test_changed_context_refused(self):
        self.assertEqual(performance()['result']['oldPreviewUnderNewContext']['reasons'],['context-changed'])
    def test_xr_rights_differ(self):
        r=xr()['result'];self.assertEqual(len(r['attendee']['groups']),1);self.assertEqual(len(r['technician']['groups']),2)
    def test_warehouse_conflict(self):
        r=warehouse()['result'];groups={g['predicate']:g for g in r['initial']['groups']}
        self.assertEqual(groups['position']['status'],'contested');self.assertEqual(groups['battery-percent']['status'],'stale')
    def test_correction_does_not_rewrite_known_history(self):
        r=warehouse()['result'];a=[g for g in r['beforeCorrectionKnown']['groups'] if g['predicate']=='position'][0]
        b=[g for g in r['afterCorrectionKnown']['groups'] if g['predicate']=='position'][0]
        self.assertEqual(a['status'],'contested');self.assertEqual(b['status'],'available')
    def test_competing_models_remain_unresolved(self):
        r=executable_worlds()['result'];self.assertEqual(len(r['simulations']),2);self.assertEqual(r['evaluation']['verdict'],'unknown')
    def test_missing_witness_modes(self):
        r=generative_reality()['result'];self.assertEqual(r['evidenceMode']['status'],'degraded-wireframe')
        self.assertEqual(r['perceptualMode']['status'],'synthesis-labeled')
        self.assertFalse(r['witnessAvailable']['decoderExecuted'])
    def test_osc_alignment(self):
        packet=osc_packet('/demo',10);self.assertEqual(len(packet)%4,0);self.assertEqual(packet[-4:],b'\x00\x00\x00\x0a')
    def test_osc_null_rejected(self):
        with self.assertRaises(ContractError): osc_packet('/bad\0path',1)
    def test_derivation_invalidation(self):
        d=Dependencies({'a':[],'b':['a'],'c':['b'],'other':[]})
        self.assertEqual(d.invalidate(['a']),['a','b','c'])
    def test_derivation_cycle(self):
        with self.assertRaises(ContractError): Dependencies({'a':['b'],'b':['a']})
    def test_derivation_missing(self):
        with self.assertRaises(ContractError): Dependencies({'a':['b']})
    def test_aggregate_suppression(self):
        self.assertEqual(aggregate_zones(['a','a','a','b'])['zones'],[{'zone':'a','count':3}])
    def test_ngsi_declared_crs(self):
        with Store() as s:
            with self.assertRaises(ContractError): ingest_pose(s,{'location':{'type':'GeoProperty','value':{'type':'Point','coordinates':[1,2]},'observedAt':T0}},standard='ngsi-ld',source='s',subject='e',frame='local',known_at=T1,purposes=['p'])
    def test_sensorthings_interval_rejected(self):
        with Store() as s:
            with self.assertRaises(ContractError): ingest_pose(s,{'phenomenonTime':T0+'/'+T1,'result':[1,2]},standard='sensorthings',source='s',subject='e',frame='local',known_at=T1,purposes=['p'])

if __name__=='__main__': unittest.main()
