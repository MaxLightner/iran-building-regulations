"""Manual, bounded official-URL checks; immutable hash-addressed private PDF cache.

Never changes validity, approved editions, or operational clauses.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit, quote, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_HOSTS = {'inbr.ir', 'www.inbr.ir'}
MAX_BYTES = 80 * 1024 * 1024


def safe_url(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname not in ALLOWED_HOSTS or p.port not in (None, 443) or p.username or p.password:
        raise ValueError('URL must use HTTPS on the reviewed official host')
    return urlunsplit((p.scheme, p.netloc, quote(p.path, safe='/%-._~'), p.query, ''))


class OfficialRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, safe_url(newurl))


def check(asset, previous, cache):
    url = asset['url']
    record = {'asset_id': asset['id'], 'url': url, 'checked_at': datetime.now(timezone.utc).isoformat(),
              'http_status': None, 'observed_sha256': None, 'previous_sha256': previous,
              'result': 'failed', 'error': None}
    try:
        request = Request(safe_url(url), headers={'User-Agent': 'IranBuildingRegulationsScaffold/0.1'})
        with build_opener(OfficialRedirect()).open(request, timeout=15) as r:
            record.update(http_status=r.status, final_url=r.url, etag=r.headers.get('ETag'), last_modified=r.headers.get('Last-Modified'))
            if int(r.headers.get('Content-Length', '0')) > MAX_BYTES:
                raise ValueError('File exceeds 80 MiB bound')
            data = r.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError('File exceeds 80 MiB bound')
            if asset['kind'] == 'pdf' and not data.startswith(b'%PDF-'):
                raise ValueError('Response is not a PDF; no PDF hash recorded')
            digest = hashlib.sha256(data).hexdigest()
            record.update(observed_sha256=digest, bytes=len(data), result='first_seen' if not previous else ('unchanged' if previous == digest else 'changed'))
            if asset['kind'] == 'pdf' and cache:
                cache.mkdir(parents=True, exist_ok=True)
                target = cache / (digest + '.pdf')
                if not target.exists():
                    with target.open('xb') as handle:
                        handle.write(data)
                record['private_cache_file'] = target.name
    except HTTPError as e:
        record.update(http_status=e.code, error='HTTP ' + str(e.code))
    except Exception as e:
        record['error'] = type(e).__name__ + ': ' + str(e)[:240]
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asset', action='append', help='Check only named asset IDs (repeatable)')
    parser.add_argument('--download', action='store_true', help='Cache received PDFs outside the repository')
    args = parser.parse_args()
    cache = None
    if args.download:
        if not os.environ.get('SOURCE_CACHE_DIR'):
            parser.error('Set SOURCE_CACHE_DIR to a private directory outside this repository')
        cache = Path(os.environ['SOURCE_CACHE_DIR']).resolve()
        if cache == ROOT or ROOT in cache.parents:
            parser.error('Private PDF cache must be outside the repository')
    manifest_path = ROOT / 'sources/manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    assets = [a for a in manifest['assets'] if not args.asset or a['id'] in args.asset]
    if args.asset and set(args.asset) - {a['id'] for a in assets}:
        parser.error('Unknown asset ID')
    checks = ROOT / 'sources/checks'
    checks.mkdir(parents=True, exist_ok=True)
    state_path = checks / 'state.json'
    state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    failures = 0
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    with (checks / (run_id + '.jsonl')).open('x', encoding='utf-8') as log:
        for asset in assets:
            record = check(asset, state.get(asset['url']), cache)
            log.write(json.dumps(record, ensure_ascii=False) + '\n')
            log.flush()
            asset['last_check'] = record
            if record['observed_sha256']:
                state[asset['url']] = record['observed_sha256']
                asset['sha256'] = record['observed_sha256']
                asset['download_status'] = 'cached_private' if record.get('private_cache_file') else 'fetched_not_stored'
            else:
                failures += 1
                asset['download_status'] = 'failed'
            # Failed checks never erase a known good baseline or its historical evidence.
            print(asset['id'], record['result'], record.get('http_status'), flush=True)
    state_path.write_text(json.dumps(state, indent=2), encoding='utf-8')
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

