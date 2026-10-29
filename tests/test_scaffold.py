import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.server import app
from backend import store
from scripts.check_sources import check, safe_url


def request(path, method='GET', body=None, query=''):
    raw=json.dumps(body).encode() if body is not None else b''
    env={'PATH_INFO':path,'REQUEST_METHOD':method,'QUERY_STRING':query,'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw)}
    status=[]
    content=b''.join(app(env,lambda s,h:status.append(s)))
    return int(status[0].split()[0]),json.loads(content)


class Scaffold(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'DATABASE_URL':''});self.env.start()
    def tearDown(self): self.env.stop()
    def test_no_fake_data(self):
        for endpoint in ('topics','search'):
            code,data=request('/api/v1/'+endpoint,query='q=stairs')
            self.assertEqual(code,200);self.assertEqual(data['items'],[])
            self.assertEqual(data['message'],store.EMPTY)
    def test_database_failure_is_visible(self):
        with patch('backend.store.query',side_effect=store.DatabaseUnavailable):
            self.assertEqual(request('/api/v1/topics')[0],503)
    def test_invalid_project_and_count(self):
        self.assertEqual(request('/api/v1/project-preview','POST',[])[0],400)
        valid={'city':'تهران','use':'مسکونی','structure':'فولادی','stage':'طراحی','area':500.25,'floors':3,'basements':0}
        self.assertEqual(request('/api/v1/project-preview','POST',valid)[0],200)
        for field,value in [('floors',1.5),('basements',-1),('area',0),('city','unknown')]:
            body={**valid,field:value}
            self.assertEqual(request('/api/v1/project-preview','POST',body)[0],400)
    def test_keyword_is_parameterized_and_literal(self):
        with patch('backend.store.query',return_value=[]) as q:
            store.search("عرض%_پله'")
            sql,params=q.call_args.args
            self.assertNotIn("عرض",sql)
            self.assertEqual(params,("%عرض\\%\\_پله'%",))
            self.assertIn("c.verification_status='approved'",sql)
    def test_normalize_preserves_original_contract(self):
        self.assertEqual(store.normalize('كف\u200cپله يک'),'کف پله یک')
    def test_official_url_boundary(self):
        for url in ['http://inbr.ir/a.pdf','https://example.com/a.pdf','https://inbr.ir.evil.test/a.pdf','https://user:pass@inbr.ir/a.pdf','https://inbr.ir:444/a.pdf']:
            with self.assertRaises(ValueError):safe_url(url)
    def test_hash_changes_and_pdf_guard(self):
        class FakeResponse:
            status=200;url='https://inbr.ir/test.pdf';headers={}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return b'%PDF-1.7\nTest fixture only'
        (ROOT/'test-results').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'test-results') as directory,patch('scripts.check_sources.build_opener') as opener:
            opener.return_value.open.return_value=FakeResponse()
            asset={'id':'test','url':'https://inbr.ir/test.pdf','kind':'pdf'}
            a=check(asset,None,Path(directory));self.assertEqual(a['result'],'first_seen')
            self.assertEqual(check(asset,a['observed_sha256'],None)['result'],'unchanged')
            self.assertEqual(check(asset,'0'*64,None)['result'],'changed')
            self.assertEqual(len(list(Path(directory).glob('*.pdf'))),1)
            with patch.object(FakeResponse,'read',return_value=b'<html>denied</html>'):
                rejected=check(asset,a['observed_sha256'],None)
                self.assertIsNone(rejected['observed_sha256']);self.assertEqual(rejected['result'],'failed')
    def test_manifest_has_no_false_validity(self):
        manifest=json.loads((ROOT/'sources/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(len([d for d in manifest['documents'] if d['kind']=='regulation']),24)
        for d in manifest['documents']:self.assertEqual(d['verification_status'],'pending')
        for a in manifest['assets']:
            safe_url(a['url'])
            if a['kind']=='pdf':self.assertIsNone(a['effective_date'])


if __name__=='__main__':unittest.main()

