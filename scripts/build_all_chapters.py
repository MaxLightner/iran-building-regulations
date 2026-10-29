#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys, tempfile, time, unicodedata
from pathlib import Path
from urllib.parse import urljoin, quote
import requests
from bs4 import BeautifulSoup
import fitz

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/"sources/chapters.json"
OUT=ROOT/"frontend/data"
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; IranBuildingRules/2.0; +https://github.com/MaxLightner/iran-building-regulations)"}
TIMEOUT=35
DIGITS=str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩","01234567890123456789")
NUMWORDS={
"اول":1,"یکم":1,"دوم":2,"سوم":3,"چهارم":4,"پنجم":5,"ششم":6,"هفتم":7,"هشتم":8,"نهم":9,"دهم":10,
"یازدهم":11,"دوازدهم":12,"سیزدهم":13,"چهاردهم":14,"پانزدهم":15,"شانزدهم":16,"هفدهم":17,"هجدهم":18,
"نوزدهم":19,"بیستم":20,"بیست و یکم":21,"بیست‌ویکم":21,"بیست و دوم":22,"بیست‌ودوم":22,
"بیست و سوم":23,"بیست‌وسوم":23,"بیست و چهارم":24,"بیست‌وچهارم":24
}
REF_RE=re.compile(r"(?<!\d)(?P<ref>\d{1,2}(?:\s*[-–—]\s*\d{1,3}){1,6})(?!\d)")
MABHAS_RE=re.compile(r"مبحث\s+(?P<n>\d{1,2}|[آ-ی‌ ]{2,20})")
TABLE_RE=re.compile(r"جدول\s+(?:شماره\s*)?(?P<ref>\d{1,2}(?:\s*[-–—]\s*\d{1,3}){1,6})")
NORMATIVE_RE=re.compile(r"(باید|نباید|الزامی|مجاز|ممنوع|حداقل|حداکثر|ضروری|لازم است|اجازه|ملزم|موظف)")
UNIT_RE=re.compile(r"(?P<value>\d+(?:[/.٫]\d+)?)\s*(?P<unit>میلی ?متر|سانتی ?متر|متر ?مربع|متر ?مکعب|متر|درصد|درجه|کیلو ?نیوتن|کیلوگرم|نفر|طبقه|واحد)")

session=requests.Session();session.headers.update(HEADERS)

def norm(s:str)->str:
    s=unicodedata.normalize("NFKC",str(s or "")).translate(DIGITS)
    s=s.replace("ي","ی").replace("ك","ک").replace("ى","ی").replace("\u200c"," ")
    s=re.sub(r"[\u064b-\u065f\u0670\u200e\u200f]","",s)
    s=re.sub(r"\s+"," ",s)
    return s.strip()

def refnorm(s):
    return re.sub(r"\s*[-–—]\s*","-",norm(s))

def canonical_ref(chapter,s):
    r=refnorm(s)
    parts=r.split("-")
    if len(parts)<2:return r
    try: nums=[int(x) for x in parts]
    except ValueError:return r
    if nums[0]==chapter:return "-".join(str(x) for x in nums)
    if nums[-1]==chapter:return "-".join(str(x) for x in reversed(nums))
    return r

def looks_like_locator(chapter,s):
    parts=refnorm(s).split("-")
    if len(parts)<2 or len(parts)>7:return False
    try: nums=[int(x) for x in parts]
    except ValueError:return False
    return nums[0]==chapter or nums[-1]==chapter

def safe_get(url,binary=False):
    r=session.get(url,timeout=TIMEOUT,allow_redirects=True)
    r.raise_for_status()
    if binary:return r.content,r.url,r.headers.get("content-type","")
    r.encoding=r.apparent_encoding or "utf-8"
    return r.text,r.url,r.headers.get("content-type","")

def find_chapter_number(text):
    t=norm(text)
    m=re.search(r"مبحث\s+(\d{1,2})\b",t)
    if m:
        n=int(m.group(1))
        if 1<=n<=24:return n
    for k,v in sorted(NUMWORDS.items(),key=lambda kv:-len(kv[0])):
        if "مبحث "+k in t:return v
    return None

