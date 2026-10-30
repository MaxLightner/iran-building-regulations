#!/usr/bin/env python3
"""Collect factual chapter/appendix headings from published HTML indexes.

No full-text copying from third-party educational sites. These are TOC hints,
not evidence that the complete regulatory clauses are available. No OCR.
"""
from __future__ import annotations
import concurrent.futures
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"frontend/data/text-phase1/online-outlines.json"
REG=ROOT/"sources/text-source-inventory.json"
S=requests.Session()
S.headers.update({"User-Agent":"Mozilla/5.0 (compatible; CodeIndexResearch/1.0)"})
DIGITS=str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩","01234567890123456789")
TOC_RE=re.compile(r"^(?:فصل\s+(?:\d+|[آ-ی]+)|پیوست\s+(?:\d+|[آ-ی]+)|مبحث\s+\d+|[0-9-]{2,15}\s+[آ-ی])")
NOISE_RE=re.compile(r"ورود|ثبت\s*نام|بیشتر|آزمون|دانلود|اشتراک|راهنما|موارد\s*مرتبط")
def clean(txt):
    return re.sub(r"\s+"," ",txt.translate(DIGITS)).strip(" .:؛-–")
def valid(s):
    return 4<=len(s)<=140 and bool(TOC_RE.search(s)) and not NOISE_RE.search(s)

def read_url(url):
    try:
        response=S.get(url,timeout=16)
        response.raise_for_status()
        response.encoding="utf-8" if response.content[:10000].decode("utf-8","ignore") else (response.apparent_encoding or "utf-8")
        return BeautifulSoup(response.text,"html.parser"),None
    except Exception as e:return None,type(e).__name__

def scan_one(item):
    num=int(item["chapter"]);source_results=[]
    for candidate in item["other_online_sources"]:
        if candidate["kind"] not in ("overview_and_table_of_contents","educational_chapter_outline","table_of_contents"):
            continue
        url=candidate["url"]
        soup,err=read_url(url)
        if err:
            source_results.append({"url":url,"kind":candidate["kind"],"error":err,"headings":[]})
            continue
        for tag in soup(["script","style","noscript","nav","footer"]):tag.decompose()
        root=soup.select_one("main,article,.entry-content,.post-content") or soup.body or soup
        headings=[];seen=set()
        for element in root.find_all(["h2","h3","h4","h5","h6","li","p"]):
            line=clean(element.get_text(" ",strip=True))
            if len(line)>140 and element.name in ("li","p"):continue
            if valid(line):
                line=line[:140]
                if line not in seen:
                    seen.add(line);headings.append(line)
        source_results.append({"url":url,"kind":candidate["kind"],"headings":headings[:120],
            "headings_count":len(headings),
            "warning":"Factual headings only, not the body of the code and not evidence of completeness"})
    return {"chapter":num,"sources":source_results}

def run():
    inventory=json.loads(REG.read_text(encoding="utf-8"))["entries"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        chapters=sorted(pool.map(scan_one,inventory),key=lambda x:x["chapter"])
    summary={
        "chapters_checked":len(chapters),
        "sources_with_headings":sum(bool(s.get("headings")) for c in chapters for s in c["sources"]),
        "chapters_with_headings":sum(any(s.get("headings") for s in c["sources"]) for c in chapters),
        "no_ocr":True,
        "full_text_imported_from_these_sources":False,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"schema_version":1,"description":"Textual online TOC inventory for phase 1; NOT a replacement for official regulations.","summary":summary,"chapters":chapters},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("ONLINE_OUTLINES",summary,flush=True)
    for c in chapters:
        print(f"M{c['chapter']:02d}: "+", ".join(f"{x['kind']}={len(x.get('headings') or [])}" for x in c["sources"]),flush=True)
    assert len(chapters)==24

if __name__=="__main__":
    run()
