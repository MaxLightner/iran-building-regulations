'use strict';
const $ = id => document.getElementById(id);
const state = { catalog: [], approved: [], demo: [], mode: 'knowledge', project: null, draft: null, cache: new Map(), knowledge: null, ontology: null, knowledgeCache: new Map(), applicability: null, applicabilityCache: new Map(), topicFilter: '', requestToken: 0 };
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
  if (state.mode === 'knowledge') return renderKnowledgeTopics();
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
  if(state.mode === 'knowledge') return renderKnowledgeSearch();
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
  $('approved-stat').textContent=state.knowledge ? state.knowledge.records : state.approved.length;
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
  document.querySelectorAll('[data-query]').forEach(button=>button.addEventListener('click',()=>{
    $('query').value=button.dataset.query||button.textContent.trim();
    $('topic-filter').value='';state.topicFilter='';
    renderSearch();$('search-panel').scrollIntoView({behavior:'smooth'});
  }));
  $('chapter-filter').addEventListener('change',()=>{if(state.mode==='knowledge'||state.mode==='draft'){renderTopics();if($('query').value.trim() || $('topic-filter').value) renderSearch();}});
  $('topic-filter').addEventListener('change',()=>{state.topicFilter=$('topic-filter').value;if(state.mode==='knowledge'||state.mode==='draft')renderSearch();});
}
async function init(){
  try{
    const [catalog,approved,demo,options,draft,knowledge,ontology,applicability]=await Promise.all([
      load('catalog'),load('records'),load('demo'),
      fetch(new URL('./options.json',document.baseURI)).then(r=>{if(!r.ok)throw Error('گزینه‌های فرم دریافت نشد');return r.json();}),
      fetch(new URL('./data/draft/manifest.json',document.baseURI)).then(r=>{if(!r.ok)throw Error('ایندکس متنی PDF دریافت نشد');return r.json();}),
      fetch(new URL('./data/knowledge/manifest.json',document.baseURI)).then(r=>{if(!r.ok)throw Error('ایندکس دانش دریافت نشد');return r.json();}),
      fetch(new URL('./data/knowledge/ontology.json',document.baseURI)).then(r=>{if(!r.ok)throw Error('واژگان موضوعی دریافت نشد');return r.json();}),
      fetch(new URL('./data/applicability/manifest.json',document.baseURI)).then(r=>{if(!r.ok)throw Error('ایندکس ارتباط پروژه دریافت نشد');return r.json();})
    ]);
    if(catalog.status!=='unverified_catalog_only'||approved.status!=='approved_only'||demo.status!=='demonstration_not_regulations')
      throw Error('ساختار مجموعه داده نامعتبر است');
    if(draft.status !== 'unverified_pdf_transcription') throw Error('ایندکس OCR نامعتبر است');
    if(knowledge.status !== 'unverified_structured_knowledge') throw Error('ایندکس دانش نامعتبر است');
    if(applicability.status !== 'project_relevance_signals_not_legal_applicability') throw Error('ایندکس ارتباط پروژه نامعتبر است');
    state.catalog=catalog.items;state.approved=approved.items;state.demo=demo.items;state.draft=draft;state.knowledge=knowledge;state.ontology=ontology;state.applicability=applicability;
    $('approved-stat').textContent=knowledge.records;
    const selected=$('chapter-filter');
    for(const chapter of draft.documents)selected.append(new Option(chapter.title,chapter.id));
    const allTopics=new Set();for(const chapter of draft.documents)for(const name of Object.keys(chapter.topics))allTopics.add(name);
    for(const t of Object.values(ontology.topics||{}))allTopics.add(t.label);
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



const PROJECT_TOPIC_WEIGHTS={
  'بتن‌آرمه':{concrete_steel:22,loads:14,geotech:12,materials:7},
  'فولادی':{concrete_steel:22,loads:14,geotech:12,fire:5},
  'بنایی':{masonry_industrial:24,loads:12,geotech:9,materials:8},
  'سایر / نامشخص':{loads:5,geotech:5},
  'مسکونی':{occupancy:15,stairs:12,fire:12,parking:9,light:8,energy:7},
  'اداری':{occupancy:14,fire:13,stairs:10,parking:9,elevator:7,energy:7},
  'تجاری':{occupancy:14,fire:16,parking:12,stairs:10,signage:8,elevator:7},
  'آموزشی':{occupancy:14,fire:17,stairs:12,signage:7,light:7},
  'درمانی':{occupancy:14,fire:18,stairs:12,elevator:11,installations:10,electrical:8},
  'صنعتی':{occupancy:10,fire:15,worksite:8,electrical:9,mechanical:9,materials:8},
  'مختلط':{occupancy:18,fire:15,stairs:10,parking:10},
  'مطالعات اولیه':{admin:12,geotech:10,general:8},
  'طراحی':{dimensions:12,fire:10,loads:10,occupancy:9,installations:8},
  'اجرا':{worksite:18,materials:12,concrete_steel:8,masonry_industrial:8,admin:5},
  'بهره‌برداری':{maintenance:20,fire:9,elevator:8,installations:8,energy:7}
};
function projectTopicBias(topicId,project=state.project){
  if(!project)return 0;
  let score=0;
  for(const key of [project.structure,project.use,project.stage]){
    const table=PROJECT_TOPIC_WEIGHTS[key];if(table)score+=table[topicId]||0;
  }
  if(project.basements>0){
    if(topicId==='geotech')score+=12;
    if(topicId==='parking')score+=8;
    if(topicId==='fire')score+=5;
  }
  if(project.floors>=5){
    if(topicId==='elevator')score+=9;
    if(topicId==='stairs')score+=7;
    if(topicId==='fire')score+=8;
  }
  if(project.area>=3000){
    if(topicId==='fire')score+=5;
    if(topicId==='parking')score+=5;
    if(topicId==='installations')score+=4;
  }
  return score;
}
function conditionMatches(condition,project){
  if(!project||!condition)return null;
  const actual=Number(project[condition.field]);
  if(!Number.isFinite(actual))return null;
  const v=Number(condition.value);
  if(condition.operator==='gt')return actual>v;
  if(condition.operator==='gte')return actual>=v;
  if(condition.operator==='lt')return actual<v;
  if(condition.operator==='lte')return actual<=v;
  if(condition.operator==='eq')return actual===v;
  return null;
}
function projectFit(rule,record,project=state.project){
  if(!project||!rule)return {score:0,level:'general',reasons:[]};
  let score=0;const reasons=[];
  for(const tid of record.topics||[])score+=projectTopicBias(tid,project);
  const m=rule.mentions||{};
  if(m.uses?.includes(project.use)){score+=20;reasons.push('کاربری '+project.use+' در متن این ضابطه دیده شده');}
  else if(m.uses?.length)score-=2;
  if(m.structures?.includes(project.structure)){score+=20;reasons.push('نوع سازه '+project.structure+' با متن ضابطه همخوان است');}
  else if(m.structures?.length)score-=2;
  if(m.stages?.includes(project.stage)){score+=12;reasons.push('برای مرحله «'+project.stage+'» مرتبط تشخیص داده شده');}
  if(m.basement&&project.basements>0){score+=10;reasons.push('ضابطه به زیرزمین مرتبط است');}
  if(m.parking&&project.basements>0){score+=4;}
  for(const c of rule.numeric_conditions||[]){
    const match=conditionMatches(c,project);
    if(match===true){score+=10;reasons.push('شرط عددی استخراج‌شده با مشخصات پروژه همخوان است: '+c.evidence);}
    else if(match===false)score-=2;
  }
  const level=score>=34?'high':score>=16?'medium':'general';
  return {score,level,reasons:reasons.slice(0,4)};
}
async function applicabilityDocument(docId){
  if(state.applicabilityCache.has(docId))return state.applicabilityCache.get(docId);
  const response=await fetch(new URL('./data/applicability/'+docId+'.json',document.baseURI));
  if(!response.ok)throw Error('سیگنال‌های پروژه '+docId+' دریافت نشد');
  const result=await response.json();
  if(result.status!=='project_relevance_signals_not_legal_applicability')throw Error('وضعیت سیگنال پروژه نامعتبر است');
  const map=new Map(result.records.map(r=>[r.id,r]));
  state.applicabilityCache.set(docId,map);return map;
}

const KNOWLEDGE_STATUS='ساختاریافته از متن PDF؛ اعتبار نسخه‌ها هنوز تأیید رسمی نشده است.';
function topicIdByLabel(label){
  if(!state.ontology)return null;
  for(const [id,t] of Object.entries(state.ontology.topics||{}))if(t.label===label)return id;
  return null;
}
const queryTopicCache=new Map();
function resolveQueryTopics(query){
  const q=fold(query);
  if(queryTopicCache.has(q))return queryTopicCache.get(q);
  const direct=new Set();
  if(!q||!state.ontology)return {direct,related:new Set()};
  for(const [id,t] of Object.entries(state.ontology.topics||{})){
    const terms=[t.label,...(t.aliases||[])].map(fold);
    if(terms.some(a=>a && (q.includes(a)||a.includes(q))))direct.add(id);
  }
  const related=new Set();
  for(const id of direct)for(const r of state.ontology.topics[id]?.related||[])if(!direct.has(r))related.add(r);
  const resolved={direct,related};queryTopicCache.set(q,resolved);return resolved;
}
async function knowledgeDocument(d){
  if(state.knowledgeCache.has(d.id))return state.knowledgeCache.get(d.id);
  const response=await fetch(new URL('./data/knowledge/'+d.id+'.json',document.baseURI));
  if(!response.ok)throw Error('داده ساختاریافته '+d.title+' دریافت نشد');
  const result=await response.json();
  if(result.status!=='unverified_structured_knowledge')throw Error('وضعیت دانش '+d.id+' نامعتبر است');
  state.knowledgeCache.set(d.id,result);
  return result;
}
async function renderKnowledgeTopics(){
  const target=$('topics'), chapter=$('chapter-filter').value;
  $('mode-note').className='caution';
  $('mode-note').textContent=KNOWLEDGE_STATUS+' موضوعات مرتبط به هم متصل‌اند؛ بازکردن PDF برای جست‌وجوی عادی لازم نیست.';
  if(!state.knowledge||!state.ontology)return setEmpty(target,'لایه دانش آماده نشده است.');
  let counts=new Map();
  if(!chapter){
    for(const [id,t] of Object.entries(state.ontology.topics||{}))counts.set(id,t.record_count||0);
  }else{
    const d=state.knowledge.documents.find(x=>x.id===chapter);
    if(d){
      const doc=await knowledgeDocument(d);
      for(const r of doc.records)for(const id of r.topics)counts.set(id,(counts.get(id)||0)+1);
    }
  }
  const rows=[...counts].filter(x=>x[1]>0)
    .map(([id,n])=>[id,n,projectTopicBias(id)])
    .sort((a,b)=>b[2]-a[2] || b[1]-a[1]);
  $('topics-count').textContent=rows.length+' موضوع'+(state.project?' · مرتب‌شده برای پروژه':'');
  target.replaceChildren();
  for(const [id,n,bias] of rows){
    const t=state.ontology.topics[id]; if(!t)continue;
    const btn=el('button',null,'topic-button');btn.type='button';
    const meta=(state.project&&bias>0?'اولویت پروژه · ':'')+n+' رکورد';
    btn.append(el('strong',t.label),el('span',meta,'count'));
    btn.addEventListener('click',()=>{
      $('topic-filter').value=t.label;state.topicFilter=t.label;
      $('search-panel').scrollIntoView({behavior:'smooth'});renderKnowledgeSearch();
    });
    target.append(btn);
  }
  if(!rows.length)setEmpty(target,'برای این مبحث هنوز موضوع ساختاریافته‌ای وجود ندارد.');
}

function searchQualityAdjustment(record){
  const title=fold(record.title),text=fold(record.text);
  let score=0;
  if(record.locator)score+=3;
  if(record.facts?.length)score+=Math.min(4,record.facts.length);
  if(record.conditions?.length)score+=2;
  if(text.length<50)score-=14;
  if(/^(فهرست|مقدمه|واژه نامه|واژه‌نامه|منابع|پیشگفتار)/.test(title))score-=16;
  const flags=record.source?.quality_flags||[];
  if(flags.length)score-=Math.min(8,flags.length*2);
  return score;
}
function dedupeRanked(matches,limit=28){
  const seen=new Set(),out=[];
  for(const item of matches){
    const key=fold(item.r.text);
    if(key.length<28)continue;
    if(seen.has(key))continue;
    seen.add(key);out.push(item);
    if(out.length>=limit)break;
  }
  return out;
}
function resultTitle(record){
  const title=String(record.title||'').trim();
  const folded=fold(title);
  if(!title || folded.length<4 || /^(فهرست|مقدمه)$/.test(folded))
    return (record.locator ? 'بند '+record.locator+' — ' : '')+(record.topic_labels?.[0]||'ضابطه ساختمان');
  return title.length>150 ? title.slice(0,147)+'…' : title;
}
function resultSummary(record){
  const summary=String(record.summary||'').trim();
  if(summary && fold(summary)!==fold(record.title))return summary;
  const text=' '.concat(record.text||'').trim().replace(/\s+/g,' ');
  return text.length>360?text.slice(0,357)+'…':text;
}
function knowledgeScore(record,query,selectedTopicId,projectScore=0){
  const terms=fold(query).split(' ').filter(Boolean);
  const resolved=resolveQueryTopics(query);
  if(selectedTopicId && !record.topics.includes(selectedTopicId))return null;
  const title=fold(record.title),summary=fold(record.summary),
    topics=fold((record.topic_labels||[]).join(' ')),
    text=record.search_text||fold(record.text);
  const direct=[...resolved.direct].some(id=>record.topics.includes(id));
  const related=[...resolved.related].some(id=>record.topics.includes(id));
  const termHits=terms.filter(t=>title.includes(t)||summary.includes(t)||topics.includes(t)||text.includes(t));
  if(terms.length && termHits.length===0 && !direct && !related)return null;
  let score=(direct?35:0)+(related?7:0)+(selectedTopicId?20:0);
  for(const t of terms)score+=(title.includes(t)?14:0)+(topics.includes(t)?12:0)+(summary.includes(t)?6:0)+(text.includes(t)?3:0);
  score+=searchQualityAdjustment(record);
  score+=projectScore;
  return score;
}
function knowledgeResultCard(record,fit={score:0,level:'general',reasons:[]}){
  const card=el('article',null,'record'), top=el('div',null,'record-top');
  top.append(el('span','از متن مقررات','tag'),el('span',record.locator||('صفحه '+record.source.pdf_page),'muted'));
  card.append(top,el('h3',resultTitle(record)),el('p',resultSummary(record),'summary'));
  if(state.project){
    const box=el('div',null,'project-fit project-fit-'+fit.level);
    const labels={high:'مرتبط‌تر با پروژه',medium:'مرتبط با پروژه',general:'ارتباط عمومی / نیازمند بررسی'};
    box.append(el('strong',labels[fit.level]||labels.general));
    if(fit.reasons?.length){
      const ul=el('ul');
      for(const reason of fit.reasons)ul.append(el('li',reason));
      box.append(ul);
    }else box.append(el('span','این نتیجه بر اساس موضوع کلی رتبه‌بندی شده و شرط اختصاصی واضحی از متن استخراج نشده است.','muted'));
    card.append(box);
  }
  const topicRow=el('div',null,'knowledge-topics');
  for(const label of record.topic_labels||[])topicRow.append(el('span',label,'knowledge-chip'));
  card.append(topicRow);
  if(record.facts?.length){
    const factors=el('div',null,'factors');
    for(const fact of record.facts.slice(0,5)){
      const box=el('div',null,'factor');
      box.append(el('strong',fact.value+' '+fact.unit),el('span',fact.context,'muted'));
      factors.append(box);
    }
    card.append(factors);
  }
  if(record.conditions?.length){
    const conditions=el('div',null,'knowledge-conditions');
    conditions.append(el('strong','شروط و قیود تشخیص‌داده‌شده'));
    const ul=el('ul');
    for(const c of record.conditions.slice(0,4))ul.append(el('li',c));
    conditions.append(ul);card.append(conditions);
  }
  if(record.related_topics?.length){
    const labels=record.related_topics.map(id=>state.ontology?.topics?.[id]?.label).filter(Boolean);
    if(labels.length)card.append(el('p','موضوعات مرتبط: '+labels.join('، '),'metadata'));
  }
  const details=el('details',null,'record-details');
  details.append(el('summary','متن کامل و منبع'));
  details.append(el('p',record.text,'full-text'));
  const meta=el('p',record.document_title+' | صفحه PDF '+record.source.pdf_page+' | '+KNOWLEDGE_STATUS,'metadata');
  details.append(meta);
  try{
    const u=new URL(record.source.pdf_url);
    if(u.hostname==='raw.githubusercontent.com'){
      u.hash='page='+record.source.pdf_page;
      const a=el('a','مشاهده منبع PDF');a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';
      details.append(a);
    }
  }catch(_e){}
  card.append(details);return card;
}
async function renderKnowledgeSearch(){
  const token=++state.requestToken,target=$('search-results');
  const query=$('query').value.trim(),chapter=$('chapter-filter').value,topicLabel=$('topic-filter').value;
  const selectedTopicId=topicIdByLabel(topicLabel);
  if(fold(query).length<2&&!selectedTopicId)return setEmpty(target,'یک عبارت یا موضوع برای جست‌وجو وارد کنید.');
  if(!state.knowledge)return setEmpty(target,'لایه دانش بارگذاری نشده است.');
  target.replaceChildren(el('p','در حال جست‌وجو در دانش مقررات…','empty'));
  try{
    const docs=state.knowledge.documents.filter(d=>!chapter||d.id===chapter);
    const loaded=await Promise.all(docs.map(async d=>({
      doc:await knowledgeDocument(d),
      rules:await applicabilityDocument(d.id)
    })));
    if(token!==state.requestToken)return;
    const groups=[];
    for(const item of loaded){
      const doc=item.doc;
      const matches=dedupeRanked(doc.records.map(r=>{
        const fit=projectFit(item.rules.get(r.id),r);
        return {r,fit,score:knowledgeScore(r,query,selectedTopicId,fit.score)};
      }).filter(x=>x.score!==null).sort((a,b)=>b.score-a.score),28);
      if(matches.length)groups.push({doc,matches});
    }
    groups.sort((a,b)=>b.matches[0].score-a.matches[0].score);
    if(!groups.length)return setEmpty(target,'نتیجه ساختاریافته‌ای پیدا نشد. عبارت دیگری را امتحان کنید.');
    const total=groups.reduce((n,g)=>n+g.matches.length,0);
    target.replaceChildren(el('p',total+' نتیجه ساختاریافته در '+groups.length+' مبحث','result-count'));
    for(const [groupNo,g] of groups.entries()){
      const section=el('details',null,'search-group'),heading=el('summary');
      heading.textContent=g.doc.document.title+' — '+g.matches.length+' نتیجه';section.append(heading);
      const list=el('div'),more=el('button','نمایش نتایج بیشتر','secondary');more.type='button';let shown=0;
      const append=()=>{for(const x of g.matches.slice(shown,shown+5))list.append(knowledgeResultCard(x.r,x.fit));shown+=5;more.hidden=shown>=g.matches.length;};
      section.append(list,more);more.addEventListener('click',append);
      section.addEventListener('toggle',()=>{if(section.open&&!shown)append();});
      if(groupNo===0){section.open=true;append();}
      target.append(section);
    }
  }catch(err){
    if(token!==state.requestToken)return;
    setEmpty(target,'خطا در جست‌وجوی دانش: '+err.message);
  }
}

init();
