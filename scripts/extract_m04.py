"""Full-page Persian OCR and conservative, reviewable chapter-four indexing.

Works on the 128-page scanned chapter four PDF; never treats OCR as legally
verified. All text is backed by a page record (including blank/non-text pages).
Numeric factors and applicability MUST be human-verified before use.
"""
from __future__ import annotations
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import unicodedata
import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "sources/pdfs/reference-m04.pdf"
PAGES = ROOT / "data/extracted/m04/pages"
RECORDS = ROOT / "data/records/m04.json"
REPORT = ROOT / "data/analysis/m04-quality.json"
STAGING = ROOT / "data/analysis/m04-extraction-progress.json"
DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
LOCATOR = re.compile(r"(?<![\d./])[\d۰-۹٠-٩]{1,3}(?:[-‐‑‒–—ـ][\d۰-۹٠-٩]{1,3}){2,6}(?!\d)")
NUMERIC = re.compile(r"(?<!\w)[\d۰-۹٠-٩]+(?:[/.٫،][\d۰-۹٠-٩]+)?")
NOISE = re.compile(r"[A-Za-z]{2,}")
TAGS = {
    "پله و راه‌پله": ["پله", "راه پله", "راه‌پله", "دستگرد", "نرده"],
    "راه خروج و حریق": ["خروج", "آتش", "حریق", "تخلیه اضطراری"],
    "پارکینگ و رمپ": ["پارکینگ", "پاركينگ", "توقفگاه", "رمپ", "خودرو", "وسایل نقلیه"],
    "نورگیری و تهویه": ["نور", "روشنایی", "تهویه", "هوا", "پنجره", "آفتابگیر"],
    "دسترسی و معلولیت": ["معلول", "دسترس پذیری", "دسترس‌پذیری", "ویلچر", "شیبراه"],
    "ضوابط مسکونی": ["مسکونی", "اقامت", "آشپزخانه", "اتاق خواب", "آشپز خانه"],
    "فضای بهداشتی": ["توالت", "حمام", "سرویس", "بهداشت", "فاضلاب"],
    "پوشش و مصالح": ["مصالح", "دیوار", "نما", "سقف", "کف", "عایق"],
    "حفاظ و جان‌پناه": ["جان پناه", "جان‌پناه", "حفاظ", "بالکن", "نرده"],
    "کاربری و تصرف": ["تصرف", "تجمعی", "تجاری", "درمانی", "اداری", "آموزشی"],
    "ابعاد و ارتفاع": ["ارتفاع", "عرض", "طول", "سطح", "مساحت", "ابعاد", "فاصله"],
    "تأسیسات و تجهیزات": ["تاسیسات", "تأسیسات", "آسانسور", "دودکش", "شوفاژ", "لوله"],
    "محوطه و حیاط": ["حیاط", "محوطه", "فضای باز", "زمین", "بام"],
}
RUNNING_HEADER = re.compile(r"^(?:مبحث\s*چهارم|الزامات\s*عمومی\s*ساختمان|فصل\s+\S+\s*[-–]\s*.*)$")
OUTPUT_VERSION = "m04-ocr-v1"


