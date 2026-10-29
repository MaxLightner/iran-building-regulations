'use strict';
const $ = id => document.getElementById(id);
const state = { catalog: [], approved: [], demo: [], mode: 'draft', project: null, draft: null, cache: new Map(), topicFilter: '', requestToken: 0 };
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
  if (state.mode === 'draft') return renderDraftTopics();
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
  if(state.mode === 'draft') return renderDraftSearch();
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
    ++state.requestToken;state.mode=event.target.value;state.topicFilter='';$('topic-filter').value='';renderTopics();
    if($('query').value.trim())renderSearch();else setEmpty($('search-results'),'عبارت یا موضوع جست‌وجو را انتخاب کنید.');
  });
  $('search').addEventListener('submit',renderSearch);
  $('chapter-filter').addEventListener('change',()=>{if(state.mode==='draft'){renderDraftTopics();if($('query').value.trim() || $('topic-filter').value) renderSearch();}});
  $('topic-filter').addEventListener('change',()=>{state.topicFilter=$('topic-filter').value;if(state.mode==='draft')renderSearch();});
}
async function init(){
  try{
    const [catalog,approved,demo,options,draft]=await Promise.all([
      load('catalog'),load('records'),load('demo'),
      fetch(new URL('./options.json',document.baseURI)).then(r=>{if(!r.ok)throw Error('گزینه‌های فرم دریافت نشد');return r.json();}),
      fetch(new URL('./data/draft/manifest.json',document.baseURI)).then(r=>{if(!r.ok)throw Error('ایندکس متنی PDF دریافت نشد');return r.json();})
    ]);
    if(catalog.status!=='unverified_catalog_only'||approved.status!=='approved_only'||demo.status!=='demonstration_not_regulations')
      throw Error('ساختار مجموعه داده نامعتبر است');
    if(draft.status !== 'unverified_pdf_transcription') throw Error('ایندکس OCR نامعتبر است');
    state.catalog=catalog.items;state.approved=approved.items;state.demo=demo.items;state.draft=draft;
    $('approved-stat').textContent=draft.indexed_pages;
    const selected=$('chapter-filter');
    for(const chapter of draft.documents)selected.append(new Option(chapter.title,chapter.id));
    const allTopics=new Set();for(const chapter of draft.documents)for(const name of Object.keys(chapter.topics))allTopics.add(name);
    for(const name of [...allTopics].sort((a,b)=>a.localeCompare(b,'fa')))$('topic-filter').append(new Option(name,name));
    initializeForm(options);renderCatalog();renderTopics();
    setEmpty($('search-results'),'یک عبارت برای جست‌وجو وارد کنید.');
  }catch(err){
    $('error').hidden=false;
    $('error').textContent='بارگذاری سایت ناقص است: '+err.message;
    setEmpty($('topics'),'داده‌ها دریافت نشدند.');
    setEmpty($('search-results'),'داده‌ها دریافت نشدند.');
  }
}

