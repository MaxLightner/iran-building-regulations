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
  await pause(100);
  const doc=win.document;
  assert.equal(doc.querySelectorAll('#chapterGrid .chapter').length,24,'all chapter controls should render');
  assert.ok(doc.querySelectorAll('#results .result').length>=1,'initial M04 results should load');
  const q=doc.querySelector('#q'),go=doc.querySelector('#go');
  q.value='عرض آشپزخانه';go.click();await pause(10);
  assert.ok(doc.querySelectorAll('#results .result').length>=1,'search click must return a result');
  doc.querySelector('[data-q="عرض راه پله"]').click();await pause(10);
  assert.ok(doc.querySelectorAll('#results .result').length>=1,'quick-search controls should work');
  assert.equal(q.value,'عرض راه پله');
  doc.querySelector('#chapterGrid .chapter:nth-child(4)').click();await pause(10);
  assert.equal(doc.querySelector('#chapter').value,'4','chapter selection must update');
  assert.ok(doc.querySelectorAll('#results .result').length>=1,'chapter 4 should contain results');
  doc.querySelector('#chapterGrid .chapter:nth-child(2)').click();await pause(10);
  const missing=doc.querySelectorAll('#results .empty').length>0;
  if(!missing){
    assert.ok(doc.querySelectorAll('#results .result').length>0,'chapter should show indexed page excerpts');
    assert.ok(doc.querySelectorAll('#results .unverified').length>0,'page-level fallback must be labeled unverified');
  }
  // Chapter-aware quick suggestions must replace, not silently reset, the chapter.
  const chapterSelect=doc.querySelector('#chapter');
  chapterSelect.value='10';
  chapterSelect.dispatchEvent(new win.Event('change'));
  await pause(10);
  assert.ok(doc.querySelector('[data-q="اتصال فولادی"]'),'steel chapter suggestions should appear');
  doc.querySelector('[data-q="اتصال فولادی"]').click();await pause(10);
  assert.equal(chapterSelect.value,'10','suggestions must preserve chapter context');
  assert.equal(q.value,'اتصال فولادی');
  // Project-based filtering must affect both chapter choices and search results.
  const structure=doc.querySelector('#pStructure'),gas=doc.querySelector('#pGas'),stage=doc.querySelector('#pStage');
  structure.value='steel';structure.dispatchEvent(new win.Event('change'));await pause(10);
  assert.ok(![...chapterSelect.options].some(o=>o.value==='9'),'concrete structural chapter excluded for steel project');
  assert.ok([...chapterSelect.options].some(o=>o.value==='10'),'steel structural chapter stays visible');
  gas.value='no';gas.dispatchEvent(new win.Event('change'));await pause(10);
  assert.ok(![...chapterSelect.options].some(o=>o.value==='17'),'gas chapter excluded when no gas');
  stage.value='design';stage.dispatchEvent(new win.Event('change'));await pause(10);
  assert.ok(![...chapterSelect.options].some(o=>o.value==='12'),'site safety not in design-phase shortlist');
  doc.querySelector('#projectOnly').checked=false;
  doc.querySelector('#projectOnly').dispatchEvent(new win.Event('change'));await pause(10);
  assert.equal(doc.querySelectorAll('#chapterGrid .chapter').length,24,'show all must restore all 24 chapters');
  doc.querySelector('#resetProject').click();await pause(10);
  assert.equal(structure.value,'','reset clears the profile');
  assert.equal(doc.querySelectorAll('#chapterGrid .chapter').length,24,'reset restores complete catalog');
    // Mandatory appendix is available, but never masquerades as a clause.
  doc.querySelector('#chapterGrid .chapter:nth-child(4)').click();await pause(10);
  assert.ok(doc.querySelector('.addenda-notice a'),'chapter 4 should expose its mandatory appendix');
  assert.ok(doc.querySelector('.addenda-notice').textContent.includes('نمایه نشده'),
    'appendix should be clearly marked as not indexed');
    // A previously indexed higher-quality source must survive upstream outages.
  doc.querySelector('#chapterGrid .chapter:nth-child(19)').click();await pause(10);
  assert.ok(doc.querySelectorAll('#results .result').length>0,'chapter 19 is searchable');
  assert.ok(doc.querySelector('#chapterGrid .chapter:nth-child(19)').textContent.includes('87'),
    'structured fallback preserves 87 records when current upstream source regresses');
    const visualManifest=path.join(root,'data/visuals/index.json');
  if(fs.existsSync(visualManifest)){
    const visuals=JSON.parse(fs.readFileSync(visualManifest,'utf8'));
    for(const n of [6,11,18,20]){
      const pages=visuals.chapters?.[String(n)]?.pages||[];
      if(!pages.length)continue;
      doc.querySelector('#chapterGrid .chapter:nth-child('+n+')').click();
      await pause(10);
      assert.equal(doc.querySelector('#visualGallery').hidden,false,'visual gallery should open for m'+n);
      assert.equal(doc.querySelectorAll('#visualItems img').length,pages.length,
        'all selected page previews must render for m'+n);
    }
  }
    // Regression: uploaded PDFs must use embedded text, NEVER the old OCR layer.
  for(const [n,edition] of [[6,'1392'],[11,'1392'],[18,'1390'],[20,'1396']]){
    doc.querySelector('#chapterGrid .chapter:nth-child('+n+')').click();await pause(10);
    const notice=doc.querySelector('#sourceProvenance');
    assert.ok(!notice.hidden && notice.textContent.includes('بدون OCR'),'user PDF should show direct text source m'+n);
    assert.equal(doc.querySelector('#chapter').value,String(n));
    assert.ok(doc.querySelector('#chapterGrid .chapter:nth-child('+n+')').textContent.includes('ویرایش '+edition));
    assert.ok(doc.querySelectorAll('#results .result').length>0,'direct PDF text results should display for m'+n);
    assert.ok(!doc.querySelector('#results').textContent.includes('خوانش OCR'),'m'+n+' cannot show legacy OCR output');
  }
  doc.querySelector('#chapterGrid .chapter:nth-child(18)').click();await pause(10);
  assert.ok(doc.querySelector('#sourceProvenance').textContent.includes('نگاشت حروف'),'warn on corrupt embedded font encoding');
    // A searchable chapter must never masquerade as fully verified.
  const auditRows=[...doc.querySelectorAll('#completenessRows .audit-item')];
  assert.equal(auditRows.length,24,'completeness audit must enumerate all 24 chapters');
  assert.ok(doc.querySelector('#completenessScore').textContent.includes('۰ از ۲۴')||
    doc.querySelector('#completenessScore').textContent.includes('0 از ۲۴'),
    'no chapter can be fully certified without source evidence');
  const auditFile=JSON.parse(fs.readFileSync(path.join(root,'data/completeness-audit.json'),'utf8'));
  const m07Risk=(auditFile.chapters[6].warnings||[]).includes('text_encoding_corruption_suspected');
  assert.equal(auditRows[6].textContent.includes('خرابی جدی کدگذاری حروف'),m07Risk,
    'chapter 7 encoding risk must match the actual corpus health');
  assert.ok(auditRows[13].textContent.includes('تکرار زیاد شناسه بند'),
    'chapter 14 repeated locator risk must be visible');
  assert.ok(auditRows[17].textContent.includes('۳')||
    auditRows[17].textContent.includes('3'),
    'chapter 18 searchable page gap must be shown');
    assert.equal(errors.length,0,'no JS errors: '+errors.join(', '));
  console.log('UI smoke PASS: 24 chapters, search, quick-search, curated answers and missing-state');
  win.close();
}
main().catch(e=>{console.error(e);process.exitCode=1;win.close()});
