'use strict';
const $ = id => document.getElementById(id);
let CATALOG = [], INDEX = [], CURATED = [], ADDENDA = [], VISUALS = {}, SUBMITTED = {};
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
const DEEP_TOPICS = {
  "1": "تعریف ساختمان|تعریف طبقه|کاربری ساختمان|تصرف ساختمان|تعریف بنا|ساختمان مسکونی|سطح زیربنا|فضای باز|حیاط|ساختمان بلند|تأسیسات ساختمان|راه خروج|طبقه زیرزمین|پارکینگ|بام|تغییر کاربری|پله|آسانسور|دیوار|پیش‌آمدگی|ارتفاع ساختمان",
  "2": "پروانه ساختمان|مسئولیت مالک|وظایف ناظر|وظایف مجری|سازنده ذیصلاح|طراح ساختمان|نقشه معماری|شناسنامه فنی|دفترچه اطلاعات|پایان کار|گزارش ناظر|دستور توقف|تخلف ساختمانی|آزمایش مصالح|قرارداد اجرای ساختمان|کنترل ساختمان|بیمه|تغییر نقشه|مجوز ساخت|ثبت مشخصات",
  "3": "حفاظت در برابر حریق|مقاومت در برابر آتش|طبقه بندی تصرف|مسیر خروج|راه پله فرار|راهرو خروج|عرض خروج|فاصله پیمایش|دودبند|درب مقاوم حریق|دسترسی آتش نشانی|اعلام حریق|اطفای حریق|اسپرینکلر|فضای امن|پارکینگ|آسانسور|خروج اضطراری|دیوار حریق|تخلیه دود|حریق نما|محدودیت ارتفاع|حفاظت سازه|کپسول آتش نشانی",
  "4": "ارتفاع جان پناه|عرض راه پله|نورگیری اتاق|عرض آشپزخانه|ارتفاع پارکینگ|حداقل مساحت اتاق|ابعاد آشپزخانه|ارتفاع سقف|نور طبیعی|تهویه طبیعی|پنجره|بازشو|ابعاد سرویس بهداشتی|توالت|حمام|راهرو|فضای مسکونی|اتاق خواب|اتاق نشیمن|بالکن|پاسیو|حیاط خلوت|حیاط|رمپ پارکینگ|تعداد پارکینگ|درب ورود|دسترسی معلولان|سطح اشغال|پله|نرده|آسانسور|بام|شیب بام|زیربنا|فضای مشاع|انبار|ایمنی شیشه|درز انقطاع|سقف کاذب|چاهک",
  "5": "مصالح ساختمانی|استاندارد مصالح|آزمایش مصالح|سیمان|بتن|بتن آماده|سنگدانه|شن|ماسه|آهک|گچ|گچ ساختمانی|آجر|آجر سفالی|آجر نسوز|بلوک سیمانی|بلوک سبک|بتن هوادار|ملات|ملات ماسه سیمان|فولاد|میلگرد|ورق فولادی|پروفیل|جوش|پیچ و مهره|سنگ ساختمانی|سنگ نما|کاشی|سرامیک|چینی|شیشه|شیشه ایمنی|شیشه دوجداره|چوب|تخته چوب|ام دی اف|پلاستیک|پلیمر|لوله|قیر|آسفالت|ایزوگام|عایق رطوبتی|عایق حرارتی|پشم سنگ|پشم شیشه|رنگ|پوشش|چسب|در و پنجره|آلومینیوم|سقف|پوشش بام|کفپوش|دیوار پوش|نماسازی|مصالح بنایی|مصالح سبک|حفاظت خوردگی|مقاومت در برابر آتش|مقاومت فشاری|کیفیت مصالح|انبار مصالح|حمل مصالح|سازگاری مصالح|آزمایشگاه|چسب کاشی|موزاییک|سفال",
  "6": "بار زنده|بار مرده|بار باد|بار برف|ترکیب بارها|بار زلزله|بار جانبی|بار ثقلی|بار بام|بار برف بام|بار پارکینگ|بار راه پله|بار کف|بار دیوار|بار تیغه|بار نما|بار آسانسور|بار آب|بار خاک|بار حرارتی|بار ضربه|ضریب اهمیت|ضریب بار|بار جرثقیل|بارگذاری سقف|بارگذاری ساختمان مسکونی",
  "7": "مطالعات ژئوتکنیک|ظرفیت باربری خاک|طراحی پی|آزمایش خاک|گمانه زنی|نشست پی|پایدارسازی گود|نیروی جانبی خاک|تحلیل خاک|سطح آب زیرزمینی|پی سطحی|پی نواری|پی گسترده|پی منفرد|پی عمیق|شمع|نیروی بالابرنده|گودبرداری|دیوار حائل|تراکم خاک|پایدارسازی شیب|مقاومت برشی|تراز پی|عمق پی",
  "8": "دیوار باربر بنایی|کلاف بندی|ارتفاع ساختمان بنایی|دیوار آجری|دیوار بلوکی|ملات|پی بنایی|دیوار غیر باربر|بازشو دیوار|نعل درگاه|اتصال دیوار|مقاومت فشاری|مقاومت جانبی|حداقل ضخامت دیوار|کلاف افقی|کلاف قائم|پایداری دیوار|دستک|شناژ|محدودیت طبقات|سقف ساختمان بنایی",
  "9": "پوشش بتن|میلگرد گذاری|وصله میلگرد|مقاومت بتن|تیر بتنی|ستون بتنی|دال بتنی|پی بتنی|سقف بتنی|دیوار برشی|بتن آرمه|خاموت|آرماتور طولی|فاصله میلگرد|طول مهاری|قلاب میلگرد|بتن ریزی|عمل آوری بتن|برش|خمش|پیچش|اتصال تیر و ستون|نسبت آرماتور|قالب بندی|برش پانچ|دال دو طرفه|کنترل خیز|تیرچه|آرماتور افت و حرارت|درز اجرایی|مقاومت فشاری بتن",
  "10": "اتصال فولادی|جوش و پیچ|بادبند|ستون فولادی|تیر فولادی|مهاربند|اتصال گیردار|اتصال مفصلی|جوشکاری|پیچ پر مقاومت|ورق اتصال|صفحه ستون|تیر به ستون|پایه ستون|مهاربند همگرا|مهاربند واگرا|قاب خمشی|کمانش|مقاومت کششی|برش|طراحی تیر|طراحی ستون|کنترل خیز|تیر مرکب|سازه فلزی|پوشش ضد حریق|خوردگی فولاد|وصله ستون|سخت کننده",
  "11": "ساخت صنعتی|قطعات پیش ساخته|اتصالات صنعتی|سازه پیش ساخته|بتن پیش ساخته|اسکلت سبک|قاب فولادی سبک|سیستم ساختمانی|تولید صنعتی|حمل قطعات|نصب قطعات|کنترل کیفیت|مونتاژ سازه|دیوار پیش ساخته|سقف پیش ساخته|مدولار|پیش ساختگی|سیستم باربر جانبی|عایق بندی",
  "12": "حفاظت کارگاه|ایمنی گودبرداری|داربست|کار در ارتفاع|ایمنی بالابر|ایمنی جرثقیل|حفاظت کارگران|حفاظت عابران|کلاه ایمنی|سقوط اشیا|نردبان|تخریب ساختمان|برق کارگاه|ایمنی آتش سوزی|حفاظ گود|حمل مصالح|انبار مصالح|ایمنی ماشین آلات|پیمانکار|مسئول ایمنی|ایمنی حفاری",
  "13": "ارتینگ|برق اضطراری|تابلو برق|حفاظت الکتریکی|روشنایی ساختمان|روشنایی اضطراری|پریز|کلید برق|مدار روشنایی|انشعاب برق|کابل کشی|سیم کشی|ارتباط زمین|سیستم اتصال زمین|حفاظت در برابر برق گرفتگی|فیوز|کلید مینیاتوری|کلید محافظ جان|جعبه تقسیم|رایزر برق|تأسیسات برقی پارکینگ|تأسیسات برقی حمام|آسانسور|صاعقه گیر|دستگاه مولد برق|ترانسفورماتور|سیستم اعلام حریق",
  "14": "تهویه مطبوع|دودکش|موتورخانه|تهویه پارکینگ|گرمایش|سرمایش|دیگ|پکیج|رادیاتور|فن کویل|هواساز|کانال تهویه|کانال هوا|تهویه آشپزخانه|تهویه سرویس بهداشتی|تخلیه دود|هواگیری|چیلر|برج خنک کننده|دستگاه سرمایش|سیستم گرمایش مرکزی|تهویه طبیعی|هواساز|لوله کشی گرمایش|عایق کاری تأسیسات|مشعل|آب گرم مصرفی|تهویه مکانیکی|دمای آسایش",
  "15": "ابعاد آسانسور|چاه آسانسور|ظرفیت کابین|تعداد آسانسور|سرعت آسانسور|ابعاد کابین|درب آسانسور|چاهک آسانسور|موتورخانه آسانسور|آسانسور بدون موتورخانه|آسانسور آتش نشانی|آسانسور معلولین|پلکان برقی|پله برقی|شیب پله برقی|ایمنی آسانسور|ترمز اضطراری|سیستم تعلیق|بارگذاری آسانسور|برق اضطراری آسانسور|دسترسی آسانسور",
  "16": "لوله کشی آب|فاضلاب|شیب لوله|تهویه فاضلاب|آب سرد|آب گرم|آب آشامیدنی|لوله کشی آشپزخانه|لوله کشی حمام|لوله کشی توالت|سیفون|کفشور|آب باران|ناودان|لوله قائم فاضلاب|شبکه فاضلاب|سپتیک|پمپ آب|مخزن آب|فشار آب|شیرآلات|لوازم بهداشتی|قطر لوله|دبی مصرفی|آب بندی|نشتی آب|تهویه شبکه فاضلاب",
  "17": "لوله کشی گاز|دودکش گاز|انشعاب گاز|متر گاز|شیر گاز|رگولاتور|فشار گاز|لوله فولادی گاز|نصب پکیج|نصب آبگرمکن|تست نشتی|آزمایش فشار|تهویه محل نصب|اتصالات گاز|مکان مجاز نصب|حفاظت لوله|لوله کشی روکار|لوله کشی توکار|دودکش بخاری",
  "18": "عایق صوتی|صدای کوبه ای|صدای هوابرد|کاهش صدا|عایق بندی صوتی|جداره جداکننده|دیوار مشترک|پنجره دوجداره|سقف عایق صوتی|کف شناور|نویز تجهیزات|صدای تأسیسات|جذب صدا|انتقال صدا|شاخص کاهش صدا|زمان واخنش|آکوستیک",
  "19": "عایق حرارتی|پوسته ساختمان|مصرف انرژی|ضریب انتقال حرارت|پنجره|شیشه دوجداره|عایق دیوار|عایق سقف|پل حرارتی|گرمایش و سرمایش|برچسب انرژی|سیستم روشنایی|انرژی تجدیدپذیر|ساختمان کم مصرف|تهویه|هوابندی|جهت گیری ساختمان|آب گرم مصرفی|بازده تجهیزات|ضریب U|انرژی خورشیدی|بام سبز",
  "20": "علائم خروج|تابلوهای ایمنی|علائم کارگاه|تابلو ورودی|تابلو راهنما|علائم خطر|علائم هشدار|علائم ممنوعیت|علائم اجباری|تابلو آسانسور|علامت آتش نشانی|پلاک ساختمان|علائم پارکینگ|علائم ترافیکی|علائم امداد|ابعاد تابلو|رنگ علائم|محل نصب تابلو|علائم مسیر خروج",
  "21": "پدافند غیرعامل|حفاظت ساختمان|الزامات پدافندی|فضای امن|پناهگاه|تاب آوری ساختمان|حفاظت تاسیسات|مقاومت انفجار|محافظت ورودی|ایمنی دسترسی|امنیت شبکه|مکان یابی|محوطه امن|حفاظت مکانیکی|تداوم کاربری",
  "22": "بازرسی دوره ای|نگهداری ساختمان|تعمیرات|بازرسی سازه|نگهداری تأسیسات|نگهداری آسانسور|بازرسی نما|نگهداری بام|بازرسی تجهیزات|تعمیر دیوار|نگهداری پارکینگ|دفترچه نگهداری|مدیریت ساختمان|بازرسی ایمنی|آزمون دوره ای|رسیدگی به خرابی|سرویس تجهیزات",
  "23": "تعداد پارکینگ|دسترسی خودرو|شیب رمپ|تردد خودرو|عرض رمپ|ارتفاع پارکینگ|ابعاد جای پارک|شعاع گردش خودرو|مسیر حرکت|ترافیک ساختمان|ورود و خروج|پارکینگ معلولین|پارکینگ دوچرخه|موتورسیکلت|راه دسترسی|عرض معبر|خیابان|دسترسی آتش نشانی|بارگیری|توقفگاه",
  "24": "انطباق شهری|ضوابط شهرسازی|معابر|خط آسمان|ارتفاع ساختمان|نما|حریم معبر|مبلمان شهری|ارتباط با شهر|پیش آمدگی|دسترسی معبر|ورودی ساختمان|بافت شهری|پیاده رو|نمای شهری|پارکینگ|پوشش گیاهی|حفاظت محیطی|تراکم ساختمانی|حقوق همسایگی"
};
const USE_PRIORITIES = {
  residential:['مسکونی','اتاق','آشپزخانه','حمام','توالت','پارکینگ','پله','نورگیری','پنجره','دیوار','کف','سقف','عایق','آسانسور','آب','برق','گاز','حریق'],
  commercial:['تجاری','پارکینگ','حریق','خروج','آسانسور','تردد','روشنایی','تهویه','بار'],
  office:['اداری','خروج','آسانسور','پارکینگ','تهویه','روشنایی','حریق'],
  industrial:['صنعتی','ماشین','جرثقیل','تهویه','سازه','بار','حریق'],
  mixed:['مسکونی','تجاری','حریق','خروج','پارکینگ','تأسیسات']
};
let TOPIC_INDEX = new Map();
function buildTopicIndex(){
  const buckets=new Map(CATALOG.map(c=>[Number(c.number),new Map()]));
  function add(n,label,priority){
    const bucket=buckets.get(Number(n));
    if(!bucket)return;
    const text=String(label||'').replace(/\s*\(شماره بند تأییدنشده\)/g,'').trim();
    const key=norm(text);
    if(!key||key.length<2||key.length>75||!/[آ-ی]/.test(text))return;
    if(/^(بند|صفحه)\s*\d/i.test(text)||/^(کلیات|تعاریف|الزامات|مقدمه|مبحث|فصل|پیوست|نتیجه گیری)$/.test(text))return;
    if(!bucket.has(key)||bucket.get(key).priority<priority)bucket.set(key,{label:text,priority,n:Number(n)});
  }
  for(const c of CATALOG){
    const n=Number(c.number);
    for(const q of QUICK_BY_CHAPTER[n]||[])add(n,q,120);
    for(const q of (DEEP_TOPICS[n]||'').split('|'))add(n,q,100);
  }
  for(const r of sourceRecords()){
    const n=Number(r.chapter);
    if(!buckets.has(n))continue;
    if(r.kind==='page_extract'||r.kind==='ocr_page'||r.kind==='direct_pdf_text')continue;
    if(r.title&&String(r.title).length>=6&&String(r.title).length<=70)add(n,r.title,60);
    if(r.topic)add(n,r.topic,65);
    for(const q of (r.keywords||[]).slice(0,20))add(n,q,45);
    for(const q of (r.q||[]).slice(0,10))add(n,q,45);
  }
  TOPIC_INDEX=buckets;
}
function topicPreference(topic,p){
  const t=norm(topic.label), hints=USE_PRIORITIES[p.pUse]||[];
  let rank=topic.priority;
  for(const hint of hints)if(t.includes(norm(hint)))rank+=22;
  if(p.pStructure==='steel'&&/(فولاد|فلزی|جوش|پیچ|مهاربند|بادبند)/.test(t))rank+=30;
  if(p.pStructure==='concrete'&&/(بتن|میلگرد|آرماتور|قالب)/.test(t))rank+=30;
  if(p.pElevator==='yes'&&t.includes('آسانسور'))rank+=25;
  if(p.pGas==='yes'&&t.includes('گاز'))rank+=25;
  return rank;
}
function renderQuick(){
  const holder=$('quick'),chosen=Number($('chapter').value),filter=norm($('topicFilter').value);
  const p=projectProfile();
  holder.replaceChildren();
  const chapters=chosen
    ? CATALOG.filter(c=>Number(c.number)===chosen)
    : CATALOG.filter(c=>!restrictToProject()||chapterRelevant(c.number,p));
  for(const c of chapters){
    const n=Number(c.number),items=[...(TOPIC_INDEX.get(n)||new Map()).values()]
      .filter(item=>!filter||norm(item.label).includes(filter))
      .sort((a,b)=>topicPreference(b,p)-topicPreference(a,p)||a.label.localeCompare(b.label,'fa'));
    if(!items.length)continue;
    const group=el('section',null,'topic-group');
    group.setAttribute('aria-label','موضوعات مبحث '+n);
    if(!chosen)group.append(el('div','مبحث '+n+' — '+c.title,'topic-group-title'));
    const chips=el('div',null,'topic-chips');
    for(const item of items){
      const button=el('button',item.label);
      button.type='button';button.dataset.q=item.label;button.dataset.chapter=String(n);
      button.addEventListener('click',()=>{
        if(!$('chapter').value||Number($('chapter').value)!==n){
          if(restrictToProject()&&!chapterRelevant(n))$('projectOnly').checked=false;
          $('chapter').value=String(n);
        }
        $('q').value=item.label;
        renderQuick();
        render();
        $('results').scrollIntoView({behavior:'smooth',block:'start'});
      });
      chips.append(button);
    }
    group.append(chips);holder.append(group);
  }
  if(!holder.children.length)holder.append(el('div','موضوعی با این عبارت پیدا نشد.','topic-empty'));
}