def clean(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(str.maketrans("يكىۀ", "یکیه"))
    text = re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", text)
    return " ".join(text.split())


def fold(text):
    return clean(text).casefold().replace("‌", " ")


def produce_one(args):
    index, expected_sha = args
    pdf = fitz.open(PDF)
    page = pdf[index]
    text_embedded = page.get_text("text", sort=True).strip()
    if text_embedded:
        raise ValueError(f"Unexpected embedded text on page {index + 1}; source changed")
    pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0), alpha=False)
    png = pix.tobytes("png")
    cmd = ["tesseract", "stdin", "stdout", "-l", "fas+eng", "--psm", "3",
           "-c", "preserve_interword_spaces=1"]
    env = dict(os.environ, OMP_THREAD_LIMIT="1")
    run = subprocess.run(cmd, input=png, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, timeout=140, env=env)
    if run.returncode:
        raise RuntimeError(f"Tesseract p{index+1}: {run.stderr.decode('utf-8','replace')[:200]}")
    raw = run.stdout.decode("utf-8", "replace")
    if len(raw.strip()) < 55:
        # Some pages are blank or graphical. Try alternate segmentation once.
        alt = subprocess.run(cmd[:6] + ["6"] + cmd[7:], input=png,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=140, env=env)
        if alt.returncode == 0:
            alternative = alt.stdout.decode("utf-8", "replace")
            if len(alternative.strip()) > len(raw.strip()) * 1.4:
                raw = alternative
    lines = [clean(v) for v in raw.splitlines() if clean(v)]
    notes = []
    if len(raw.strip()) < 100:
        notes.append("low_or_no_ocr_text")
    if sum(bool(NOISE.search(x)) for x in lines) > max(3, len(lines)//3):
        notes.append("possible_latin_noise")
    if any(ord(x) == 0xfffd for x in raw):
        notes.append("replacement_characters")
    result = {
        "pdf_page": index+1, "source_sha256": expected_sha,
        "method": "tesseract_fas_eng_psm3_216dpi_with_psm6_fallback",
        "width": page.rect.width, "height": page.rect.height,
        "image_count": len(page.get_images(full=True)),
        "ocr_text": raw.strip(), "ocr_lines": lines,
        "char_count": len(raw.strip()), "line_count": len(lines),
        "quality_flags": notes, "review_status": "pending_manual_visual_comparison",
    }
    pdf.close()
    return result


def candidate_locator(line):
    # Allow a short OCR artifact before a valid-looking section number.
    hit = LOCATOR.search(line[:40])
    if not hit or hit.start() > 17:
        return None
    token = hit.group()
    parts = [p.translate(DIGIT_MAP) for p in re.split(r"[-‐‑‒–—ـ]", token)]
    if len(parts) < 3 or len(parts) > 7:
        return None
    if not ("4" in (parts[0], parts[-1])):
        return None
    return hit, parts


def assign_topic(text):
    value = fold(text)
    matches = [(sum(value.count(fold(w)) for w in words), topic)
               for topic, words in TAGS.items()]
    matches = [(score, topic) for score, topic in matches if score > 0]
    matches.sort(key=lambda x: (-x[0], x[1]))
    return (matches[0][1] if matches else "سایر مقررات", [topic for _, topic in matches[:4]])


def build_records(pages, source_sha):
    rows = []
    active = None
    unmatched = []
    counts_by_page = {}
    current_chapter = None
    # A conservative boundary: front matter excluded from candidate clauses,
    # all pages remain in raw OCR archive.
    first_body_page = next((p["pdf_page"] for p in pages if p["pdf_page"] >= 16
                            and any("فصل اول" in fold(t) for t in p["ocr_lines"][:6])), 18)
    for page in pages:
        i = page["pdf_page"]
        if i < first_body_page:
            continue
        lines = page["ocr_lines"]
        page_records=0
        for pos, line in enumerate(lines):
            if not line or (len(line) < 80 and RUNNING_HEADER.match(line)):
                continue
            match = candidate_locator(line)
            if match:
                hit, parts = match
                # Header OCR occasionally damages the chapter number. Keep the
                # raw label intact, never silently assign a legal locator.
                if active:
                    rows.append(active)
                name = line[hit.end():].strip(" -–.،:؛")
                # Some lines begin with artifacts: do not pretend they are clean.
                if not name:
                    name = "بند شناسایی‌شده توسط OCR"
                original = hit.group()
                active = {
                    "start": i, "last":i, "start_line":pos+1,
                    "locator":original, "locator_components_ocr":parts,
                    "title":name[:150], "lines":[line],
                }
                page_records+=1
            elif active:
                active["lines"].append(line)
                active["last"]=i
            else:
                unmatched.append({"pdf_page":i,"line":pos+1,"text":line[:240]})
        counts_by_page[i]=page_records
    if active:
        rows.append(active)
    output=[]
    for n, row in enumerate(rows,1):
        original_text="\n".join(row["lines"]).strip()
        topic,topics=assign_topic(original_text)
        numeric=[m.group() for m in NUMERIC.finditer(original_text)]
        # Structural heuristics are proposals, not verified clause identities.
        record={
            "id":f"m04-1396-ocr-{n:05d}",
            "document_id":"m4","edition_id":"m4-1396-third-unverified",
            "section_id":None,"kind":"clause",
            "locator":row["locator"],"title":row["title"],
            "original_text":original_text,
            "summary":"","topic":topic,"tags":topics,"aliases":[],
            "key_factors":[],
            "applicability":{"status":"not_evaluated","conditions":[]},
            "references":[],
            "source":{
                "authority":"secondary","official_page_url":"https://inbr.ir/دانلود-مبحث-چهارم/",
                "official_pdf_url":None,"sha256":source_sha,
                "pdf_page":row["start"],"printed_page":None,
                "publication_rights":"unverified",
            },
            "version":{"edition_label":"ویرایش سوم (۱۳۹۶) ـ شناسایی جلد، نیازمند تطبیق",
                       "published_date":None,"effective_date":None,
                       "effective_evidence":None,"status":"unconfirmed","last_checked":None},
            "review":{"status":"pending","reviewer":None,"reviewed_at":None},
            "extraction":{
                "status":"ocr_unverified","method":OUTPUT_VERSION,
                "start_pdf_page":row["start"],"end_pdf_page":row["last"],
                "start_ocr_line":row["start_line"],
                "locator_components_ocr":row["locator_components_ocr"],
                "numeric_candidates_unverified":numeric[:50],
                "kind_is_inferred":True,
                "notes":["OCR may alter characters and digits; verify against PDF image",
                         "No extracted numeric values are approved as key_factors"],
            },
        }
        output.append(record)
    return output, first_body_page, unmatched, counts_by_page


def main():
    source_sha=hashlib.sha256(PDF.read_bytes()).hexdigest()
    report=json.loads((ROOT/"sources/reference-mirror-report.json").read_text(encoding="utf-8"))
    expected=next(x["sha256"] for x in report["results"] if x["mabhas"]==4)
    if expected!=source_sha:
        raise ValueError("PDF SHA256 differs from archived source: refuse processing")
    with fitz.open(PDF) as pdf:
        total=len(pdf)
    PAGES.mkdir(parents=True,exist_ok=True)
    data={}
    # Always re-check source hash even when resuming.
    for i in range(1,total+1):
        path=PAGES/f"{i:04d}.json"
        if path.exists():
            cached=json.loads(path.read_text(encoding="utf-8"))
            if cached.get("source_sha256")==source_sha and cached.get("method","").startswith("tesseract"):
                data[i]=cached
    pending=[(i,source_sha) for i in range(total) if i+1 not in data]
    print(f"OCR {total} pages; cached {len(data)}, remaining {len(pending)}",flush=True)
    if pending:
        with ProcessPoolExecutor(max_workers=4) as pool:
            tasks=[pool.submit(produce_one,args) for args in pending]
            for task in as_completed(tasks):
                page=task.result()
                data[page["pdf_page"]]=page
                path=PAGES/f"{page['pdf_page']:04d}.json"
                path.write_text(json.dumps(page,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
                if len(data)%10==0:
                    print(f"Completed {len(data)}/{total}",flush=True)
    if len(data)!=total:
        raise ValueError("Not all pages OCRed")
    pages=[data[i] for i in range(1,total+1)]
    rows,first_body,unmatched,per_page=build_records(pages,source_sha)
    RECORDS.parent.mkdir(parents=True,exist_ok=True)
    RECORDS.write_text(json.dumps({
        "schema_version":"1.0","document_id":"m4",
        "edition_id":"m4-1396-third-unverified",
        "source_pdf_sha256":source_sha,
        "workflow_status":"OCR_COMPLETE_PENDING_VISUAL_LEGAL_REVIEW",
        "notice":"All text is machine-read, unverified; do not cite as authoritative.",
        "records":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    quality={
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "pdf_file":"sources/pdfs/reference-m04.pdf",
      "pdf_sha256":source_sha,"pdf_pages":total,
      "ocr_pages":len(pages),
      "ocr_nonempty_pages":sum(bool(x["char_count"]) for x in pages),
      "ocr_empty_pages":[x["pdf_page"] for x in pages if not x["char_count"]],
      "low_text_pages":[x["pdf_page"] for x in pages if x["char_count"]<100],
      "total_ocr_characters":sum(x["char_count"] for x in pages),
      "source_cover_edition":"ویرایش سوم (۱۳۹۶), OCR sample; not verified effective edition",
      "first_body_page_inferred":first_body,
      "candidate_numbered_records":len(rows),
      "numeric_candidates_unverified":sum(len(r["extraction"]["numeric_candidates_unverified"]) for r in rows),
      "topic_distribution":{t:sum(r["topic"]==t for r in rows) for t in sorted(set(r["topic"] for r in rows))},
      "pages_with_no_numbered_record":[i for i in range(first_body,total+1) if not per_page.get(i)],
      "unmatched_ocr_lines":len(unmatched),
      "unmatched_ocr_examples":unmatched[:40],
      "source_verified":False, "legal_effective_date_verified":False,
      "manual_quality_review_complete":False,
      "text_validated_against_image":False,
      "tables_verified":False,"numbers_verified":False,
      "phase2_status":"machine_extraction_complete_review_pending",
      "notes":[
        "One page JSON preserved for each PDF page (including blank pages).",
        "Numbered OCR segments are heuristic and may include misread numbering or merged clauses.",
        "Tables and illustrations require separate visual comparison; OCR is not a table model.",
        "No summaries, legal applicability conditions or numeric key_factors are invented.",
        "No record eligible for frontend publication until source and human review approved."
      ]
    }
    REPORT.write_text(json.dumps(quality,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"OCR complete {total} pages, {len(rows)} candidate records; manual review pending",flush=True)


if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print("FATAL",type(exc).__name__,str(exc),file=sys.stderr)
        sys.exit(1)
