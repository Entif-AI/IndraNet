"""Reference integration envelopes, not imports of the named research systems.

No vendor/model code, model weight, renderer or hardware service is invoked.
Supplied executable-code references stay inert. These adapters test the exchange
contract around a hypothetical upstream result, never the upstream system.
"""
from __future__ import annotations
from copy import deepcopy
from .native import ExchangeError, instant

SYSTEMS = {
 'code-as-world':('S14','https://arxiv.org/abs/2608.27549','composition/evolution/appearance program references'),
 'physmind':('S16','https://arxiv.org/abs/2608.04575','world geometry/dynamics and intervention references'),
 'programmable-world-model':('S36','https://arxiv.org/abs/2609.10540','program state and generated appearance references'),
 'stateflow':('S37','https://arxiv.org/abs/2608.12314','editable scene, camera intent and render references'),
 'pilebelief':('S53','https://arxiv.org/abs/2609.22858','historical belief update and separate imagined branch references'),
 'object-path-graphs':('S54','https://arxiv.org/abs/2609.24189','semantic object/topological path references'),
 'astronex-world':('S55','https://arxiv.org/abs/2609.20034','camera/action/event conditioning and generated video references'),
}

def reference_result(system: str, *, record_id: str, role: str, inputs: list[str],
                     outputs: list[str], at: str, branch: str = 'proposal:A', counterfactual: bool = False) -> dict:
    if system not in SYSTEMS or role not in {'hypothesis','simulation','prediction','evaluation','generated-appearance','topology'}:
        raise ExchangeError('Unknown reference system or result role')
    if not record_id or not inputs or not outputs or any(not isinstance(x,str) or not x for x in inputs+outputs):
        raise ExchangeError('Reference envelope requires record, input and output identifiers')
    instant(at)
    if type(counterfactual) is not bool or not branch or (counterfactual and branch=='historical'):
        raise ExchangeError('Counterfactual result requires a nonhistorical branch')
    source,url,contract=SYSTEMS[system]
    return {'schemaVersion':'0.5.0','recordId':record_id,'systemLabel':system,'sourceId':source,'sourceUrl':url,
        'role':role,'inputRefs':list(inputs),'outputRefs':list(outputs),'knownAt':at,'branch':branch,
        'counterfactual':counterfactual,'contractIntent':contract,'execution':'simulated-reference-envelope',
        'assumptions':['Upstream output has been supplied as a fixture','References are inert and not dereferenced',
            'Coordinate, clock and licensing bindings require the upstream integration owner'],
        'nonclaims':['No upstream implementation or weights were executed','No benchmark is reproduced',
            'No vendor interoperability, endorsement or actuation authorization'],
        'physicalActuationAuthority':False}

def separate_belief_and_imagination(measured_refs: list[str], imagined_refs: list[str]) -> dict:
    if set(measured_refs) & set(imagined_refs):
        raise ExchangeError('The same supplied result cannot be admitted to both roles')
    return {'historicalEvidenceRefs':deepcopy(measured_refs),'imaginedBranchRefs':deepcopy(imagined_refs),
            'admission':'separate storage roles, not a physical truth verifier'}
