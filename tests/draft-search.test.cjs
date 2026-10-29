/* Minimal behavior checks against the actual browser search functions, no dependencies. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'frontend/app.js'),'utf8').replace(/init\(\);\s*$/,'');
const context=vm.createContext({console,URL});
vm.runInContext(source+'\n globalThis.__searchTest={fold,draftScores};',context);
const {fold,draftScores}=context.__searchTest;
assert.equal(fold('راه‌پله'), 'راه پله');
assert.equal(fold('ساختمان  كاربري'), 'ساختمان کاربری');
const pages=[
 {pdf_page:1,text:'عرض راه پله ۱ متر',search_text:fold('عرض راه پله ۱ متر'),topics:['راه‌پله و دسترسی']},
 {pdf_page:2,text:'مصالح ساختمانی',search_text:fold('مصالح ساختمانی'),topics:['پوشش و مصالح']},
 {pdf_page:3,text:'راه خروج حریق',search_text:fold('راه خروج حریق'),topics:['حریق و ایمنی']},
];
assert.equal(draftScores(pages,'عرض پله','').length,1);
assert.equal(draftScores(pages,'','حریق و ایمنی').length,1);
assert.equal(draftScores(pages,'عرض پله','حریق و ایمنی').length,0);
assert.equal(draftScores(pages,'مصالح','').length,1);
const indexDir=path.join(root,'frontend/data/draft');
const manifest=JSON.parse(fs.readFileSync(path.join(indexDir,'manifest.json'),'utf8'));
assert.ok(manifest.documents.length>=2);
for(const doc of manifest.documents){
  const index=JSON.parse(fs.readFileSync(path.join(indexDir,doc.id+'.json'),'utf8'));
  assert.equal(index.pages.length,doc.pages);
  const sample=index.pages.find(p=>p.search_text.length>=12);
  assert.ok(sample,'no searchable text in '+doc.id);
  const term=sample.search_text.match(/[\u0621-\u06ff]{4,}/);
  if(term){
    assert.ok(draftScores(index.pages,term[0],'').some(x=>x.page.pdf_page===sample.pdf_page),
      'search does not find its own source page '+doc.id);
  }
}
console.log('PASS: actual browser search core returns relevant PDF pages and honors filters');
