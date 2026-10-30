#!/usr/bin/env python3
"""Import topic 1 (1392) from its original PDF, without OCR or summaries."""
import argparse
import collections
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path
import fitz

URL = "https://dl.archweb.ir/Mabahes-File/Mabhas-1-%28Virayesh-1392%29.pdf"
HEADING = re.compile(r"^(\d+(?:\s*-\s*\d+){1,4})(?!\s*-)\s*(.*)$")
TOKEN = re.compile(r"[0-9a-zA-Z\u0621-\u06ff]{2,}")

def normalize(value):
    value = unicodedata.normalize("NFKC", value)
    return "".join(ch for ch in value if unicodedata.category(ch) != "Cf").replace("ي", "ی").replace("ك", "ک")

def normalize_search(value):
    value = normalize(value).lower()
    value = "".join(ch for ch in value if not unicodedata.category(ch).startswith("M"))
    trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    return value.translate(trans).replace("‌", " ").replace("ـ", "")

def read_pages(path):
    raw = subprocess.check_output(["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"]).decode("utf-8")
    pages = [normalize(page) for page in raw.split("\f")]
    if not pages[-1].strip():
        pages.pop()
    return pages

def parse(path):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    pdf = fitz.open(stream=raw, filetype="pdf")
    pages = read_pages(path)
    assert len(pdf) == len(pages) == 122, "Unexpected source layout or edition: stop for review"
    duplicates = []
    for first in range(11, 67):
        second = first + 56
        assert " ".join(pages[first-1].split()) == " ".join(pages[second-1].split()), f"Duplicate mismatch {first}/{second}"
        duplicates.append([first, second])
    graphic_candidates = []
    for num in range(11, 67):
        page = pdf[num-1]
        if page.get_images(full=True):
            graphic_candidates.append({"page": num, "kind": "raster"})
        for item in page.get_drawings():
            rect = item["rect"]
            if rect.width > 50 and rect.height > 30:
                graphic_candidates.append({"page": num, "kind": "vector"})
    assert not graphic_candidates, "Unlinked illustrations must be reviewed"
    sections, audited, unassigned = [], [], []
    used_codes = set()
    current = None
    for num in range(11, 67):
        lines = [line.strip() for line in pages[num-1].splitlines() if line.strip()]
        assert lines[0].startswith(("مبحث اول", "1-1", "2-1")), ("Unexpected header", num, lines[0])
        assert lines[-1] == str(num - 10), ("Unexpected footer", num, lines[-1])
        lines = lines[1:-1]
        item = {"pdf_page": num, "printed_page": num-10,
                "content_lines": len(lines), "assigned_lines": 0,
                "source_characters": sum(len(s) for s in lines),
                "image_candidates": 0}
        audited.append(item)
        for line_i, line in enumerate(lines, 1):
            m = HEADING.match(line)
            if m:
                printed_code = re.sub(r"\s+", "", m.group(1))
                code = "-".join(reversed(printed_code.split("-")))
                assert code not in used_codes and m.group(2).strip(), ("Duplicate/empty heading", code, num)
                used_codes.add(code)
                current = {
                    "id": "m01-1392-" + code, "number": code,
                    "source_pdf_code": printed_code, "title": m.group(2).strip(),
                    "order": len(sections)+1, "parent_id": None, "parent_inferred": False,
                    "source_page_start": num, "source_page_end": num,
                    "page_segments": [], "text": "", "assets": [],
                    "review_state": "machine_transferred"
                }
                sections.append(current)
            elif current is None:
                unassigned.append((num, line_i, line))
                continue
            segs = current["page_segments"]
            if not segs or segs[-1]["pdf_page"] != num:
                segs.append({"pdf_page": num, "printed_page": num-10, "lines": []})
            segs[-1]["lines"].append(line)
            current["source_page_end"] = num
            item["assigned_lines"] += 1
    assert not unassigned, ("Unassigned PDF lines", unassigned[:4])
    assert all(p["content_lines"] == p["assigned_lines"] for p in audited)
    by_id = {s["id"]: s for s in sections}
    ancestors = []
    for s in sections:
        parts = s["number"].split("-")
        parent = "m01-1392-" + "-".join(parts[:-1])
        if len(parts) > 2:
            if parent in by_id:
                s["parent_id"] = parent
            else:
                # Keep the printed anomaly, infer navigation parent only.
                candidates = [x for x in ancestors if len(x["number"].split("-")) == 3 and x["number"].startswith("1-1-")]
                if candidates:
                    s["parent_id"] = candidates[-1]["id"]
                    s["parent_inferred"] = True
        ancestors = [a for a in ancestors if len(a["number"].split("-")) < len(parts)]
        ancestors.append(s)
        contents = []
        for idx, segment in enumerate(s["page_segments"]):
            seg_lines = segment.pop("lines")
            segment["text"] = " ".join(seg_lines)
            contents.extend(seg_lines[1:] if idx == 0 else seg_lines)
        s["text"] = " ".join(contents).strip()
        s["search_text"] = normalize_search(s["title"]+" "+s["text"])
        s["search_terms"] = sorted(set(TOKEN.findall(s["search_text"])))
    defs = sorted(int(s["number"].split("-")[-1]) for s in sections
                  if re.fullmatch(r"1-2-\d+", s["number"]))
    assert defs == list(range(1, 269)), "Missing or duplicated definition code(s)"
    inverted = collections.defaultdict(list)
    for s in sections:
        for term in s["search_terms"]:
            inverted[term].append(s["id"])
    warnings = [{"code": s["number"], "printed": s["source_pdf_code"], "parent": s["parent_id"]}
                for s in sections if s["parent_inferred"]]
    doc_meta = {"id": "m01-1392", "mabhas": 1, "title": "تعاریف", "edition": "1392",
                "pdf_url": URL, "pdf_sha256": digest, "source_pdf_pages": 122}
    document = {"schema_version": 1, "document": doc_meta, "sections": sections}
    coverage = {"schema_version": 1, "document_id": doc_meta["id"],
                "source_sha256": digest, "pdf_pages": 122,
                "excluded_preliminary_pages": list(range(1, 11)),
                "duplicate_page_pairs": duplicates,
                "unique_content_pages": list(range(11, 67)),
                "pages": audited, "sections_indexed": len(sections),
                "definitions_indexed": 268, "assets_linked": 0,
                "unassigned_lines": 0, "unlinked_graphics": 0,
                "structure_warnings": warnings,
                "review_state": "structural_checks_passed_visual_proofreading_pending"}
    index = {"schema_version": 1, "document_id": doc_meta["id"],
             "postings": dict(sorted(inverted.items()))}
    return document, coverage, index

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("data/m01-1392"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    document, coverage, index = parse(args.pdf)
    print(json.dumps({
        "source_sha256": document["document"]["pdf_sha256"],
        "sections": len(document["sections"]),
        "content_pages": len(coverage["unique_content_pages"]),
        "definitions": coverage["definitions_indexed"],
        "numbering_warnings": coverage["structure_warnings"],
        "search_terms": len(index["postings"]),
        "empty_sections": [s["number"] for s in document["sections"] if not s["text"]][:30],
    }, ensure_ascii=False, indent=2))
    if args.dry_run:
        return
    args.out.mkdir(parents=True, exist_ok=True)
    for name, payload in [("sections.json", document), ("coverage.json", coverage),
                          ("search-index.json", index)]:
        (args.out / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

if __name__ == "__main__":
    main()
