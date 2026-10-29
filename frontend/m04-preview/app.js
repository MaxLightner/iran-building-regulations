'use strict';
let DATA;
const $=id=>document.getElementById(id);
const faMap={'ي':'ی','ك':'ک','ۀ':'ه','ة':'ه'};
function norm(s){return String(s||'').normalize('NFKC').replace(/[يكۀة]/g,c=>faMap[c]||c).replace(/\u200c/g,' ').replace(/[۰-۹]/g,d=>'۰۱۲۳۴۵۶۷۸۹'.indexOf(d)).replace(/[^\p{L}\p{N}]+/gu,' ').replace(/\s+/g,' ').trim().toLowerCase()}
const stop=new Set(['حداقل','حداکثر','چقدر','چیست','است','برای','در','از','به','و','یا','یک','چه','مقدار']);
function terms(q){return norm(q).split(' ').filter(x=>x.length>1&&!stop.has(x))}
function score(r,q){
  const ts=terms(q), hayTitle=norm(r.title), hayAns=norm(r.answer), hayQ=norm((r.q||[]).join(' ')), hayTopic=norm(r.topic), hayCond=norm((r.conditions||[]).join(' '));
  let s=0,hit=0;
  for(const t of ts){
    let local=0;
    if(hayTitle.includes(t))local+=10;
    if(hayQ.includes(t))local+=12;
    if(hayTopic.includes(t))local+=8;
    if(hayAns.includes(t))local+=5;
    if(hayCond.includes(t))local+=2;
    if(local){hit++;s+=local}
  }
  if(!hit)return -1;
  s+=(hit/Math.max(1,ts.length))*12;
  const nq=norm(q);
  for(const phrase of r.q||[])if(nq.includes(norm(phrase)))s+=20;
  return s;
}
function search(q){
  return DATA.rules.map(r=>({r,s:score(r,q)})).filter(x=>x.s>=0).sort((a,b)=>b.s-a.s).slice(0,3).map(x=>x.r);
}
function el(tag,text,cls){const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n}
function card(r,i){
  const a=el('article',null,'result'+(i===0?' primary':''));
  const top=el('div',null,'topline');top.append(el('span',i===0?'پاسخ اصلی':'پاسخ مرتبط','rank'),el('span','بند '+r.ref,'ref'));a.append(top);
  a.append(el('h2',r.title));
  a.append(el('div',r.answer,'answerbox'));
  if(r.conditions?.length){a.append(el('div','شرایط / نکات','label'));const ul=el('ul',null,'conditions');r.conditions.forEach(x=>ul.append(el('li',x)));a.append(ul)}
  a.append(el('span',r.topic,'topic'));
  return a;
}
function run(){
  const q=$('q').value.trim(),res=$('results');res.replaceChildren();
  if(q.length<2){res.append(el('div','سؤال را بنویس.','empty'));return}
  const rows=search(q);
  $('status').textContent=rows.length?'جواب مستقیم':'نتیجه پیدا نشد';
  $('count').textContent=rows.length?rows.length+' نتیجه از مجموعه تستی مبحث ۴':'';
  if(!rows.length){res.append(el('div','این سؤال هنوز در مجموعه تستی پوشش داده نشده.','empty'));return}
  rows.forEach((r,i)=>res.append(card(r,i)));
}
async function init(){
  const r=await fetch('./rules.json',{cache:'no-store'});DATA=await r.json();
  $('sourceLink').href=DATA.meta.source_url;
  $('status').textContent='آماده';
  $('count').textContent=DATA.rules.length+' ضابطه منتخب';
  $('go').onclick=run;
  $('q').onkeydown=e=>{if(e.key==='Enter')run()};
  document.querySelectorAll('[data-q]').forEach(b=>b.onclick=()=>{$('q').value=b.dataset.q;run()});
  $('q').value='عرض راه پله 7 طبقه';run();
}
init().catch(e=>{$('status').textContent='خطا در بارگذاری'});
