"""Run with an already running local server: python scripts/smoke.py."""
import json
import os
from urllib.request import urlopen, Request
from urllib.error import HTTPError

BASE = os.environ.get('SMOKE_BASE_URL', 'http://127.0.0.1:8765')


def get(path):
    with urlopen(BASE + path, timeout=5) as r:
        return json.load(r)


assert get('/health')['status'] == 'ok'
assert len(get('/api/v1/sources')['items']) >= 24
assert get('/api/v1/topics')['items'] == []  # phase-zero environment only
assert get('/api/v1/search?q=stairs')['items'] == []
with urlopen(Request(BASE+'/api/v1/project-preview', data=json.dumps({'city':'تهران','use':'مسکونی','structure':'فولادی','stage':'طراحی','area':500.25,'floors':3,'basements':1}).encode(),headers={'Content-Type':'application/json'})) as r:
    data=json.load(r)
    assert not data['persisted'] and data['applicability_status']=='not_implemented'
for path, code in [('/api/v1/search?q=x',400),('/.env',404),('/sources/manifest.json',404),('/../README.md',404)]:
    try:
        urlopen(BASE+path)
        raise AssertionError('Expected rejection: '+path)
    except HTTPError as e:
        assert e.code==code
assert get('/openapi.json')['openapi']=='3.1.0'
print('PASS: health, catalog, empty-data truthfulness, project preview, validation, file isolation, OpenAPI')

