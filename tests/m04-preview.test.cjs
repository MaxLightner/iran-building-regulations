const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const app=require(path.join(root,'frontend/m04-preview/app.js'));
const data=JSON.parse(fs.readFileSync(path.join(root,'frontend/m04-preview/data/rules.json'),'utf8'));
app.setData(data);
const cases=[
 ['راه پله','stairs'],
 ['پارکینگ زیرزمین','parking'],
 ['رمپ پارکینگ','ramp'],
 ['نورگیری اتاق','light'],
 ['جان پناه','guard'],
 ['ارتفاع اتاق','height'],
 ['بالکن','balcony'],
 ['دسترسی معلول','access']
];
let pass=0;
for(const [q,topic] of cases){
  const rows=app.search(q,5);
  const ok=rows.some(r=>(r.topics||[]).includes(topic));
  if(ok)pass++;
  console.log(ok?'PASS':'FAIL',q,'=>',rows.slice(0,3).map(r=>r.locator+':'+r.topic_labels.join('/')).join(' | '));
}
console.log('M04 preview benchmark',pass+'/'+cases.length);
assert.ok(pass>=7,'M04 preview must pass at least 7/8 user-facing queries');
console.log('PASS: M04 rule preview is ready for user evaluation');
