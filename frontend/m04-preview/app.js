'use strict';
const $=id=>document.getElementById(id);
let DATA=null;
const fold=v=>String(v||'').normalize('NFKC').replace(/ي/g,'ی').replace(/ك/g,'ک').replace(/ى/g,'ی').replace(/\u200c/g,' ').replace(/[\u064b-\u065f\u0670]/g,'').replace(/\s+/g,' ').trim().toLowerCase();

function expandQuery(q){
  const n=fold(q),terms=new Set(n.split(' ').filter(x=>x.length>1));
  if(!DATA)return [...terms];
  for(const [key,alts] of Object.entries(DATA.synonyms||{})){
    if(n.includes(fold(key))||alts.some(a=>n.includes(fold(a)))) for(const a of alts) for(const t of fold(a).split(' ')) if(t.length>1)terms.add(t);
  }
  return [...terms];
}
function score(rule,q){
  const terms=expandQuery(q), title=fold(rule.title), statement=fold(rule.statement),
    topics=fold((rule.topic_labels||[]).join(' ')), text=fold(rule.search_text||rule.source_text);
  let s=rule.confidence*8;
  let matched=0;
  for(const t of terms){
    const hit=title.includes(t)||statement.includes(t)||topics.includes(t)||text.includes(t);
    if(hit)matched++;
    s+=(title.includes(t)?14:0)+(topics.includes(t)?12:0)+(statement.includes(t)?8:0)+(text.includes(t)?2:0);
  }
  if(!matched)return null;
  if(rule.facts?.length)s+=4;
  if(rule.locator)s+=3;
  return s+(matched/Math.max(1,terms.length))*8;
}
function search(q,limit=5){
  if(!DATA)return [];
  const ranked=DATA.rules.map(r=>({r,s:score(r,q)})).filter(x=>x.s!==null).sort((a,b)=>b.s-a.s);
  const seen=new Set(),out=[];
  for(const x of ranked){
    const key=fold(x.r.statement).slice(0,180);
    if(seen.has(key))continue;
    seen.add(key);out.push(x.r);
    if(out.length>=limit)break;
  }
  return out;
}
function node(tag,text,cls){const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n}
function card(r,i){
  const c=node('article',null,'card'),top=node('div',null,'top');
  top.append(node('span','پاسخ '+(i+1),'rank'),node('span','بند '+r.locator+' · صفحه '+r.page,'source'));
  c.append(top,node('h2',r.title),node('p',r.statement,'answer'));
  if(r.facts?.length){
    const f=node('div',null,'facts');
    for(const x of r.facts.slice(0,4)){const b=node('div',null,'fact');b.append(node('strong',x.value+' '+x.unit),node('span',x.context));f.append(b)}
    c.append(f);
  }
  if(r.conditions?.length){c.append(node('div','شرایط','label'));const ul=node('ul',null,'list');for(const x of r.conditions.slice(0,3))ul.append(node('li',x));c.append(ul)}
  if(r.exceptions?.length){c.append(node('div','استثنا / تبصره','label'));const ul=node('ul',null,'list');for(const x of r.exceptions.slice(0,2))ul.append(node('li',x));c.append(ul)}
  const topics=node('div',null,'topics');for(const x of r.topic_labels||[])topics.append(node('span',x,'topic'));c.append(topics);
  const d=node('details',null,'details');d.append(node('summary','متن منبع و PDF'),node('p',r.source_text,'raw'));
  const a=node('a','مشاهده صفحه در PDF');a.href='../data/../';a.href='https://raw.githubusercontent.com/MaxLightner/iran-building-regulations/main/sources/pdfs/reference-m04.pdf#page='+r.page;a.target='_blank';a.rel='noopener';d.append(a);c.append(d);
  return c;
}
function run(){
  const q=$('q').value.trim(),target=$('results');
  if(q.length<2){target.replaceChildren(node('p','یک سؤال یا موضوع وارد کن.','empty'));return}
  const rows=search(q,5);target.replaceChildren();
  $('status').textContent=rows.length?'۵ پاسخ برتر یا کمتر':'نتیجه‌ای پیدا نشد';
  $('meta').textContent='از '+DATA.rule_count+' Rule مبحث ۴';
  if(!rows.length){target.append(node('p','برای این عبارت Rule قابل اتکایی در Preview پیدا نشد.','empty'));return}
  rows.forEach((r,i)=>target.append(card(r,i)));
}
async function init(){
  const res=await fetch('./data/rules.json',{cache:'no-cache'});
  if(!res.ok)throw Error('Rule DB دریافت نشد');
  DATA=await res.json();
  $('status').textContent='آماده تست';
  $('meta').textContent=DATA.rule_count+' Rule از مبحث ۴';
  $('go').addEventListener('click',run);
  $('q').addEventListener('keydown',e=>{if(e.key==='Enter')run()});
  document.querySelectorAll('[data-q]').forEach(b=>b.addEventListener('click',()=>{$('q').value=b.dataset.q;run()}));
  $('q').value='راه پله';run();
}
if(typeof window!=='undefined')init().catch(e=>{$('status').textContent='خطا: '+e.message});
if(typeof module!=='undefined')module.exports={fold,expandQuery,score,search,setData:x=>DATA=x};
