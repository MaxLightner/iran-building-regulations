"""Build a conservative project-applicability signal index from structured knowledge.

This does NOT make a legal applicability determination. It extracts project signals
(use, structure, stage, basement, candidate floor/area thresholds) so the static app
can rank and explain results for a project profile. Uncertain signals never remove a
record from search.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json,re,unicodedata

ROOT=Path(__file__).resolve().parents[1]
KNOW=ROOT/"frontend"/"data"/"knowledge"
OUT=ROOT/"frontend"/"data"/"applicability"

USE_ALIASES={
 "مسکونی":["مسکونی","واحد مسکونی","آپارتمان"],
 "اداری":["اداری","دفتر کار","ساختمان اداری"],
 "تجاری":["تجاری","فروشگاه","مرکز خرید","واحد تجاری"],
 "آموزشی":["آموزشی","مدرسه","دانشگاه","کلاس درس"],
 "درمانی":["درمانی","بیمارستان","درمانگاه","کلینیک"],
 "صنعتی":["صنعتی","کارخانه","کارگاه صنعتی"],
}
STRUCTURE_ALIASES={
 "بتن‌آرمه":["بتن آرمه","بتن‌آرمه","سازه بتنی","ساختمان بتنی"],
 "فولادی":["سازه فولادی","ساختمان فولادی","اسکلت فولادی","فولادی"],
 "بنایی":["مصالح بنایی","ساختمان بنایی","دیوار باربر","بنایی"],
}
STAGE_DEFAULTS={
 "m01":["مطالعات اولیه","طراحی","اجرا"],"m02":["مطالعات اولیه","طراحی","اجرا"],
 "m12":["اجرا"],"m22":["بهره‌برداری"],
}
STAGE_ALIASES={
 "مطالعات اولیه":["مطالعات اولیه","مطالعات","شناخت زمین","بررسی اولیه"],
 "طراحی":["طراحی","طرح","محاسبه","محاسبات"],
 "اجرا":["اجرا","نصب","کارگاه","حین اجرا","اجرایی"],
 "بهره‌برداری":["بهره برداری","بهره‌برداری","نگهداری","بازرسی دوره","تعمیرات"],
}
GENERAL_DESIGN_EXEC={f"m{i:02d}" for i in range(3,25)}-{"m12","m22"}

DIGIT_TRANS=str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩","01234567890123456789")
COMPARATORS=[
 ("بیشتر از","gt"),("بیش از","gt"),("حداقل","gte"),("کمتر از","lt"),
 ("کمتر از","lt"),("حداکثر","lte"),("تا حداکثر","lte"),("تا","lte"),
]
NUM_UNIT=re.compile(r"(?P<num>\d+(?:[./]\d+)?)\s*(?P<unit>متر\s*مربع|طبقه)")
BASEMENT=re.compile(r"زیر\s*زمین|زیرزمین")
PARKING=re.compile(r"پارکینگ|توقفگاه")
HEIGHT=re.compile(r"ارتفاع")

def norm(v):
    s=unicodedata.normalize("NFKC",str(v or "")).translate(DIGIT_TRANS)
    s=s.translate(str.maketrans("يكىۀ‌","یکیه "))
    s=re.sub(r"[\u064b-\u065f\u0670\u200e-\u200f]","",s)
    return " ".join(s.casefold().split())

def read(path):return json.loads(path.read_text(encoding="utf-8"))
def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")

def hits(text,mapping):
    result=[]
    for label,aliases in mapping.items():
        if any(norm(a) in text for a in aliases): result.append(label)
    return result

def stages(docid,text):
    found=set(STAGE_DEFAULTS.get(docid,["طراحی","اجرا"] if docid in GENERAL_DESIGN_EXEC else []))
    for label,aliases in STAGE_ALIASES.items():
        if any(norm(a) in text for a in aliases):found.add(label)
    return sorted(found)

def numeric_conditions(record):
    out=[];seen=set()
    sources=list(record.get("conditions") or [])
    # Conditions are the safest text window. If none exist, do not infer thresholds from arbitrary numbers.
    for sentence in sources:
        n=norm(sentence)
        comparator=None
        for phrase,op in COMPARATORS:
            if phrase in n:
                comparator=op;break
        if not comparator:continue
        for m in NUM_UNIT.finditer(n):
            value=float(m.group("num").replace("/","."));unit=m.group("unit").replace(" ","")
            field="area" if "مربع" in unit else ("basements" if BASEMENT.search(n) else "floors")
            key=(field,comparator,value)
            if key in seen:continue
            seen.add(key)
            out.append({"field":field,"operator":comparator,"value":value,
                        "unit":"مترمربع" if field=="area" else "طبقه",
                        "evidence":" ".join(str(sentence).split())[:300],
                        "confidence":"candidate"})
            if len(out)>=5:return out
    return out

def project_topics(record):
    return record.get("topics") or []

def build():
    manifest=read(KNOW/"manifest.json")
    OUT.mkdir(parents=True,exist_ok=True)
    docs=[];totals=Counter()
    for d in manifest["documents"]:
        shard=read(KNOW/(d["id"]+".json"))
        rows=[]
        for r in shard["records"]:
            text=norm(" ".join([r.get("title",""),r.get("summary",""),r.get("text",""),
                                " ".join(r.get("conditions") or [])]))
            use=hits(text,USE_ALIASES);structure=hits(text,STRUCTURE_ALIASES)
            stage=stages(d["id"],text);numeric=numeric_conditions(r)
            row={
                "id":r["id"],"topics":project_topics(r),
                "mentions":{"uses":use,"structures":structure,"stages":stage,
                            "basement":bool(BASEMENT.search(text)),
                            "parking":bool(PARKING.search(text)),
                            "height":bool(HEIGHT.search(text))},
                "numeric_conditions":numeric,
                "status":"project_relevance_signals_not_legal_applicability",
            }
            rows.append(row)
            totals["records"]+=1
            totals["numeric_conditions"]+=len(numeric)
            totals["use_mentions"]+=bool(use);totals["structure_mentions"]+=bool(structure)
            totals["basement_mentions"]+=row["mentions"]["basement"]
        save(OUT/(d["id"]+".json"),{"schema_version":"1.0",
            "status":"project_relevance_signals_not_legal_applicability",
            "document":{"id":d["id"],"chapter":d["chapter"],"title":d["title"]},
            "records":rows})
        docs.append({"id":d["id"],"chapter":d["chapter"],"title":d["title"],
                     "records":len(rows),"index_file":"./data/applicability/"+d["id"]+".json"})
    save(OUT/"manifest.json",{"schema_version":"1.0",
        "status":"project_relevance_signals_not_legal_applicability",
        "documents":docs,"documents_indexed":len(docs),"counts":dict(totals),
        "project_fields":["city","use","structure","area","floors","basements","stage"],
        "city_policy":"neutral_national_regulations",
        "warning":"Signals rank and explain relevance only. They never hide a record or assert legal applicability."})
    print("Applicability:",len(docs),"docs",dict(totals))

if __name__=="__main__":build()
