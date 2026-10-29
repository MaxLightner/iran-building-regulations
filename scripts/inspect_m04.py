"""Inspect the chapter-four PDF before implementing extraction. Stores no new public data."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import fitz

ROOT=Path(__file__).resolve().parents[1]
PDF=ROOT/"sources/pdfs/reference-m04.pdf"
OUT=ROOT/"data/analysis/m04-inspection.json"
doc=fitz.open(PDF)
pages=[]
for i,p in enumerate(doc):
    raw=p.get_text("text",sort=True)
    blocks=p.get_text("blocks",sort=True)
    lines=[s.strip() for s in raw.splitlines() if s.strip()]
    pages.append({"pdf_page":i+1,"chars":len(raw),
        "block_count":len(blocks),"line_count":len(lines),
        "sample":lines[:15] if i in {0,1,2,3,4,5,10,20,30,40,50,60,80,100,120,150,180,200} else [],
        "last_lines":lines[-5:] if i in {0,1,2,3,4,5,10,20,30,50,100,150} else [],
        "image_count":len(p.get_images()),"width":round(p.rect.width),"height":round(p.rect.height)})
total=sum(x["chars"] for x in pages)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps({"source":"reference-m04.pdf","source_sha256":hashlib.sha256(PDF.read_bytes()).hexdigest(),
   "generated_at":datetime.now(timezone.utc).isoformat(),"pages":len(doc),"total_chars":total,
   "empty_pages":[x["pdf_page"] for x in pages if x["chars"]<30],"samples":pages[:8]+[x for x in pages[8:] if x["sample"]],
   "largest_page_chars":sorted([{"page":x["pdf_page"],"chars":x["chars"]} for x in pages],key=lambda x:x["chars"],reverse=True)[:10],
   "page_metrics":[[x["pdf_page"],x["chars"],x["line_count"],x["image_count"]] for x in pages]
   },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Pages:",len(doc),"total text characters:",total,"pages with little text:",sum(p["chars"]<30 for p in pages))
