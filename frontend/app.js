'use strict';
let CATALOG=[],COVERAGE={},INDEX=[],CURATED=[];
const $=id=>document.getElementById(id);
const fa={'ي':'ی','ك':'ک','ۀ':'ه','ة':'ه'};
const stop=new Set(['حداقل','حداکثر','چقدر','چیست','است','برای','در','از','به','و','یا','یک','چه','مقدار','ضابطه','ساختمان']);
function norm(s){return String(s||'').normalize('NFKC').replace(/[يكۀة]/g,c=>fa[c]||c).replace(/\u200c/g,' ').replace(/[۰-۹]/g,d=>'۰۱۲۳۴۵۶۷۸۹'.indexOf(d)).replace(/[^\p{L}\p{N}]+/gu,' ').replace(/\s+/g,' ').trim().toLowerCase()}
function terms(q){return norm(q).split(' ').filter(x=>x.length>1&&!stop.has(x))}
function nref(s){return String(s||'').replace(/[۰-۹]/g,d=>'۰۱۲۳۴۵۶۷۸۹'.indexOf(d)).replace(/\s+/g,'').replace(/–|—/g,'-')}
function chapterMeta(n){return CATALOG.find(x=>x.number===Number(n))||{number:n,title:'مبحث '+n,edition:''}}

