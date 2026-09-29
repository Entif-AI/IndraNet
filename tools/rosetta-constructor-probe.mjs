// Source-derived reproduction of the inspected constructor's canonical body.
// This is an interoperability probe over the packaged subset, not a monorepo build.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
const root=path.resolve(process.argv[2]??'outputs');
function sortValue(value){
  if(Array.isArray(value))return value.map(sortValue);
  if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value)
    .sort(([a],[b])=>a<b?-1:a>b?1:0).map(([k,v])=>[k,sortValue(v)]));
  if(typeof value==='number'&&!Number.isFinite(value))throw new Error('Nonfinite JSON');
  return value;
}
function check(t){
  const body={kind:t.kind,pack:t.pack,parents:[...t.parents].sort(),payload:t.payload,version:t.version};
  const canonical=JSON.stringify(sortValue(body));
  const cid='cidv1-sha256-'+crypto.createHash('sha256').update(canonical).digest('hex');
  assert.equal(t.canonical,canonical);assert.equal(t.cid,cid);
}
let count=0;
for(const file of fs.readdirSync(root).filter(f=>f.endsWith('.json')&&f!=='index.json')){
  const example=JSON.parse(fs.readFileSync(path.join(root,file),'utf8'));
  if(!example.tiles)continue;
  for(const t of example.tiles){check(t);count++;}
  if(example.result.signedFixture){
    const signed=example.result.signedFixture;check(signed.receipt);
    assert.equal(signed.signature.signedCid,signed.receipt.cid);
    assert(crypto.verify(null,Buffer.from(signed.signature.signedCid),signed.signature.publicKeyPem,
      Buffer.from(signed.signature.signatureBase64,'base64')));
  }
}
console.log(JSON.stringify({status:'PASS',constructorSubsetTiles:count,ed25519FixtureVerified:true,
  nativeRepositoryBuild:false,fullCoreConformance:false},null,2));
