from pathlib import Path
import json
from rebuild_readable_passages import page_text, load, BASE, TARGETS
from build_clause_text import parse_pages
for n in TARGETS:
    if n in (6,11,18,20):
        files=sorted((BASE/"submitted").glob(f"m{n:02d}-*-direct.json"))
        payload=next((x for f in files if (x:=load(f)).get("records")),{})
    else:
        payload=load(BASE/"chapters"/f"m{n:02d}.json")
    rows=[r for r in payload.get("records",[]) if r.get("kind") in ("page_extract","direct_pdf_text")]
    pages=page_text(rows)
    d=dict(pages)
    contiguous=[d.get(p,"") for p in range(1,max(d.keys())+1)] if d else []
    recs,qa=parse_pages(n,contiguous,"",str(payload.get("edition","")))
    lens=sorted(len(r["answer"]) for r in recs)
    median=lens[len(lens)//2] if lens else 0
    samples=[{"ref":r["locator"],"text":r["answer"][:140]} for r in recs[:6]]
    print("CHAPTER_CLAUSE_DIAGNOSTIC",json.dumps({"n":n,"input_pages":len(pages),
      "candidates":qa["candidate_markers"],"clauses":len(recs),"median":median,
      "samples":samples},ensure_ascii=False),flush=True)
