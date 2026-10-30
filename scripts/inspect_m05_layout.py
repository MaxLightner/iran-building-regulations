#!/usr/bin/env python3
import re, requests, fitz
URL="https://dl.archweb.ir/Mabahes-File/Mabhas-5-%28Virayesh-1396%29.pdf"
r=requests.get(URL,timeout=90);r.raise_for_status()
d=fitz.open(stream=r.content,filetype="pdf")
print("PDF_PAGES",len(d),"BYTES",len(r.content),flush=True)
digits=str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩","01234567890123456789")
patterns=[r"5\s*[-–]\s*2\s*[-–]\s*6\s*[-–]\s*1\s*[-–]\s*[3-9]",r"2\s*[-–]\s*6\s*[-–]\s*1\s*[-–]\s*[3-9]",r"وزن\s*اسمی",r"کیسه\s*سیمان",r"50\s*کیلو"]
found=0
for i,p in enumerate(d):
    raw=p.get_text("text")
    t=raw.translate(digits)
    for pat in patterns:
        m=re.search(pat,t,re.I)
        if m:
            print("PAGE",i+1,"PATTERN",pat,"METHOD plain","CONTEXT",repr(t[max(0,m.start()-180):m.end()+380]),flush=True)
            print("PAGE_LINES",repr(t.splitlines()[:10]),flush=True)
            found+=1
            break
    if found>=9:break
if not found:print("NO_MATCH. PAGE 70 sample",repr(d[70].get_text("text")[:2000]),flush=True)
