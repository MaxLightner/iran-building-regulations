"""Preview chapter-four pending OCR search locally (never regulatory advice)."""
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
PATHS=[ROOT/"data/records/m04.json",ROOT/"data/records/m04-security-1403.json"]

def normalize(s):
    s=unicodedata.normalize("NFKC",str(s or ""))
    s=s.translate(str.maketrans("يكىۀ", "یکیه"))
    return " ".join(s.replace("‌"," ").casefold().split())

def search(query,limit=15):
    q=[v for v in normalize(query).split() if v]
    if not q:return []
    results=[]
    for path in PATHS:
        doc=json.loads(path.read_text(encoding="utf-8"))
        for r in doc["records"]:
            title=normalize(r["title"]);topic=normalize(r["topic"])
            content=normalize(r["original_text"])
            tags=normalize(" ".join(r["tags"]))
            if not all(any(term in val for val in [title,topic,tags,content]) for term in q):
                continue
            score=sum(6*(t in title)+4*(t in tags)+3*(t in topic)+(t in content) for t in q)
            results.append((score,r))
    return [r for _,r in sorted(results,key=lambda x:-x[0])[:limit]]

def main():
    if len(sys.argv)<2:
        print("Usage: python scripts/search_m04_draft.py 'پارکینگ' [max_results]")
        return 2
    found=search(sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else 15)
    print("WARNING: all matches are unverified OCR, not certified rules; matches:",len(found))
    for r in found:
        print(r["document_id"],"page",r["source"]["pdf_page"],"locator",r["locator"],
              "topic",r["topic"],"—",r["title"][:90])
    return 0

if __name__=="__main__":sys.exit(main())
