'use strict';
let DATA;
const $=id=>document.getElementById(id);
const faMap={'ي':'ی','ك':'ک','ۀ':'ه','ة':'ه'};

function norm(s){
  return String(s||'').normalize('NFKC')
    .replace(/[يكۀة]/g,c=>faMap[c]||c)
    .replace(/\u200c/g,' ')
    .replace(/[۰-۹]/g,d=>'۰۱۲۳۴۵۶۷۸۹'.indexOf(d))
    .replace(/[^\p{L}\p{N}]+/gu,' ')
    .replace(/\s+/g,' ').trim().toLowerCase();
}

const stop=new Set(['حداقل','حداکثر','چقدر','چیست','است','برای','در','از','به','و','یا','یک','چه','مقدار']);
function terms(q){return norm(q).split(' ').filter(x=>x.length>1&&!stop.has(x))}

function normalizeRef(s){return String(s||'').replace(/[۰-۹]/g,d=>'۰۱۲۳۴۵۶۷۸۹'.indexOf(d)).replace(/\s+/g,'').replace(/–|—/g,'-')}

function score(r,q){
  const raw=String(q||'').trim();
  if(raw.startsWith('ref:')){
    const target=normalizeRef(raw.slice(4));
    const rr=normalizeRef(r.ref);
    if(rr===target)return 1000;
    if(rr.startsWith(target+'-'))return 850;
    return -1;
  }

  const ts=terms(q), hayTitle=norm(r.title), hayAns=norm(r.answer),
    hayQ=norm((r.q||[]).join(' ')), hayTopic=norm(r.topic),
    hayCond=norm((r.conditions||[]).join(' ')), hayRefs=norm((r.cross_refs||[]).map(x=>x.label+' '+x.ref).join(' '));
  let s=0,hit=0;
  for(const t of ts){
    let local=0;
    if(hayTitle.includes(t))local+=10;
    if(hayQ.includes(t))local+=12;
    if(hayTopic.includes(t))local+=8;
    if(hayAns.includes(t))local+=5;
    if(hayCond.includes(t))local+=2;
    if(hayRefs.includes(t))local+=3;
    if(local){hit++;s+=local}
  }
  if(!hit)return -1;
  s+=(hit/Math.max(1,ts.length))*12;
  const nq=norm(q);
  for(const phrase of r.q||[])if(nq.includes(norm(phrase)))s+=20;
  return s;
}

function search(q){
  return DATA.rules.map(r=>({r,s:score(r,q)}))
    .filter(x=>x.s>=0).sort((a,b)=>b.s-a.s).slice(0,3).map(x=>x.r);
}

function el(tag,text,cls){
  const n=document.createElement(tag);
  if(text!=null)n.textContent=text;
  if(cls)n.className=cls;
  return n;
}

function jumpToRef(ref){
  $('q').value='ref:'+normalizeRef(ref);
  run();
  setTimeout(()=>document.getElementById('results')?.scrollIntoView({behavior:'smooth',block:'start'}),20);
}

function appendLinkedText(parent,text){
  const src=String(text||'');
  const re=/(جدول\s*)?(4(?:\s*-\s*\d+){1,5})/g;
  let last=0,m;
  while((m=re.exec(src))){
    if(m.index>last)parent.append(document.createTextNode(src.slice(last,m.index)));
    const a=el('a',m[0],'xref-inline');
    const ref=normalizeRef(m[2]);
    a.href='#ref='+encodeURIComponent(ref);
    a.title='رفتن به ارجاع '+ref;
    a.onclick=e=>{e.preventDefault();jumpToRef(ref)};
    parent.append(a);
    last=re.lastIndex;
  }
  if(last<src.length)parent.append(document.createTextNode(src.slice(last)));
}

function linkedBlock(tag,text,cls){
  const n=el(tag,null,cls);
  appendLinkedText(n,text);
  return n;
}

function card(r,i){
  const a=el('article',null,'result'+(i===0?' primary':''));
  a.id='rule-'+r.id;
  const top=el('div',null,'topline');
  const refLink=el('a','بند '+r.ref,'ref');
  refLink.href='#ref='+encodeURIComponent(r.ref);
  refLink.onclick=e=>{e.preventDefault();jumpToRef(r.ref)};
  top.append(el('span',i===0?'پاسخ اصلی':'پاسخ مرتبط','rank'),refLink);
  a.append(top);

  a.append(el('h2',r.title));
  a.append(linkedBlock('div',r.answer,'answerbox'));

  if(r.conditions?.length){
    a.append(el('div','شرایط / نکات','label'));
    const ul=el('ul',null,'conditions');
    r.conditions.forEach(x=>{
      const li=el('li');
      appendLinkedText(li,x);
      ul.append(li);
    });
    a.append(ul);
  }

  if(r.cross_refs?.length){
    a.append(el('div','ارجاعات مرتبط','label'));
    const refs=el('div',null,'crossrefs');
    r.cross_refs.forEach(x=>{
      const link=el('a',x.label,'crossref');
      link.href='#ref='+encodeURIComponent(x.ref);
      link.onclick=e=>{e.preventDefault();jumpToRef(x.ref)};
      refs.append(link);
    });
    a.append(refs);
  }

  a.append(el('span',r.topic,'topic'));
  return a;
}

function renderCoverage(){
  const c=DATA.meta.coverage||{};
  $('coverageRules').textContent=(c.selected_rule_count||DATA.rules.length)+' ضابطه منتخب';
  $('coverageChapters').textContent=(c.source_main_chapters_observed||'?')+'/'+(c.expected_main_chapters||'?')+' فصل اصلی در منبع دیده شده';
  $('coverageClauses').textContent=c.clause_level_completeness==='pending_audit'?'ممیزی بندبه‌بند هنوز انجام نشده':'ممیزی بندها انجام شده';
  $('coverageRefs').textContent=c.cross_reference_resolution==='partial'?'ارجاعات فعلاً بخشی حل شده‌اند':'ارجاعات کامل حل شده‌اند';
}

function run(){
  const q=$('q').value.trim(),res=$('results');
  res.replaceChildren();
  if(q.length<2){res.append(el('div','سؤال را بنویس.','empty'));return}
  const rows=search(q);
  $('status').textContent=rows.length?'جواب مستقیم':'نتیجه پیدا نشد';
  $('count').textContent=rows.length?rows.length+' نتیجه از مجموعه تستی مبحث ۴':'';
  if(!rows.length){
    res.append(el('div','این مرجع/سؤال هنوز در مجموعه تستی پوشش داده نشده.','empty'));
    return;
  }
  rows.forEach((r,i)=>res.append(card(r,i)));
}

async function init(){
  const r=await fetch('./rules.json',{cache:'no-store'});
  DATA=await r.json();
  $('sourceLink').href=DATA.meta.source_url;
  $('status').textContent='آماده';
  $('count').textContent=DATA.rules.length+' ضابطه منتخب';
  renderCoverage();
  $('go').onclick=run;
  $('q').onkeydown=e=>{if(e.key==='Enter')run()};
  document.querySelectorAll('[data-q]').forEach(b=>b.onclick=()=>{$('q').value=b.dataset.q;run()});

  const hash=decodeURIComponent(location.hash||'');
  const m=hash.match(/^#ref=(.+)$/);
  $('q').value=m?'ref:'+m[1]:'عرض راه پله 7 طبقه';
  run();
}

init().catch(()=>{$('status').textContent='خطا در بارگذاری'});