/* Behavioral test for structured-knowledge search functions. */
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'frontend/app.js'),'utf8').replace(/init\(\);\s*$/,'');
const context=vm.createContext({console,URL});
vm.runInContext(source+'\n globalThis.__k={fold,knowledgeScore,resolveQueryTopics,state};',context);
const {fold,knowledgeScore,resolveQueryTopics,state}=context.__k;
state.ontology=JSON.parse(fs.readFileSync(path.join(root,'frontend/data/knowledge/ontology.json'),'utf8'));
assert.ok(resolveQueryTopics('راه پله').direct.has('stairs'));
assert.ok(resolveQueryTopics('بار برف').direct.has('loads'));
assert.ok(resolveQueryTopics('آسانسور').direct.has('elevator'));
assert.ok(resolveQueryTopics('میلگرد').direct.has('concrete_steel'));
const manifest=JSON.parse(fs.readFileSync(path.join(root,'frontend/data/knowledge/manifest.json'),'utf8'));
for(const [docid,query] of [['m03','حریق'],['m06','بار برف'],['m07','خاک'],['m09','میلگرد'],['m15','آسانسور']]){
  const shard=JSON.parse(fs.readFileSync(path.join(root,'frontend/data/knowledge',docid+'.json'),'utf8'));
  const ranked=shard.records.map(r=>({r,score:knowledgeScore(r,query,null)})).filter(x=>x.score!==null).sort((a,b)=>b.score-a.score);
  assert.ok(ranked.length>0,query+' has no result in '+docid);
  assert.ok(ranked[0].score>0,query+' result has no relevance score');
}
console.log('PASS: knowledge search resolves topics and returns structured records');
