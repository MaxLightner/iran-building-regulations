#!/usr/bin/env python3
"""Recover numbered regulations from reconstructed native PDF text.
Conservative: only well-formed chapter-local identifiers and substantive bodies.
No OCR and no guessed identifiers. Chapters not passing checks keep readable text.
"""
import json
import re
from pathlib import Path
from build_clause_text import parse_pages
from rebuild_readable_passages import load,page_text,BASE,OUT

TARGETS={2:["2-1-1-1","2-1-1-2"],3:["3-1-1","3-1-3"],22:["22-2-6","22-2-9"]}
catalog={int(c["number"]):c for c in load(BASE/"catalog.json")}
all_records=[]
for chapter,examples in TARGETS.items():
    raw=load(BASE/"chapters"/f"m{chapter:02d}.json")
    pdf_pages=page_text([r for r in raw.get("records",[]) if r.get("kind")=="page_extract"])
    p=dict(pdf_pages)
    pages=[p.get(i,"") for i in range(1,max(p)+1)]
    recovered,details=parse_pages(chapter,pages,str(catalog[chapter].get("source") or ""),str(raw.get("edition") or ""))
    valid=[]
    for r in recovered:
        nums=[int(i) for i in r["locator"].split("-")]
        body=r["answer"]
        if any(x>80 for x in nums[1:]):continue
        if len(body)<65:continue
        if re.search(r"(?:\.\s*){5,}|فهرست مطالب|شماره کتابشناسی|شابک|ISBN",body,re.I):continue
        r["extraction_method"]="recovered_original_number_native_pdf_text"
        valid.append(r)
    by_id={r["locator"]:r for r in valid}
    missing=[x for x in examples if x not in by_id]
    print("CLAUSE_RECOVERY",json.dumps({
        "chapter":chapter,"candidates":details["candidate_markers"],
        "unique_candidates":len(recovered),"accepted":len(valid),"missing_examples":missing,
        "example_text":{x:by_id[x]["answer"][:260] for x in examples if x in by_id}
    },ensure_ascii=False),flush=True)
    assert not missing, f"m{chapter} missing required authentic clauses: {missing}"
    assert len(valid)>50,f"m{chapter} too few unambiguous clauses: {len(valid)}"
    OUT.mkdir(parents=True,exist_ok=True)
    payload={"chapter":chapter,"edition":raw.get("edition"),
             "method":"exact_pdf_clause_numbers_no_ocr",
             "record_count":len(valid),"records":valid}
    (OUT/f"m{chapter:02d}.json").write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    all_records.extend(valid)
(OUT/"more-numbered-index.json").write_text(json.dumps(all_records,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
print("TOTAL_NUMBERED",len(all_records),flush=True)