def discover_mihansazan():
    found={}
    urls=set()
    seeds=["https://mihansazan.app/robots.txt","https://mihansazan.app/sitemap.xml","https://mihansazan.app/sitemap_index.xml"]
    for u in seeds:
        try:
            txt,final,ct=safe_get(u)
        except Exception:
            continue
        for x in re.findall(r"https?://[^\s<>\"]+",txt):
            x=x.rstrip("</loc>)")
            if "mihansazan.app" in x and ("sitemap" in x or "/posts/nbci-" in x):urls.add(x)
    # Expand sitemap files discovered from sitemap index/robots.
    for sm in list(urls):
        if "sitemap" not in sm:continue
        try:txt,_,_=safe_get(sm)
        except Exception:continue
        for x in re.findall(r"<loc>\s*(https?://[^<]+)\s*</loc>",txt):
            if "/posts/nbci-" in x:urls.add(x.strip())
    # Known URLs are supplied by the registry and handled separately; discovery is extra.
    for u in sorted(x for x in urls if "/posts/nbci-" in x):
        try:
            html,_,_=safe_get(u); soup=BeautifulSoup(html,"html.parser")
            title=(soup.title.get_text(" ",strip=True) if soup.title else "")+" "+(soup.find("h1").get_text(" ",strip=True) if soup.find("h1") else "")
            n=find_chapter_number(title)
            if n and n not in found: found[n]=u
        except Exception:continue
    return found

def main_article(soup):
    for sel in ["article",".post-content",".entry-content",".prose","main"]:
        n=soup.select_one(sel)
        if n:return n
    return soup.body or soup

def html_records(chapter,url):
    html,final,_=safe_get(url)
    soup=BeautifulSoup(html,"html.parser")
    root=main_article(soup)
    out=[];current=None;order=0;last_heading=""
    def flush():
        nonlocal current
        if not current:return
        text=norm(" ".join(current.pop("_parts",[])))
        if len(text)>=20:
            current["text"]=text
            current["answer"]=text
            current["normative"]=bool(NORMATIVE_RE.search(text))
            current["numbers"]=[{"value":m.group("value"),"unit":norm(m.group("unit"))} for m in UNIT_RE.finditer(text)][:10]
            current["cross_refs"]=crossrefs(chapter,text,current.get("locator"))
            out.append(current)
        current=None
    elems=root.find_all(["h1","h2","h3","h4","h5","h6","p","li","table"],recursive=True)
    for e in elems:
        # Ignore nested p/li duplicated through a table.
        if e.find_parent("table") and e.name!="table": continue
        text=norm(e.get_text(" ",strip=True))
        if not text:continue
        if e.name.startswith("h"):
            last_heading=text
            m=REF_RE.search(text)
            if m:
                flush();order+=1
                current={"id":f"m{chapter:02d}-{order:05d}","chapter":chapter,"locator":canonical_ref(chapter,m.group("ref")),
                         "title":norm(REF_RE.sub("",text)).strip(" -–—:؛") or text,"kind":"clause","_parts":[],"source_url":final}
            continue
        if e.name=="table":
            rows=[]
            for tr in e.find_all("tr"):
                cells=[norm(c.get_text(" ",strip=True)) for c in tr.find_all(["th","td"])]
                if any(cells):rows.append(" | ".join(cells))
            text=norm(" ؛ ".join(rows))
            if not text:continue
            m=TABLE_RE.search(last_heading+" "+text)
            flush();order+=1
            current={"id":f"m{chapter:02d}-{order:05d}","chapter":chapter,"locator":canonical_ref(chapter,m.group("ref")) if m else None,
                     "title":last_heading or "جدول","kind":"table","_parts":[text],"source_url":final}
            flush();continue
        # Paragraph/list that begins with a clause ref starts a new record.
        m=REF_RE.match(text)
        if m:
            flush();order+=1
            body=norm(text[m.end():]).strip(" -–—:؛")
            current={"id":f"m{chapter:02d}-{order:05d}","chapter":chapter,"locator":canonical_ref(chapter,m.group("ref")),
                     "title":last_heading or f"بند {canonical_ref(chapter,m.group('ref'))}","kind":"clause","_parts":[body],"source_url":final}
        elif current:
            current["_parts"].append(text)
    flush()
    return dedupe(out),final

