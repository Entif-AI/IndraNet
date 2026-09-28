import ast
from pathlib import Path
import unittest
from indranet.native import ExchangeError
from indranet.research_reference import SYSTEMS, reference_result, separate_belief_and_imagination
from indranet.scenarios import time_at

class ResearchReferenceTests(unittest.TestCase):
    def test_all_systems_are_labeled(self):
        for name in SYSTEMS:
            r=reference_result(name,record_id='urn:fixture:result',role='hypothesis',inputs=['urn:evidence:a'],outputs=['urn:model:b'],at=time_at(1))
            self.assertEqual(r['execution'],'simulated-reference-envelope');self.assertFalse(r['physicalActuationAuthority'])
    def test_raw_code_stays_inert(self):
        r=reference_result('code-as-world',record_id='r',role='hypothesis',inputs=['source'],outputs=['python:raise RuntimeError()'],at=time_at(1))
        self.assertEqual(r['outputRefs'],['python:raise RuntimeError()'])
    def test_no_measurement_role(self):
        with self.assertRaises(ExchangeError):reference_result('pilebelief',record_id='r',role='measurement',inputs=['a'],outputs=['b'],at=time_at(1))
    def test_counterfactual_not_history(self):
        with self.assertRaises(ExchangeError):reference_result('physmind',record_id='r',role='simulation',inputs=['a'],outputs=['b'],at=time_at(1),branch='historical',counterfactual=True)
    def test_unknown_model(self):
        with self.assertRaises(ExchangeError):reference_result('invented-vendor',record_id='r',role='hypothesis',inputs=['a'],outputs=['b'],at=time_at(1))
    def test_role_partition(self):self.assertEqual(separate_belief_and_imagination(['m'],['s'])['historicalEvidenceRefs'],['m'])
    def test_overlap_rejected(self):
        with self.assertRaises(ExchangeError):separate_belief_and_imagination(['a'],['a'])
    def test_native_has_only_standard_library_imports(self):
        p=Path(__file__).resolve().parents[1]/'src/indranet/native.py';tree=ast.parse(p.read_text())
        allowed={'__future__','copy','hashlib','json','datetime','decimal','typing'}
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):self.assertTrue(all(x.name in allowed for x in node.names))
            if isinstance(node,ast.ImportFrom):self.assertIn(node.module,allowed);self.assertEqual(node.level,0)