function updateProjectNote(){
  const p=projectProfile();
  $('projectNote').textContent=p.active
    ? 'موضوعات و نتایج بر اساس مشخصات انتخابی پیشنهاد می‌شوند. برای دیدن همه مباحث، گزینه «فقط مباحث پیشنهادی» را خاموش کن.'
    : 'مشخصات پروژه را می‌توانی برای مرتب‌کردن موضوعات و انتخاب حوزه جست‌وجو وارد کنی.';
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
  parent.append(el('div','ارجاعات مرتبط','label'),holder);
}
function renderVisuals(ch){
  const gallery=$('visualGallery'),list=$('visualItems');
  const info=VISUALS[String(Number(ch))];
  list.replaceChildren();
  if(!info||!Array.isArray(info.pages)||!info.pages.length){
    gallery.hidden=true;
    return;
  }
  gallery.hidden=false;
  $('visualTitle').textContent='تصاویر، نمودارها و جدول‌های مبحث '+Number(ch);
  $('visualMeta').textContent='ویرایش '+info.edition;
  for(const entry of info.pages){
    const a=el('a',null,'visual-tile');
    a.href=entry.preview;
    a.target='_blank';
    a.rel='noopener noreferrer';
    a.setAttribute('aria-label','مشاهده پیش‌نمایش صفحه '+entry.page);
    const img=el('img');
    img.src=entry.preview;
    img.alt='پیش‌نمایش صفحه '+entry.page+' مبحث '+ch+'، ویرایش '+info.edition;
    img.loading='lazy';img.decoding='async';
    a.append(img,el('strong','صفحه PDF '+entry.page),
      el('span',(entry.features||[]).join(' · ')||'صفحه دارای عناصر تصویری'));
    list.append(a);
  }
  if(info.source_url){
    const link=el('a','مشاهده سند اصلی برای بررسی بزرگ‌نمایی','visual-source-link');
    link.href=info.source_url;link.rel='noopener noreferrer';link.target='_blank';
    list.after(link);
    // Remove the previously appended source link from a prior chapter.
    [...gallery.querySelectorAll('.visual-source-link')].slice(0,-1).forEach(x=>x.remove());
  }else gallery.querySelectorAll('.visual-source-link').forEach(x=>x.remove());
}
function resultCard(r,i){
  const m=chapterMeta(r.chapter);
  const card=el('article',null,'result'+(i===0?' primary':''));
  const top=el('div',null,'topline');
  top.append(el('span','مبحث '+r.chapter+(r.locator?' · بند '+r.locator:'')+(m.edition?' · ویرایش '+m.edition:''),'source'));
  card.append(top);
  card.append(el('h2',String(r.title||('بند '+(r.locator||''))).replace(/\s*\(شماره بند تأییدنشده\)/g,'')));
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
  const visual=VISUALS[String(Number(r.chapter))];
  const nearest=String(visual?.edition||'')===String(r.edition||chapterMeta(r.chapter).edition)?visual?.pages?.find(p=>Number(p.page)===Number(r.page)):null;
  if(nearest){
    const figure=el('a',null,'inline-visual');
    figure.href=nearest.preview;figure.target='_blank';figure.rel='noopener noreferrer';
    const thumbnail=el('img');
    thumbnail.src=nearest.preview;
    thumbnail.loading='lazy';
    thumbnail.alt='پیش‌نمایش مرتبط با صفحه '+r.page;
    figure.append(thumbnail,el('span','مشاهده تصویر و ترسیم صفحه PDF '+r.page));
    card.append(figure);
  }
  if(r.source_url){
    const link=el('a',r.page?'مشاهده منبع · صفحه PDF '+r.page:'مشاهده منبع متن','source-link');
    link.href=/\\.pdf(?:[?#]|$)/i.test(r.source_url)&&r.page
      ? r.source_url.split('#')[0]+'#page='+Number(r.page):r.source_url;
    link.target='_blank';link.rel='noopener noreferrer';card.append(link);
  }
  return card;
}
function render(){
  const q=$('q').value.trim(),ch=$('chapter').value,area=$('results');
  area.replaceChildren();
  renderVisuals(ch);
  if(q.length<2){
    $('status').textContent='عبارت جست‌وجو را بنویس';
    area.append(el('div','برای شروع یکی از موضوع‌های پیشنهادی را انتخاب کن.','empty'));return;
  }
  const rows=search(q,ch);
  $('status').textContent=rows.length?'نتایج جست‌وجو':'نتیجه‌ای پیدا نشد';
  if(!rows.length){
    const m=ch?chapterMeta(ch):null;
    const notIndexed=m&&!sourceRecords().some(r=>Number(r.chapter)===Number(ch));
    const empty=el('div',
      notIndexed?'برای این مبحث نتیجه‌ای پیدا نشد.':
      'برای عبارت انتخابی نتیجه‌ای پیدا نشد.',
      'empty');
    if(notIndexed){
      const preferred=(m.attempts||[]).find(a=>a.type==='document_source'&&a.ok&&a.url&&a.url.startsWith('https:'));
      const source=preferred||(m.attempts||[]).find(a=>a.url&&a.url.startsWith('https:'));
      if(source){
        const link=el('a','مشاهده فایل یا صفحه منبع');
        link.href=source.url;link.target='_blank';link.rel='noopener noreferrer';
        empty.append(link);
      }
    }
    area.append(empty);
    return;
  }
  rows.forEach((r,i)=>area.append(resultCard(r,i)));
  if(!ch&&rows.length)renderVisuals(rows[0].r?.chapter||rows[0].chapter);
}
function showChapter(n){
  if(restrictToProject()&&!chapterRelevant(n))$('projectOnly').checked=false;
  $('chapter').value=String(n);
  renderQuick();
  renderVisuals(n);
  const matches=sourceRecords().filter(x=>Number(x.chapter)===Number(n));
  const area=$('results');area.replaceChildren();
  const m=chapterMeta(n);
  $('status').textContent='مبحث '+n+' — '+m.title;
  const addenda=ADDENDA.filter(x=>Number(x.chapter)===Number(n));
  if(addenda.length){
    const aside=el('aside',null,'addenda-notice');
    aside.append(el('strong','اسناد و پیوست‌های مرتبط:'));
    for(const x of addenda){
      const link=el('a',x.title+' · مشاهده PDF');
      link.href=x.source_url;
      link.target='_blank';link.rel='noopener noreferrer';aside.append(link);
    }
    area.append(aside);
  }
  if(!matches.length){
    const message=el('div','برای این مبحث نتیجه‌ای پیدا نشد.','empty');
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
  for(const c of CATALOG){
    if(restrictToProject()&&!chapterRelevant(c.number))continue;
    const option=el('option','مبحث '+c.number+' — '+c.title);
    option.value=c.number;sel.append(option);
    const btn=el('button',null,'chapter');
    btn.type='button';
    btn.append(el('strong','مبحث '+c.number+' — '+c.title));
    btn.addEventListener('click',()=>showChapter(c.number));grid.append(btn);
  }
  if(previous&&[...sel.options].some(x=>x.value===previous))sel.value=previous;
  else if(previous){sel.value='';$('q').value='';}
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
  $('topicFilter').addEventListener('input',renderQuick);
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
  const [catalog,index,curated,addenda,energyBackup,visualIndex,submitted6,submitted11,submitted18,submitted20,completeness,numbered5]=await Promise.all([
    jsonOr('./data/catalog.json',[]),
    jsonOr('./data/search-index.json',[]),
    jsonOr('./m04-preview/rules.json',{rules:[]}),
    jsonOr('./data/addenda.json',[]),
    jsonOr('./data/m19-structured-backup.json',{records:[]}),
    jsonOr('./data/visuals/index.json',{chapters:{}}),
    jsonOr('./data/submitted/m06-1392-direct.json',{records:[]}),
    jsonOr('./data/submitted/m11-1392-direct.json',{records:[]}),
    jsonOr('./data/submitted/m18-1390-direct.json',{records:[]}),
    jsonOr('./data/submitted/m20-1396-direct.json',{records:[]}),
    jsonOr('./data/completeness-audit.json',null),
    jsonOr('./data/clause-text/m05.json',{records:[]})
  ]);
  CATALOG=Array.isArray(catalog)?catalog:[];
  ADDENDA=Array.isArray(addenda)?addenda:[];
  VISUALS=visualIndex?.chapters||{};
  // OCR content is deliberately excluded from the live search, even if legacy
  // snapshots still contain it. Uploaded searchable-text PDFs are separate editions.
  INDEX=Array.isArray(index)?index.filter(x=>x&&x.chapter&&x.answer&&x.kind!=='ocr_page'):[];
  for(const uploaded of [submitted6,submitted11,submitted18,submitted20]){
    if(!uploaded||!Array.isArray(uploaded.records)||!uploaded.records.length)continue;
    const n=Number(uploaded.chapter);
    SUBMITTED[String(n)]=uploaded;
    INDEX=INDEX.filter(x=>Number(x.chapter)!==n).concat(uploaded.records);
    const meta=CATALOG.find(x=>Number(x.number)===n);
    if(meta){
      meta.original_edition=meta.edition;
      meta.edition=String(uploaded.edition);
      meta.record_count=uploaded.records.length;
      meta.method='direct_pdf_text';
      meta.status='uploaded_text_edition';
      meta.source=uploaded.source_name;
    }
  }
  // Display the complete, real numbered clauses from the PDF text layer.
  // Do not use the old arbitrary page fragments for Chapter 5.
  if(Array.isArray(numbered5?.records)&&numbered5.records.length>90){
    INDEX=INDEX.filter(x=>Number(x.chapter)!==5).concat(numbered5.records);
    const c=CATALOG.find(x=>Number(x.number)===5);
    if(c){c.record_count=numbered5.records.length;c.method='numbered_clause';}
  }
    const backup=Array.isArray(energyBackup?.records)?energyBackup.records.filter(x=>x&&Number(x.chapter)===19&&x.answer):[];
  const activeM19=INDEX.filter(x=>Number(x.chapter)===19);
  if(backup.length>activeM19.length){
    INDEX=INDEX.filter(x=>Number(x.chapter)!==19).concat(backup);
    const meta=CATALOG.find(x=>Number(x.number)===19);
    if(meta){meta.record_count=backup.length;meta.method='structured_text';meta.source=energyBackup.source_url;meta.preserved_previous_snapshot=true;}
  }
  // Never expose unreadable mojibake as regulatory text. The audit records the
  // excluded volume; later correct UTF-8 rebuilds can automatically restore it.
  const bad=new Set((completeness?.chapters||[])
    .filter(c=>c.quarantined_due_to_encoding||
      (c.warnings||[]).includes('text_encoding_corruption_suspected'))
    .map(c=>Number(c.chapter)));
  if(bad.size){
    INDEX=INDEX.filter(r=>!bad.has(Number(r.chapter)));
    for(const c of CATALOG){
      if(!bad.has(Number(c.number)))continue;
      c.record_count=0;
      c.status='unusable_encoding';
      c.method='unusable_encoding';
    }
  }
  setCurated(curated);
  buildTopicIndex();
  renderCatalog();
  renderQuick();
  $('q').value='ارتفاع جان پناه';
  render();
}
init().catch(e=>{
  console.error(e);
  $('status').textContent='اشکال در آماده‌سازی صفحه';
});
