#!/usr/bin/env python3
"""Repair historic search chunks into readable sentence-complete passages.
This is a presentation fallback ONLY where original clause boundaries are
unavailable. Never call passages numbered regulatory clauses. No OCR.
"""
from __future__ import annotations
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"frontend/data"
OUT=BASE/"clause-text"
TARGETS=[1,2,3,6,11,12,18,20,22,24]
SENTENCES=re.compile(r".+?(?:[.!؟؛]+(?=\s|$)|$)",re.S)
FRONT_MATTER=re.compile(r"(?:^| )(?:شابک|فهرست نویسی|رده بندی|هیأت تدوین|نام کتاب|وزارت راه و شهرسازی|وزارت مسکن و شهرسازی)")

def load(path):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError):return {}

def overlaps(a:str,b:str)->int:
    # Historical chunkers used 70-90 characters of overlap at fixed offsets.
    m=min(len(a),len(b),180)
    for k in range(m,13,-1):
        if a[-k:]==b[:k]:return k
    return 0

def page_text(rows):
    out=defaultdict(list)
    for row in rows:
        p=row.get("page")
        if isinstance(p,int) and p>=1:
            text=str(row.get("answer") or row.get("text") or "").strip()
            if text:out[p].append(text)
    pages=[]
    for p,parts in sorted(out.items()):
        joined=parts[0]
        for next_part in parts[1:]:
            overlap=overlaps(joined,next_part)
            joined+=(next_part[overlap:] if overlap else " "+next_part)
        pages.append((p,joined.strip()))
    return pages

def join_pages(pages):
    text="";ranges=[]
    for page,part in pages:
        if text:text+=" "
        start=len(text)
        text+=part
        ranges.append((start,len(text),page))
    return text,ranges

def for_offset(offset,ranges):
    for a,b,p in ranges:
        if a<=offset<=b:return p
    return ranges[-1][2] if ranges else None

def paragraphs(chapter,pages,edition,source):
    original,ranges=join_pages(pages)
    if not original:return []
    sentences=[]
    for m in SENTENCES.finditer(original):
        s=m.group(0).strip()
        if not s:continue
        # Keep punctuation AND original order. Unfinished fragments remain
        # joined to the next completed sentence, including across PDF pages.
        sentences.append((m.start(),s))
    out=[];buf=[];start=None;size=0
    def emit():
        nonlocal buf,size,start
        if not buf:return
        body=" ".join(buf).strip()
        # Never make a fake clause locator or cut a sentence for presentation.
        if len(body)>=48 and re.search(r"[آ-ی]",body):
            first=re.split(r"(?<=[.!؟؛])\s+",body,maxsplit=1)[0]
            title=first[:94].strip()
            if len(first)>94:title+="…"
            out.append({
                "id":f"m{chapter:02d}-readable-{len(out)+1:05d}",
                "chapter":chapter,"edition":edition,
                "locator":None,"title":title,
                "kind":"readable_paragraph","answer":body,"text":body,
                "page":for_offset(start,ranges),
                "source_url":source,
                "method":"joined_page_text_at_sentence_boundaries_no_ocr"
            })
        buf=[];start=None;size=0
    for at,s in sentences:
        if start is None:start=at
        buf.append(s);size+=len(s)
        # End *only* after complete sentence punctuation. Never truncate.
        # The size target is a readability hint, not a split point.
        if size>=640 and re.search(r"[.!؟؛]$",s):
            emit()
    emit()
    return out

def build():
    catalog={int(c["number"]):c for c in load(BASE/"catalog.json") if "number" in c}
    manifest={}
    all_rows=[]
    for n in TARGETS:
        if n in (6,11,18,20):
            paths=sorted((BASE/"submitted").glob(f"m{n:02d}-*-direct.json"))
            doc=next((x for p in paths if (x:=load(p)).get("records")),None)
            source=str(doc.get("source_name") or "") if doc else ""
            method="user_provided_pdf"
        else:
            doc=load(BASE/"chapters"/f"m{n:02d}.json")
            source=str(catalog.get(n,{}).get("source") or "")
            method="indexed_pdf"
        rows=[r for r in doc.get("records",[]) if r.get("kind") in ("page_extract","direct_pdf_text")]
        pages=page_text(rows)
        records=paragraphs(n,pages,str(doc.get("edition") or catalog.get(n,{}).get("edition") or ""),source)
        manifest[str(n)]={"method":method,"source_pages":len(pages),
                           "input_fragments":len(rows),"readable_passages":len(records),
                           "output_file":f"m{n:02d}-readable.json"}
        payload={"chapter":n,"title":catalog.get(n,{}).get("title"),
                 "edition":doc.get("edition"),"kind":"sentence_complete_fallback",
                 "record_count":len(records),"records":records}
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/f"m{n:02d}-readable.json").write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
        all_rows+=records
        print(f"M{n:02d} {len(rows)} fragments -> {len(records)} sentence-complete passages over {len(pages)} pages",flush=True)
    manifest_data={"method":"join_overlapping_chunks_and_only_split_at_complete_sentences",
        "note":"Paragraph-like passages are not independently verified clause boundaries.",
        "original_regulatory_clause_numbers_never_fabricated":True,
        "chapters":manifest,"total_passages":len(all_rows)}
    (OUT/"readable-manifest.json").write_text(json.dumps(manifest_data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    build()
