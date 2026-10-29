"""OCR quality probe for scanned chapter four. Source is image-only."""
import fitz
from pathlib import Path
import json, subprocess, hashlib
ROOT=Path(__file__).resolve().parents[1]
d=fitz.open(ROOT/"sources/pdfs/reference-m04.pdf")
results=[]
for i in [0,3,7,12,20,35,55,80,105,127]:
    p=d[i]
    pix=p.get_pixmap(matrix=fitz.Matrix(2.8,2.8),alpha=False)
    raw=pix.tobytes("png")
    cmd=["tesseract","stdin","stdout","-l","fas+eng","--psm","3","-c","preserve_interword_spaces=1"]
    run=subprocess.run(cmd,input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=110)
    t=run.stdout.decode("utf-8","replace")
    lines=[x.strip() for x in t.splitlines() if x.strip()]
    results.append({"pdf_page":i+1,"length":len(t),"lines":len(lines),
                    "sample":lines[:45],"last":lines[-12:],
                    "stderr":run.stderr.decode("utf-8","replace")[:200]})
    print("sample",i+1,len(t),flush=True)
out=ROOT/"data/analysis/m04-ocr-samples.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({"engine":"Tesseract fas+eng psm3 201 dpi","samples":results},
                          ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
