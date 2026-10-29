"""Build a safe static index for GitHub Pages, with no runtime backend.

Only explicitly verified/approved and cleared data from data/records/*.json
can enter public search. Demo records live in a SEPARATE, labeled dataset.
No PDF binary, private manifest or secret is ever copied into frontend/.
"""
from pathlib import Path
import hashlib
import json
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "data"
INPUT = ROOT / "data" / "records"
SCHEMA = "1.0"


def normalize(value):
    value = unicodedata.normalize("NFKC", str(value or ""))
    value = value.translate(str.maketrans("يكىۀ‌", "یکیه "))
    value = re.sub(r"[\u064b-\u065f\u0670]", "", value)
    return " ".join(value.casefold().split())


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_record(record):
    required = {"id","document_id","edition_id","kind","locator","title",
        "original_text","summary","topic","tags","aliases","key_factors",
        "applicability","references","source","version","review"}
    if not isinstance(record, dict) or not required.issubset(record):
        raise ValueError("Incomplete record")
    if not isinstance(record["tags"], list) or not isinstance(record["aliases"], list):
        raise ValueError("Tags and aliases must be arrays")
    if record["kind"] not in {"clause","table","note","figure","appendix"}:
        raise ValueError("Invalid kind")
    return True


def publishable(record):
    source, version, review = record["source"], record["version"], record["review"]
    if review.get("status") != "approved" or not review.get("reviewer") or not review.get("reviewed_at"):
        return False
    if source.get("authority") != "official" or source.get("publication_rights") != "approved":
        return False
    if not re.fullmatch("[0-9a-f]{64}", source.get("sha256") or ""):
        return False
    if not isinstance(source.get("pdf_page"), int) or source["pdf_page"] < 1:
        return False
    if not (source.get("official_page_url") or "").startswith("https://inbr.ir/"):
        return False
    if not record.get("locator") or not record.get("original_text"):
        return False
    if version.get("status") not in ("current","historical"):
        return False
    if version.get("status") == "current" and not version.get("effective_evidence"):
        return False
    return True


def index_record(r):
    result = dict(r)
    result["search_text"] = normalize(" ".join([
        r["title"], r["original_text"], r["summary"], r["topic"], r["locator"],
        *r["tags"], *r["aliases"]]))
    return result


def main():
    manifest = load(ROOT / "sources" / "manifest.json")
    catalog = []
    for doc in manifest["documents"]:
        if doc.get("kind") != "regulation":
            continue
        catalog.append({"id":doc["id"],"number":doc["mabhas_number"],
            "title":doc["title"],"official_page_url":doc.get("official_page_url"),
            "verification_status":doc.get("verification_status","pending"),
            "validity_status":doc.get("validity_status","unconfirmed")})
    catalog.sort(key=lambda r:r["number"])
    files = sorted(INPUT.glob("*.json")) if INPUT.exists() else []
    checked, published, excluded = set(), [], []
    for path in files:
        content = load(path)
        for record in content.get("records", []):
            valid_record(record)
            if record["id"] in checked:
                raise ValueError("Duplicate record id: "+record["id"])
            checked.add(record["id"])
            if publishable(record):
                published.append(index_record(record))
            else:
                excluded.append(record["id"])
    demo = load(ROOT / "data" / "fixtures" / "demo-records.json")
    if any(r.get("review",{}).get("status") != "demo" for r in demo["records"]):
        raise ValueError("Demo data must have review.status=demo")
    for r in demo["records"]:
        valid_record(r)
    save(OUT / "catalog.json", {"schema_version":SCHEMA, "status":"unverified_catalog_only", "items":catalog})
    save(OUT / "records.json", {"schema_version":SCHEMA,
        "status":"approved_only", "items":published})
    save(OUT / "demo.json", {"schema_version":SCHEMA,
        "status":"demonstration_not_regulations", "items":[index_record(r) for r in demo["records"]]})
    save(OUT / "build-report.json", {"schema_version":SCHEMA, "catalog":len(catalog),
        "approved":len(published),"excluded":len(excluded),
        "excluded_ids":excluded,"note":"No unreviewed text published."})
    print("Catalog:",len(catalog),"approved:",len(published),"excluded:",len(excluded))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print("BUILD FAILED:",exc,file=sys.stderr)
        sys.exit(1)
