"""Build a structured, searchable knowledge layer from the extracted regulation PDFs.

This is deliberately source-grounded and deterministic:
page text -> clause-like records -> topics -> numeric facts -> conditions -> references.
The original PDF page remains provenance, but normal search consumes these records.

Current source editions are not asserted as legally current. The purpose of this layer
is functional retrieval over the archived PDFs.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import json
import re
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
DRAFT=ROOT/"frontend"/"data"/"draft"
OUT=ROOT/"frontend"/"data"/"knowledge"

# Product ontology: deliberately compact. Related topics are explicit so a query can
# discover adjacent requirements without pairwise-linking thousands of records.
ONTOLOGY={
 "fire":{"label":"حریق و ایمنی","aliases":["حریق","آتش","آتش سوزی","راه خروج","خروج اضطراری","دود","مقاومت حریق","خاموش کننده"],"related":["stairs","occupancy","materials","installations"]},
 "stairs":{"label":"راه‌پله و دسترسی","aliases":["راه پله","راه‌پله","پله","پلکان","دستگرد","رمپ","شیبراه","دسترسی","ویلچر"],"related":["fire","dimensions","elevator","occupancy"]},
 "parking":{"label":"پارکینگ و توقفگاه","aliases":["پارکینگ","توقفگاه","خودرو","اتومبیل","رمپ پارکینگ","مانور"],"related":["dimensions","occupancy","fire"]},
 "dimensions":{"label":"ابعاد و ارتفاع","aliases":["ارتفاع","عرض","طول","ابعاد","اندازه","فاصله","مساحت","زیربنا","حداقل عرض","حداکثر ارتفاع"],"related":["stairs","parking","occupancy","yard"]},
 "light":{"label":"نورگیری و تهویه","aliases":["نورگیری","نور طبیعی","روشنایی","تهویه","پنجره","هوا"],"related":["occupancy","dimensions","installations"]},
 "occupancy":{"label":"فضا و کاربری","aliases":["مسکونی","تجاری","اداری","تجمعی","تصرف","کاربری","فضاهای ساختمان","اتاق","آشپزخانه"],"related":["dimensions","fire","stairs","parking","light"]},
 "materials":{"label":"پوشش و مصالح","aliases":["مصالح","فرآورده","سنگ","آجر","سیمان","قیر","عایق","پوشش","بتن"],"related":["fire","concrete_steel","geotech"]},
 "elevator":{"label":"آسانسور و پله‌برقی","aliases":["آسانسور","پله برقی","پلکان برقی","چاه آسانسور","کابین آسانسور"],"related":["stairs","installations","dimensions","fire"]},
 "installations":{"label":"تأسیسات و تجهیزات","aliases":["تاسیسات","تأسیسات","برق","لوله","گرمایش","تهویه مطبوع","تجهیزات"],"related":["fire","light","elevator"]},
 "yard":{"label":"محوطه و جان‌پناه","aliases":["حیاط","محوطه","جان پناه","جان‌پناه","بالکن","بام","حفاظ"],"related":["dimensions","fire"]},
 "loads":{"label":"سازه و بارگذاری","aliases":["بار زنده","بار مرده","بار باد","بار برف","بارگذاری","زلزله","ترکیب بار","تحلیل سازه","بار جانبی"],"related":["concrete_steel","geotech"]},
 "geotech":{"label":"ژئوتکنیک و پی","aliases":["ژئوتکنیک","خاک","گودبرداری","پی سازی","پی‌سازی","پی","شمع","نشست","ظرفیت باربری"],"related":["loads","concrete_steel","materials"]},
 "concrete_steel":{"label":"بتن و فولاد","aliases":["بتن آرمه","بتن‌آرمه","میلگرد","آرماتور","فولاد","جوش","پیچ","اتصال فولادی","اتصالات فولادی"],"related":["loads","geotech","materials","fire"]},
 "security":{"label":"حفاظت و امنیت","aliases":["حفاظتی","انتظامی","امنیت","سرقت","دوربین","کنترل دسترسی"],"related":["occupancy","installations","yard"]},
}
DEFAULT_BY_DOC={"m03":"fire","m04":"occupancy","m04-security-1403":"security","m05":"materials",
                "m06":"loads","m07":"geotech","m09":"concrete_steel","m10":"concrete_steel","m15":"elevator"}

DIGITS=str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩","01234567890123456789")
LOCATOR=re.compile(r"(?<![\d./])(?:[\d۰-۹٠-٩]{1,3}\s*[-ـ–—]\s*){1,6}[\d۰-۹٠-٩]{1,3}(?!\d)")
HEADLINE=re.compile(r"^(?:فصل|بخش|گفتار|پیوست|ضمیمه)\s+.{2,120}$")
CONDITION=re.compile(r"(?:در\s+صورت|درصورتی|چنانچه|اگر|هرگاه|زمانی\s+که|به\s+شرط|مشروط|باید|نباید|الزامی|مجاز\s+نیست|حداقل|حداکثر|بیش\s+از|کمتر\s+از)")
UNITS=r"(?:میلی\s*متر|سانتی\s*متر|متر(?:\s*مربع|\s*مکعب)?|درصد|درجه|طبقه|نفر|خودرو|کیلو\s*گرم|تن|کیلو\s*نیوتن|نیوتن|مگا\s*پاسکال|مگاپاسکال|پاسکال|ساعت|دقیقه|ثانیه)"
NUMBER_FACT=re.compile(r"(?P<value>[\d۰-۹٠-٩]+(?:[/.٫][\d۰-۹٠-٩]+)?)\s*(?P<unit>"+UNITS+r")")
MABHAS_REF=re.compile(r"مبحث\s+(?P<name>[\w\u200c‌]+)")
TABLE_REF=re.compile(r"(?:جدول|شکل|بند)\s*[\d۰-۹٠-٩]+(?:\s*[-ـ–—]\s*[\d۰-۹٠-٩]+)*")

def norm(value):
    s=unicodedata.normalize("NFKC",str(value or ""))
    s=s.translate(str.maketrans("يكىۀ‌","یکیه "))
    s=re.sub(r"[\u064b-\u065f\u0670\u200e-\u200f]","",s)
    s=s.replace("أ","ا").replace("إ","ا")
    return " ".join(s.casefold().split())

def read(path): return json.loads(path.read_text(encoding="utf-8"))
def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")

def score_topics(text,default):
    folded=norm(text)
    scored=[]
    for tid,t in ONTOLOGY.items():
        score=sum(folded.count(norm(alias)) for alias in t["aliases"])
        if score: scored.append((score,tid))
    scored.sort(key=lambda x:(-x[0],x[1]))
    ids=[default]
    for score,tid in scored[:4]:
        if tid not in ids: ids.append(tid)
    return ids[:4]

def clean_line(line):
    return " ".join(str(line).replace("\u200f","").replace("\u200e","").split())

def split_page(text):
    lines=[clean_line(x) for x in str(text or "").splitlines() if clean_line(x)]
    if not lines:return []
    segments=[]; current=[]; locator=None; title=None
    def flush():
        nonlocal current,locator,title
        body="\n".join(current).strip()
        if body:
            segments.append({"locator":locator,"title":title,"text":body})
        current=[];locator=None;title=None
    for line in lines:
        hit=LOCATOR.search(line[:45])
        heading=HEADLINE.match(line)
        if hit and hit.start()<16:
            flush()
            locator=hit.group().replace(" ","")
            rest=line[hit.end():].strip(" -–—:؛،.")
            title=rest[:170] if rest else None
            current=[line]
        elif heading and current:
            flush(); title=line[:170]; current=[line]
        else:
            current.append(line)
            if title is None and len(line)<=100 and not line.endswith((".", "،","؛")):
                title=line[:170]
    flush()
    # Avoid one-record-per-short-line noise; adjacent tiny fragments are kept with page record.
    meaningful=[x for x in segments if len(norm(x["text"]))>=45]
    if not meaningful:
        meaningful=[{"locator":None,"title":lines[0][:170],"text":"\n".join(lines)}]
    return meaningful

def sentence_summary(text,title):
    body=norm(text)
    # Preserve original chars for display; deterministic extractive summary, no invented rule.
    original=" ".join(str(text).split())
    if title and original.startswith(" ".join(title.split())):
        original=original[len(" ".join(title.split())):].lstrip(" .،؛:-")
    parts=re.split(r"(?<=[.!؟؛])\s+",original)
    summary=" ".join(parts[:2]).strip()
    return (summary[:420] if summary else str(title or "")[:420])

def extract_facts(text):
    result=[];seen=set()
    for hit in NUMBER_FACT.finditer(text):
        value=hit.group("value");unit=" ".join(hit.group("unit").split())
        key=(norm(value),norm(unit))
        if key in seen:continue
        seen.add(key)
        left=max(0,hit.start()-70);right=min(len(text),hit.end()+90)
        context=" ".join(text[left:right].split())
        result.append({"value":value,"unit":unit,"context":context[:220]})
        if len(result)>=14:break
    return result

def extract_conditions(text):
    out=[];seen=set()
    for raw in re.split(r"[\n.!؟؛]+",text):
        line=" ".join(raw.split())
        if len(line)<12 or not CONDITION.search(line):continue
        key=norm(line)
        if key in seen:continue
        seen.add(key);out.append(line[:360])
        if len(out)>=8:break
    return out

def extract_refs(text):
    out=[];seen=set()
    for m in MABHAS_REF.finditer(text):
        val=m.group(0).strip()
        if norm(val) not in seen: out.append({"type":"chapter","label":val});seen.add(norm(val))
    for m in TABLE_REF.finditer(text):
        val=m.group(0).strip()
        if norm(val) not in seen: out.append({"type":"internal","label":val});seen.add(norm(val))
    return out[:12]

def build():
    manifest=read(DRAFT/"manifest.json")
    OUT.mkdir(parents=True,exist_ok=True)
    documents=[];topic_counts=Counter();total_records=0;total_facts=0;total_conditions=0
    global_topic_records=defaultdict(list)
    for doc in manifest["documents"]:
        docid=doc["id"]
        default=DEFAULT_BY_DOC.get(docid)
        if not default:continue
        source=read(DRAFT/(docid+".json"))
        records=[];counter=0
        for page in source["pages"]:
            for seg in split_page(page["text"]):
                counter+=1
                topics=score_topics(seg["text"],default)
                facts=extract_facts(seg["text"])
                conditions=extract_conditions(seg["text"])
                refs=extract_refs(seg["text"])
                title=seg["title"] or (ONTOLOGY[topics[0]]["label"]+" — صفحه "+str(page["pdf_page"]))
                rid=f"{docid}-k{counter:05d}"
                record={
                    "id":rid,"document_id":docid,"chapter":doc["chapter"],
                    "document_title":doc["title"],"locator":seg["locator"],
                    "title":title[:170],"summary":sentence_summary(seg["text"],title),
                    "text":seg["text"],"topics":topics,
                    "topic_labels":[ONTOLOGY[x]["label"] for x in topics],
                    "related_topics":sorted({r for t in topics for r in ONTOLOGY[t]["related"] if r not in topics}),
                    "facts":facts,"conditions":conditions,"references":refs,
                    "source":{"pdf_page":page["pdf_page"],"pdf_url":source["pdf_url"],
                              "quality_flags":page.get("quality_flags",[]),"method":page.get("method")},
                    "search_text":norm(" ".join([title,seg["text"]," ".join(ONTOLOGY[t]["label"] for t in topics)])),
                    "status":"unverified_structured_from_pdf"
                }
                records.append(record);total_records+=1;total_facts+=len(facts);total_conditions+=len(conditions)
                for t in topics:
                    topic_counts[t]+=1
                    if len(global_topic_records[t])<80: global_topic_records[t].append(rid)
        save(OUT/(docid+".json"),{"schema_version":"1.0","status":"unverified_structured_knowledge",
            "document":doc,"records":records})
        documents.append({"id":docid,"chapter":doc["chapter"],"title":doc["title"],
                          "records":len(records),"index_file":"./data/knowledge/"+docid+".json"})
    ontology_public={tid:{"label":x["label"],"aliases":x["aliases"],"related":x["related"],
                          "record_count":topic_counts[tid],
                          "sample_record_ids":global_topic_records[tid]} for tid,x in ONTOLOGY.items()}
    save(OUT/"ontology.json",{"schema_version":"1.0","topics":ontology_public})
    save(OUT/"manifest.json",{"schema_version":"1.0","status":"unverified_structured_knowledge",
        "documents":documents,"documents_indexed":len(documents),"records":total_records,
        "facts":total_facts,"conditions":total_conditions,
        "topics":{tid:topic_counts[tid] for tid in ONTOLOGY}})
    print("Knowledge:",len(documents),"docs",total_records,"records",total_facts,"facts",total_conditions,"conditions")
    return documents

if __name__=="__main__": build()
