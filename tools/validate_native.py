"""Validate native schemas, negative vectors and deterministic composition replay."""
from pathlib import Path
import json,sys,tempfile,hashlib
import jsonschema
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from indranet.native import validate, ExchangeError
from indranet.scenarios import run
PACK=ROOT/'packs/stdpack-indranet-context'
schema=json.loads((PACK/'schema/native-record.schema.json').read_text())
checker=jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker())
count=0
for path in (ROOT/'composition-results').glob('*.json'):
 data=json.loads(path.read_text())
 for record in (data.get('records',[]) if isinstance(data,dict) else []):
  checker.validate(record);validate(record);count+=1
negative=json.loads((PACK/'test-vectors/native-negative.json').read_text())
for vector in negative:
 try:validate(vector['record'])
 except ExchangeError:continue
 raise AssertionError('Invalid fixture accepted: '+vector['case'])
replay=[]
with tempfile.TemporaryDirectory() as tmp:
 run(Path(tmp))
 for p in (ROOT/'composition-results').glob('*.json'):
  if p.name=='validation.json':continue
  other=Path(tmp)/p.name
  if not other.exists() or p.read_bytes()!=other.read_bytes():raise AssertionError('Replay drift: '+p.name)
  replay.append({'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'equal':True})
report={'status':'PASS','nativeRecordsValidated':count,'negativeVectorsRejected':len(negative),'replay':replay,
 'officialConformance':False,'scope':'Native schema plus explicit codec and replay contracts only'}
(ROOT/'composition-results/validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
