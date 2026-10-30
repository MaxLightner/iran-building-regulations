#!/usr/bin/env python3
"""Evidence-based completeness audit. No OCR, scraping or network calls.

Passing an extraction step NEVER means a building code is complete or certified.
Certification requires human-reviewed, per-edition evidence for every gate.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "frontend" / "data"
REG = ROOT / "sources"
OUTPUT = DATA / "completeness-audit.json"
CHECKS = (
    "official_edition",
    "all_chapters_and_clauses",
    "tables_formulas_and_values",
    "figures_and_drawings",
    "amendments_and_appendices",
    "source_to_index_spot_checks",
)


def load(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def persian_ratio(rows):
    text = " ".join(str(x.get("answer") or x.get("text") or "") for x in rows[:60])[:50000]
    letters = sum(unicodedata.category(ch).startswith("L") for ch in text)
    persian = sum("\u0600" <= ch <= "\u06ff" and unicodedata.category(ch).startswith("L") for ch in text)
    return round(persian / max(1, letters), 3)


def page_count_from_attempts(item):
    attempts = item.get("attempts", [])
    return max((int(x.get("pages") or 0) for x in attempts if
                x.get("type") == "document" and x.get("accepted")), default=None)


def doc_for(n, target_edition):
    path = DATA / "submitted"
    matches = sorted(path.glob(f"m{n:02d}-*-direct.json"))
    for match in matches:
        result = load(match, {})
        if result.get("chapter") == n and result.get("records"):
            return result
    return None


def audit():
    registry = load(REG / "chapters.json", {}).get("chapters", [])
    assert len(registry) == 24 and {int(x["number"]) for x in registry} == set(range(1, 25))
    catalog = load(DATA / "catalog.json", [])
    raw_coverage = load(DATA / "coverage.json", {})
    visual = load(DATA / "visuals" / "index.json", {}).get("chapters", {})
    addenda = load(DATA / "addenda.json", [])
    evidence = load(REG / "verification-evidence.json", {})
    by_n = {int(x["number"]): x for x in catalog}
    target = {int(x["number"]): x for x in registry}
    archive19 = load(DATA / "m19-structured-backup.json", {}).get("records", [])
    results = []

    for n in range(1, 25):
        reg = target[n]
        raw = load(DATA / "chapters" / f"m{n:02d}.json", {})
        imported = doc_for(n, str(reg["edition"]))
        rows = list(raw.get("records") or [])
        source_kind = by_n.get(n, {}).get("method") or "unknown"
        edition = str(reg.get("edition", ""))
        doc_source = by_n.get(n, {}).get("source")
        warnings = []

        if source_kind == "ocr_page" or raw.get("status") == "ocr_index":
            # The historical OCR archive is not used in the live search.
            rows = []
            warnings.append("legacy_ocr_excluded")

        if imported:
            rows = imported["records"]
            source_kind = "direct_pdf_text"
            edition = str(imported.get("edition", edition))
            doc_source = imported.get("source_name")
            if edition != str(reg["edition"]):
                warnings.append("uploaded_edition_differs_from_target")
            if imported.get("pages_readable", 0) < imported.get("pages_total", 0) * .80:
                warnings.append("many_pages_unreadable_without_ocr")

        if n == 19 and len(archive19) > len(rows):
            rows = archive19
            source_kind = "structured_text_backup"
            warnings.append("previous_snapshot_restored")

        if not rows:
            warnings.append("no_non_ocr_searchable_text")

        if source_kind == "page_extract":
            warnings.append("page_chunks_not_clause_index")
        elif source_kind == "direct_pdf_text":
            warnings.append("direct_pdf_text_not_clause_index")

        ratio = persian_ratio(rows)
        if rows and ratio < .55:
            warnings.append("text_encoding_corruption_suspected")

        unique_refs = set()
        refs = []
        for record in rows:
            ref = str(record.get("locator") or "").strip()
            if ref:
                refs.append(ref)
                unique_refs.add(ref)
        duplicate_refs = len(refs) - len(unique_refs)
        if refs and duplicate_refs / len(refs) > .10:
            warnings.append("high_duplicate_locator_rate")
        if rows and not refs:
            warnings.append("no_verified_clause_locators")

        tiny = sum(1 for record in rows if len(str(record.get("answer") or "")) < 80)
        tiny_ratio = tiny / max(len(rows), 1)
        if len(rows) > 20 and tiny_ratio > .20:
            warnings.append("short_or_toc_like_excerpts_need_review")

        supplements = [x for x in addenda if int(x.get("chapter", -1)) == n]
        if supplements and any(not x.get("indexed") for x in supplements):
            warnings.append("known_amendments_not_indexed")

        visual_item = visual.get(str(n), {})
        thumbnails = len(visual_item.get("pages") or [])
        if thumbnails:
            warnings.append("visuals_are_page_previews_not_verified_figures")
        else:
            warnings.append("figures_and_tables_not_indexed")

        page_set = {int(r["page"]) for r in rows if isinstance(r.get("page"), int) and r["page"] > 0}
        pdf_pages = imported.get("pages_total") if imported else page_count_from_attempts(by_n.get(n, {}))
        page_ratio = round(len(page_set) / pdf_pages, 3) if pdf_pages else None
        if pdf_pages and len(page_set) < pdf_pages * .8:
            warnings.append("many_pdf_pages_without_indexed_text")

        # A certification is allowed only with independent evidence for EVERY gate.
        cert = evidence.get(str(n), {})
        checks = {
            k: bool(cert.get(k, {}).get("passed") is True and
                    str(cert.get(k, {}).get("evidence_uri", "")).strip())
            for k in CHECKS
        }
        certified = all(checks.values())
        pending = [k for k, passed in checks.items() if not passed]
        results.append({
            "chapter": n,
            "title": reg["title"],
            "target_edition": str(reg["edition"]),
            "indexed_edition": edition,
            "source_method": source_kind,
            "source_url_or_filename": doc_source,
            "indexed_records": len(rows),
            "distinct_clause_locators_unverified": len(unique_refs),
            "duplicated_clause_locators": duplicate_refs,
            "pdf_pages": pdf_pages,
            "pages_with_indexed_text": len(page_set) if pdf_pages else None,
            "page_presence_ratio_not_completeness": page_ratio,
            "persian_letter_ratio_sample": ratio,
            "short_excerpt_ratio": round(tiny_ratio, 3),
            "figure_page_previews_not_independent_figures": thumbnails,
            "known_addenda": len(supplements),
            "unindexed_addenda": sum(not x.get("indexed", False) for x in supplements),
            "certified_complete": certified,
            "checks": checks,
            "pending_checks": pending,
            "warnings": warnings,
            "extraction_note": "Indexed data and page previews do not establish textual or legal completeness.",
        })

    report = {
        "schema_version": 1,
        "basis": "Stored source files and metadata only; no OCR; no claims of official endorsement.",
        "definition_of_complete": "All six certification gates passed with independent evidence_uri; all editions, clauses, numerical tables, graphics and addenda reviewed.",
        "mandatory_checks": list(CHECKS),
        "summary": {
            "chapters": len(results),
            "certified_complete": sum(bool(x["certified_complete"]) for x in results),
            "not_certified": sum(not x["certified_complete"] for x in results),
            "active_search_records": sum(x["indexed_records"] for x in results),
            "encoding_risk": sum("text_encoding_corruption_suspected" in x["warnings"] for x in results),
            "no_verified_locators": sum("no_verified_clause_locators" in x["warnings"] for x in results),
            "visual_preview_chapters": sum(x["figure_page_previews_not_independent_figures"] > 0 for x in results),
            "known_unindexed_addenda": sum(x["unindexed_addenda"] for x in results),
        },
        "chapters": results,
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert report["summary"]["chapters"] == 24
    assert report["summary"]["certified_complete"] == 0 or evidence
    print(json.dumps(report["summary"], ensure_ascii=False), flush=True)
    for c in results:
        print(f"M{c['chapter']:02d}: {c['indexed_records']} rows, "
              f"{len(c['pending_checks'])}/6 gates pending, warnings={','.join(c['warnings'])}", flush=True)


if __name__ == "__main__":
    audit()
