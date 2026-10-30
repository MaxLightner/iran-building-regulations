#!/usr/bin/env python3
"""Audit availability of searchable text and page imagery in sourced books."""

import argparse
import hashlib
import json
from pathlib import Path

import fitz


def audit(path: Path, chapter: int, edition: str) -> dict:
    source = path.read_bytes()
    document = fitz.open(stream=source, filetype="pdf")
    pages = []
    for index, page in enumerate(document):
        text = page.get_text().strip()
        raster_count = len(page.get_images(full=True))
        drawing_count = len(page.get_drawings())
        pages.append({
            "pdf_page": index + 1,
            "text_characters": len(text),
            "raster_image_count": raster_count,
            "vector_drawing_count": drawing_count,
            "image_only": len(text) < 30 and (raster_count > 0 or drawing_count > 0),
        })
    return {
        "chapter": chapter,
        "edition": edition,
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "pdf_pages": len(document),
        "text_characters": sum(p["text_characters"] for p in pages),
        "image_only_pages": [p["pdf_page"] for p in pages if p["image_only"]],
        "no_extractable_text_pages": [p["pdf_page"] for p in pages if p["text_characters"] < 30],
        "pages": pages,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=Path("/tmp"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    reports = []
    for chapter, edition in [(1, "1392"), (2, "1384"), (3, "1395"), (4, "1396"),
                             (5, "1396"), (6, "1398"), (7, "1400"), (8, "1398"),
                             (9, "1399"), (10, "1401")]:
        reports.append(audit(args.source_dir / f"m{chapter:02d}-{edition}.pdf", chapter, edition))
    result = {"schema_version": 1, "reports": reports}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps([{k: v for k, v in r.items() if k != "pages"} for r in reports], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
