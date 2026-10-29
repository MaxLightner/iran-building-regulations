/* End-to-end search benchmark over all 24 chapters and project relevance data. */
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'frontend/app.js'),'utf8').replace(/init\(\);\s*$/,'');
const context=vm.createContext({console,URL,Map,Set});
vm.runInContext(source+'\n globalThis.__b={knowledgeScore,projectFit,dedupeRanked,state};',context);
const {knowledgeScore,projectFit,dedupeRanked,state}=context.__b;
state.ontology=JSON.parse(fs.readFileSync(path.join(root,'frontend/data/knowledge/ontology.json'),'utf8'));
const manifest=JSON.parse(fs.readFileSync(path.join(root,'frontend/data/knowledge/manifest.json'),'utf8'));
const benchmark=JSON.parse(fs.readFileSync(path.join(root,'benchmarks/search-cases.json'),'utf8'));
const corpus=[];
for(const d of manifest.documents){
  const knowledge=JSON.parse(fs.readFileSync(path.join(root,'frontend/data/knowledge',d.id+'.json'),'utf8'));
  const applicability=JSON.parse(fs.readFileSync(path.join(root,'frontend/data/applicability',d.id+'.json'),'utf8'));
  const rules=new Map(applicability.records.map(r=>[r.id,r]));
  for(const r of knowledge.records)corpus.push({r,rule:rules.get(r.id)});
}
let topicPass=0,chapterPass=0,chapterCases=0;
for(const c of benchmark.cases){
  state.project=c.project||null;
  const ranked=dedupeRanked(corpus.map(({r,rule})=>{
    const fit=projectFit(rule,r,state.project);
    return {r,fit,score:knowledgeScore(r,c.q,null,fit.score)};
  }).filter(x=>x.score!==null).sort((a,b)=>b.score-a.score),Math.max(c.top_k||20,30));
  const top=ranked.slice(0,c.top_k||20);
  const topicOk=top.some(x=>(x.r.topics||[]).includes(c.topic));
  if(topicOk)topicPass++;
  let chapterOk=true;
  if(c.chapter){
    chapterCases++;chapterOk=top.some(x=>x.r.document_id===c.chapter);
    if(chapterOk)chapterPass++;
  }
  console.log((topicOk&&chapterOk?'PASS':'FAIL'),c.q,'topic=',topicOk,'chapter=',c.chapter?chapterOk:'n/a',
    'top=',top.slice(0,3).map(x=>x.r.document_id+':'+(x.r.locator||x.r.id)).join(','));
  if(c.chapter)assert.ok(chapterOk,'expected chapter '+c.chapter+' not in top results for '+c.q);
}
const rate=topicPass/benchmark.cases.length;
console.log('Benchmark topic pass',topicPass+'/'+benchmark.cases.length,'=',rate.toFixed(3),
  'chapter pass',chapterPass+'/'+chapterCases);
assert.ok(rate>=benchmark.minimum_topic_pass_rate,'topic benchmark below threshold');
console.log('PASS: final search benchmark meets MVP threshold');
