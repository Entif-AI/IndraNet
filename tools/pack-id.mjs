#!/usr/bin/env node
// Compatible with inspected rosetta-pack-id-v1. Does not assign a ROCK number.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
export function ordered(x) {
  if (Array.isArray(x)) return x.map(ordered);
  if (x && typeof x === 'object') return Object.fromEntries(Object.entries(x).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>[k,ordered(v)]));
  return x;
}
export function identity(input) {
  return 'cidv1-sha256-' + crypto.createHash('sha256').update(JSON.stringify(ordered(input))).digest('hex');
}
export function packInput(root) {
  const files = [];
  function visit(dir) {
    for (const item of fs.readdirSync(dir, {withFileTypes:true})) {
      if (item.name === '.DS_Store') continue;
      const full = path.join(dir,item.name);
      if (item.isDirectory()) visit(full);
      else if (item.isFile() && item.name !== 'pack.json') {
        const bytes = fs.readFileSync(full);
        files.push({path:path.relative(root,full).split(path.sep).join('/'),
          sha256:crypto.createHash('sha256').update(bytes).digest('hex'),size:bytes.length});
      }
    }
  }
  visit(root); files.sort((a,b)=>a.path.localeCompare(b.path));
  const manifest = JSON.parse(fs.readFileSync(path.join(root,'pack.json'),'utf8'));
  delete manifest.pack_id;
  return {algorithm:'rosetta-pack-id-v1',files,manifest};
}
if (process.argv[2] === '--golden') {
  const vector = JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
  const actual = identity(vector.input);
  console.log(JSON.stringify({expected:vector.expected_pack_id,actual,pass:actual===vector.expected_pack_id},null,2));
  if(actual!==vector.expected_pack_id) process.exitCode=1;
} else if (process.argv[2]) {
  const root = process.argv[2];
  const input = packInput(root); const packId = identity(input);
  if (process.argv.includes('--write')) {
    const file=path.join(root,'pack.json'); const m=JSON.parse(fs.readFileSync(file,'utf8'));
    m.pack_id=packId; fs.writeFileSync(file,JSON.stringify(m,null,2)+'\n');
  }
  console.log(JSON.stringify({pack_id:packId,files:input.files.length,algorithm:input.algorithm},null,2));
}