def mediafire_pdf(page_url):
    """Return MediaFire's real file URL from either a MediaFire page or a page linking to it."""
    targets=[]
    if "mediafire.com/" in page_url:
        targets.append(page_url)
    else:
        html,_,_=safe_get(page_url)
        soup=BeautifulSoup(html,"html.parser")
        targets.extend(urljoin(page_url,a.get("href")) for a in soup.find_all("a",href=True) if "mediafire.com" in a.get("href",""))
    for u in targets:
        try:
            mh,_,_=safe_get(u); ms=BeautifulSoup(mh,"html.parser")
            a=ms.select_one("a#downloadButton")
            if not a:
                a=next((x for x in ms.find_all("a",href=True) if x.get("href","").startswith("http") and ("download" in x.get("href","") or "download" in norm(x.get_text(" ",strip=True)))),None)
            if a:return urljoin(u,a.get("href"))
        except Exception:continue
    return None

def archweb_landing_map():
    index="https://archweb.ir/2024/09/26/دانلود-مباحث-مقررات-ملی-ساختمان/"
    try:html,_,_=safe_get(index)
    except Exception:return {}
    soup=BeautifulSoup(html,"html.parser");out={}
    for a in soup.find_all("a",href=True):
        txt=norm(a.get_text(" ",strip=True)); href=urljoin(index,a["href"])
        n=find_chapter_number(txt+" "+href)
        if n and "archweb.ir" in href and ("مبحث" in txt or "%D9%85%D8%A8%D8%AD%D8%AB" in href):
            if "/download/" not in href:out.setdefault(n,href)
    return out

def archweb_pdf(landing):
    """Resolve a downloadable document from an Archweb landing page."""
    html,_,_=safe_get(landing); soup=BeautifulSoup(html,"html.parser")
    candidates=[]
    # WordPress download plugins may expose the URL in href, data-* or inline JS.
    for tag in soup.find_all(True):
        vals=[]
        for key in ("href","data-url","data-downloadurl","data-download","onclick"):
            v=tag.get(key)
            if v: vals.append(str(v))
        txt=norm(tag.get_text(" ",strip=True))
        for v in vals:
            for raw in re.findall(r"https?://[^\"' <>]+|/[^\"' <>]+",v):
                u=urljoin(landing,raw.replace("\\/","/"))
                if (".pdf" in u.lower() or "wpdmdl=" in u or "/download/" in u or "download" in txt) and u!=landing:
                    candidates.append(u)
    # Raw HTML fallback catches JSON-escaped/plugin URLs.
    for raw in re.findall(r"https?:\\?/\\?/[^\"' <>]+|/[^\"' <>]*(?:wpdmdl=|download)[^\"' <>]*",html,re.I):
        candidates.append(urljoin(landing,raw.replace("\\/","/")))
    seen=set()
    for u in candidates:
        if u in seen:continue
        seen.add(u)
        try:
            data,final,ct=safe_get(u,binary=True)
            if data.startswith(b"%PDF-"):return data,final
        except Exception:continue
    return None,None

def source_years(url):
    return set(re.findall(r"(?<!\d)(13\d{2}|14\d{2})(?!\d)",norm(url)))

def edition_ok(url,expected):
    years=source_years(url)
    return not years or str(expected) in years

def document_from_source(source,expected):
    """Resolve an explicit source to PDF bytes without persisting the binary."""
    try:
        if "mediafire.com/" in source:
            direct=mediafire_pdf(source)
            if not direct:return None,None
            if not edition_ok(direct,expected):return None,None
            data,final,_=safe_get(direct,binary=True)
            return (data,final) if data.startswith(b"%PDF-") else (None,None)
        if "archweb.ir/" in source and not source.lower().endswith(".pdf"):
            data,final=archweb_pdf(source)
            if data and edition_ok(final,expected):return data,final
            return None,None
        data,final,ct=safe_get(source,binary=True)
        if data.startswith(b"%PDF-") and edition_ok(final,expected):return data,final
    except Exception:
        pass
    return None,None

