"""Fetch secondary copies for PRIVATE verification only.

The qsce.ir website is a third-party engineering resource portal, NOT the
issuing regulatory authority. Downloads are UNVERIFIED and must not be used
as currently effective regulations until checked against official editions.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import time
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sources" / "pdfs"
REPORT = ROOT / "sources" / "reference-mirror-report.json"
BASE = "https://qsce.ir/uploads/"
NAMES = {
    1: "یکم", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم",
    6: "ششم", 7: "هفتم", 8: "هشتم", 9: "نهم", 10: "دهم",
    11: "یازدهم", 12: "دوازدهم", 13: "سیزدهم", 14: "چهاردهم",
    15: "پانزدهم", 16: "شانزدهم", 17: "هفدهم", 18: "هجدهم",
    19: "نوزدهم", 20: "بیستم", 21: "بیست و یکم",
    22: "بیست و دوم", 23: "بیست و سوم", 24: "بیست و چهارم",
}
MAX = 65 * 1024 * 1024


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    # Probe a confirmed indexed PDF before attempting the rest.
    order = [24] + [i for i in range(1, 25) if i != 24]
    for i, n in enumerate(order, 1):
        label = "مبحث " + NAMES[n] + " مقررات ملی.pdf"
        url = BASE + quote(label)
        path = OUT / f"reference-m{n:02d}.pdf"
        row = {"mabhas": n, "url": url, "path": str(path.relative_to(ROOT)),
               "source_type": "third_party_unverified", "status": "failed",
               "checked_at": datetime.now(timezone.utc).isoformat()}
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; BuildingRegulationsPrivateResearch/1.0)", "Accept": "application/pdf,*/*;q=0.5"})
            with urlopen(req, timeout=35) as res:
                row["http_status"] = res.status
                if int(res.headers.get("Content-Length") or 0) > MAX:
                    raise ValueError("exceeds 65 MiB")
                if res.url.split("/")[2].lower() != "qsce.ir":
                    raise ValueError("unexpected redirect host")
                data = res.read(MAX + 1)
            if len(data) > MAX:
                raise ValueError("exceeds 65 MiB")
            if not data.startswith(b"%PDF-"):
                raise ValueError("not a PDF")
            digest = hashlib.sha256(data).hexdigest()
            row.update(sha256=digest, size_bytes=len(data))
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == digest:
                row["status"] = "unchanged"
            else:
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(data)
                tmp.replace(path)
                row["status"] = "saved"
        except HTTPError as e:
            row.update(http_status=e.code, error="HTTP " + str(e.code))
        except (URLError, OSError, ValueError, TimeoutError) as e:
            row["error"] = type(e).__name__ + ": " + str(e)[:200]
        results.append(row)
        print(f"{i}/24 m{n}: {row['status']} {row.get('error','')}", flush=True)
        # If the first representative file cannot be fetched, don't hammer the mirror.
        if i == 1 and row["status"] == "failed":
            print("Mirror probe failed; skipping remaining 23 URLs", flush=True)
            break
        time.sleep(0.3)
    REPORT.write_text(json.dumps({"generated_at":datetime.now(timezone.utc).isoformat(),
        "source_index":BASE, "source_status":"secondary_unverified",
        "warning":"Not authoritative; do not publish as approved regulations.",
        "attempted":len(results), "saved":sum(x["status"]=="saved" for x in results),
        "available":sum((OUT / f"reference-m{i:02d}.pdf").exists() for i in NAMES),
        "results":results},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
