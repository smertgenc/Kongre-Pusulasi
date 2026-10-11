import base64
import copy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from app.main import create_app
from app.database import SCHEMA_VERSION
from app.ai_provider import source_input
from app.ai_schemas import SourceInput
from app.models import AIAnalysis
from app.search import SearchConnection, search_web, safe_result_url
from app.sources import extract_sources
from app.image_ocr import extract_image, image_bytes
from app.services import encode, now
from tests.test_ai import FixtureProvider, TEXT

class SearchContractTests(unittest.TestCase):
    def run_search(self,pid,payload,status=200):
        seen=[]
        def handler(request):
            seen.append(request)
            return httpx.Response(status,json=payload)
        client=httpx.Client(transport=httpx.MockTransport(handler))
        with patch('app.search.httpx.Client',return_value=client):
            result=search_web('Kongre 2027 / bilim kurulu',SearchConnection(pid,'test-secret'))
        return result,seen[0]

    def test_jina_query_auth_content_and_original_url(self):
        rows,req=self.run_search('jina',{'data':[{'title':'Program','url':'https://example.org/program','content':TEXT}]})
        self.assertEqual(req.method,'GET');self.assertEqual(req.url.host,'s.jina.ai')
        self.assertEqual(req.url.params['count'],'3');self.assertEqual(req.headers['Authorization'],'Bearer test-secret')
        self.assertIn('2027%20%2F',req.url.raw_path.decode())
        self.assertEqual(rows[0]['text'],TEXT);self.assertFalse(rows[0]['excerpt_only'])

    def test_tavily_search_only_no_generated_answer(self):
        rows,req=self.run_search('tavily',{'answer':'MUST NOT USE','results':[{'url':'https://example.org','title':'Congress','raw_content':TEXT,'content':'snippet'}]})
        self.assertEqual(req.url.host,'api.tavily.com');body=json.loads(req.content)
        self.assertFalse(body['include_answer']);self.assertEqual(body['max_results'],3)
        self.assertEqual(body['include_raw_content'],'text');self.assertEqual(rows[0]['text'],TEXT)

    def test_results_bounded_deduplicated_and_unsafe_urls_discarded(self):
        rows,req=self.run_search('tavily',{'results':[
            {'url':'http://127.0.0.1/private','content':TEXT},
            {'url':'javascript:alert(1)','content':TEXT},
            *[{'url':'https://example.org/'+str(i),'content':'a'*13000} for i in [1,1,2,3,4]]
        ]})
        self.assertEqual(len(rows),3);self.assertTrue(all(r['excerpt_only'] and r['truncated'] for r in rows))
        self.assertTrue(all(len(r['text'])==12000 for r in rows))
        for url in ['http://localhost','http://local.test:22','http://user:pw@example.org','file:///etc/passwd','http://[::1]','http://host.local']:
            self.assertFalse(safe_result_url(url),url)

    def test_empty_and_malformed_responses_and_secret_safe_errors(self):
        for status in (400,401,403,429,432,433,500,302):
            with self.subTest(status=status),self.assertRaises(ValueError) as caught:
                self.run_search('jina',{'error':'test-secret'},status)
            self.assertNotIn('test-secret',str(caught.exception))
        for body in ({'data':[]},{'data':None},[],{'results':[]}):
            with self.assertRaises(ValueError):self.run_search('jina',body)
        with self.assertRaises(ValueError):search_web('Congress',SearchConnection('tavily',''))

    def test_timeouts_and_oversized_response(self):
        def timeout(request):raise httpx.ReadTimeout('SECRET')
        with patch('app.search.httpx.Client',return_value=httpx.Client(transport=httpx.MockTransport(timeout))):
            with self.assertRaisesRegex(ValueError,'zaman aşımına'):search_web('Kongre',SearchConnection('jina','secret'))
        def oversized(request):return httpx.Response(200,content=b'x'*2_000_001)
        with patch('app.search.httpx.Client',return_value=httpx.Client(transport=httpx.MockTransport(oversized))):
            with self.assertRaisesRegex(ValueError,'çok büyük'):search_web('Kongre',SearchConnection('jina','secret'))

class ExtensionAPITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.provider=FixtureProvider();self.app=create_app(self.root/'db',settings_path=self.root/'.env',ai_provider=self.provider)
        self.client=TestClient(self.app).__enter__()
        self.client.post('/api/ai/settings',json={'api_key':'test-llm-secret','model':'fixture'})
    def tearDown(self):
        self.client.__exit__(None,None,None);self.temp.cleanup()
    def analyze(self,sources=None):
        return self.client.post('/api/ai/analyze',json={'sources':sources or [{'kind':'text','content':TEXT}],'transfer_consent':True})
    def test_search_settings_separate_keys_and_blank_preserves(self):
        for pid in ('jina','tavily'):
            r=self.client.post('/api/search/settings',json={'provider_id':pid,'api_key':'test-'+pid+'-secret'})
            self.assertEqual(r.status_code,200,r.text);self.assertNotIn('secret',r.text)
        self.client.post('/api/search/settings',json={'provider_id':'jina','api_key':''})
        settings=self.client.get('/api/search/settings').json()
        self.assertTrue(all(p['configured'] for p in settings['providers']))
        ai=self.app.state.ai
        self.assertEqual(ai.settings.search_credentials('jina').key,'test-jina-secret')
        self.assertEqual(ai.settings.credentials().key,'test-llm-secret')
        self.assertEqual(os.stat(self.root/'.env').st_mode&0o777,0o600)
        self.assertNotIn('test-jina-secret',self.client.get('/api/backup').text)
        self.assertEqual(self.client.post('/api/search/settings',json={'provider_id':'jina','api_key':'has space'}).status_code,422)
        self.assertEqual(self.client.post('/api/search/settings',json={'provider_id':'openai','api_key':'x'}).status_code,422)

    def test_search_key_missing_fails_before_llm(self):
        r=self.analyze([{'kind':'search','search_provider':'jina','content':'Kongre 2027'}])
        self.assertEqual(r.status_code,409);self.assertEqual(self.provider.calls,0)
        self.assertEqual(self.analyze([{'kind':'search','content':'Kongre 2027'}]).status_code,422)
        self.assertEqual(self.client.post('/api/search/test',json={}).status_code,422)

    def test_search_snapshot_evidence_and_ahp(self):
        self.client.post('/api/search/settings',json={'provider_id':'jina','api_key':'search-test'})
        rows=[{'label':'Program','text':TEXT,'url':'https://example.org/program','excerpt_only':False,'truncated':False,'published_date':'2027-01-01'}]
        with patch('app.ai_service.search_web',return_value=rows) as call:
            d=self.analyze([{'kind':'search','search_provider':'jina','content':'Test Kongresi 2027'}]).json()
        self.assertEqual(d['status'],'ready',d.get('error'));s=d['sources'][0]
        self.assertEqual(s['query'],'Test Kongresi 2027');self.assertEqual(s['search_provider'],'jina')
        self.assertEqual(s['segments'][0]['url'],'https://example.org/program')
        self.assertEqual(d['analysis']['raw_score'],10);self.assertAlmostEqual(d['analysis']['result']['total'],100)
        self.assertEqual(call.call_args.args[1].key,'search-test')
        with patch('app.main.search_web',return_value=rows):
            r=self.client.post('/api/search/test',json={'provider_id':'jina'})
        self.assertEqual(r.status_code,200);self.assertTrue(r.json()['ok']);self.assertNotIn(TEXT,r.text)

    def test_history_delete_restore_preserves_review_and_original_sources(self):
        d=self.analyze().json();aid=d['id'];base='/api/ai/analyses/'+aid
        body={'metadata':{'name':'TEST KONGRESI','edition':'2027','context':d['context']},'evaluator':'Test','decisions':{f'K{i}':{'action':'approve'} for i in range(1,11)}}
        self.assertEqual(self.client.post(base+'/review',json=body).status_code,200)
        before=self.client.get('/api/state').json()
        for _ in range(2):self.assertEqual(self.client.post(base+'/delete',json={}).status_code,200)
        self.assertEqual(self.client.get('/api/ai/analyses').json(),[])
        self.assertEqual(len(self.client.get('/api/ai/analyses?deleted=true').json()),1)
        deleted=self.client.get(base).json();self.assertTrue(deleted['deleted']);self.assertEqual(deleted['sources'],d['sources'])
        self.assertEqual(self.client.get('/api/state').json(),before)
        self.assertEqual(self.client.get(base+'/result').status_code,200)
        for _ in range(2):self.assertEqual(self.client.post(base+'/restore',json={}).status_code,200)
        self.assertEqual(len(self.client.get('/api/ai/analyses').json()),1)

    def test_clear_all_not_just_visible_100_and_protect_processing(self):
        d=self.analyze().json()
        with self.app.state.database.session(write=True) as session:
            template=session.get(AIAnalysis,d['id'])
            for n in range(105):session.add(AIAnalysis(id='bulk-'+str(n),model_id=template.model_id,status='failed',data=template.data,created_at=now()))
            session.add(AIAnalysis(id='running',model_id=template.model_id,status='processing',data=template.data,created_at=now()))
        self.assertEqual(len(self.client.get('/api/ai/analyses').json()),100)
        self.assertEqual(self.client.post('/api/ai/analyses/running/delete',json={}).status_code,409)
        r=self.client.post('/api/ai/analyses/clear',json={}).json()
        self.assertEqual(r,{'deleted':106,'processing':1})
        self.assertEqual([r['id'] for r in self.client.get('/api/ai/analyses').json()],['running'])
        self.assertEqual(self.client.post('/api/ai/analyses/clear',json={}).json()['deleted'],0)
        for action in ('delete','restore'):self.assertEqual(self.client.post('/api/ai/analyses/missing/'+action,json={}).status_code,404)

    def test_unreviewed_deleted_analysis_requires_restore(self):
        d=self.analyze().json();base='/api/ai/analyses/'+d['id']
        self.client.post(base+'/delete',json={})
        body={'metadata':{'name':'TEST','edition':'2027','context':d['context']},'evaluator':'Test','decisions':{f'K{i}':{'action':'approve'} for i in range(1,11)}}
        self.assertEqual(self.client.post(base+'/review',json=body).status_code,409)

    def test_v3_migration_preserves_every_old_row(self):
        self.analyze()
        with sqlite3.connect(self.root/'db') as c:
            tables=['models','congresses','evaluations','ai_analyses','ai_reviews','congress_deletions']
            before={t:c.execute('SELECT * FROM '+t).fetchall() for t in tables}
            c.execute('DROP TABLE ai_analysis_deletions');c.execute('PRAGMA user_version=3')
        with TestClient(create_app(self.root/'db',settings_path=self.root/'.env')) as client:
            self.assertEqual(client.get('/api/health').json()['schema_version'],SCHEMA_VERSION)
        with sqlite3.connect(self.root/'db') as c:
            self.assertEqual(before,{t:c.execute('SELECT * FROM '+t).fetchall() for t in tables})

    def test_image_only_extracted_text_sent_to_model(self):
        image={'mime':'image/png','data':'PRIVATE_IMAGE_BYTES','width':100,'height':100,'content_hash':'hash'}
        ocr={'text':TEXT,'engine':'test OCR','lines':[{'text':TEXT,'confidence':.9}]}
        with patch('app.image_ocr.extract_image',return_value=(ocr,image)):
            d=self.analyze([{'kind':'image','content':'test-image','label':'Test afişi'}]).json()
        self.assertEqual(d['status'],'ready');snapshot=copy.deepcopy(d['sources'])
        for compact in (False,True):
            wire=source_input(d['sources'],'',d['method'],compact=compact)
            self.assertNotIn('PRIVATE_IMAGE_BYTES',wire);self.assertNotIn('"ocr"',wire)
            self.assertIn(TEXT,wire)
        self.assertEqual(d['sources'],snapshot);self.assertEqual(d['analysis']['raw_score'],10)

    def test_invalid_images_fail_before_llm(self):
        for raw in (b'not image',b'%PDF-1.7',b''):
            r=self.analyze([{'kind':'image','content':base64.b64encode(raw).decode()}]).json()
            self.assertEqual(r['status'],'failed');self.assertIn('görsel',r['error'])
        self.assertEqual(self.provider.calls,0)
        with self.assertRaisesRegex(ValueError,'4 MB'):image_bytes(base64.b64encode(b'\x89PNG\r\n\x1a\n'+b'x'*4_000_000).decode())
        with self.assertRaises(ValueError):image_bytes('not base64')

