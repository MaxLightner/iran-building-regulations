#!/usr/bin/env python3
"""Build a clean M04 rule preview from the scanned PDF.

Pipeline:
PDF -> higher-resolution OCR -> clause segmentation -> normative rules ->
facts / conditions / exceptions / topics -> compact preview JSON.

This is an evaluation preview. It does not assert legal-currentness.
"""
from __future__ import annotations
from pathlib import Path
import json,re,subprocess,tempfile,unicodedata
import fitz

ROOT=Path(__file__).resolve().parents[1]
PDF=ROOT/"sources/pdfs/reference-m04.pdf"
FALLBACK=ROOT/"data/extracted/m04/pages"
OUT=ROOT/"frontend/m04-preview/data/rules.json"

DIGITS=str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩","01234567890123456789")
CLAUSE=re.compile(r"^\s*((?:[\d۰-۹٠-٩]{1,3}\s*[-ـ–—]\s*){1,5}[\d۰-۹٠-٩]{1,3})\s+(.+)$")
NORMATIVE=re.compile(r"(باید|نباید|الزام|مجاز|ممنوع|ضروری|حداقل|حداکثر|لازم است|اجازه داده|می ?تواند|می ?توان)")
COND=re.compile(r"(در\s*صورت|چنانچه|اگر|هرگاه|مشروط|به\s*شرط|به\s*استثنای|به\s*جز|مگر)")
EXCEPT=re.compile(r"(استثنا|به\s*استثنای|به\s*جز|مگر|تبصره)")
NUM=re.compile(r"(?P<v>[\d۰-۹٠-٩]+(?:[/.٫][\d۰-۹٠-٩]+)?)\s*(?P<u>میلی\s*متر|سانتی\s*متر|متر(?:\s*مربع)?|درصد|درجه|طبقه|واحد|نفر)")
LATIN_NOISE=re.compile(r"[A-Za-z]{2,}")

TOPICS={
 "stairs":{"label":"راه‌پله و پلکان","aliases":["راه پله","راه‌پله","پلکان","پله","کف پله","دستگرد"]},
 "parking":{"label":"پارکینگ و توقفگاه","aliases":["پارکینگ","توقفگاه","خودرو","رمپ پارکینگ","شیبراه"]},
 "light":{"label":"نورگیری و پنجره","aliases":["نورگیر","نورگیری","نور طبیعی","پنجره","جداره نورگذر"]},
 "guard":{"label":"جان‌پناه و حفاظ","aliases":["جان پناه","جان‌پناه","حفاظ","نرده","دست انداز","دست‌انداز"]},
 "ramp":{"label":"رمپ و شیبراه","aliases":["رمپ","شیبراه","شیب راه","سطح شیبدار"]},
 "room":{"label":"فضاهای داخلی","aliases":["اتاق","فضای اقامت","آشپزخانه","فضای سکونت","مسکونی"]},
 "access":{"label":"دسترسی و ورودی","aliases":["دسترسی","ورودی","در ورودی","راهرو","معلول","ویلچر"]},
 "height":{"label":"ارتفاع و ابعاد","aliases":["ارتفاع","حداقل عرض","حداقل ارتفاع","عرض مفید","ابعاد"]},
 "balcony":{"label":"بالکن و فضای نیمه‌باز","aliases":["بالکن","تراس","فضای نیمه باز","نیمه‌باز"]},
 "occupancy":{"label":"کاربری و تصرف","aliases":["تصرف","کاربری","مسکونی","تجاری","اداری"]},
}

SYNONYMS={
 "راه پله":["راه پله","راه‌پله","پلکان","پله"],
 "پارکینگ":["پارکینگ","توقفگاه","خودرو"],
 "نورگیری":["نورگیری","نورگیر","نور طبیعی","پنجره"],
 "جان پناه":["جان پناه","جان‌پناه","حفاظ","نرده"],
 "رمپ":["رمپ","شیبراه","شیب راه"],
 "اتاق":["اتاق","فضای اقامت","فضای سکونت"],
 "بالکن":["بالکن","تراس","نیمه باز","نیمه‌باز"],
 "دسترسی":["دسترسی","راهرو","ورودی","ویلچر","معلول"],
}

def norm(s):
    s=unicodedata.normalize("NFKC",str(s or "")).translate(DIGITS)
    s=s.replace("ي","ی").replace("ك","ک").replace("ى","ی").replace("\u200c"," ")
    s=re.sub(r"[\u064b-\u065f\u0670\u200e-\u200f]","",s)
    s=re.sub(r"\s+"," ",s)
    return s.strip()

def clean(s):
    s=norm(s)
    s=s.replace("مبحثچهارم","").replace("مبحث چهارم","")
    s=re.sub(r"\s*([،؛:.])\s*",r"\1 ",s)
    s=re.sub(r"(?<=[اآبپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی])(?=(?:است|باشد|شود|گردد|مجاز|الزامی|ساختمان|فضا|عرض|ارتفاع)\b)", " ", s)
    s=re.sub(r"\s+"," ",s).strip(" -،؛:.")
    return s

def quality(text):
    if not text:return -999
    p=sum("\u0600"<=c<="\u06ff" for c in text)
    latin=len(LATIN_NOISE.findall(text))
    clauses=len(re.findall(r"(?m)^\s*(?:[\d۰-۹٠-٩]{1,3}\s*[-ـ–—]\s*){2,}",text))
    return p/50 + clauses*8 - latin*4 - text.count("�")*20

