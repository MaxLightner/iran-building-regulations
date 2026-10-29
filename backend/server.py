"""Dependency-free development server; versioned JSON API + static RTL client."""
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server
from backend import store

FRONTEND = store.ROOT / 'frontend'


def response(start, status, body, content_type='application/json; charset=utf-8'):
    if not isinstance(body, bytes):
        body = json.dumps(body, ensure_ascii=False, default=str).encode('utf-8')
    start(status, [('Content-Type', content_type), ('Content-Length', str(len(body))),
                  ('X-Content-Type-Options', 'nosniff'), ('Cache-Control', 'no-store'),
                  ('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")])
    return [body]


def validate_project(body):
    if not isinstance(body, dict):
        raise ValueError('Project must be an object')
    options = json.loads((FRONTEND / 'options.json').read_text(encoding='utf-8'))
    for field in ('city', 'use', 'structure', 'stage'):
        if body.get(field) not in options[field]:
            raise ValueError('گزینه نامعتبر: ' + field)
    for field, low, high in [('area', 1, 1000000), ('floors', 1, 200), ('basements', 0, 20)]:
        value = body.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
            raise ValueError('مقدار نامعتبر: ' + field)
        if field != 'area' and int(value) != value:
            raise ValueError('تعداد طبقات باید عدد صحیح باشد')
    return body


def app(env, start):
    path, method = env.get('PATH_INFO', '/'), env.get('REQUEST_METHOD', 'GET')
    send = lambda status, data: response(start, status, data)
    try:
        if method == 'GET' and path in ('/health', '/api/v1/health'):
            configured = bool(os.environ.get('DATABASE_URL'))
            if configured:
                store.query('SELECT 1')
            return send('200 OK', {'status': 'ok', 'phase': 0, 'database': 'connected' if configured else 'not_configured', 'operational_data': 'not_certified'})
        if method == 'GET' and path == '/api/v1/sources':
            return send('200 OK', store.sources())
        if method == 'GET' and path == '/api/v1/topics':
            return send('200 OK', store.topics())
        if method == 'GET' and path == '/api/v1/search':
            text = parse_qs(env.get('QUERY_STRING', '')).get('q', [''])[0]
            if not 2 <= len(text.strip()) <= 200:
                return send('400 Bad Request', {'message': 'عبارت جست‌وجو باید بین ۲ تا ۲۰۰ نویسه باشد'})
            return send('200 OK', store.search(text))
        if method == 'POST' and path == '/api/v1/project-preview':
            size = int(env.get('CONTENT_LENGTH') or 0)
            if not 0 < size <= 8192:
                return send('413 Payload Too Large', {'message': 'اندازه درخواست نامعتبر است'})
            body = validate_project(json.loads(env['wsgi.input'].read(size)))
            return send('200 OK', {'project': body, **store.topics(), 'persisted': False,
                                   'message': 'تطبیق ضوابط با مشخصات پروژه هنوز آماده نشده است'})
        if method == 'GET' and path == '/openapi.json':
            return response(start, '200 OK', (store.ROOT / 'docs/openapi.json').read_bytes())
        # Explicit static allowlist: source PDFs, .env and repository files cannot be served.
        name = {'/': 'index.html', '/app.js': 'app.js', '/styles.css': 'styles.css',
                '/options.json': 'options.json'}.get(path)
        if method == 'GET' and name:
            return response(start, '200 OK', (FRONTEND / name).read_bytes(),
                            (mimetypes.guess_type(name)[0] or 'text/plain') + '; charset=utf-8')
        if path.startswith('/api/') and method not in ('GET', 'POST'):
            return send('405 Method Not Allowed', {'message': 'روش درخواست پشتیبانی نمی‌شود'})
        return send('404 Not Found', {'message': 'مسیر پیدا نشد'})
    except (ValueError, TypeError, UnicodeDecodeError):
        return send('400 Bad Request', {'message': 'درخواست نامعتبر است'})
    except store.DatabaseUnavailable:
        return send('503 Service Unavailable', {'message': 'ارتباط پایگاه داده آماده نیست', 'code': 'database_unavailable'})
    except Exception:
        return send('500 Internal Server Error', {'message': 'خطای داخلی؛ گزارش محلی را بررسی کنید'})


if __name__ == '__main__':
    host, port = os.environ.get('HOST', '127.0.0.1'), int(os.environ.get('PORT', '8765'))
    print(f'Local scaffold: http://{host}:{port}', flush=True)
    with make_server(host, port, app) as server:
        server.serve_forever()

