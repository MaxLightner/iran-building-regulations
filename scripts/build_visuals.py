#!/usr/bin/env python3
"""Build a small figure/page-preview index for the currently catalogued editions.

This is a VISUAL NAVIGATION AID, not republication of full books or rule verification.
Only selected downscaled previews are stored. Original PDFs remain at source sites.
"""
from __future__ import annotations
import json
import re
import shutil
from pathlib import Path

import fitz

from build_all_chapters import document_from_source

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"frontend/data/visuals"
CHAPTERS=(6,11,18,20)
MAX_PAGES=24
MAX_SOURCE_PAGES=400
NUM_RE=re.compile(r"(?:شکل|جدول|نمودار)\\s*[-:شماره. ]*[\\d۰-۹]{1,4}",re.I)
GENERAL_RE=re.compile(r"شکل|نمودار|جدول|دیاگرام|نمونه",re.I)


def discover_source(chapter,registry,coverage):
    entry=registry[chapter]
    # Prefer the previously indexed edition, fall back to registry sources.
    options=[coverage.get(chapter,{}).get("source")]
    options+=entry.get("document_sources",[])
    checked=set()
    for source in options:
        if not source or source in checked:continue
        checked.add(source)
        try:
            data,final=document_from_source(source,str(entry["edition"]))
            if data and len(data)>1000:
                return data,source
        except Exception as exc:
            print(f"m{chapter:02d}: source not accessible: {type(exc).__name__}",flush=True)
    return None,None


def indexed_page_text(chapter):
    path=ROOT/"frontend/data/chapters"/f"m{chapter:02d}.json"
    try:rows=json.loads(path.read_text(encoding="utf-8")).get("records",[])
    except (FileNotFoundError,ValueError):return {}
    pages={}
    for row in rows:
        if not isinstance(row.get("page"),int):continue
        p=row["page"]
        pages[p]=pages.get(p,"")+" "+str(row.get("answer",""))[:1200]
    return pages


def candidate_pages(doc,page_text):
    scored=[]
    for i,page in enumerate(doc):
        pg=i+1
        if pg<=7:continue
        area=page.rect.get_area()
        images=0
        try:
            for item in page.get_images(full=True):
                for box in page.get_image_rects(item[0]):
                    proportion=box.get_area()/max(area,1)
                    # Ignore full-page raster scans: they occur even on text-only pages.
                    if .012<=proportion<=.82:images+=1
        except (ValueError,RuntimeError):pass
        drawings=0
        try:
            for line in page.get_drawings():
                box=line.get("rect")
                if box and box.get_area()>area*.003:drawings+=1
        except (ValueError,RuntimeError):pass
        indexed=page_text.get(pg,"")
        # The OCR often reads the keyword even when it cannot read the clause number.
        keyword_score=min(len(NUM_RE.findall(indexed)),4)*4
        general=bool(GENERAL_RE.search(indexed))
        score=min(images,12)*8+keyword_score+(4 if drawings>25 else 0)+(1 if general else 0)
        if score<4:continue
        labels=[]
        if images:labels.append("تصویر")
        if drawings>25:labels.append("نقشه/ترسیم")
        if keyword_score:labels.append("شکل یا جدول در متن")
        scored.append((score,pg,labels))
    # Pick diverse pages rather than filling the gallery with one dense section.
    scored.sort(key=lambda x:(-x[0],x[1]))
    chosen=[]
    for item in scored:
        if len(chosen)>=MAX_PAGES:break
        if any(abs(item[1]-s[1])<=1 for s in chosen) and len(scored)>MAX_PAGES:
            continue
        chosen.append(item)
    if len(chosen)<min(MAX_PAGES,len(scored)):
        for item in scored:
            if len(chosen)>=MAX_PAGES:break
            if item not in chosen:chosen.append(item)
    return sorted(chosen,key=lambda x:x[1])


def main():
    reg={int(x["number"]):x for x in json.loads((ROOT/"sources/chapters.json").read_text(encoding="utf-8"))["chapters"]}
    cov={int(x["number"]):x for x in json.loads((ROOT/"frontend/data/coverage.json").read_text(encoding="utf-8"))["chapters"]}
    OUTPUT.mkdir(parents=True,exist_ok=True)
    manifest={"schema_version":1,"purpose":"low-resolution visual navigation","chapters":{}}
    for chapter in CHAPTERS:
        data,source=discover_source(chapter,reg,cov)
        if not data:
            print(f"M{chapter:02d}: no current-edition PDF available",flush=True)
            manifest["chapters"][str(chapter)]={"status":"source_unavailable","pages":[]}
            continue
        with fitz.open(stream=data,filetype="pdf") as pdf:
            if len(pdf)>MAX_SOURCE_PAGES:continue
            texts=indexed_page_text(chapter)
            selected=candidate_pages(pdf,texts)
            folder=OUTPUT/f"m{chapter:02d}"
            if folder.exists():shutil.rmtree(folder)
            folder.mkdir(parents=True)
            rows=[]
            for _,page_number,labels in selected:
                page=pdf[page_number-1]
                scale=1.25
                try:
                    pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
                    filename=f"p{page_number:03d}.jpg"
                    blob=pix.tobytes("jpeg",jpg_quality=58)
                    (folder/filename).write_bytes(blob)
                    rows.append({"page":page_number,"preview":f"./data/visuals/m{chapter:02d}/{filename}","features":labels})
                except (ValueError,RuntimeError):continue
            manifest["chapters"][str(chapter)]={
                "status":"ready" if rows else "no_visual_candidates",
                "edition":str(reg[chapter]["edition"]),
                "source_url":source,
                "pdf_pages":len(pdf),
                "visual_pages":len(rows),
                "note":"Selected page previews; page numbers are PDF page indexes, not printed folio numbers.",
                "pages":rows
            }
            print(f"M{chapter:02d} edition={reg[chapter]['edition']} source_pages={len(pdf)} previews={len(rows)}",flush=True)
    (OUTPUT/"index.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    if sum(len(c.get("pages",[])) for c in manifest["chapters"].values())<12:
        raise RuntimeError("Fewer than 12 graphic previews generated")
    print("VISUAL GALLERY READY",flush=True)


if __name__=="__main__":
    main()
