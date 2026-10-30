#!/usr/bin/env python3
"""Build clause-level (not page-chunk) records directly from a PDF's text layer.
No OCR, no fixed-length chunking. Preserve exact multi-part clause numbers.
"""
from __future__ import annotations
import json
import re
import sys
import unicodedata
from pathlib import Path
import fitz
import requests

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"frontend/data/clause-text"
NORM_DIGITS=str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩","01234567890123456789")
CLAUSE=re.compile(r"(?<![\d])(?P<ref>\d{1,2}(?:\s*[-‐‑–—]\s*\d{1,3}){2,7})(?![\d])")
REFERENCES=re.compile(r"(?:بند|جدول|شکل|شماره|طبق|مطابق|به استناد|ماده|ارجاع به)\s*$")
PUNCT=re.compile(r"[.!؟؛:]\s*$")


def norm(text:str)->str:
    t=unicodedata.normalize("NFKC",text).translate(NORM_DIGITS)
    t=t.replace("ك","ک").replace("ي","ی").replace("ى","ی").replace("\u200c"," ")
    return re.sub(r"\s+"," ",t).strip()

def refparts(text:str):
    return [int(x) for x in re.split(r"\s*[-‐‑–—]\s*",text)]

def canonical(raw,n:int):
    parts=refparts(raw)
    if parts[0]==n:return "-".join(map(str,parts))
    if parts[-1]==n:return "-".join(map(str,reversed(parts)))
    return None

def parse_pages(chapter:int,pages:list[str],source:str,edition:str):
    full=[];ranges=[];cursor=0
    for page_no,text in enumerate(pages,1):
        page=norm(text)
        # Preserve a clean separator between pages without creating records.
        start=cursor
        full.append(page)
        cursor+=len(page)
        ranges.append((start,cursor,page_no))
        full.append(" ")
        cursor+=1
    corpus="".join(full)
    markers=[];idx=0
    for m in CLAUSE.finditer(corpus):
        ref=canonical(m.group("ref"),chapter)
        if not ref:continue
        parts=refparts(ref)
        if not (3<=len(parts)<=8):continue
        # Look only for full multi-level clauses, not pure dates, table numbers
        # or references embedded in a paragraph.
        before=corpus[max(m.start()-75,0):m.start()].strip()
        if REFERENCES.search(before):continue
        # Reference followed by a unit, a date, or punctuation is not a heading.
        after=corpus[m.end():m.end()+90].lstrip()
        if not after or re.match(r"^[\d./-]+\s*(?:تا|الی|و|،)",after):continue
        while idx<len(ranges)-1 and ranges[idx][1]<m.start():idx+=1
        markers.append({"pos":m.start(),"end":m.end(),"ref":ref,
                        "page":ranges[idx][2], "raw_number":norm(m.group("ref"))})
    records=[];dups=0
    for i,mark in enumerate(markers):
        next_pos=markers[i+1]["pos"] if i+1<len(markers) else len(corpus)
        body=norm(corpus[mark["end"]:next_pos])
        # Short TOC references and table/index entries aren't regulations.
        if len(body)<24 or len(body.split())<4:continue
        if re.fullmatch(r"[\d\s.:/ـ\-،|]+",body):continue
        end_page=mark["page"]
        for a,b,p in ranges:
            if a<next_pos<=b+1:
                end_page=p;break
        rec={"id":f"m{chapter:02d}-{mark['ref']}",
             "chapter":chapter,"edition":edition,
             "locator":mark["ref"],
             "original_locator":mark["raw_number"],
             "title":f"بند {mark['ref']}",
             "kind":"clause",
             "answer":body,
             "text":body,
             "page":mark["page"],"page_end":end_page,
             "source_url":source,
             "extraction_method":"pdf_embedded_text_clause_number_no_ocr"}
        records.append(rec)
    # Prefer longer body if the same number appeared in a TOC or cross-reference.
    best={}
    for r in records:
        k=r["locator"]
        if k in best:dups+=1
        if k not in best or len(r["answer"])>len(best[k]["answer"]):
            best[k]=r
    final=list(best.values())
    return final,{"candidate_markers":len(markers),"candidate_records":len(records),
                  "deduplicated_number_collisions":dups,
                  "distinct_clause_records":len(final),"pdf_pages":len(pages)}

def download_text(url):
    r=requests.get(url,timeout=90,headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    if not r.content.startswith(b"%PDF-"):
        raise ValueError("URL returned non-PDF content")
    doc=fitz.open(stream=r.content,filetype="pdf")
    pages=[p.get_text("text",sort=False) or "" for p in doc]
    return pages

def build_m05():
    url="https://dl.archweb.ir/Mabahes-File/Mabhas-5-%28Virayesh-1396%29.pdf"
    pages=download_text(url)
    recs,qa=parse_pages(5,pages,url,"1396")
    sample={}
    for ref in ["5-2-6-1-3","5-2-6-1-4","5-2-6-1-5","5-2-6-1-6","5-2-6-1-7","5-2-6-1-8","5-2-6-1-9"]:
        a=next((r for r in recs if r["locator"]==ref),None)
        sample[ref]={"found":bool(a),"length":len(a["answer"]) if a else None,
                     "text":a["answer"][:450] if a else None,"page":a["page"] if a else None}
    print("CLAUSE_QA",json.dumps(qa,ensure_ascii=False),flush=True)
    print("CLAUSE_EXAMPLES",json.dumps(sample,ensure_ascii=False),flush=True)
    # Fail rather than publish another broken, fake-numbered dataset.
    assert len(recs)>90,f"Only {len(recs)} identified clauses"
    for ref in ["5-2-6-1-3","5-2-6-1-4","5-2-6-1-5","5-2-6-1-6","5-2-6-1-7","5-2-6-1-8","5-2-6-1-9"]:
        assert sample[ref]["found"],f"Missing actual PDF clause: {ref}"
    assert "50" in sample["5-2-6-1-4"]["text"],"Cement 50kg clause incorrectly segmented"
    assert "سیمان" in sample["5-2-6-1-4"]["text"],"Cement clause misplaced"
    assert "تولید" in sample["5-2-6-1-5"]["text"],"Delivery manufacturing-date clause incomplete"
    assert "100" in sample["5-2-6-1-7"]["text"],"100mm storage-floor clause incomplete"
    assert "12" in sample["5-2-6-1-9"]["text"],"12-bag limit clause incomplete"
    OUT.mkdir(parents=True,exist_ok=True)
    payload={"chapter":5,"title":"مصالح و فرآورده‌های ساختمانی",
             "edition":"1396","method":"continuous_pdf_clause_extraction_no_ocr",
             "source_url":url,"record_count":len(recs),"qa":qa,"records":recs}
    (OUT/"m05.json").write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print("WROTE",str(OUT/"m05.json"),len(recs),flush=True)

if __name__=="__main__":
    build_m05()