const DRAFT_STATUS = 'استخراج اولیه از PDF؛ اعداد، جداول و نسخه باید با صفحه اصلی بررسی شوند.';
function renderDraftTopics() {
  const target=$('topics'), counts=new Map(), chapter=$('chapter-filter').value;
  $('mode-note').className='caution';
  $('mode-note').textContent=DRAFT_STATUS+' این فهرست موضوعات است، نه صدها بند جداگانه.';
  if(!state.draft)return setEmpty(target,'ایندکس PDF در حال آماده‌سازی است.');
  for(const d of state.draft.documents) {
    if(chapter && d.id!==chapter)continue;
    for(const [topic,pages] of Object.entries(d.topics))
      counts.set(topic,(counts.get(topic)||0)+pages);
  }
  $('topics-count').textContent=counts.size+' موضوع';
  target.replaceChildren();
  for(const [topic,n] of [...counts].sort((a,b)=>b[1]-a[1])) {
    const btn=el('button',null,'topic-button');
    btn.type='button';
    btn.append(el('strong',topic),el('span',n+' صفحه مرتبط','count'));
    btn.addEventListener('click',()=>{
      state.topicFilter=topic;$('topic-filter').value=topic;
      $('search-panel').scrollIntoView({behavior:'smooth'});
      renderDraftSearch();
    });
    target.append(btn);
  }
  if(!counts.size)setEmpty(target,'در این مجموعه موضوعی پیدا نشد.');
}
async function draftDocument(d) {
  if(state.cache.has(d.id))return state.cache.get(d.id);
  const url=new URL('./data/draft/'+d.id+'.json',document.baseURI);
  const response=await fetch(url);
  if(!response.ok)throw Error('ایندکس '+d.title+' دریافت نشد');
  const result=await response.json();
  if(result.status!=='unverified_pdf_transcription' || result.document_id!==d.id)
    throw Error('وضعیت ایندکس '+d.id+' نامعتبر است');
  state.cache.set(d.id,result);
  return result;
}
function draftResultCard(match) {
  const page=match.page, d=match.document;
  const card=el('article',null,'record');
  const top=el('div',null,'record-top');
  top.append(el('span','متن PDF · تأییدنشده','tag tag-demo'),
    el('span','صفحه PDF: '+page.pdf_page,'muted'));
  card.append(top,el('h3',d.title+' — صفحه '+page.pdf_page));
  const query=fold($('query').value);
  const normalized=page.search_text||fold(page.text);
  const firstTerm=query.split(' ').find(Boolean)||'';
  const found=firstTerm ? normalized.indexOf(firstTerm) : -1;
  const sampleStart=found>130?Math.max(0,found-110):0;
  const sample=page.text.slice(sampleStart,sampleStart+380);
  card.append(el('p',(sampleStart?'…':'')+sample+(page.text.length>sampleStart+380?'…':''),'summary'));
  const actions=el('div',null,'source-links');
  try {
    const u=new URL(d.pdf_url);
    if(u.hostname==='raw.githubusercontent.com' && u.pathname.startsWith('/MaxLightner/iran-building-regulations/main/sources/pdfs/')) {
      u.hash='page='+page.pdf_page;
      const a=el('a','مشاهده صفحه در PDF اصلی');
      a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';
      actions.append(a);
    }
  }catch(_e){}
  card.append(actions);
  const details=el('details',null,'record-details');
  details.append(el('summary','نمایش متن کامل این صفحه'));
  details.append(el('p',page.text||'در این صفحه متن قابل استخراج شناسایی نشد. PDF اصلی را مشاهده کنید.','full-text'));
  details.append(el('p',DRAFT_STATUS,'caution'));
  card.append(details);
  return card;
}
function draftScores(pages,query,topic) {
  const terms=fold(query).split(' ').filter(Boolean);
  return pages.flatMap(page=>{
    if(topic && !page.topics.includes(topic))return [];
    const text=page.search_text||fold(page.text), extras=fold(page.topics.join(' '));
    if(terms.length && !terms.every(t=>text.includes(t)||extras.includes(t)))return [];
    let score=0;
    for(const t of terms)score+=(text.includes(t)?2:0)+(extras.includes(t)?3:0);
    if(topic)score+=2;
    return [{page,score}];
  }).sort((a,b)=>b.score-a.score || a.page.pdf_page-b.page.pdf_page);
}
async function renderDraftSearch(){
  const token=++state.requestToken, target=$('search-results');
  const query=$('query').value.trim(), topic=$('topic-filter').value, chapter=$('chapter-filter').value;
  if(fold(query).length<2 && !topic)return setEmpty(target,'عبارت حداقل دو نویسه‌ای وارد کنید یا یک موضوع انتخاب کنید.');
  if(!state.draft)return setEmpty(target,'فهرست داده‌های PDF بارگذاری نشده است.');
  target.replaceChildren(el('p','در حال جست‌وجو در PDFها…','empty'));
  try{
    const docs=state.draft.documents.filter(d=>(!chapter || d.id===chapter) && (!topic || (d.topics && d.topics[topic])));
    const loaded=await Promise.all(docs.map(d=>draftDocument(d)));
    if(token!==state.requestToken)return;
    const result=[];
    for(const doc of loaded){
      const metadata=docs.find(d=>d.id===doc.document_id);
      const matches=draftScores(doc.pages,query,topic);
      if(matches.length)result.push({document:doc,metadata,matches});
    }
    result.sort((a,b)=>b.matches[0].score-a.matches[0].score);
    if(!result.length)return setEmpty(target,'نتیجه‌ای پیدا نشد. عبارت دیگری را امتحان کنید یا فیلترها را بردارید.');
    target.replaceChildren(el('p',result.reduce((n,g)=>n+g.matches.length,0)+' صفحه مرتبط در '+result.length+' سند','result-count'));
    for(const [groupNumber,group] of result.entries()){
      const section=el('details',null,'search-group');
      const heading=el('summary');
      heading.textContent=group.document.title+' — '+group.matches.length+' صفحه مرتبط';
      section.append(heading);
      const list=el('div'), button=el('button','نمایش صفحات بیشتر','secondary');
      button.type='button';
      let shown=0;
      const append=()=>{
        for(const item of group.matches.slice(shown,shown+5))
          list.append(draftResultCard({page:item.page,document:group.document}));
        shown+=5;
        button.hidden=shown>=group.matches.length;
      };
      section.append(list,button);
      button.addEventListener('click',append);
      section.addEventListener('toggle',()=>{if(section.open && !shown)append();});
      if(groupNumber===0){
        section.open=true;
        append();
      }
      target.append(section);
    }
  }catch(err){
    if(token!==state.requestToken)return;
    setEmpty(target,'خطا در جست‌وجو: '+err.message);
  }
}

init();