def pdf_records(chapter,data,source_url):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tf:
        tf.write(data);tf.flush()
        doc=fitz.open(tf.name)
        pages=[norm(p.get_text("text")) for p in doc]
    total=sum(len(x) for x in pages)
    persian=sum("\u0600"<=c<="\u06ff" for x in pages for c in x)
    letters=sum(c.isalpha() for x in pages for c in x)
    ratio=persian/max(1,letters)
    if total<5000 or ratio<0.45:
        return [],{"pages":len(pages),"chars":total,"persian_ratio":round(ratio,3),"accepted":False}
    out=[];order=0;current=None;last_heading=""
    def flush():
        nonlocal current
        if not current:return
        text=norm(" ".join(current.pop("_parts",[])))
        if len(text)>=25:
            current["text"]=text;current["answer"]=text
            current["normative"]=bool(NORMATIVE_RE.search(text))
            current["numbers"]=[{"value":m.group("value"),"unit":norm(m.group("unit"))} for m in UNIT_RE.finditer(text)][:10]
            current["cross_refs"]=crossrefs(chapter,text,current.get("locator"))
            out.append(current)
        current=None
    for page_i,pt in enumerate(pages,1):
        for raw in pt.splitlines():
            line=norm(raw)
            if len(line)<2:continue
            m=REF_RE.search(line)
            if m and looks_like_locator(chapter,m.group("ref")):
                flush();order+=1
                before=norm(line[:m.start()]).strip(" -–—:؛")
                after=norm(line[m.end():]).strip(" -–—:؛")
                body=after if len(after)>=len(before) else before
                locator=canonical_ref(chapter,m.group("ref"))
                current={"id":f"m{chapter:02d}-{order:05d}","chapter":chapter,"locator":locator,
                         "title":last_heading or f"بند {locator}","kind":"clause","_parts":[body],
                         "page":page_i,"source_url":source_url}
            elif current:
                current["_parts"].append(line)
            elif len(line)<120 and any(k in line for k in ["فصل","کلیات","پیوست","الزامات","تعاریف"]):
                last_heading=line
        # Don't let one malformed clause swallow pages.
        if current and sum(len(x) for x in current["_parts"])>1800:flush()
    flush()
    return dedupe(out),{"pages":len(pages),"chars":total,"persian_ratio":round(ratio,3),"accepted":True}

def crossrefs(chapter,text,locator=None):
    refs=[];seen=set()
    # Other chapters.
    for m in MABHAS_RE.finditer(text):
        raw=norm(m.group("n")); n=int(raw) if raw.isdigit() else NUMWORDS.get(raw)
        if n and 1<=n<=24 and n!=chapter:
            key=("chapter",n)
            if key not in seen:
                seen.add(key);refs.append({"type":"chapter","chapter":n,"label":f"مبحث {n}"})
    # Explicit local/internal references.
    for m in REF_RE.finditer(text):
        raw_ref=refnorm(m.group("ref"))
        first=int(raw_ref.split("-")[0])
        last=int(raw_ref.split("-")[-1])
        target_chapter=first if 1<=first<=24 else (last if 1<=last<=24 else chapter)
        r=canonical_ref(target_chapter,raw_ref)
        if r==locator:continue
        key=("ref",target_chapter,r)
        if key not in seen:
            seen.add(key);refs.append({"type":"ref","chapter":target_chapter,"ref":r,"label":f"بند {r}"})
        if len(refs)>=12:break
    return refs

def dedupe(records):
    out=[];seen=set()
    for r in records:
        key=(r.get("locator"),norm(r.get("text"))[:280])
        if key in seen:continue
        seen.add(key);out.append(r)
    return out

def source_score(records):
    if not records:return 0
    loc=sum(bool(r.get("locator")) for r in records)
    normative=sum(bool(r.get("normative")) for r in records)
    return len(records)+loc*0.7+normative*0.3

