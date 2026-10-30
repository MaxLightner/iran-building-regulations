const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const root=path.resolve(__dirname,'../frontend');
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const app=fs.readFileSync(path.join(root,'app.js'),'utf8');
const dom=new JSDOM(html,{url:'https://test.example/iran-building-regulations/',runScripts:'outside-only',pretendToBeVisual:true});
const win=dom.window;
win.HTMLElement.prototype.scrollIntoView=function(){};
const errors=[];
win.addEventListener('error',e=>errors.push(String(e.error||e.message)));
win.addEventListener('unhandledrejection',e=>errors.push(String(e.reason)));
win.fetch=async(url)=>{
  const p=path.resolve(root,String(url).replace(/^\.\//,''));
  if(!p.startsWith(root+path.sep)||!fs.existsSync(p))return {ok:false,status:404};
  return {ok:true,status:200,json:async()=>JSON.parse(fs.readFileSync(p,'utf8'))};
};
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function main(){
  win.eval(app);
  await pause(120);
  const doc=win.document;
  const q=doc.querySelector('#q');
  const go=doc.querySelector('#go');
  const select=doc.querySelector('#chapter');
  const topicChips=()=>[...doc.querySelectorAll('#quick button[data-q]')];
  const topicGroups=()=>doc.querySelectorAll('#quick .topic-group');
  const chapterButtons=()=>doc.querySelectorAll('#chapterGrid .chapter');

  // No database health / coverage / certification details in the public UI.
  for(const name of ['completenessCard','datasetCoverage','sourceProvenance','coverage','chapterCount']){
    assert.equal(doc.getElementById(name),null,'database status element must be absent: '+name);
  }
  assert.equal(chapterButtons().length,24,'all chapter controls should appear');
  assert.ok(doc.querySelectorAll('#results .result').length>=1,'initial search still returns results');
  assert.equal(topicGroups().length,24,'without scope, all 24 chapter topic groups show');
  assert.ok(topicChips().length>400,'uncapped topic explorer must show hundreds of tags');

  // Clicking a tag scopes searches to its chapter and runs the query.
  const stairs=doc.querySelector('[data-q="عرض راه پله"]');
  assert.ok(stairs,'stairs tag should exist');
  stairs.click();await pause(10);
  assert.equal(select.value,'4','tag chooses relevant chapter');
  assert.equal(q.value,'عرض راه پله','clicked topic fills search box');
  assert.ok(doc.querySelectorAll('#results .result').length>=1,'topic click executes a search');

  select.value='';select.dispatchEvent(new win.Event('change'));await pause(10);
  const use=doc.querySelector('#pUse');
  use.value='residential';use.dispatchEvent(new win.Event('change'));await pause(10);
  assert.equal(topicGroups().length,24,'residential must keep all chapters available');
  assert.ok(topicChips().length>400,'residential must not collapse the topic list');

  // Chapter 5 should expose the broad materials vocabulary, not three hard-coded tags.
  select.value='5';select.dispatchEvent(new win.Event('change'));await pause(10);
  assert.equal(topicGroups().length,1,'a chapter filter reduces groups');
  assert.ok(topicChips().length>40,'Chapter 5 should offer extensive material tags');
  for(const label of ['سیمان','آجر','بلوک سیمانی','بتن','گچ','شیشه','عایق حرارتی','کاشی']){
    assert.ok(topicChips().some(el=>el.dataset.q===label),'missing Chapter 5 topic: '+label);
  }
  const tagFilter=doc.querySelector('#topicFilter');
  tagFilter.value='شیشه';tagFilter.dispatchEvent(new win.Event('input'));await pause(10);
  assert.ok(topicChips().length>=1,'topic text filter should find matching subjects');
  assert.ok(topicChips().every(el=>el.dataset.q.includes('شیشه')),'topic text filter must exclude nonmatches');
  tagFilter.value='';tagFilter.dispatchEvent(new win.Event('input'));await pause(10);
  assert.ok(topicChips().length>40,'clearing filter restores all Chapter 5 tags');
  doc.querySelector('[data-q="سیمان"]').click();await pause(10);
  assert.equal(select.value,'5');
  assert.equal(q.value,'سیمان');
  assert.ok(doc.querySelectorAll('#results .result').length>=1,'clicking a material should search chapter 5');

  q.value='عرض آشپزخانه';select.value='';go.click();await pause(10);
  assert.ok(doc.querySelectorAll('#results .result').length>=1,'manual search click should work');
  doc.querySelector('#chapterGrid .chapter:nth-child(10)').click();await pause(10);
  assert.equal(select.value,'10');
  assert.ok(doc.querySelector('[data-q="اتصال فولادی"]'),'steel tag appears in Chapter 10');
  doc.querySelector('[data-q="اتصال فولادی"]').click();await pause(10);
  assert.equal(select.value,'10');
  assert.equal(q.value,'اتصال فولادی');

  // Existing project filters still affect which chapters can be selected.
  const structure=doc.querySelector('#pStructure'),gas=doc.querySelector('#pGas'),stage=doc.querySelector('#pStage');
  structure.value='steel';structure.dispatchEvent(new win.Event('change'));await pause(10);
  assert.ok(![...select.options].some(o=>o.value==='9'));
  assert.ok([...select.options].some(o=>o.value==='10'));
  gas.value='no';gas.dispatchEvent(new win.Event('change'));await pause(10);
  assert.ok(![...select.options].some(o=>o.value==='17'));
  stage.value='design';stage.dispatchEvent(new win.Event('change'));await pause(10);
  assert.ok(![...select.options].some(o=>o.value==='12'));
  doc.querySelector('#projectOnly').checked=false;
  doc.querySelector('#projectOnly').dispatchEvent(new win.Event('change'));await pause(10);
  assert.equal(chapterButtons().length,24);
  doc.querySelector('#resetProject').click();await pause(10);
  assert.equal(structure.value,'');
  assert.equal(chapterButtons().length,24);
  select.value='';select.dispatchEvent(new win.Event('change'));await pause(10);
  assert.equal(topicGroups().length,24,'returning to all chapters restores all topics');

  // Clause numbering is the native hierarchy from the regulation, not a PDF page segment.
  select.value='5';select.dispatchEvent(new win.Event('change'));await pause(10);
  q.value='وزن اسمی هر کیسه سیمان';go.click();await pause(15);
  const cementResult=[...doc.querySelectorAll('#results .result')]
    .find(card=>card.textContent.includes('5-2-6-1-4'));
  assert.ok(cementResult,'actual clause 5-2-6-1-4 must be searchable');
  assert.ok(cementResult.textContent.includes('50'),'50kg cement clause must retain its number');
  assert.ok(cementResult.textContent.includes('کیلوگرم'),'cement clause must retain its unit');
  assert.ok(!/صفحه\\s+\\d+\\s*[-،]\\s*بخش/.test(cementResult.textContent),
    'a PDF page/part cannot masquerade as a regulatory clause');
  for(const n of [1,2,3,6,11,12,18,20,22,24]){
    doc.querySelector('#chapterGrid .chapter:nth-child('+n+')').click();await pause(10);
    const items=[...doc.querySelectorAll('#results .result')];
    assert.ok(items.length>0,'chapter '+n+' must remain readable');
    assert.ok(items.every(el=>!/^صفحه\\s+\\d+\\s*[-،]\\s*بخش/m.test(el.textContent)),
      'no arbitrary part title on chapter '+n);
  }

    // Cross-references, addenda and page images are still functional.
  doc.querySelector('#chapterGrid .chapter:nth-child(4)').click();await pause(10);
  assert.ok(doc.querySelector('.addenda-notice a'),'chapter 4 should have appendix link');
  assert.ok(!doc.querySelector('.addenda-notice').textContent.includes('نمایه نشده'),
    'no database-index status must leak into the interface');
  doc.querySelector('#chapterGrid .chapter:nth-child(19)').click();await pause(10);
  assert.ok(doc.querySelectorAll('#results .result').length>0);
  const visualManifest=path.join(root,'data/visuals/index.json');
  if(fs.existsSync(visualManifest)){
    const visuals=JSON.parse(fs.readFileSync(visualManifest,'utf8'));
    for(const n of [6,11,18,20]){
      doc.querySelector('#chapterGrid .chapter:nth-child('+n+')').click();await pause(10);
      const pages=visuals.chapters?.[String(n)]?.pages||[];
      if(!pages.length)continue;
      assert.equal(doc.querySelector('#visualGallery').hidden,false);
      assert.equal(doc.querySelectorAll('#visualItems img').length,pages.length);
    }
  }
  assert.equal(doc.querySelectorAll('#results .unverified').length,0,'no certification banners in search results');
  assert.equal(errors.length,0,'no JS errors: '+errors.join(', '));
  console.log('UI smoke PASS: uncapped topic groups, 24 chapters, residential/chapter filters, no DB status');
  win.close();
}
main().catch(e=>{console.error(e);process.exitCode=1;win.close()});
