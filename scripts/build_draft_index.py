"""Create private-build, source-linked page-search shards, not approved legal clauses.

The page is the durable search unit. OCR '843 candidates' stay in research files,
never become 843 top-level navigation entries. Source and OCR status are visible.
This script writes into frontend/data/ but the Pages workflow currently NEVER deploys.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import hashlib
import json
import re
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"frontend"/"data"/"draft"
PAGES=ROOT/"data"/"extracted"
PDF=ROOT/"sources"/"pdfs"
REPO="https://raw.githubusercontent.com/MaxLightner/iran-building-regulations/main/sources/pdfs/"
TOPICS = {
    "حریق و ایمنی":["حریق","آتش","آتش سوزی","راه خروج","دود","خاموش کننده","مقاومت در برابر آتش"],
    "راه‌پله و دسترسی":["پله","راه پله","راه‌پله","رمپ","دسترس پذیری","ویلچر","شیبراه","دستگرد"],
    "پارکینگ و توقفگاه":["پارکینگ","توقفگاه","خودرو","اتومبیل","مانور"],
    "ابعاد و ارتفاع":["ارتفاع","عرض","ابعاد","اندازه","فاصله","زیربنا","مساحت"],
    "نورگیری و تهویه":["روشنایی","نورگیری","نور طبیعی","تهویه","پنجره"],
    "فضا و کاربری":["مسکونی","تجاری","اداری","تجمعی","تصرف","فضاهای ساختمان"],
    "پوشش و مصالح":["مصالح","فرآورده","سنگ","آجر","سیمان","بتن","پوشش","عایق"],
    "آسانسور و پله‌برقی":["آسانسور","آسانسورها","پلکان برقی","پله برقی","چاه آسانسور"],
    "تأسیسات و تجهیزات":["تاسیسات","تأسیسات","برق","لوله","گرمایش","تهویه مطبوع"],
    "محوطه و جان‌پناه":["حیاط","جان پناه","جان‌پناه","بالکن","محوطه","بام"]
}
SPECS=[
    ("m03",3,"حریق و ایمنی","reference-m03.pdf","حریق و ایمنی"),
    ("m04",4,"الزامات عمومی ساختمان","reference-m04.pdf","فضا و کاربری"),
    ("m04-security-1403",4,"پیوست حفاظتی انتظامی مبحث چهارم","m04-security-1403.pdf","فضا و کاربری"),
    ("m05",5,"مصالح و فرآورده‌های ساختمانی","reference-m05.pdf","پوشش و مصالح"),
    ("m15",15,"آسانسور و پلکان برقی","reference-m15.pdf","آسانسور و پله‌برقی")
]
PERSIAN="".join(chr(i) for i in range(0x0621,0x065b))

def norm(value):
    s=unicodedata.normalize("NFKC",str(value or ""))
    s=s.translate(str.maketrans("يكىۀ‌","یکیه "))
    s=re.sub(r"[\u064b-\u065f\u0670\u200e-\u200f]","",s)
    s=s.replace("أ","ا").replace("إ","ا")
    return " ".join(s.casefold().split())

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")

def topics_for(text, default_topic):
    text=norm(text)
    scores=[]
    for name,terms in TOPICS.items():
        score=sum(text.count(norm(term)) for term in terms)
        if score: scores.append((score,name))
    scores.sort(key=lambda x:(-x[0],x[1]))
    names=[default_topic]
    for score,name in scores[:3]:
        if name not in names: names.append(name)
    return names[:4]

def valid_source(docid,filename,rows):
    pdf=PDF/filename
    if not pdf.is_file():raise ValueError("PDF not present: "+filename)
    digest=hashlib.sha256(pdf.read_bytes()).hexdigest()
    for p in rows:
        if p.get("source_sha256")!=digest:
            raise ValueError("Page hash mismatch: "+docid+" page "+str(p.get("pdf_page")))
    return digest

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    summaries=[]
    all_count=0
    for docid,number,label,pdfname,default_topic in SPECS:
        folder=PAGES/docid/"pages"
        if not folder.is_dir():continue
        filenames=sorted(folder.glob("*.json"))
        if not filenames:continue
        rows=[read(p) for p in filenames]
        if [p.get("pdf_page") for p in rows] != list(range(1,len(rows)+1)):
            raise ValueError("Page gaps in "+docid)
        digest=valid_source(docid,pdfname,rows)
        entries=[]
        counts=Counter()
        for row in rows:
            page=row["pdf_page"]
            content=(row.get("ocr_text") or "").strip()
            ts=topics_for(content,default_topic) if content else [default_topic]
            for topic in ts: counts[topic]+=1
            entries.append({
                "id":docid+"-p"+str(page).zfill(4),
                "pdf_page":page,
                "text":content,
                "topics":ts,
                "method":row.get("method","unknown"),
                "quality_flags":row.get("quality_flags",[]),
                "search_text":norm(content),
            })
        save(OUT/(docid+".json"),{
            "schema_version":"1.0","status":"unverified_pdf_transcription",
            "document_id":docid,"chapter":number,"title":label,
            "pdf_sha256":digest,"pdf_url":REPO+pdfname,"pages":entries
        })
        summaries.append({"id":docid,"chapter":number,"title":label,
            "pdf_url":REPO+pdfname,"pages":len(entries),
            "nonempty_pages":sum(bool(p["text"]) for p in entries),
            "topics":dict(counts),"index_file":"./data/draft/"+docid+".json",
            "status":"unverified_pdf_transcription"})
        all_count+=len(entries)
    save(OUT/"manifest.json",{"schema_version":"1.0","status":"unverified_pdf_transcription",
        "description":"Page-grounded searchable OCR. Do not treat as verified technical rule.",
        "documents":summaries,"indexed_pages":all_count,
        "documents_indexed":len(summaries)})
    print("Draft index:",len(summaries),"documents,",all_count,"pages")
    return summaries

if __name__=="__main__":
    build()
