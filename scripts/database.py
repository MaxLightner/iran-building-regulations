"""Explicit PostgreSQL setup and catalog import. No automatic approval or extraction."""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['migrate', 'import-catalog', 'import-checks'])
    p.add_argument('--checks-file', type=Path)
    args = p.parse_args()
    if not os.environ.get('DATABASE_URL'):
        p.error('DATABASE_URL is required; no fallback database is used')
    try:
        import psycopg
    except ImportError:
        p.error('psycopg is not installed; consult README and approve dependency installation first')
    with psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=5) as conn:
        if args.action == 'migrate':
            # Dedicated connection lock serializes migration runners.
            conn.execute('SELECT pg_advisory_xact_lock(149521003)')
            conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY, sha256 text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())')
            for path in sorted((ROOT / 'db/migrations').glob('*.sql')):
                content = path.read_bytes()
                digest = hashlib.sha256(content).hexdigest()
                existing = conn.execute('SELECT sha256 FROM schema_migrations WHERE name=%s', (path.name,)).fetchone()
                if existing:
                    if existing[0] != digest:
                        raise RuntimeError('Applied migration changed: ' + path.name)
                    continue
                conn.execute(content.decode('utf-8'))
                conn.execute('INSERT INTO schema_migrations(name,sha256) VALUES (%s,%s)', (path.name, digest))
                print('Applied', path.name)
        elif args.action == 'import-catalog':
            m = json.loads((ROOT / 'sources/manifest.json').read_text(encoding='utf-8'))
            conn.execute('''INSERT INTO sources(id,name,official_base_url,authority_type,checked_at)
                            VALUES ('inbr',%s,'https://inbr.ir/','government_office',%s) ON CONFLICT(id) DO NOTHING''', ('دفتر مقررات ملی و کنترل ساختمان',m['checked_at']))
            for d in m['documents']:
                conn.execute('''INSERT INTO documents(id,source_id,mabhas_number,title,kind,official_page_url,parent_document_id)
                    VALUES (%s,'inbr',%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING''', (d['id'],d['mabhas_number'],d['title'],d['kind'],d['official_page_url'],d.get('parent_document_id')))
            for a in m['assets']:
                if a['kind'] != 'pdf':
                    continue
                conn.execute('''INSERT INTO editions(id,document_id,label,edition_number,edition_year_text,official_pdf_url,sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING''', (a['id'],a['document_id'],a.get('label'),a.get('edition_number'),a.get('edition_year_text'),a['url'],a.get('sha256')))
            print('Imported discovery metadata only; all records remain pending/unconfirmed')
        else:
            if not args.checks_file:
                p.error('--checks-file is required')
            for line in args.checks_file.read_text(encoding='utf-8').splitlines():
                r = json.loads(line)
                conn.execute('''INSERT INTO source_checks(source_id,url,final_url,checked_at,http_status,observed_sha256,previous_sha256,result,error,etag,last_modified)
                    VALUES ('inbr',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''', tuple(r.get(k) for k in ['url','final_url','checked_at','http_status','observed_sha256','previous_sha256','result','error','etag','last_modified']))
            print('Imported check history; no validity or clause records changed')


if __name__ == '__main__':
    main()

