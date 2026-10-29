'use strict';
const $ = id => document.getElementById(id);
const text = (tag, value) => { const n = document.createElement(tag); n.textContent = value; return n; };
async function api(path, init) {
  const r = await fetch(path, init); const data = await r.json();
  if (!r.ok) throw new Error(data.message || 'دریافت داده ناموفق بود');
  return data;
}
function error(e) { $('error').hidden = false; $('error').textContent = e.message; }
function clearError() { $('error').hidden = true; }
function link(label, url) {
  if (!url) return text('span', 'لینک ثبت نشده');
  try { const u = new URL(url); if (u.protocol !== 'https:' || u.hostname !== 'inbr.ir') return text('span', 'لینک در انتظار بازبینی'); } catch { return text('span','لینک نامعتبر'); }
  const a = text('a', label); a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a;
}
function empty(target, message) { const p=text('p',message);p.className='empty';target.replaceChildren(p); }
function step(value) {
  $('part1').hidden = value !== 1; $('part2').hidden = value !== 2;
  for (let n=1;n<=3;n++) { const el=$('step'+n);el.removeAttribute('aria-current');if(n===value)el.setAttribute('aria-current','step'); }
  const target=value===3 ? $('results') : $('part'+value).querySelector('select,input');target.focus();
}
$('next').onclick = () => { if ([...$('part1').querySelectorAll('select')].every(n=>n.reportValidity())) step(2); };
$('back').onclick = () => step(1);
$('edit-project').onclick = () => { $('results').hidden=true; step(1); };
$('area').oninput = () => { if($('area').validity.valid) $('area-range').value=$('area').value; };
$('area-range').oninput = () => $('area').value=$('area-range').value;
document.querySelectorAll('[data-delta]').forEach(b=>b.onclick=()=> { const i=$(b.dataset.target);i.value=Math.max(Number(i.min),Math.min(Number(i.max),Number(i.value)+Number(b.dataset.delta))); });
$('project').onsubmit = async e => {
  e.preventDefault();clearError();const button=e.submitter;button.disabled=true;
  const body=Object.fromEntries(new FormData(e.currentTarget));for(const k of ['area','floors','basements']) body[k]=Number(body[k]);
  try {
    const data=await api('/api/v1/project-preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    $('results').hidden=false;step(3);$('project-summary').textContent=`${body.city}، ${body.use}، ${body.structure}؛ زیربنا ${body.area} متر مربع، ${body.floors} طبقه و ${body.basements} زیرزمین`;
    if(!data.items.length) empty($('topics'),'داده هنوز بارگذاری نشده');
    else { $('topics').replaceChildren();for(const item of data.items){const a=text('article','');a.className='result';a.append(text('h3',item.title),text('p',item.summary||'خلاصه هنوز ثبت نشده'));if(item.key_factors)a.append(text('p',JSON.stringify(item.key_factors)));$('topics').append(a);} }
  }catch(e){error(e);}finally{button.disabled=false;}
};
$('search').onsubmit = async e => {
  e.preventDefault();clearError();const b=e.submitter;b.disabled=true;$('search-results').textContent='در حال جست‌وجو…';
  try { const data=await api('/api/v1/search?q='+encodeURIComponent($('query').value));
    if(!data.items.length)empty($('search-results'),data.message||'نتیجه‌ای پیدا نشد');
    else { $('search-results').replaceChildren();for(const item of data.items){const card=text('article','');card.className='result';card.append(text('h3',item.title||item.locator),text('p',item.original_text),text('p',`${item.document}؛ بند ${item.locator}؛ صفحه PDF ${item.pdf_page}؛ صفحه چاپی ${item.printed_page||'نامشخص'}`),text('p',`ویرایش: ${item.edition||'نامشخص'}؛ به‌روزرسانی رکورد: ${item.updated_at}؛ تاریخ اجرا: ${item.effective_date_text||'نامشخص'}`),link('منبع اصلی',item.source_url),text('span',' | '),link('PDF رسمی',item.official_pdf_url));$('search-results').append(card);} }
  }catch(e){empty($('search-results'),'دریافت نتیجه انجام نشد');error(e);}finally{b.disabled=false;}
};
async function init(){
  try { const r=await fetch('/options.json');if(!r.ok)throw new Error('گزینه‌های فرم دریافت نشد');const options=await r.json();for(const [name,values]of Object.entries(options)){const s=document.querySelector(`[name="${name}"]`);s.append(new Option('انتخاب کنید',''));for(const v of values)s.append(new Option(v,v));}
    const data=await api('/api/v1/sources');$('catalog-count').textContent=`${data.items.length} سند`;
    $('catalog-status').textContent=data.mode==='catalog_only'?'فهرست شناسایی منابع؛ پایگاه داده عملیاتی هنوز متصل نیست.':'فهرست منابع از پایگاه داده';
    for(const item of data.items){const row=text('details','');row.className='source';row.append(text('summary',item.title));row.append(text('p','وضعیت اعتبار: نیازمند بررسی؛ متن مقررات هنوز بارگذاری نشده'));const p=text('p','');p.append(link('صفحه رسمی منبع',item.official_page_url));row.append(p);$('source-list').append(row);}
  }catch(e){$('catalog-status').textContent='فهرست منابع دریافت نشد';error(e);}
}
init();

