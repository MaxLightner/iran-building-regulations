'use strict';
const $ = id => document.getElementById(id);
let CATALOG = [], INDEX = [], CURATED = [], COVERAGE = {};
const SYNONYMS = {
  'پله':['راه پله','پلکان','راه‌پله'], 'جانپناه':['جان پناه','حفاظ'],
  'پارکینگ':['توقفگاه','خودرو'], 'بتن':['بتن آرمه'], 'روشنایی':['نور','نورگیری'],
  'آتش':['حریق'], 'برق':['الکتریکی','تاسیسات برقی'], 'آسانسور':['بالابر']
};
const STOP = new Set(['حداقل','حداکثر','چقدر','چیست','است','برای','در','از','به','و','یا','یک','چه','مقدار','ضابطه','ساختمان','های','باید','شود','مقررات']);
function norm(s) {
  return String(s ?? '').normalize('NFKC')
    .replace(/[يى]/g,'ی').replace(/ك/g,'ک').replace(/\u200c/g,' ')
    .replace(/[۰-۹]/g,d=>'۰۱۲۳۴۵۶۷۸۹'.indexOf(d))
    .replace(/[٠-٩]/g,d=>'٠١٢٣٤٥٦٧٨٩'.indexOf(d))
    .replace(/[^\p{L}\p{N}]+/gu,' ').replace(/\s+/g,' ').trim().toLowerCase();
}
function terms(q) { return [...new Set(norm(q).split(' ').filter(x=>x.length>1&&!STOP.has(x)))]; }
function el(tag, text, cls) {
  const n=document.createElement(tag);
  if(text!==undefined&&text!==null)n.textContent=String(text);
  if(cls)n.className=cls;
  return n;
}
function chapterMeta(n) {
  return CATALOG.find(c=>Number(c.number)===Number(n))||{number:Number(n),title:'مبحث '+n,edition:'',status:'pending'};
}
function refnorm(s){return String(s||'').replace(/[۰-۹]/g,d=>'۰۱۲۳۴۵۶۷۸۹'.indexOf(d)).replace(/\s+/g,'').replace(/[–—]/g,'-')}
function sourceRecords() { return CURATED.concat(INDEX); }
function score(r,q,chapter) {
  if(chapter && Number(chapter)!==Number(r.chapter))return -1;
  if(q.startsWith('ref:')){
    const chunks=q.slice(4).split(':');const ref=refnorm(chunks.pop());
    if(chunks.length&&Number(chunks[0])!==Number(r.chapter))return -1;
    const loc=refnorm(r.locator);
    if(loc===ref)return 9000+(r.curated?100:0);
    return loc.startsWith(ref+'-')?7000+(r.curated?100:0):-1;
  }
  const tt=terms(q);
  if(!tt.length)return -1;
  const title=norm(r.title), body=norm(r.answer), topic=norm(r.topic),
    keys=norm((r.keywords||[]).join(' ')+' '+(r.q||[]).join(' '));
  let matched=0;let value=r.curated?75:0;
  for(const t of tt){
    let hit=0;
    if(title.includes(t))hit+=20;
    if(keys.includes(t))hit+=28;
    if(topic.includes(t))hit+=14;
    if(body.includes(t))hit+=6;
    if(!hit){
      const syn=SYNONYMS[t]||[];
      if(syn.some(s=>title.includes(norm(s))||keys.includes(norm(s))))hit=10;
    }
    if(hit){matched++;value+=hit}
  }
  if(!matched)return -1;
  value+=Math.round(matched/tt.length*25);
  const phrase=norm(q);
  if(title.includes(phrase)||keys.includes(phrase))value+=50;
  if(!r.curated&&!r.locator)value-=20;
  return value;
}
function search(q,ch){
  const rows=sourceRecords().map(r=>({r,score:score(r,q,ch)}))
    .filter(x=>x.score>=0).sort((a,b)=>b.score-a.score);
  const seen=new Set(),out=[];
  for(const {r} of rows){
    const key=Number(r.chapter)+':'+refnorm(r.locator)+':'+norm(r.answer).slice(0,75);
    if(seen.has(key))continue;
    seen.add(key);out.push(r);
    if(out.length===5)break;
  }
  return out;
}
function goToRef(ch,ref){
  $('chapter').value=String(ch);
  $('q').value='ref:'+ch+':'+refnorm(ref);
  render();
  $('results').scrollIntoView({behavior:'smooth',block:'start'});
}
function appendRefLinks(parent, r) {
  const references=r.cross_refs||[];
  if(!references.length)return;
  const holder=el('div',null,'refs');
  for(const x of references.slice(0,8)){
    const ch=Number(x.chapter||r.chapter),label=x.label||('بند '+x.ref);
    const a=el('a',label);
    a.href=x.ref?'#m'+ch+'-'+refnorm(x.ref):'#chapter-'+ch;
    a.addEventListener('click',e=>{
      e.preventDefault();
      if(x.ref)goToRef(ch,x.ref);else showChapter(ch);
    });
    holder.append(a);
  }
  parent.append(el('div','ارجاعات مرتبط','label'),holder);
}
function resultCard(r,i){
  const m=chapterMeta(r.chapter);
  const card=el('article',null,'result'+(i===0?' primary':''));
  const top=el('div',null,'topline');
  top.append(el('span',r.curated?'پاسخ منتخب':'متن مرتبط مقررات','rank'),
    el('span','مبحث '+r.chapter+(r.locator?' · بند '+r.locator:'')+(m.edition?' · '+m.edition:''),'source'));
  card.append(top);
  card.append(el('h2',r.title||('بند '+(r.locator||''))));
  const answer=String(r.answer||'').trim();
  card.append(el('div',answer||'متن این بخش هنوز آماده نشده است.','answer'));
  if(r.conditions?.length){
    card.append(el('div','شرایط و نکات','label'));
    const ul=el('ul');
    for(const c of r.conditions)ul.append(el('li',c));
    card.append(ul);
  }
  if(r.numbers?.length) {
    const facts=el('div',null,'facts');
    for(const n of r.numbers.slice(0,5)){
      const item=el('span',null,'fact');item.append(el('strong',n.value+' '+n.unit));facts.append(item);
    }
    card.append(facts);
  }
  appendRefLinks(card,r);
  if(r.source_url){
    const link=el('a','مشاهده مرجع','source-link');link.href=r.source_url;
    link.target='_blank';link.rel='noopener noreferrer';card.append(link);
  }
  return card;
}
function render(){
  const q=$('q').value.trim(),ch=$('chapter').value,area=$('results');
  area.replaceChildren();
  if(q.length<2){
    $('status').textContent='عبارت جست‌وجو را بنویس';
    area.append(el('div','برای شروع یکی از موضوع‌های پیشنهادی را انتخاب کن.','empty'));return;
  }
  const rows=search(q,ch);
  $('status').textContent=rows.length?'نتایج جست‌وجو':'نتیجه‌ای پیدا نشد';
  $('coverage').textContent=rows.length?rows.length+' نتیجه':'';
  if(!rows.length){
    const m=ch?chapterMeta(ch):null;
    area.append(el('div',
      m&&m.status!=='ready'&&m.status!=='selected_rules'?
      'متن این مبحث هنوز وارد مجموعه جست‌وجو نشده است. سایر مباحث و نتایج آماده قابل جست‌وجو هستند.':
      'برای این عبارت هنوز نتیجه قابل استناد در داده‌های موجود نداریم. عبارت دیگری امتحان کن.',
      'empty'));
    return;
  }
  rows.forEach((r,i)=>area.append(resultCard(r,i)));
}
function showChapter(n){
  $('chapter').value=String(n);
  const matches=sourceRecords().filter(x=>Number(x.chapter)===Number(n));
  const area=$('results');area.replaceChildren();
  const m=chapterMeta(n);
  $('status').textContent='مبحث '+n+' — '+m.title;
  $('coverage').textContent=matches.length+' مورد موجود';
  if(!matches.length){
    area.append(el('div','این مبحث در فهرست قرار گرفته اما متن قابل جست‌وجوی آن هنوز آماده نیست.','empty'));
  }else{
    $('q').value='';
    matches.filter(x=>x.curated||x.normative).slice(0,5).forEach((r,i)=>area.append(resultCard(r,i)));
  }
  $('results').scrollIntoView({behavior:'smooth',block:'start'});
}
function renderCatalog(){
  const sel=$('chapter'),grid=$('chapterGrid');
  sel.replaceChildren();grid.replaceChildren();
  const all=el('option','همه مباحث');all.value='';sel.append(all);
  for(const c of CATALOG){
    const o=el('option','مبحث '+c.number+' — '+c.title);o.value=c.number;sel.append(o);
    const has=sourceRecords().some(r=>Number(r.chapter)===Number(c.number));
    const b=el('button',null,'chapter'+(has?'':' missing'));
    b.type='button';
    b.append(el('strong','مبحث '+c.number+' — '+c.title),
      el('span',has?'مشاهده '+(c.record_count||sourceRecords().filter(r=>Number(r.chapter)===Number(c.number)).length)+' مورد':'در حال تکمیل'));
    b.addEventListener('click',()=>showChapter(c.number));grid.append(b);
  }
  $('chapterCount').textContent=CATALOG.length+' مبحث';
}
async function jsonOr(url,fallback){
  try {
    const response=await fetch(url,{cache:'no-store'});
    if(!response.ok)throw Error('HTTP '+response.status);
    return await response.json();
  }catch(e){console.warn('Optional data unavailable:',url,e);return fallback;}
}
function setCurated(d){
  CURATED=(d.rules||[]).map((r,i)=>({
    id:'m04-selected-'+i,chapter:4,locator:r.ref,title:r.title,
    answer:r.answer,conditions:r.conditions||[],q:r.q||[],topic:r.topic,
    cross_refs:(r.cross_refs||[]).map(x=>({...x,chapter:4})),
    source_url:d.meta?.source_url,numbers:[],normative:true,curated:true
  }));
}
function wire(){
  $('go').addEventListener('click',render);
  $('q').addEventListener('keydown',e=>{if(e.key==='Enter')render()});
  $('chapter').addEventListener('change',render);
  document.querySelectorAll('[data-q]').forEach(b=>b.addEventListener('click',()=>{
    $('chapter').value='';$('q').value=b.dataset.q;render();
  }));
}
async function init(){
  wire();
  $('status').textContent='در حال بارگذاری نتایج…';
  const [catalog,coverage,index,curated]=await Promise.all([
    jsonOr('./data/catalog.json',[]),
    jsonOr('./data/coverage.json',{}),
    jsonOr('./data/search-index.json',[]),
    jsonOr('./m04-preview/rules.json',{rules:[]})
  ]);
  CATALOG=Array.isArray(catalog)?catalog:[];
  COVERAGE=coverage||{};
  INDEX=Array.isArray(index)?index.filter(x=>x&&x.chapter&&x.answer):[];
  setCurated(curated);
  renderCatalog();
  $('q').value='ارتفاع جان پناه';
  render();
  const withData=new Set(sourceRecords().map(r=>Number(r.chapter))).size;
  $('coverage').textContent=withData+' مبحث دارای داده · '+sourceRecords().length+' مورد';
  if(!sourceRecords().length){
    $('status').textContent='داده‌های جست‌وجو در حال تکمیل است';
  }
}
init().catch(e=>{
  console.error(e);
  $('status').textContent='اشکال در آماده‌سازی صفحه';
});
