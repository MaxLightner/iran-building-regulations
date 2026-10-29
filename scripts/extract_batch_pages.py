"""Phase 3-1: full-page, source-grounded PDF text extraction for chapters 3, 5, 15.

Each PDF page is independently preserved. OCR is used only where embedded text
is unavailable or appears unusable; every page has source SHA and provenance.
No candidate is claimed to be an authoritative clause or current regulation.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CHAPTERS = (3, 5, 15)
DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
TOPICS = {
    3: "حریق و ایمنی",
    5: "مصالح و فرآورده‌های ساختمانی",
    15: "آسانسور و پله‌برقی",
}
MAX_WORKERS = 3


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def readable_embedded(raw):
    persian = len(re.findall(r"[\u0621-\u064a\u067e\u0686\u0698\u06af]", raw))
    words = re.findall(r"[\u0621-\u064a\u067e\u0686\u0698\u06af]{3,}", raw)
    return len(raw.strip()) >= 160 and persian >= 80 and len(words) >= 18


def one_page(arg):
    chapter, index, digest = arg
    import fitz
    filename = ROOT / "sources" / "pdfs" / f"reference-m{chapter:02d}.pdf"
    with fitz.open(filename) as document:
        page = document[index]
        original = page.get_text("text", sort=True)
        method = "embedded_text"
        text = original
        if not readable_embedded(original):
            pix = page.get_pixmap(matrix=fitz.Matrix(2.3, 2.3), alpha=False)
            png = pix.tobytes("png")
            env = {**os.environ, "OMP_THREAD_LIMIT": "1"}
            command = ["tesseract", "stdin", "stdout", "-l", "fas+eng", "--psm", "3"]
            run = subprocess.run(command, input=png, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, env=env, timeout=160)
            if run.returncode:
                raise RuntimeError(f"tesseract m{chapter} p{index+1}: {run.stderr.decode('utf-8','replace')[:160]}")
            text = run.stdout.decode("utf-8", "replace")
            method = "tesseract_fas_eng_166dpi_psm3"
            if len(text.strip()) < 40:
                # Retry short, graphical, or table-heavy pages using uniform block mode.
                command[-1] = "6"
                alt = subprocess.run(command, input=png, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, env=env, timeout=160)
                if alt.returncode == 0 and len(alt.stdout.strip()) > len(text.strip()):
                    text = alt.stdout.decode("utf-8", "replace")
                    method = "tesseract_fas_eng_166dpi_psm6"
        raw = text.strip()
        flags = []
        if not raw:
            flags.append("empty_text_needs_visual_review")
        elif len(raw) < 120:
            flags.append("short_text_needs_visual_review")
        if "جدول" in raw or "شکل" in raw:
            flags.append("table_or_figure_visual_check")
        return {
            "pdf_page": index + 1,
            "source_sha256": digest,
            "method": method,
            "ocr_text": raw,
            "char_count": len(raw),
            "quality_flags": flags,
            "review_status": "unverified_source_transcription",
        }


def chapter_run(chapter, expected):
    import fitz
    pdf = ROOT / "sources" / "pdfs" / f"reference-m{chapter:02d}.pdf"
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if digest != expected:
        raise ValueError(f"m{chapter} sha256 mismatch against manifest")
    with fitz.open(pdf) as doc:
        count = len(doc)
    folder = ROOT / "data" / "extracted" / f"m{chapter:02d}" / "pages"
    folder.mkdir(parents=True, exist_ok=True)
    cached, tasks = {}, []
    for i in range(count):
        target = folder / f"{i+1:04d}.json"
        if target.exists():
            old = load(target)
            if (old.get("pdf_page") == i+1
                and old.get("source_sha256") == digest
                and old.get("method") in ("embedded_text","tesseract_fas_eng_166dpi_psm3",
                                           "tesseract_fas_eng_166dpi_psm6")):
                cached[i+1] = old
                continue
        tasks.append((chapter,i,digest))
    print(f"m{chapter}: {count} pages; existing {len(cached)}; pending {len(tasks)}",flush=True)
    if tasks:
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = [pool.submit(one_page, task) for task in tasks]
            for future in as_completed(futures):
                row = future.result()
                write(folder / f"{row['pdf_page']:04d}.json", row)
                cached[row["pdf_page"]] = row
                if len(cached) % 20 == 0:
                    print(f"m{chapter}: {len(cached)}/{count}",flush=True)
    if len(cached) != count:
        raise RuntimeError(f"m{chapter}: incomplete extraction")
    pages = [cached[i] for i in range(1,count+1)]
    report = {
        "chapter":chapter,"topic":TOPICS[chapter],"generated_at":datetime.now(timezone.utc).isoformat(),
        "source_pdf":str(pdf.relative_to(ROOT)),"source_sha256":digest,
        "total_pages":count,"extracted_pages":len(pages),
        "nonempty_pages":sum(bool(x["ocr_text"]) for x in pages),
        "empty_pages":[x["pdf_page"] for x in pages if not x["ocr_text"]],
        "methods":{x:sum(p["method"]==x for p in pages) for x in sorted({p["method"] for p in pages})},
        "requires_visual_review":[x["pdf_page"] for x in pages if x["quality_flags"]],
        "status":"full_page_extraction_complete_unverified",
        "warning":"Text transcription is not an official verified legal clause database.",
    }
    write(ROOT/"data"/"analysis"/f"m{chapter:02d}-quality.json", report)
    print(f"m{chapter}: finished; nonempty {report['nonempty_pages']}/{count}",flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapters",nargs="+",type=int,choices=CHAPTERS,default=CHAPTERS)
    args = parser.parse_args()
    report = load(ROOT/"sources"/"reference-mirror-report.json")
    sha = {int(x["mabhas"]):x["sha256"] for x in report["results"]
           if x.get("status") in ("saved","unchanged")}
    for chapter in args.chapters:
        chapter_run(chapter, sha[chapter])


if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print(type(exc).__name__+": "+str(exc),file=sys.stderr,flush=True)
        sys.exit(1)
