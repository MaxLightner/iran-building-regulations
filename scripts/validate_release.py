#!/usr/bin/env python3
"""Block publishing if imported clauses, references or linked images are broken."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG = json.loads((ROOT / "data/catalog.json").read_text(encoding="utf-8"))


def validate(topic):
    dataset = ROOT / topic["dataset"]
    document = json.loads((dataset / "sections.json").read_text(encoding="utf-8"))
    coverage = json.loads((dataset / "coverage.json").read_text(encoding="utf-8"))
    metadata = document["document"]
    assert metadata["mabhas"] == topic["mabhas"]
    sections = document["sections"]
    assert sections and len(sections) == topic["sections"]
    ids = {s["id"] for s in sections}
    codes = [s["number"] for s in sections]
    assert len(ids) == len(sections) == len(set(codes)), "Duplicated clause id/number"
    assets_count = 0
    for i, s in enumerate(sections, start=1):
        assert s["order"] == i, (topic["mabhas"], s["id"], "order")
        assert s["number"].startswith(str(topic["mabhas"]) + "-"), s["number"]
        assert 1 <= s["source_page_start"] <= s["source_page_end"] <= metadata["source_pdf_pages"]
        assert s["page_segments"], s["id"]
        if s["parent_id"]:
            assert s["parent_id"] in ids, s["parent_id"]
        for seg in s["page_segments"]:
            assert s["source_page_start"] <= seg["pdf_page"] <= s["source_page_end"]
        for asset in s["assets"]:
            p = ROOT / asset["file"]
            assert p.is_file(), asset["file"]
            assert asset["source_pdf_page"] > 0
            assert hashlib.sha256(p.read_bytes()).hexdigest() == asset["asset_sha256"]
            assert asset["link_method"] == "caption_code", asset
            assets_count += 1
    if topic["mabhas"] in (4, 5):
        assert coverage["unlinked_graphic_pages"] == 0
        assert len(coverage["unassigned_lines"]) <= 1
        audited = [p["pdf_page"] for p in coverage["pages"]]
        separating = coverage["separating_blank_pages"]
        assert len(audited) == len(set(audited))
        assert set(audited).isdisjoint(separating)
        assert set(audited) | set(separating) == set(range(coverage["included_page_range"][0], metadata["source_pdf_pages"] + 1))
        assert assets_count >= topic["graphics_page_previews_linked"]
    return {"mabhas": topic["mabhas"], "sections": len(sections), "assets": assets_count}


def main():
    result = [validate(topic) for topic in CATALOG["topics"] if topic.get("dataset")]
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
