'use strict';
const $ = id => document.getElementById(id);
let CATALOG = [], INDEX = [], CURATED = [], COVERAGE = {}, ADDENDA = [];
const SYNONYMS = {
  'پله':['راه پله','پلکان','راه‌پله'], 'جانپناه':['جان پناه','حفاظ'],
  'پارکینگ':['توقفگاه','خودرو'], 'بتن':['بتن آرمه'], 'روشنایی':['نور','نورگیری'],
  'آتش':['حریق'], 'برق':['الکتریکی','تاسیسات برقی'], 'آسانسور':['بالابر']
};
const QUICK_BY_CHAPTER = {
  1:['تعریف ساختمان','تعریف طبقه','تعریف تصرف'],
  2:['وظایف مهندس ناظر','مسئولیت مجری','پروانه ساختمان'],
  3:['مسیر خروج حریق','عرض خروج اضطراری','مقاومت در برابر آتش'],
  4:['ارتفاع جان پناه','عرض راه پله','نورگیری اتاق','عرض آشپزخانه','ارتفاع پارکینگ'],
  5:['مصالح ساختمانی','استاندارد مصالح','آزمایش مصالح'],
  6:['بار زنده','بار باد','بار برف','ترکیب بارها'],
  7:['مطالعات ژئوتکنیک','ظرفیت باربری خاک','طراحی پی'],
  8:['دیوار باربر بنایی','کلاف بندی','ارتفاع ساختمان بنایی'],
  9:['پوشش بتن','میلگرد گذاری','وصله میلگرد','مقاومت بتن'],
  10:['اتصال فولادی','جوش و پیچ','بادبند','ستون فولادی'],
  11:['ساخت صنعتی','قطعات پیش ساخته','اتصالات صنعتی'],
  12:['حفاظت کارگاه','ایمنی گودبرداری','داربست'],
  13:['ارتینگ','برق اضطراری','تابلو برق','حفاظت الکتریکی'],
  14:['تهویه مطبوع','دودکش','موتورخانه','تهویه پارکینگ'],
  15:['ابعاد آسانسور','چاه آسانسور','ظرفیت کابین'],
  16:['لوله کشی آب','فاضلاب','شیب لوله','تهویه فاضلاب'],
  17:['لوله کشی گاز','دودکش گاز','انشعاب گاز'],
  18:['عایق صوتی','صدای کوبه ای','صدای هوابرد'],
  19:['عایق حرارتی','پوسته ساختمان','مصرف انرژی'],
  20:['علائم خروج','تابلوهای ایمنی','علائم کارگاه'],
  21:['پدافند غیرعامل','حفاظت ساختمان','الزامات پدافندی'],
  22:['بازرسی دوره ای','نگهداری ساختمان','تعمیرات'],
  23:['تعداد پارکینگ','دسترسی خودرو','شیب رمپ','تردد خودرو'],
  24:['انطباق شهری','ضوابط شهرسازی','معابر']
};
const QUICK_GENERAL=['ارتفاع جان پناه','عرض راه پله','بار زنده','مقاومت در برابر حریق','پارکینگ و دسترسی خودرو','عایق حرارتی'];
const PROJECT_INPUTS=['pUse','pStructure','pStage','pFloors','pElevator','pGas','pCity'];
function saveProfile(){
  try {
    const record={};
    for(const id of PROJECT_INPUTS)record[id]=$(id).value;
    record.projectOnly=$('projectOnly').checked;
    localStorage.setItem('building-regulations-profile-v1',JSON.stringify(record));
  } catch(e){console.warn('Profile persistence unavailable:',e)}
}
function restoreProfile(){
  try {
    const data=JSON.parse(localStorage.getItem('building-regulations-profile-v1')||'null');
    if(!data||typeof data!=='object')return;
    for(const id of PROJECT_INPUTS){
      if(typeof data[id]!=='string')continue;
      const input=$(id);
      if(input.tagName==='SELECT' && ![...input.options].some(o=>o.value===data[id]))continue;
      input.value=data[id];
    }
    if(typeof data.projectOnly==='boolean')$('projectOnly').checked=data.projectOnly;
  } catch(e){console.warn('Profile restore unavailable:',e)}
}
function projectProfile(){
  const p={};
  for(const key of PROJECT_INPUTS)p[key]=($(key).value||'').trim();
  p.pFloors=p.pFloors?Number(p.pFloors):null;
  p.active=PROJECT_INPUTS.some(key=>key==='pFloors'?Number.isFinite(p.pFloors)&&p.pFloors>0:!!p[key]);
  return p;
}
function chapterRelevant(n,p=projectProfile()){
  if(!p.active)return true;
  n=Number(n);
  if(p.pStructure==='concrete'&&(n===8||n===10))return false;
  if(p.pStructure==='steel'&&(n===8||n===9))return false;
  if(p.pStructure==='masonry'&&(n===9||n===10))return false;
  if(p.pElevator==='no'&&n===15)return false;
  if(p.pGas==='no'&&n===17)return false;
  if(['design','permit'].includes(p.pStage)&&(n===12||n===22))return false;
  if(p.pStage==='operation'&&n===12)return false;
  return true;
}
function restrictToProject(){return $('projectOnly').checked && projectProfile().active;}
function renderQuick(){
  const area=$('quick'),chapter=Number($('chapter').value),suggestions=QUICK_BY_CHAPTER[chapter]||QUICK_GENERAL;
  area.replaceChildren();
  for(const q of suggestions){
    const b=el('button',q);b.type='button';b.dataset.q=q;
    b.addEventListener('click',()=>{$('q').value=q;render()});
    area.append(b);
  }
}
function updateProjectNote(){
  const p=projectProfile(),all=CATALOG.length,kept=CATALOG.filter(c=>chapterRelevant(c.number,p)).length;
  const note=$('projectNote');
  note.textContent=p.active
    ? 'پروفایل فعال: '+kept+' مبحث از '+all+' مبحث در گروه پیشنهادی قرار دارند. '+(p.pCity?'شهر '+p.pCity+' انتخاب شده، اما ضوابط شهرداری هنوز متصل نیست. ':'')+'کاربری و تعداد طبقات فعلاً فقط ثبت می‌شوند و هنوز به محاسبات دقیق شمول بندها متصل نیستند. فهرست پیشنهادی به معنای عدم شمول قانونی سایر مباحث نیست.'
    : 'برای محدودکردن نتایج مشخصات پروژه را وارد کن. این فیلتر جایگزین کنترل حقوقی و ضوابط شهرداری نیست.';
}
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
  if(restrictToProject()&&!chapterRelevant(r.chapter))return -1;
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
    if(out.length===20)break;
  }
  return out;
}
function goToRef(ch,ref){
  if(!chapterRelevant(ch))$('projectOnly').checked=false;
  $('chapter').value=String(ch);
  renderQuick();
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
  parent.append(el('div','ارجاعات ماشینی (نیازمند تطبیق)','label'),holder);
}
function resultCard(r,i){
  const m=chapterMeta(r.chapter);
  const card=el('article',null,'result'+(i===0?' primary':''));
  const top=el('div',null,'topline');
  top.append(el('span',r.curated?'پاسخ منتخب':r.kind==='ocr_page'?'خوانش ماشینی تصویر؛ تأییدنشده':r.kind==='page_extract'?'متن صفحه؛ بدون بند تأییدشده':'متن استخراجی؛ نیازمند تطبیق','rank'),
    el('span','مبحث '+r.chapter+(r.locator?' · بند '+r.locator:'')+(m.edition?' · ویرایش ثبت‌شده '+m.edition:''),'source'));
  card.append(top);
  card.append(el('h2',r.title||('بند '+(r.locator||''))));
  const answer=String(r.answer||'').trim();
  if(r.kind==='page_extract'||r.kind==='ocr_page'){
    const label=r.kind==='ocr_page'
      ? 'خوانش OCR فارسی از تصویر صفحه '+(r.page||'؟')+'؛ متن ممکن است دارای خطا باشد و شماره بند آن تأیید نشده است.'
      : 'متن خام استخراج‌شده از صفحه '+(r.page||'؟')+'؛ شماره بند و صحت تطبیق هنوز تأیید نشده است.';
    card.append(el('div',label,'unverified'));
  }
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
    const link=el('a','مشاهده منبع متن','source-link');link.href=r.source_url;
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
  $('coverage').textContent=rows.length?(rows.length===20?'۲۰ نتیجه اول؛ عبارت را دقیق‌تر کن':rows.length+' نتیجه'):'';
  if(!rows.length){
    const m=ch?chapterMeta(ch):null;
    area.append(el('div',
      m&&!sourceRecords().some(r=>Number(r.chapter)===Number(ch))?
      'متن این مبحث هنوز وارد مجموعه جست‌وجو نشده است. سایر مباحث و نتایج آماده قابل جست‌وجو هستند.':
      'برای این عبارت هنوز نتیجه قابل استناد در داده‌های موجود نداریم. عبارت دیگری امتحان کن.',
      'empty'));
    return;
  }
  rows.forEach((r,i)=>area.append(resultCard(r,i)));
}
function showChapter(n){
  if(restrictToProject()&&!chapterRelevant(n))$('projectOnly').checked=false;
  $('chapter').value=String(n);
  renderQuick();
  const matches=sourceRecords().filter(x=>Number(x.chapter)===Number(n));
  const area=$('results');area.replaceChildren();
  const m=chapterMeta(n);
  $('status').textContent='مبحث '+n+' — '+m.title;
  const addenda=ADDENDA.filter(x=>Number(x.chapter)===Number(n));
  if(addenda.length){
    const aside=el('aside',null,'addenda-notice');
    aside.append(el('strong','اسناد تکمیلی مرتبط (متن هنوز در جست‌وجو نمایه نشده):'));
    for(const x of addenda){
      const link=el('a',x.title+' · مشاهده PDF');
      link.href=x.source_url;
      link.target='_blank';link.rel='noopener noreferrer';aside.append(link);
    }
    area.append(aside);
  }
  $('coverage').textContent=matches.length+' مورد موجود';
  if(!matches.length){
    const message=el('div','برای این مبحث هنوز متن قابل جست‌وجوی قابل اتکا تهیه نشده است. برای یافتن متن منبع از پیوند زیر استفاده کن؛ این به معنای تأیید نسخه نیست.','empty');
    const links=(m.attempts||[]).filter(x=>x.url&&/^https:/.test(x.url));
    const link=links.find(x=>x.type==='document_source')||links[0];
    if(link){const a=el('a','مشاهده منبع کاندید');a.href=link.url;a.target='_blank';a.rel='noopener noreferrer';message.append(a);}
    area.append(message);
  }else{
    $('q').value='';
    const prioritised=matches.filter(x=>x.curated||x.normative);
    (prioritised.length?prioritised:matches).slice(0,10).forEach((r,i)=>area.append(resultCard(r,i)));
  }
  $('results').scrollIntoView({behavior:'smooth',block:'start'});
}
function renderCatalog(){
  const sel=$('chapter'),grid=$('chapterGrid'),previous=sel.value;
  sel.replaceChildren();grid.replaceChildren();
  const all=el('option','همه مباحث');all.value='';sel.append(all);
  const restricted=restrictToProject();
  let visible=0;
  for(const c of CATALOG){
    const relevant=chapterRelevant(c.number);
    if(restricted&&!relevant)continue;
    visible++;
    const o=el('option','مبحث '+c.number+' — '+c.title+(c.record_count?'':' (بدون داده)'));o.value=c.number;sel.append(o);
    const count=Number(c.record_count)||0;
    const b=el('button',null,'chapter'+(count?'':' missing'));
    b.type='button';
    b.append(el('strong','مبحث '+c.number+' — '+c.title),
      el('span',(count?count+' مورد استخراج‌شده'+(c.method==='ocr_page'?' · OCR تأییدنشده':c.method==='page_extract'?' · متن صفحه':''):'فاقد متن جست‌وجو')+
        (ADDENDA.some(a=>Number(a.chapter)===Number(c.number))?' · اصلاحیه/پیوست':'')));
    b.addEventListener('click',()=>showChapter(c.number));grid.append(b);
  }
  if(previous&&[...sel.options].some(x=>x.value===previous))sel.value=previous;
  else if(previous){sel.value='';$('q').value='';}
  $('chapterCount').textContent=visible+' از '+CATALOG.length+' مبحث'+(restricted?' · مطابق پروفایل اولیه':'');
  updateProjectNote();
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
  $('chapter').addEventListener('change',()=>{
    const n=Number($('chapter').value);
    if(n)showChapter(n);
    else{$('q').value='';renderQuick();render();}
  });
  for(const key of PROJECT_INPUTS){
    $(key).addEventListener(key==='pCity'||key==='pFloors'?'change':'change',()=>{
      saveProfile();renderCatalog();renderQuick();render();
    });
  }
  $('projectOnly').addEventListener('change',()=>{saveProfile();renderCatalog();renderQuick();render()});
  $('resetProject').addEventListener('click',()=>{
    for(const key of PROJECT_INPUTS)$(key).value='';
    $('projectOnly').checked=true;
    saveProfile();renderCatalog();renderQuick();render();
  });
}
async function init(){
  restoreProfile();
  wire();
  $('status').textContent='در حال بارگذاری نتایج…';
  const [catalog,coverage,index,curated,addenda]=await Promise.all([
    jsonOr('./data/catalog.json',[]),
    jsonOr('./data/coverage.json',{}),
    jsonOr('./data/search-index.json',[]),
    jsonOr('./m04-preview/rules.json',{rules:[]}),
    jsonOr('./data/addenda.json',[])
  ]);
  CATALOG=Array.isArray(catalog)?catalog:[];
  COVERAGE=coverage||{};
  ADDENDA=Array.isArray(addenda)?addenda:[];
  INDEX=Array.isArray(index)?index.filter(x=>x&&x.chapter&&x.answer):[];
  setCurated(curated);
  renderCatalog();
  renderQuick();
  $('q').value='ارتفاع جان پناه';
  render();
  const withData=new Set(sourceRecords().map(r=>Number(r.chapter))).size;
  const ocr=Number(COVERAGE.chapters_ocr_index||0);
  const pageOnly=Number(COVERAGE.chapters_page_index||0)-ocr;
  const structured=Number(COVERAGE.chapters_ready||0);
  const total=structured+pageOnly+ocr;
  $('datasetCoverage').textContent=total
    ? structured+' مبحث استخراج ساختاریافته · '+pageOnly+' مبحث متن صفحه · '+ocr+' مبحث OCR تأییدنشده · '+sourceRecords().length+' رکورد · پوشش بندها هنوز کامل‌سنجی نشده'
    : 'داده‌های قابل جست‌وجو هنوز بارگذاری نشده‌اند';
  if(!sourceRecords().length){
    $('status').textContent='داده‌های جست‌وجو در حال تکمیل است';
  }
}
init().catch(e=>{
  console.error(e);
  $('status').textContent='اشکال در آماده‌سازی صفحه';
});
