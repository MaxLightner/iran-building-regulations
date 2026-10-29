"""PostgreSQL is the operational source. Manifest is discovery metadata only."""
import json
import os
from pathlib import Path
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
EMPTY = 'داده هنوز بارگذاری نشده'


def normalize(value):
    value = unicodedata.normalize('NFKC', value).translate(str.maketrans('يك٠١٢٣٤٥٦٧٨٩', 'یک0123456789'))
    return ' '.join(value.replace('\u200c', ' ').split())


class DatabaseUnavailable(Exception):
    pass


def query(sql, params=()):
    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        return None
    try:
        import psycopg
        from psycopg.rows import dict_row
        with psycopg.connect(dsn, connect_timeout=3, row_factory=dict_row) as conn:
            conn.execute("SET statement_timeout = '3000ms'")
            return conn.execute(sql, params).fetchall()
    except Exception as exc:
        # Never expose a DSN, credentials or driver diagnostics in HTTP responses.
        raise DatabaseUnavailable() from exc


def sources():
    rows = query('''SELECT d.id, d.title, d.kind, d.mabhas_number, d.official_page_url,
                          d.verification_status, s.name AS publisher
                   FROM documents d JOIN sources s ON s.id=d.source_id
                   ORDER BY d.mabhas_number NULLS LAST, d.id''')
    if rows is not None:
        return {'mode': 'database', 'items': rows}
    manifest = json.loads((ROOT / 'sources/manifest.json').read_text(encoding='utf-8'))
    return {'mode': 'catalog_only', 'message': EMPTY, 'items': manifest['documents'],
            'checked_at': manifest['checked_at'], 'coverage': manifest['coverage']}


def topics():
    rows = query('''SELECT t.id, t.title, t.summary, t.key_factors, t.updated_at
                   FROM topics t WHERE t.verification_status='approved'
                   AND EXISTS (SELECT 1 FROM topic_clauses tc
                     JOIN clauses c ON c.id=tc.clause_id
                     JOIN editions e ON e.id=c.edition_id
                     JOIN documents d ON d.id=e.document_id
                     WHERE tc.topic_id=t.id AND c.verification_status='approved'
                       AND e.verification_status='approved' AND d.verification_status='approved'
                       AND e.validity_status='current' AND e.sha256 IS NOT NULL
                       AND e.official_pdf_url IS NOT NULL AND c.locator IS NOT NULL AND c.pdf_page IS NOT NULL)
                   ORDER BY t.title''')
    return {'mode': 'database' if rows is not None else 'catalog_only',
            'items': rows or [], 'message': EMPTY if not rows else None,
            'applicability_status': 'not_implemented'}


def search(text):
    term = normalize(text)
    escaped = term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    rows = query('''SELECT c.id, c.title, c.original_text, c.locator, c.pdf_page,
                     c.printed_page, c.updated_at, e.id AS edition_id, e.label AS edition,
                     e.publication_date_text, e.effective_date_text, e.effective_date_status,
                     e.official_pdf_url, e.sha256, d.title AS document,
                     d.official_page_url AS source_url
                   FROM clauses c JOIN editions e ON e.id=c.edition_id
                   JOIN documents d ON d.id=e.document_id
                   WHERE c.verification_status='approved'
                     AND e.verification_status='approved'
                     AND d.verification_status='approved'
                     AND e.validity_status='current'
                     AND e.sha256 IS NOT NULL AND e.official_pdf_url IS NOT NULL
                     AND c.pdf_page IS NOT NULL AND c.locator IS NOT NULL
                     AND c.search_text LIKE %s ESCAPE E'\\\\'
                   ORDER BY c.id LIMIT 50''', ('%' + escaped + '%',))
    return {'mode': 'database' if rows is not None else 'catalog_only',
            'query': term, 'items': rows or [], 'limit': 50,
            'message': EMPTY if rows is None or not rows else None,
            'search_type': 'literal_keyword', 'applicability_status': 'not_implemented'}

