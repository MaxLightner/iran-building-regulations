#!/usr/bin/env python3
"""Phase 1: consolidate the project's existing full-text sources into a versioned
independent database. Offline. No OCR, no PDF parsing, no LLM completion.

The database retains EVERY usable embedded-text / HTML record, preserving the
source and the edition. Missing target editions are explicitly missing.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONT = ROOT / "frontend" / "data"
OUT = FRONT / "text-phase1"
SOURCES = ROOT / "sources"


def read(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return fallback


def normalized(value):
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def quality(rows):
    material = " ".join(str(r.get("answer") or r.get("text") or "") for r in rows[:80])[:90000]
    letters = sum(unicodedata.category(c).startswith("L") for c in material)
    farsi = sum("\u0600" <= c <= "\u06ff" and
                unicodedata.category(c).startswith("L") for c in material)
    score = round(farsi / max(1, letters), 3)
    has_usable_text = score >= .55 and len(material) >= 150
    return {"persian_letter_ratio": score, "readable": has_usable_text,
            "reason": None if has_usable_text else "insufficient_persian_or_corrupt_encoding"}


def records_from_payload(n, payload, source_key, kind, target_edition):
    output = []
    edition = str(payload.get("edition") or target_edition)
    for item in payload.get("records", []):
        # Quarantine ALL legacy OCR, including rows from old pre-OCR-reversal snapshots.
        if str(item.get("kind") or "") == "ocr_page":
            continue
        body = str(item.get("text") or item.get("answer") or "").strip()
        if len(normalized(body)) < 25:
            continue
        src = item.get("source_url") or payload.get("source_url") or source_key
        item_edition = str(item.get("edition") or edition)
        digest = hashlib.sha256(normalized(body).encode("utf-8")).hexdigest()
        output.append({
            "id": str(item.get("id") or f"m{n:02d}-{digest[:12]}"),
            "chapter": n,
            "edition": item_edition,
            "locator": item.get("locator"),
            "title": str(item.get("title") or "").strip(),
            "kind": item.get("kind") or kind,
            "text": body,
            "source_url": src,
            "source_key": source_key,
            "source_class": kind,
            "page": item.get("page"),
            "sha256": digest,
        })
    return output


def ingest():
    register = read(SOURCES / "chapters.json", {}).get("chapters", [])
    catalog = {int(x["number"]): x for x in read(FRONT / "catalog.json", [])}
    catalog_inventory = read(SOURCES / "text-source-inventory.json", {}).get("entries", [])
    inventory = {int(x["chapter"]): x for x in catalog_inventory}
    if len(register) != 24 or len(inventory) != 24:
        raise ValueError("All 24 source registry chapters must be present")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "chapters").mkdir(exist_ok=True)

    overview = []
    for entry in register:
        n = int(entry["number"])
        target = str(entry["edition"])
        candidates = []
        variants = []
        base = read(FRONT / "chapters" / f"m{n:02d}.json", {})
        primary_method = catalog.get(n, {}).get("method")
        if base.get("records") and primary_method != "ocr_page":
            candidates.extend(records_from_payload(
                n, base, str(catalog.get(n, {}).get("source") or "existing_corpus"),
                str(primary_method or "unknown"), target))
        else:
            if primary_method == "ocr_page":
                variants.append({"source": catalog.get(n, {}).get("source"),
                                 "reason": "legacy_ocr_not_imported"})

        for file in sorted((FRONT / "submitted").glob(f"m{n:02d}-*-direct.json")):
            sub = read(file, {})
            if sub.get("records"):
                candidates.extend(records_from_payload(
                    n, sub, file.name, "user_provided_embedded_pdf_text", target))
                if str(sub.get("edition")) != target:
                    variants.append({
                        "source": file.name,
                        "edition": str(sub.get("edition")),
                        "reason": "older_or_different_edition_retained_separately"
                    })
                if int(sub.get("pages_readable") or 0) < int(sub.get("pages_total") or 0) * .8:
                    variants.append({"source": file.name,
                                     "reason": "text_layer_incomplete_or_wrong_font_mapping"})

        if n == 19:
            backup = read(FRONT / "m19-structured-backup.json", {})
            if backup.get("records"):
                candidates.extend(records_from_payload(
                    n, backup, "m19-structured-backup.json",
                    "historic_structured_backup", target))

        # The dataset is versioned by edition, never merged across editions.
        grouped = defaultdict(list)
        for item in candidates:
            grouped[item["edition"]].append(item)
        versions = []
        total = 0
        for edition, entries in sorted(grouped.items()):
            # Merge exact duplicates; keep conflicting locator bodies for review.
            deduped, hashes, refs = [], set(), defaultdict(set)
            for item in entries:
                key = (item["sha256"], item.get("locator") or "", item.get("page") or 0)
                if key in hashes:
                    continue
                hashes.add(key)
                deduped.append(item)
                if item["locator"]:
                    refs[normalized(item["locator"])].add(item["sha256"])
            q = quality(deduped)
            conflict_count = sum(len(v) > 1 for v in refs.values())
            if conflict_count:
                variants.append({"edition": edition, "reason": "multiple_texts_share_a_locator",
                                 "conflicting_locators": conflict_count})
            included = q["readable"] and len(deduped) > 0
            versions.append({
                "edition": edition,
                "target_edition": edition == target,
                "record_count": len(deduped),
                "unique_locators_unverified": len(refs),
                "locators_with_different_text": conflict_count,
                "source_ids": sorted({str(x["source_key"]) for x in deduped}),
                "quality": q,
                "text_retrievable": included,
                "records": deduped,
            })
            total += len(deduped)

        target_rows = next((x for x in versions if x["target_edition"]), None)
        target_usable = bool(target_rows and target_rows["text_retrievable"])
        risks = []
        if not target_usable:
            risks.append("target_edition_full_text_missing_or_unreadable")
        if any(not x["quality"]["readable"] for x in versions):
            risks.append("some_text_encoding_unreadable")
        if any(x["locators_with_different_text"] for x in versions):
            risks.append("intra_edition_locator_conflicts")
        if target_rows and not target_rows["unique_locators_unverified"]:
            risks.append("no_clause_level_structure_in_target_version")
        if not versions:
            risks.append("no_non_ocr_text_sources")
        if any(not x["target_edition"] for x in versions):
            risks.append("multiple_editions_stored_without_merging")
        if n in (14, 16):
            risks.append("previous_index_includes_toc_like_records_review_needed")

        chapter_doc = {
            "chapter": n,
            "title": entry["title"],
            "target_edition": target,
            "target_text_present": target_usable,
            "complete_or_officially_verified": False,
            "total_stored_rows": total,
            "versions": versions,
            "source_inventory": inventory[n],
            "exceptions": variants,
            "gaps": risks,
            "note": "Not an official or fully checked edition; OCR never used.",
        }
        (OUT / "chapters" / f"m{n:02d}.json").write_text(
            json.dumps(chapter_doc, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8")
        overview.append({
            "chapter": n,
            "title": entry["title"],
            "target_edition": target,
            "target_text_present": target_usable,
            "versions": [{
                "edition": v["edition"],
                "records": v["record_count"],
                "readable": v["quality"]["readable"],
                "unverified_locators": v["unique_locators_unverified"]
            } for v in versions],
            "stored_rows": total,
            "gaps": risks,
            "source_file": f"./chapters/m{n:02d}.json",
        })
        print(f"M{n:02d}: {total} rows, versions={len(versions)}, target_text={target_usable}, gaps={risks}", flush=True)

    manifest = {
        "schema_version": 1,
        "phase": "text-first-source-consolidation",
        "note": "Actual text snapshots in our own repo, preserved by edition; no OCR and no invented sections.",
        "fully_verified_chapters": 0,
        "target_editions_with_any_readable_text": sum(x["target_text_present"] for x in overview),
        "target_editions_missing_text": [x["chapter"] for x in overview if not x["target_text_present"]],
        "chapters": overview,
        "total_stored_rows_including_historical_editions": sum(x["stored_rows"] for x in overview),
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PHASE1_TEXT_DATABASE", manifest["total_stored_rows_including_historical_editions"],
          "TARGET_EDITIONS_PRESENT", manifest["target_editions_with_any_readable_text"], "/24", flush=True)
    assert len(overview) == 24
    assert manifest["fully_verified_chapters"] == 0


if __name__ == "__main__":
    ingest()
