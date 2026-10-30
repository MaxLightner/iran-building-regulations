#!/usr/bin/env python3
"""Conservative paragraph/section importer for born-digital Persian regulation PDFs.

Never uses OCR. Excludes front matter, retains PDF/page provenance and fails closed
on unverifiable structure or unassociated illustrations. Import output is staged
until a separate visual proofreading pass approves it.
"""

import argparse
import collections
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

import fitz
from PIL import Image


BOOKS = {
    2: ("1384", "نظامات اداری", 10),
    3: ("1395", "حفاظت ساختمان‌ها در مقابل حریق", 17),
    4: ("1396", "الزامات عمومی ساختمان", 15),
    5: ("1396", "مصالح و فرآورده‌های ساختمانی", 18),
}
MAIN_LAST_PAGE = {2: 178, 3: 217, 4: 128, 5: 178}
APPENDICES = {
    3: [(219, 220, "پیوست ۱ · نظامات اداری"),
        (221, 226, "پیوست ۲ · واکنش مصالح در برابر آتش"),
        (227, 230, "واژه‌نامهٔ فارسی به انگلیسی")],
    5: [(180, 201, "پیوست ۱ · مصالح نوین"),
        (202, 291, "پیوست ۲ · استانداردهای مرجع"),
        (292, 303, "پیوست ۳ · واژه‌نامه")],
}
HEADING = re.compile(r"^\s*((?:\d{1,2}\s*-\s*){1,6}\d{1,3})(?!\s*-\s*\d)\s*(.*)$")
TOKEN = re.compile(r"[0-9a-zA-Z\u0621-\u06ff]{2,}")
CAPTION = re.compile(r"(جدول|شکل|نمودار)\s*((?:[0-9]{1,2}\s*-\s*)+[0-9]{1,2})")


def clean(text):
    text = unicodedata.normalize("NFKC", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Cf")
    return text.replace("ي", "ی").replace("ك", "ک").replace("ـ", "")


def search_normalize(text):
    text = clean(text).lower()
    text = "".join(c for c in text if not unicodedata.category(c).startswith("M"))
    return text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))


def parse_code(printed, chapter):
    parts = [int(x.strip()) for x in printed.split("-")]
    if len(parts) < 2 or len(parts) > 7:
        return None
    # In these RTL PDFs pdftotext emits printed code components in reverse.
    # Also reverse ambiguous codes such as 3-4-1-3 (both ends equal chapter).
    if parts[-1] == chapter:
        parts.reverse()
    elif parts[0] != chapter:
        return None
    return "-".join(map(str, parts))


def printable_page(path):
    raw = subprocess.check_output(["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"])
    pages = [clean(p) for p in raw.decode("utf-8").split("\f")]
    if not pages[-1].strip():
        pages.pop()
    return pages


def ignored_running_line(line, line_number, total):
    if re.fullmatch(r"[۰-۹٠-٩0-9]{1,4}", line) and (line_number < 3 or line_number > total - 3):
        return True
    if (line_number < 3 or line_number > total - 3) and re.fullmatch(r"مبحث\s+\S+", line):
        return True
    return False


