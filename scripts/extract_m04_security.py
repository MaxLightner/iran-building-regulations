"""Archive and extract the linked 1403 protective/security appendix of m04.

Unverified source copy from a cited media document. Do not silently infer
legality, dates or applicability from news reporting. All structured records
remain PENDING until visual and source review.
"""
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
import hashlib, json, re, os, subprocess
import fitz

ROOT=Path(__file__).resolve().parents[1]
SOURCE="https://newsmedia.tasnimnews.ir/Tasnim/Uploaded/Document/1404/01/23/140401231106219313256425.pdf"
PDF=ROOT/"sources/pdfs/m04-security-1403.pdf"
PAGES=ROOT/"data/extracted/m04-security-1403/pages"
RECORDS=ROOT/"data/records/m04-security-1403.json"
REPORT=ROOT/"data/analysis/m04-security-quality.json"
HEADER=re.compile(r"(?<!\w)(?:پ\s*[-ـ–]?\s*)?[\d۰-۹٠-٩]{1,3}(?:\s*[-ـ–]\s*[\d۰-۹٠-٩]{1,3}){1,4}")
NUMERIC=re.compile(r"(?<!\w)[\d۰-۹٠-٩]+(?:[/.٫][\d۰-۹٠-٩]+)?")
DIGITS=str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩","01234567890123456789")

def download():
    if PDF.exists() and PDF.stat().st_size>1000:
        if PDF.read_bytes()[:5]==b"%PDF-":
            return
    req=Request(SOURCE,headers={"User-Agent":"Mozilla/5.0","Accept":"application/pdf"})
    with urlopen(req,timeout=45) as res:
        if res.url.split("/")[2].lower()!="newsmedia.tasnimnews.ir":
            raise ValueError("Unexpected document redirect")
        raw=res.read(20*1024*1024+1)
    if len(raw)>20*1024*1024 or raw[:5]!=b"%PDF-":
        raise ValueError("Source not a PDF or too large")
    PDF.parent.mkdir(parents=True,exist_ok=True)
    PDF.write_bytes(raw)

def is_good_text(t):
    letters=sum(("\u0600"<=c<="\u06ff") for c in t)
    return len(t.strip())>200 and letters>max(60,len(t)*0.33)

def scan(doc,page_index,source_sha):
    p=doc[page_index]
    raw=p.get_text("text",sort=True)
    method="embedded_pdf_text"
    if not is_good_text(raw):
        pix=p.get_pixmap(matrix=fitz.Matrix(3,3),alpha=False)
        image=pix.tobytes("png")
        cmd=["tesseract","stdin","stdout","-l","fas+eng","--psm","3"]
        run=subprocess.run(cmd,input=image,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                           timeout=160,env={**os.environ,"OMP_THREAD_LIMIT":"1"})
        if run.returncode:
            raise RuntimeError("OCR failed on appendix page "+str(page_index+1))
        raw=run.stdout.decode("utf-8","replace")
        method="tesseract_fas_eng"
    lines=[x.strip() for x in raw.splitlines() if x.strip()]
    return {"pdf_page":page_index+1,"source_sha256":source_sha,"ocr_text":raw.strip(),
        "lines":lines,"method":method,"chars":len(raw.strip()),
        "review_status":"pending_manual_comparison"}

def main():
    download()
    source_sha=hashlib.sha256(PDF.read_bytes()).hexdigest()
    d=fitz.open(PDF)
    PAGES.mkdir(parents=True,exist_ok=True)
    pages=[]
    for i in range(len(d)):
        p=scan(d,i,source_sha)
        (PAGES/f"{i+1:04d}.json").write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        pages.append(p)
        print("appendix page",i+1,len(d),p["method"],p["chars"],flush=True)
    d.close()
    records=[];active=None;unassigned=0
    for page in pages:
        for n,line in enumerate(page["lines"],1):
            hit=HEADER.search(line[:55])
            # Do not confuse free-standing numeric values with section locators.
            if hit and hit.start()<15 and len(hit.group())>=3:
                if active:records.append(active)
                active={"pdf_page":page["pdf_page"],"end_page":page["pdf_page"],
                        "ocr_line":n,"locator":hit.group(),
                        "title":line[hit.end():].strip()[:160] or "عنوان نیازمند تصحیح",
                        "text":[line]}
            elif active:
                active["text"].append(line)
                active["end_page"]=page["pdf_page"]
            else:
                unassigned+=1
    if active:records.append(active)
    structured=[]
    for n,r in enumerate(records,1):
        t="\n".join(r["text"]).strip()
        nums=[x.group() for x in NUMERIC.finditer(t)]
        structured.append({
           "id":f"m04-security-1403-ocr-{n:04d}",
           "document_id":"m4-security-1403",
           "edition_id":"m4-security-1403-unverified",
           "section_id":None, "kind":"clause","locator":r["locator"],
           "title":r["title"],"original_text":t,
           "summary":"","topic":"ضوابط حفاظتی و انتظامی",
           "tags":["امنیت ساختمان","حفاظت","پیوست مبحث چهارم"],"aliases":[],
           "key_factors":[],"applicability":{"status":"not_evaluated","conditions":[]},
           "references":[],
           "source":{"authority":"secondary","official_page_url":"https://inbr.ir/دانلود-مبحث-چهارم/",
                 "official_pdf_url":None,"sha256":source_sha,
                 "pdf_page":r["pdf_page"],"printed_page":None,
                 "publication_rights":"unverified"},
           "version":{"edition_label":"پیوست حفاظتی انتظامی ۱۴۰۳ ـ تطبیق نشده",
                "published_date":None,"effective_date":None,"effective_evidence":None,
                "status":"unconfirmed","last_checked":None},
           "review":{"status":"pending","reviewer":None,"reviewed_at":None},
           "extraction":{"status":"unverified","method":"embedded_or_ocr_v1",
               "start_pdf_page":r["pdf_page"],"end_pdf_page":r["end_page"],
               "start_ocr_line":r["ocr_line"],"numeric_candidates_unverified":nums[:50],
               "kind_is_inferred":True,"notes":["Requires check with original document and signed circular"]}
        })
    RECORDS.parent.mkdir(parents=True,exist_ok=True)
    RECORDS.write_text(json.dumps({"schema_version":"1.0","document_id":"m4-security-1403",
         "source_pdf_sha256":source_sha,"source_url":SOURCE,
         "workflow_status":"EXTRACTED_PENDING_OFFICIAL_AND_VISUAL_REVIEW",
         "records":structured},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps({
        "source_url":SOURCE,"source_type":"news_embedded_pdf_not_official_domain",
        "source_sha256":source_sha,"pdf_pages":len(pages),"extracted_pages":len(pages),
        "nonempty_pages":sum(p["chars"]>0 for p in pages),
        "methods":{m:sum(p["method"]==m for p in pages) for m in sorted(set(p["method"] for p in pages))},
        "candidate_numbered_records":len(structured),"unassigned_lines":unassigned,
        "review_status":"pending_official_document_comparison",
        "note":"Appendix is reportedly legally effective; legal scope and dates require signed official evidence, no rules approved.",
        "generated_at":datetime.now(timezone.utc).isoformat()
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Appendix extracted, candidate sections",len(structured),flush=True)

if __name__=="__main__": main()