@unittest.skipUnless(os.getenv('RUN_NATIVE_OCR_TEST')=='1','Native OCR requires macOS Vision access')
class NativeOCRTests(unittest.TestCase):
    def test_real_poster_and_corrupt_image(self):
        raw=Path('tests/fixtures/ocr-poster.png').read_bytes()
        data,image=extract_image(base64.b64encode(raw).decode())
        self.assertIn('TEST KONGRESI 2027',data['text']);self.assertIn('1000 TL',data['text'])
        self.assertEqual(image['mime'],'image/png');self.assertEqual(image['width'],1400)
        from PIL import Image
        from io import BytesIO
        for format,mime in [('JPEG','image/jpeg'),('WEBP','image/webp')]:
            out=BytesIO();Image.open(BytesIO(raw)).convert('RGB').save(out,format=format)
            text,archive=extract_image(base64.b64encode(out.getvalue()).decode())
            self.assertIn('TEST KONGRESI 2027',text['text']);self.assertEqual(archive['mime'],mime)
        too_large=BytesIO();Image.new('RGB',(6000,4000),'white').save(too_large,format='PNG')
        with self.assertRaisesRegex(ValueError,'20 megapiksel'):extract_image(base64.b64encode(too_large.getvalue()).decode())
        with self.assertRaises(ValueError):extract_image(base64.b64encode(b'\x89PNG\r\n\x1a\ncorrupt').decode())


