"""Download official regulation PDFs into a PRIVATE GitHub repository.

This script fetches only verified https://inbr.ir URLs already listed in the
manifest. It never infers legal validity or overwrites a known-good file on
failure. It is for private archival and source comparison, not public hosting.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit, quote
from urllib.request import Request, HTTPRedirectHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "sources" / "manifest.json"
PDF_DIR = ROOT / "sources" / "pdfs"
REPORT = ROOT / "sources" / "pdf-download-report.json"
MAX_BYTES = 70 * 1024 * 1024
ALLOWED = {"inbr.ir", "www.inbr.ir"}


def safe_url(url: str) -> str:
    u = urlsplit(url)
    if u.scheme != "https" or u.hostname not in ALLOWED or u.port not in (None, 443) or u.username or u.password:
        raise ValueError("Not an allowed official HTTPS URL")
    return urlunsplit((u.scheme, u.netloc, quote(u.path, safe="/%-._~"), u.query, ""))


class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, safe_url(newurl))


def receive(asset):
    url = safe_url(asset["url"])
    request = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; IranianBuildingRegulationsArchive/0.1)",
        "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.5",
    })
    with build_opener(Redirects()).open(request, timeout=28) as response:
        status = response.status
        length = response.headers.get("Content-Length")
        if length and int(length) > MAX_BYTES:
            raise ValueError("PDF exceeds 70 MiB limit")
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("PDF exceeds 70 MiB limit")
        if not data.startswith(b"%PDF-"):
            raise ValueError("Server did not return a PDF")
        return data, status


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assets = [a for a in manifest["assets"] if a.get("kind") == "pdf"]
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    outcomes = []
    changed = 0
    for i, asset in enumerate(assets, 1):
        name = asset["id"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            raise ValueError("Invalid PDF identifier " + repr(name))
        path = PDF_DIR / (name + ".pdf")
        entry = {"id": name, "source_url": asset["url"], "path": str(path.relative_to(ROOT)),
                 "checked_at": datetime.now(timezone.utc).isoformat(), "outcome": "failed"}
        try:
            data, http = receive(asset)
            digest = hashlib.sha256(data).hexdigest()
            entry.update(http_status=http, sha256=digest, bytes=len(data))
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == digest:
                entry["outcome"] = "unchanged"
            else:
                # Replace only after the complete new PDF has been validated.
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(data)
                tmp.replace(path)
                entry["outcome"] = "saved"
                changed += 1
            asset["sha256"] = digest
            asset["download_status"] = "stored_private_repo"
            asset["private_git_path"] = entry["path"]
        except HTTPError as exc:
            entry.update(http_status=exc.code, error=f"HTTP {exc.code}")
        except (URLError, OSError, ValueError, TimeoutError) as exc:
            entry["error"] = f"{type(exc).__name__}: {str(exc)[:180]}"
        outcomes.append(entry)
        print(f"{i}/{len(assets)} {name}: {entry['outcome']} {entry.get('error', '')}", flush=True)
        time.sleep(0.3)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "notice": "Not proof of current legal validity or redistribution rights; private archival only.",
        "attempted": len(assets), "saved_new_or_changed": changed,
        "available_in_repository": sum((PDF_DIR / (a["id"] + ".pdf")).exists() for a in assets),
        "results": outcomes,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("TOTAL", report["attempted"], "SAVED", changed, "PRESENT", report["available_in_repository"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