def tesseract_page(doc,page_no,tmp):
    page=doc[page_no-1]
    pix=page.get_pixmap(matrix=fitz.Matrix(300/72,300/72),colorspace=fitz.csGRAY,alpha=False)
    img=tmp/f"p{page_no:04d}.png"; pix.save(str(img))
    candidates=[]
    for psm in ("6","4"):
        cmd=["tesseract",str(img),"stdout","-l","fas+eng","--psm",psm,
             "-c","preserve_interword_spaces=1"]
        out=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True).stdout.decode("utf-8","ignore")
        candidates.append(out)
    fb=FALLBACK/f"{page_no:04d}.json"
    if fb.exists():
        try:candidates.append(json.loads(fb.read_text(encoding="utf-8")).get("ocr_text",""))
        except Exception:pass
    return max(candidates,key=quality)

def segment_page(text,page_no):
    lines=[clean(x) for x in text.splitlines()]
    lines=[x for x in lines if x and not re.fullmatch(r"\d{1,3}",x)]
    segs=[];cur=None
    for line in lines:
        m=CLAUSE.match(line)
        if m:
            if cur:segs.append(cur)
            cur={"locator":norm(m.group(1)).replace(" ",""),"lines":[clean(m.group(2))],"page":page_no}
        elif cur:
            cur["lines"].append(line)
    if cur:segs.append(cur)
    return segs

def topic_ids(text):
    n=norm(text)
    scored=[]
    for tid,t in TOPICS.items():
        score=sum(n.count(norm(a)) for a in t["aliases"])
        if score:scored.append((score,tid))
    scored.sort(reverse=True)
    return [tid for _,tid in scored[:3]]

def facts(text):
    out=[];seen=set()
    for m in NUM.finditer(text):
        value=m.group("v");unit=norm(m.group("u"))
        key=(value,unit)
        if key in seen:continue
        seen.add(key)
        a=max(0,m.start()-55);b=min(len(text),m.end()+80)
        out.append({"value":value,"unit":unit,"context":clean(text[a:b])})
        if len(out)>=5:break
    return out

def sentences(text):
    return [clean(x) for x in re.split(r"(?<=[.؟؛])\s+|\n+",text) if len(clean(x))>12]

def extract_rule(seg):
    text=clean(" ".join(seg["lines"]))
    if len(text)<45:return None
    if not (NORMATIVE.search(text) or NUM.search(text)):return None
    ts=topic_ids(text)
    if not ts:return None
    sents=sentences(text)
    normative=[s for s in sents if NORMATIVE.search(s) or NUM.search(s)]
    statement=(normative[0] if normative else sents[0])[:520]
    conditions=[s[:360] for s in sents if COND.search(s)][:4]
    exceptions=[s[:360] for s in sents if EXCEPT.search(s)][:3]
    fs=facts(text)
    primary=TOPICS[ts[0]]["label"]
    title=primary
    # Add the most informative first phrase without dumping OCR.
    if statement:
        short=re.split(r"[؛,.]",statement)[0].strip()
        if 12<=len(short)<=95:title=short
    noise=len(LATIN_NOISE.findall(text))
    persian=sum("\u0600"<=c<="\u06ff" for c in text)
    conf=max(0,min(1,0.55+(0.12 if seg["locator"] else 0)+(0.1 if fs else 0)+(0.08 if NORMATIVE.search(text) else 0)-noise*0.03))
    return {
      "id":f"m04-r-{seg['page']:03d}-{seg['locator']}",
      "locator":seg["locator"],"page":seg["page"],"title":title,
      "statement":statement,"facts":fs,"conditions":conditions,"exceptions":exceptions,
      "topics":ts,"topic_labels":[TOPICS[x]["label"] for x in ts],
      "source_text":text,"confidence":round(conf,2),
      "search_text":norm(" ".join([title,statement,text]+[TOPICS[x]["label"] for x in ts]))
    }

def dedupe(rules):
    out=[];seen=set()
    for r in sorted(rules,key=lambda x:(x["page"],x["locator"])):
        key=(r["locator"],norm(r["statement"])[:160])
        if key in seen:continue
        seen.add(key);out.append(r)
    return out

def build():
    doc=fitz.open(PDF)
    rules=[]
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td)
        for p in range(1,len(doc)+1):
            text=tesseract_page(doc,p,tmp)
            for seg in segment_page(text,p):
                r=extract_rule(seg)
                if r:rules.append(r)
            if p%10==0:print("OCR/rules",p,"/",len(doc),"rules",len(rules),flush=True)
    rules=dedupe(rules)
    payload={
      "schema_version":"m04-preview-1",
      "status":"preview_rules_not_legally_validated",
      "document":{"id":"m04","title":"مبحث چهارم — الزامات عمومی ساختمان","pages":len(doc)},
      "sample_project":{"city":"مشهد","use":"مسکونی","structure":"بتن‌آرمه","floors":7,"basements":2,"stage":"طراحی"},
      "topics":{k:v["label"] for k,v in TOPICS.items()},
      "synonyms":SYNONYMS,
      "rule_count":len(rules),"rules":rules
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print("M04 preview rules:",len(rules))

if __name__=="__main__":build()
