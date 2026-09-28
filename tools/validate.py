"""Validate the exact local candidate and replay without mutating its payload."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import sys
import jsonschema
from rdflib import Graph, URIRef, Literal, RDF, XSD, Namespace
from indranet.demo import run_all
from indranet.canon import verify
from indranet.rdfcheck import validate as validate_rdf
ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'packs/stdpack-indranet-context'

def main(report: Path | None = None) -> dict:
    schemas={}
    for path in (PACK/'schema').glob('*.json'):
        schema=json.loads(path.read_text());jsonschema.Draft202012Validator.check_schema(schema)
        schemas[path.name.replace('.schema.json','')]=schema
    count=0;tile_count=0
    for path in (PACK/'examples').glob('*.json'):
        example=json.loads(path.read_text())
        if 'tiles' in example:
            ids={row['cid'] for row in example['tiles']}
            for row in example['tiles']:
                verify(row)
                jsonschema.validate(row,schemas['tile-envelope'],format_checker=jsonschema.FormatChecker())
                if not set(row['parents']).issubset(ids): raise ValueError('Broken scenario closure')
                if row['kind'].startswith('indranet.'):
                    key=row['kind'].split('.',1)[1].replace('_','-')
                    jsonschema.validate(row['payload'],schemas[key],format_checker=jsonschema.FormatChecker());count+=1
                tile_count+=1
        else:
            jsonschema.validate(example['payload'],schemas[example['schema']],format_checker=jsonschema.FormatChecker());count+=1
    replay=[]
    with tempfile.TemporaryDirectory() as tmp:
        run_all(Path(tmp))
        for path in sorted((ROOT/'outputs').glob('*.json')):
            other=Path(tmp)/path.name
            if not other.exists(): continue
            equal=path.read_bytes()==other.read_bytes()
            if not equal: raise ValueError('Replay drift: '+path.name)
            replay.append({'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'match':True})
    shapes=Graph().parse(PACK/'shacl/context.shapes.ttl',format='turtle')
    I=Namespace('urn:indranet:candidate:');P=Namespace('http://www.w3.org/ns/prov#')
    data=Graph();subject=URIRef('urn:fixture:state')
    data.add((subject,RDF.type,I.StateAssertion));data.add((subject,I.subject,URIRef('urn:fixture:entity')))
    data.add((subject,I.eventTime,Literal('2026-09-15T12:00:00Z',datatype=XSD.dateTime)))
    data.add((subject,I.knownAt,Literal('2026-09-15T12:00:01Z',datatype=XSD.dateTime)))
    data.add((subject,I.purpose,Literal('operations')));data.add((subject,P.wasDerivedFrom,URIRef('urn:fixture:observation')))
    data.add((subject,I.epistemicRole,Literal('reported-measurement')))
    if validate_rdf(data,shapes): raise ValueError('Positive RDF fixture failed')
    data.remove((subject,P.wasDerivedFrom,None))
    negative=validate_rdf(data,shapes)
    if not negative: raise ValueError('Negative RDF fixture was accepted')
    identity=json.loads(subprocess.check_output(['node',str(ROOT/'tools/pack-id.mjs'),str(PACK)],text=True))
    manifest=json.loads((PACK/'pack.json').read_text())
    # The inspected schema is retained as a local reconstruction with provenance.
    manifest_schema=json.loads((ROOT/'tools/pack-manifest-inspected.schema.json').read_text())
    jsonschema.validate(manifest,manifest_schema)
    if identity['pack_id']!=manifest['pack_id']: raise ValueError('Pack identity mismatch')
    for export in manifest['exports']:
        if not (PACK/export['path']).is_file(): raise ValueError('Missing export '+export['path'])
    result={'status':'PASS','schemaCount':len(schemas),'payloadValidations':count,'scenarioTiles':tile_count,
        'replay':replay,'rdfConstraintSubset':{'positive':'PASS','missingEvidenceNegative':'REJECTED','fullShaclEngine':False},
        'pack':identity,'nativeRuntimeConformance':False,'fullRosettaConformance':False}
    if report: report.write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path);args=parser.parse_args()
    print(json.dumps(main(args.report),indent=2))