function score(r,q,chapter){
  if(chapter && Number(r.chapter)!==Number(chapter))return -1;
  const raw=String(q||'').trim();
  if(raw.startsWith('ref:')){
    const parts=raw.slice(4).split(':'); const targetChapter=parts.length>1?Number(parts[0]):null; const target=nref(parts.at(-1));
    if(targetChapter&&Number(r.chapter)!==targetChapter)return -1;
    const rr=nref(r.locator);
    if(rr===target)return 2000+(r.curated?200:0);
    if(rr&&rr.startsWith(target+'-'))return 1700+(r.curated?200:0);
    return -1;
  }
  const ts=terms(q); if(!ts.length)return -1;
  const title=norm(r.title),ans=norm(r.answer),loc=norm(r.locator),
        refs=norm((r.cross_refs||[]).map(x=>x.label+' '+(x.ref||'')).join(' '));
  let s=r.curated?90:0,hit=0;
  for(const t of ts){
    let p=0;
    if(title.includes(t))p+=18;
    if(ans.includes(t))p+=8;
    if(refs.includes(t))p+=4;
    if(loc.includes(t))p+=3;
    if(p){hit++;s+=p}
  }
  if(!hit)return -1;
  s+=(hit/ts.length)*20;
  if(r.normative)s+=8;
  if(r.numbers?.length)s+=5;
  return s;
}
function search(q,chapter){
  return INDEX.concat(CURATED).map(r=>({r,s:score(r,q,chapter)})).filter(x=>x.s>=0)
    .sort((a,b)=>b.s-a.s).filter((x,i,a)=>i===a.findIndex(y=>nref(y.r.locator)===nref(x.r.locator)&&Number(y.r.chapter)===Number(x.r.chapter)&&norm(y.r.answer).slice(0,180)===norm(x.r.answer).slice(0,180)))
    .slice(0,5).map(x=>x.r);
}
function el(tag,text,cls){const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n}
function jump(ch,ref){$('chapter').value=String(ch);$('q').value='ref:'+ch+':'+nref(ref);run();setTimeout(()=>$('results').scrollIntoView({behavior:'smooth',block:'start'}),20)}
function card(r,i){
  const m=chapterMeta(r.chapter),a=el('article',null,'result'+(i===0?' primary':''));
  const top=el('div',null,'topline');
  top.append(el('span',i===0?'پاسخ اصلی':'پاسخ مرتبط','rank'),el('span','مبحث '+r.chapter+(r.locator?' · بند '+r.locator:'')+(m.edition?' · ویرایش '+m.edition:''),'source'));a.append(top);
  const h=el('h2',r.title||('بند '+(r.locator||'')));if(r.curated)h.append(el('span',' پاسخ منتخب','curated'));a.append(h);
  a.append(el('div',r.answer,'answer'));
  if(r.numbers?.length){const f=el('div',null,'facts');r.numbers.slice(0,6).forEach(x=>{const b=el('div',null,'fact');b.append(el('strong',x.value+' '+x.unit));f.append(b)});a.append(f)}
  if(r.cross_refs?.length){a.append(el('div','ارجاعات مرتبط','label'));const refs=el('div',null,'refs');r.cross_refs.slice(0,8).forEach(x=>{const ch=x.chapter||r.chapter;const link=el('a',x.label||('بند '+x.ref));link.href='#';link.onclick=e=>{e.preventDefault();if(x.ref)jump(ch,x.ref);else{$('chapter').value=String(ch);$('q').value='';renderChapter(ch)}};refs.append(link)});a.append(refs)}
  if(r.source_url){const link=el('a','مشاهده مرجع','source-link');link.href=r.source_url;link.target='_blank';link.rel='noopener';a.append(link)}
  return a;
}
function run(){
  const q=$('q').value.trim(),ch=$('chapter').value,res=$('results');res.replaceChildren();
  if(q.length<2){res.append(el('div','عبارت جست‌وجو را وارد کن.','empty'));return}
  const rows=search(q,ch);$('status').textContent=rows.length?'نتایج مرتبط':'نتیجه‌ای پیدا نشد';$('coverage').textContent=rows.length?rows.length+' نتیجه برتر':'';
  if(!rows.length){res.append(el('div','برای این عبارت نتیجه قابل استفاده‌ای پیدا نشد.','empty'));return}
  rows.forEach((r,i)=>res.append(card(r,i)));
}
function renderChapter(n){
  $('chapter').value=String(n);const m=chapterMeta(n);$('q').value=m.title;run()
}
function renderCatalog(){
  const sel=$('chapter'),grid=$('chapterGrid');grid.replaceChildren();
  CATALOG.forEach(c=>{
    const o=document.createElement('option');o.value=c.number;o.textContent='مبحث '+c.number+' — '+c.title;sel.append(o);
    const b=el('button',null,'chapter'+(c.status==='ready'?'':' missing'));b.type='button';
    b.append(el('strong','مبحث '+c.number+' — '+c.title),el('span',c.status==='ready'?(c.record_count+' بند/رکورد'):'در انتظار تکمیل منبع'));b.onclick=()=>renderChapter(c.number);grid.append(b);
  });
  $('chapterCount').textContent=CATALOG.length+' مبحث';
}
async function init(){
  const [a,b,c,d]=await Promise.all([
    fetch('./data/catalog.json',{cache:'no-store'}).then(r=>r.json()),
    fetch('./data/coverage.json',{cache:'no-store'}).then(r=>r.json()),
    fetch('./data/search-index.json',{cache:'no-store'}).then(r=>r.json()),
    fetch('./m04-preview/rules.json',{cache:'no-store'}).then(r=>r.json()).catch(()=>({rules:[]}))
  ]);
  CATALOG=a;COVERAGE=b;INDEX=c;
  CURATED=(d.rules||[]).map((r,i)=>({id:'curated-m04-'+i,chapter:4,locator:r.ref,title:r.title,answer:r.answer,cross_refs:(r.cross_refs||[]).map(x=>({chapter:4,ref:x.ref,label:x.label})),numbers:[],normative:true,source_url:d.meta?.source_url,curated:true}));
  renderCatalog();
  $('status').textContent='آماده';
  $('coverage').textContent=COVERAGE.chapters_ready+'/24 مبحث · '+COVERAGE.records_total+' بند/رکورد';
  $('go').onclick=run;$('q').onkeydown=e=>{if(e.key==='Enter')run()};$('chapter').onchange=run;
  document.querySelectorAll('[data-q]').forEach(b=>b.onclick=()=>{$('q').value=b.dataset.q;run()});
  $('q').value='ارتفاع جان پناه';run();
}
init().catch(e=>{$('status').textContent='خطا در بارگذاری داده';console.error(e)});