class PDFTests(unittest.TestCase):
    setUp=ExtensionAPITests.setUp
    tearDown=ExtensionAPITests.tearDown
    analyze=ExtensionAPITests.analyze
    # Only PDF-specific cases; API tests run once in their own class.
    def test_pdf_download_preserves_turkish_and_scores(self):
        from io import BytesIO
        from pypdf import PdfReader
        d=self.analyze().json();base='/api/ai/analyses/'+d['id']
        r=self.client.get(base+'/pdf');self.assertEqual(r.status_code,200,r.text[:100] if r.status_code!=200 else '')
        self.assertTrue(r.content.startswith(b'%PDF'));self.assertIn('attachment',r.headers['content-disposition'])
        text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(r.content)).pages)
        for expected in ('Katılımcı Memnuniyeti','Ham puan: 10 / 10','AHP puanı: 100,00','Yüksek Uygunluk','Kaynak künyeleri'):
            self.assertIn(expected,text)
        body={'metadata':{'name':'Çığ Özgünlük Kongresi','edition':'2027','context':d['context']},'evaluator':'İnceleyen','decisions':{f'K{i}':{'action':'approve'} for i in range(1,11)}}
        body['decisions']['K1']={'action':'correct','value':False,'note':'İnceleme sonucunda değiştirildi.'}
        self.client.post(base+'/review',json=body)
        r=self.client.get(base+'/pdf');self.assertEqual(r.status_code,200)
        text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(r.content)).pages)
        self.assertIn('Ham puan: 9 / 10',text);self.assertIn('Çığ Özgünlük Kongresi',text)
        self.assertIn('Orta Uygunluk',text)
        self.assertIn('Kullanıcı kararı',text);self.assertIn('İnceleme sonucunda değiştirildi.',text)

    def test_pdf_rejects_failed_and_missing(self):
        d=self.analyze([{'kind':'image','content':'invalid'}]).json()
        self.assertEqual(self.client.get('/api/ai/analyses/'+d['id']+'/pdf').status_code,409)
        self.assertEqual(self.client.get('/api/ai/analyses/missing/pdf').status_code,404)

if __name__=='__main__':unittest.main()
