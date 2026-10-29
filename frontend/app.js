'use strict';
const $ = id => document.getElementById(id);
const state = { catalog: [], approved: [], demo: [], mode: 'approved', project: null };
const el = (tag, value, className) => {
  const node = document.createElement(tag);
  if (value !== undefined && value !== null) node.textContent = String(value);
  if (className) node.className = className;
  return node;
};
const fold = value => String(value || '').normalize('NFKC')
  .replace(/ي/g,'ی').replace(/ك/g,'ک').replace(/ى/g,'ی')
  .replace(/ۀ/g,'ه').replace(/[\u064b-\u065f\u0670\u200c]/g,' ')
  .toLocaleLowerCase('fa').replace(/\s+/g,' ').trim();
async function load(name) {
  const response = await fetch(new URL('./data/' + name + '.json', document.baseURI), { cache:'no-cache' });
  if (!response.ok) throw new Error('فایل داده ' + name + ' موجود نیست (' + response.status + ')');
  return response.json();
}
function setEmpty(target, message) { target.replaceChildren(el('p',message,'empty')); }
function safeOfficialLink(label, raw) {
  if (!raw) return el('span','نشانی مرجع ثبت نشده','muted');
  try {
    const url = new URL(raw);
    if (url.protocol !== 'https:' || !['inbr.ir','www.inbr.ir'].includes(url.hostname))
      return el('span','نشانی نیازمند بررسی','muted');
    const a = el('a',label);
    a.href = url.toString(); a.target='_blank'; a.rel='noopener noreferrer';
    return a;
  } catch { return el('span','نشانی نامعتبر','muted'); }
}
function modeRecords() { return state.mode === 'demo' ? state.demo : state.approved; }
function renderRecord(r) {
  const article = el('article',null,'record');
  const top = el('div',null,'record-top'), isDemo=r.review && r.review.status === 'demo';
  top.append(el('span',isDemo ? 'متن ساختگی نمایشی' : 'بند تأییدشده',
    'tag'+(isDemo ? ' tag-demo' : '')));
  top.append(el('span',r.locator || 'بدون شماره','muted'));
  article.append(top,el('h3',r.title),el('p',r.summary || 'خلاصه ثبت نشده','summary'));
  if (Array.isArray(r.key_factors) && r.key_factors.length) {
    const factors = el('div',null,'factors');
    for(const f of r.key_factors) {
      const box=el('div',null,'factor');
      box.append(el('span',f.label,'muted'),el('strong',String(f.value)+(f.unit ? ' '+f.unit : '')));
      factors.append(box);
    }
    article.append(factors);
  }
  const details=el('details',null,'record-details');
  details.append(el('summary','متن کامل و مرجع'));
  details.append(el('p',r.original_text,'full-text'));
  if(isDemo) details.append(el('p','نمونه ساختگی، فاقد منبع و اعتبار قانونی.','caution'));
  else {
    const s=r.source||{}, v=r.version||{};
    const info='سند: '+r.document_id+' | ویرایش: '+(v.edition_label||'نامعلوم')+
      ' | صفحه PDF: '+(s.pdf_page||'نامعلوم')+
      ' | صفحه چاپی: '+(s.printed_page||'نامعلوم')+
      ' | تاریخ آخرین بررسی: '+(v.last_checked||'نامعلوم');
    details.append(el('p',info,'metadata'));
    const links=el('div',null,'source-links');
    links.append(safeOfficialLink('صفحه رسمی مبحث',s.official_page_url));
    if(s.official_pdf_url) links.append(safeOfficialLink('PDF رسمی',s.official_pdf_url));
    details.append(links);
  }
  article.append(details);
  return article;
}
function renderTopics() {
  const grouped=new Map(), target=$('topics');
  for (const r of modeRecords()) {
    const key=r.topic||'سایر';
    if(!grouped.has(key)) grouped.set(key,[]);
    grouped.get(key).push(r);
  }
  $('topics-count').textContent=grouped.size+' موضوع';
  $('mode-note').textContent=state.mode==='demo'
    ? 'حالت نمایشی: تمامی بندها ساختگی‌اند و فقط برای تست رابط هستند. هیچ الزام واقعی ارائه نمی‌شود.'
    : 'فقط بندهای تأییدشده با منبع رسمی و مجوز انتشار نمایش داده می‌شوند. PDFهای اولیه فعلاً تأیید نشده‌اند.';
  $('mode-note').className='caution'+(state.mode==='demo'?' caution-demo':'');
  if(!grouped.size) return setEmpty(target,'هنوز داده تأییدشده برای جست‌وجو وارد نشده است. حالت نمایشی را برای آزمودن مسیر کار انتخاب کنید.');
  target.replaceChildren();
  for (const [name,records] of grouped) {
    const detail=el('details',null,'topic'), heading=el('summary');
    heading.append(el('strong',name),el('span',records.length+' مورد','count'));
    detail.append(heading);
    const body=el('div',null,'topic-body');
    for(const r of records) body.append(renderRecord(r));
    detail.append(body); target.append(detail);
  }
}
function rankedSearch(query) {
  const terms=fold(query).split(' ').filter(Boolean);
  return modeRecords().map(r=>{
    const title=fold(r.title),topic=fold(r.topic);
    const tags=fold([...(r.tags||[]),...(r.aliases||[])].join(' '));
    const full=fold([r.original_text,r.summary,r.locator].join(' '));
    if(!terms.every(t=>[title,topic,tags,full].some(v=>v.includes(t)))) return null;
    const score=terms.reduce((v,t)=>v+(title.includes(t)?9:0)+(tags.includes(t)?6:0)+(topic.includes(t)?4:0)+(full.includes(t)?1:0),0);
    return {r,score};
  }).filter(Boolean).sort((a,b)=>b.score-a.score).slice(0,50).map(x=>x.r);
}
function renderSearch(event) {
  if(event) event.preventDefault();
  const query=$('query').value.trim(), target=$('search-results');
  if(fold(query).length<2) return setEmpty(target,'حداقل دو نویسه وارد کنید.');
  const matches=rankedSearch(query);
  if(!matches.length) return setEmpty(target,'برای این عبارت نتیجه‌ای در مجموعه انتخاب‌شده وجود ندارد.');
  target.replaceChildren(el('p',matches.length+' نتیجه','result-count'));
  for(const r of matches) target.append(renderRecord(r));
}
function renderCatalog() {
  const target=$('source-list');
  target.replaceChildren();
  $('catalog-stat').textContent=state.catalog.length;
  $('approved-stat').textContent=state.approved.length;
  $('catalog-count').textContent=state.catalog.length+' مبحث';
  for(const item of state.catalog) {
    const row=el('div',null,'catalog-item');
    row.append(el('span',String(item.number).padStart(2,'0'),'catalog-number'));
    const body=el('div');
    body.append(el('strong',item.title),el('p','اعتبار نسخه: بررسی نشده','muted'));
    body.append(safeOfficialLink('صفحه رسمی',item.official_page_url));
    row.append(body);target.append(row);
  }
}
function setStep(step) {
  $('part1').hidden=step!==1;
  $('part2').hidden=step!==2;
  for(let i=1;i<=3;i++){
    const entry=$('step'+i);entry.removeAttribute('aria-current');
    if(i===step)entry.setAttribute('aria-current','step');
  }
  if(step===3){$('results').hidden=false;$('results').focus();}
  else{
    $('results').hidden=true;
    ($('part'+step).querySelector('select')||$('part'+step).querySelector('input')).focus();
  }
}
function initializeForm(options) {
  for(const [key,values] of Object.entries(options)){
    const select=document.querySelector('select[name="'+key+'"]');
    if(!select)continue;
    select.replaceChildren(new Option('انتخاب کنید',''));
    for(const value of values)select.append(new Option(value,value));
  }
  $('next').addEventListener('click',()=>{if([...$('part1').querySelectorAll('select')].every(x=>x.reportValidity()))setStep(2);});
  $('back').addEventListener('click',()=>setStep(1));
  $('edit-project').addEventListener('click',()=>{setStep(1);$('wizard').scrollIntoView({behavior:'smooth'});});
  $('area').addEventListener('input',()=>{if($('area').validity.valid)$('area-range').value=$('area').value;});
  $('area-range').addEventListener('input',()=>{$('area').value=$('area-range').value;});
  document.querySelectorAll('[data-delta]').forEach(button=>button.addEventListener('click',()=>{
    const input=$(button.dataset.target),step=Number(button.dataset.delta);
    input.value=Math.max(Number(input.min),Math.min(Number(input.max),Number(input.value)+step));
  }));
  $('project').addEventListener('submit',event=>{
    event.preventDefault();
    if(!event.currentTarget.reportValidity())return;
    const p=Object.fromEntries(new FormData(event.currentTarget));
    for(const k of ['area','floors','basements'])p[k]=Number(p[k]);
    state.project=p;
    $('project-summary').textContent=p.city+' • '+p.use+' • '+p.structure+' • '+p.area+
      ' مترمربع • '+p.floors+' طبقه روی زمین • '+p.basements+' زیرزمین • '+p.stage;
    setStep(3);renderTopics();$('results').scrollIntoView({behavior:'smooth'});
  });
  $('mode').addEventListener('change',event=>{
    state.mode=event.target.value;renderTopics();
    if($('query').value.trim())renderSearch();else $('search-results').replaceChildren();
  });
  $('search').addEventListener('submit',renderSearch);
}
async function init(){
  try{
    const [catalog,approved,demo,options]=await Promise.all([
      load('catalog'),load('records'),load('demo'),
      fetch(new URL('./options.json',document.baseURI)).then(r=>{if(!r.ok)throw Error('گزینه‌های فرم دریافت نشد');return r.json();})
    ]);
    if(catalog.status!=='unverified_catalog_only'||approved.status!=='approved_only'||demo.status!=='demonstration_not_regulations')
      throw Error('ساختار مجموعه داده نامعتبر است');
    state.catalog=catalog.items;state.approved=approved.items;state.demo=demo.items;
    initializeForm(options);renderCatalog();renderTopics();
    setEmpty($('search-results'),'یک عبارت برای جست‌وجو وارد کنید.');
  }catch(err){
    $('error').hidden=false;
    $('error').textContent='بارگذاری سایت ناقص است: '+err.message;
    setEmpty($('topics'),'داده‌ها دریافت نشدند.');
    setEmpty($('search-results'),'داده‌ها دریافت نشدند.');
  }
}
init();