def parse(chapter, path, max_pages=None):
    edition, title, first_body = BOOKS[chapter]
    source = path.read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    pdf = fitz.open(stream=source, filetype="pdf")
    pages = printable_page(path)
    if len(pages) != len(pdf):
        raise RuntimeError("PDF/text page count mismatch")
    start = first_body - 1
    end = min(len(pdf), MAIN_LAST_PAGE[chapter]) if max_pages is None else min(len(pdf), MAIN_LAST_PAGE[chapter], max_pages)
    sections, seen_codes, unassigned, graphics, excluded, page_audit = [], {}, [], [], [], []
    active = None
    for index in range(start, end):
        page_number = index + 1
        all_lines = [x.strip() for x in pages[index].splitlines() if x.strip()]
        lines = [(i, x) for i, x in enumerate(all_lines) if not ignored_running_line(x, i, len(all_lines))]
        page = pdf[index]
        raster_count = len(page.get_images(full=True))
        drawings = page.get_drawings()
        vector_count = len(drawings)
        caption_codes = []
        for caption_type, printed in CAPTION.findall(pages[index]):
            code = parse_code(printed, chapter)
            if code:
                caption_codes.append({"type": caption_type, "code": code})
        if raster_count or vector_count > 15:
            graphics.append({"pdf_page": page_number, "raster_count": raster_count,
                             "vector_drawings": vector_count, "caption_codes": caption_codes,
                             "assigned_to": None, "status": "requires_figure_to_clause_review"})
        audit = {"pdf_page": page_number, "source_lines": len(lines),
                 "assigned_lines": 0, "unassigned_lines": 0, "text_characters": sum(len(t) for _, t in lines),
                 "raster_count": raster_count, "vector_drawings": vector_count}
        page_audit.append(audit)
        if len(lines) == 0:
            excluded.append({"pdf_page": page_number, "reason": "no_extractable_substantive_text"})
        for i, line in lines:
            h = HEADING.match(line)
            code = parse_code(h.group(1), chapter) if h else None
            if code:
                rest = h.group(2).strip()
                if code in seen_codes:
                    prior = seen_codes[code]
                    # A repeated running section title, not a second section.
                    if i <= 2 and search_normalize(prior["title"]) == search_normalize(rest):
                        continue
                    # A repeated code on later pages must not silently fork the paragraph.
                    prior.setdefault("repeat_code_locations", []).append(page_number)
                    code = None
                else:
                    section = {"id": f"m{chapter:02d}-{edition}-{code}", "number": code,
                               "source_pdf_code": h.group(1), "title": rest[:180] or code,
                               "order": len(sections) + 1, "parent_id": None,
                               "parent_inferred": False, "source_page_start": page_number,
                               "source_page_end": page_number, "page_segments": [], "text": "",
                               "assets": [], "review_state": "machine_transferred_unverified"}
                    sections.append(section)
                    seen_codes[code] = section
                    active = section
                    # Keep the complete first line; it may contain an obligation.
            if active is None:
                unassigned.append({"pdf_page": page_number, "line": i + 1, "text": line})
                audit["unassigned_lines"] += 1
                continue
            if not active["page_segments"] or active["page_segments"][-1]["pdf_page"] != page_number:
                active["page_segments"].append({"pdf_page": page_number, "lines": []})
            active["page_segments"][-1]["lines"].append(line)
            active["source_page_end"] = page_number
            audit["assigned_lines"] += 1

    for section in sections:
        code = section["number"]
        parts = code.split("-")
        parent = "-".join(parts[:-1])
        if parent in seen_codes:
            section["parent_id"] = seen_codes[parent]["id"]
        text_lines = []
        for segment in section["page_segments"]:
            lines = segment.pop("lines")
            segment["text"] = "\n".join(lines)
            text_lines.extend(lines)
        # A printed chapter/section heading is navigation, never an answer.
        if len(text_lines) == 1:
            heading = HEADING.match(text_lines[0])
            if heading and search_normalize(heading.group(2)) == search_normalize(section["title"]):
                section["text"] = ""
            else:
                section["text"] = "\n".join(text_lines).strip()
        else:
            section["text"] = "\n".join(text_lines).strip()
        section["search_text"] = search_normalize(section["title"] + " " + section["text"])
        section["search_terms"] = sorted(set(TOKEN.findall(section["search_text"])))

    # Appendices are part of the book, but they are not the final numbered clause.
    # Index them as explicitly named book divisions with their own page ranges.
    for number, (first, last, appendix_title) in enumerate(APPENDICES.get(chapter, []), 1):
        if max_pages is not None and first > max_pages:
            break
        last = min(last, len(pdf), max_pages if max_pages is not None else len(pdf))
        segments = []
        for p in range(first, last + 1):
            page_lines = [s.strip() for s in pages[p-1].splitlines() if s.strip()]
            substantive = [line for i, line in enumerate(page_lines)
                           if not ignored_running_line(line, i, len(page_lines))]
            segments.append({"pdf_page": p, "text": "\n".join(substantive)})
            page_audit.append({"pdf_page": p, "source_lines": len(substantive),
                               "assigned_lines": len(substantive), "unassigned_lines": 0,
                               "text_characters": sum(map(len, substantive)),
                               "raster_count": len(pdf[p-1].get_images(full=True)),
                               "vector_drawings": len(pdf[p-1].get_drawings())})
        content = "\n".join(x["text"] for x in segments)
        section = {"id": f"m{chapter:02d}-{edition}-appendix-{number}",
                   "number": f"{chapter}-A{number}", "source_pdf_code": f"پیوست {number}",
                   "title": appendix_title, "order": len(sections) + 1, "parent_id": None,
                   "parent_inferred": False, "source_page_start": first, "source_page_end": last,
                   "page_segments": segments, "text": content, "assets": [],
                   "review_state": "machine_transferred_unverified",
                   "search_text": search_normalize(appendix_title + " " + content)}
        section["search_terms"] = sorted(set(TOKEN.findall(section["search_text"])))
        sections.append(section)
        seen_codes[section["number"]] = section

    for graphic in graphics:
        targets = [seen_codes[x["code"]] for x in graphic["caption_codes"] if x["code"] in seen_codes]
        if targets:
            # Multiple captions on one page can refer to multiple actual clauses.
            graphic["assigned_to"] = sorted(set(s["id"] for s in targets))
            graphic["status"] = "caption_code_linked_page_preview"

    # PDF graphics are deliberately *not* attached to arbitrary neighboring codes.
    # The review workflow must place every figure/table against its actual clause.
    index = collections.defaultdict(list)
    for section in sections:
        for term in section["search_terms"]:
            index[term].append(section["id"])
    document_id = f"m{chapter:02d}-{edition}"
    document = {"schema_version": 1, "document": {
        "id": document_id, "mabhas": chapter, "title": title, "edition": edition,
        "pdf_sha256": digest, "source_pdf_pages": len(pdf),
        "pdf_url": f"https://dl.archweb.ir/Mabahes-File/Mabhas-{chapter}-%28Virayesh-{edition}%29.pdf",
    }, "sections": sections}
    coverage = {"schema_version": 1, "document_id": document_id, "source_sha256": digest,
                "source_pdf_pages": len(pdf), "included_page_range": [first_body, end],
                "excluded_preliminary_pages": list(range(1, first_body)),
                "appendix_ranges": APPENDICES.get(chapter, []),
                "separating_blank_pages": [x for x in range(end+1, len(pdf)+1)
                                            if not any(a <= x <= b for a, b, _ in APPENDICES.get(chapter, []))],
                "pages": page_audit, "sections_indexed": len(sections),
                "unassigned_lines": unassigned, "graphic_candidates": graphics,
                "unlinked_graphic_pages": sum(not x["assigned_to"] for x in graphics),
                "page_warnings": excluded,
                "review_state": "staging_only_needs_structure_graphics_and_text_visual_proofreading"}
    search_index = {"schema_version": 1, "document_id": document_id,
                    "postings": dict(sorted(index.items()))}
    return document, coverage, search_index


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--chapter", type=int, choices=BOOKS, required=True)
    p.add_argument("--pdf", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("staging"))
    p.add_argument("--max-pages", type=int)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--render-assets", action="store_true", help="Render each caption-linked graphic page as WebP")
    args = p.parse_args()
    document, coverage, index = parse(args.chapter, args.pdf, args.max_pages)
    print(json.dumps({"chapter": args.chapter, "sections": len(document["sections"]),
                      "unassigned_lines": len(coverage["unassigned_lines"]),
                      "unlinked_graphic_pages": coverage["unlinked_graphic_pages"],
                      "page_warnings": coverage["page_warnings"][:12],
                      "first_codes": [s["number"] for s in document["sections"][:15]],
                      "duplicate_code_locations": [(s["number"], s.get("repeat_code_locations")) for s in document["sections"] if s.get("repeat_code_locations")][:12]}, ensure_ascii=False, indent=2))
    if args.dry_run:
        return
    folder = args.out / document["document"]["id"]
    folder.mkdir(parents=True, exist_ok=True)
    if args.render_assets:
        with fitz.open(args.pdf) as pdf:
            by_id = {s["id"]: s for s in document["sections"]}
            for graphic in coverage["graphic_candidates"]:
                if not graphic["assigned_to"]:
                    continue
                page_number = graphic["pdf_page"]
                filename = f"p{page_number:04d}.webp"
                output = folder / "assets" / filename
                output.parent.mkdir(parents=True, exist_ok=True)
                pix = pdf[page_number - 1].get_pixmap(matrix=fitz.Matrix(1.8, 1.8), alpha=False)
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                image.save(output, "WEBP", quality=82, method=5)
                codes = ", ".join(x["code"] for x in graphic["caption_codes"])
                for target in graphic["assigned_to"]:
                    by_id[target]["assets"].append({
                        "type": "source_page_with_table_or_figure", "file": f"{args.out.name}/{document['document']['id']}/assets/{filename}",
                        "caption": f"جدول یا شکل {codes}؛ صفحه {page_number} PDF",
                        "source_pdf_page": page_number, "link_method": "caption_code",
                        "asset_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                    })
                graphic["asset_file"] = str(output.relative_to(args.out))
    for name, payload in [("sections.json", document), ("coverage.json", coverage), ("search-index.json", index)]:
        (folder / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