def build():
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"chapters").mkdir(parents=True,exist_ok=True)
    discovered=discover_mihansazan()
    archmap=archweb_landing_map()
    catalog=[];all_records=[]
    for c in registry["chapters"]:
        n=c["number"]; candidates=[];attempts=[]
        urls=list(c.get("text_sources") or [])
        if discovered.get(n) and discovered[n] not in urls:urls.append(discovered[n])
        for u in urls:
            try:
                recs,final=html_records(n,u)
                attempts.append({"type":"text","url":u,"records":len(recs),"ok":len(recs)>=12})
                if len(recs)>=12:candidates.append((source_score(recs),recs,final,"structured_text"))
            except Exception as e:
                attempts.append({"type":"text","url":u,"ok":False,"error":type(e).__name__})
        # Searchable document sources. Binaries are fetched transiently and never stored.
        if not candidates or max(x[0] for x in candidates)<120:
            pdf_candidates=[]
            for source in c.get("document_sources") or []:
                data,final=document_from_source(source,c["edition"])
                attempts.append({"type":"document_source","url":source,"resolved":final,"ok":bool(data)})
                if data:pdf_candidates.append((data,final))
            # Generic discovery is fallback only. Reject an explicit edition mismatch.
            if not pdf_candidates:
                landing=archmap.get(n)
                if landing:
                    try:
                        data,final=archweb_pdf(landing)
                        if data and edition_ok(final,c["edition"]):pdf_candidates.append((data,final))
                    except Exception:pass
            if not pdf_candidates:
                try:
                    direct=mediafire_pdf(c["technobetar"])
                    if direct and edition_ok(direct,c["edition"]):
                        data,final,_=safe_get(direct,binary=True)
                        if data.startswith(b"%PDF-"):pdf_candidates.append((data,final))
                except Exception:pass
            for pdf_data,pdf_url in pdf_candidates:
                try:
                    recs,qa=pdf_records(n,pdf_data,pdf_url)
                    attempts.append({"type":"document","url":pdf_url,"records":len(recs),**qa})
                    if qa.get("accepted") and len(recs)>=12:
                        candidates.append((source_score(recs),recs,pdf_url,"searchable_document"))
                        break
                except Exception as e:
                    attempts.append({"type":"document","url":pdf_url,"ok":False,"error":type(e).__name__})
        if candidates:
            candidates.sort(key=lambda x:x[0],reverse=True)
            _,records,chosen,method=candidates[0]
            status="ready"
        else:
            records=[];chosen=None;method=None;status="source_needed"
        payload={"chapter":n,"title":c["title"],"edition":c["edition"],"status":status,
                 "record_count":len(records),"records":records}
        (OUT/"chapters"/f"m{n:02d}.json").write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
        cat={"number":n,"id":c["id"],"title":c["title"],"edition":c["edition"],"status":status,
             "record_count":len(records),"source":chosen,"method":method,"attempts":attempts}
        catalog.append(cat);all_records.extend(records)
        print(f"M{n:02d} {status} records={len(records)} source={chosen}",flush=True)
        if status!="ready":
            print("  attempts="+json.dumps(attempts,ensure_ascii=False)[:5000],flush=True)
        time.sleep(.15)
    coverage={"chapters_total":24,"chapters_ready":sum(x["status"]=="ready" for x in catalog),
              "records_total":sum(x["record_count"] for x in catalog),
              "chapters":catalog}
    index=[]
    for r in all_records:
        item={k:r.get(k) for k in ["id","chapter","locator","title","kind","answer","normative","numbers","cross_refs","source_url","page"]}
        if item.get("answer") and len(item["answer"])>1200:item["answer"]=item["answer"][:1200]+"…"
        index.append(item)
    (OUT/"catalog.json").write_text(json.dumps(catalog,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    (OUT/"coverage.json").write_text(json.dumps(coverage,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    (OUT/"search-index.json").write_text(json.dumps(index,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print("READY",coverage["chapters_ready"],"/24","RECORDS",coverage["records_total"],flush=True)
    if coverage["chapters_ready"]<18:
        print("Too few chapters passed the text-quality gate",file=sys.stderr)
        return 2
    return 0

if __name__=="__main__":
    raise SystemExit(build())
