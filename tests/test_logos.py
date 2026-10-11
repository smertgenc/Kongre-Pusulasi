import base64
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader
from app.main import create_app
from app.logo_service import raster_logo, logo_candidates, fetch_asset, logo_surface
from app.models import CongressLogo
from app.services import ConflictError
from tests.test_ai import FixtureProvider, TEXT


def png(size=(200, 100), color='#194acf'):
    stream = io.BytesIO(); Image.new('RGB', size, color).save(stream, format='PNG');return stream.getvalue()

class LogoUnitTests(unittest.TestCase):
    def test_white_transparent_logo_uses_dark_surface_without_recoloring(self):
        image=Image.new('RGBA',(80,40),(0,0,0,0));image.paste((255,255,255,255),(10,10,60,30))
        out=io.BytesIO();image.save(out,format='PNG')
        self.assertEqual(logo_surface(out.getvalue()),'dark')
        self.assertEqual(logo_surface(png(color='white')),'light')

    def test_decode_reencode_bounds_and_unsupported_active_files(self):
        normalized=raster_logo(png((1200, 300)))
        with Image.open(io.BytesIO(normalized)) as image:
            self.assertEqual(image.size,(512,128));self.assertEqual(image.format,'PNG');self.assertFalse(image.info)
        for bad in [b'<svg onload="alert(1)"></svg>',b'not a picture',png((2,2)),b'x'*3_000_001]:
            with self.assertRaises(ValueError):raster_logo(bad)

    def test_discovery_prefers_brand_over_sponsors_and_site_icon_over_photos(self):
        html='''<header><a class="brand"><img src="/event-logo.png" alt="Congress"></a></header>
        <img src="/ieee_logo.png"><meta property="og:image" content="/random-photo.jpg">
        <link rel="icon" href="/favicon.ico"><img src="/sponsors/logo.png">'''
        candidates=logo_candidates(html,'https://conference.example/2027/')
        self.assertEqual(candidates,[('https://conference.example/event-logo.png','website'),('https://conference.example/favicon.ico','site_icon')])
        self.assertEqual(logo_candidates('<img src="/poster.png">','https://conference.example'),[])

    def test_redirect_revalidates_target_instead_of_accessing_private_network(self):
        class Response:
            status=302
            def getheader(self,key,default=None):return 'http://127.0.0.1/private' if key=='Location' else default
        class Connection:
            def __init__(self,*args):pass
            def request(self,*args,**kwargs):pass
            def getresponse(self):return Response()
            def close(self):pass
        from urllib.parse import urlsplit
        with patch('app.logo_service.public_target',side_effect=[(urlsplit('https://conference.example'),'conference.example','8.8.8.8'),ValueError('blocked private address')]) as validate,patch('app.logo_service.PinnedConnection',Connection):
            with self.assertRaisesRegex(ValueError,'blocked'):fetch_asset('https://conference.example')
            self.assertEqual(validate.call_args.args[0],'http://127.0.0.1/private')

class LogoAPITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.app=create_app(self.root/'test.db',settings_path=self.root/'.env',ai_provider=FixtureProvider())
        self.client=TestClient(self.app).__enter__();self.mid=self.client.get('/api/state').json()['models'][0]['id']
        self.payload={'model_id':self.mid,'metadata':{'name':'Logo Test Congress','edition':'2027','context':'same','website':'https://conference.example/2027'},
                      'evaluator':'Test','scale':1,'scores':{f'K{i}':1 for i in range(1,11)},'notes':{f'K{i}':'Test evidence' for i in range(1,11)}}
        self.saved=self.client.post('/api/evaluations',json=self.payload).json();self.cid=self.saved['id'];self.url='/api/congresses/'+self.cid+'/logo'

    def tearDown(self):
        self.client.__exit__(None,None,None);self.temp.cleanup()

    def upload(self,raw=None):return self.client.post(self.url+'/upload',json={'content':base64.b64encode(raw or png()).decode()})

    def test_upload_is_local_and_does_not_change_evaluations_and_works_in_backup(self):
        before=self.client.get('/api/state').json()['congresses'];response=self.upload();self.assertEqual(response.status_code,200,response.text)
        logo=response.json()['logo'];self.assertEqual(logo['source'],'upload');self.assertTrue(logo['url'].startswith(self.url))
        image=self.client.get(logo['url']);self.assertEqual(image.status_code,200);self.assertEqual(image.headers['content-type'],'image/png')
        state=self.client.get('/api/state').json();self.assertEqual(state['congresses'],before);self.assertNotIn('content',state['logos'][self.cid]);self.assertEqual(state['logos'][self.cid],logo)
        with sqlite3.connect(self.root/'restored.db') as db:
            db.executescript(self.client.get('/api/backup').text)
            self.assertEqual(db.execute('select image from congress_logos where congress_id=?',(self.cid,)).fetchone()[0],image.content)
            self.assertEqual(db.execute('pragma foreign_key_check').fetchall(),[])

    def test_hide_restore_trash_and_edit_preserve_logo(self):
        original=self.upload().json()['logo'];self.client.post(self.url+'/hide',json={})
        self.assertEqual(self.client.get(self.url).status_code,404)
        with patch('app.logo_service.discover_logo') as discovery:
            self.assertEqual(self.client.post(self.url+'/discover',json={}).json()['logo']['status'],'hidden');discovery.assert_not_called()
        restored=self.client.post(self.url+'/restore',json={}).json()['logo'];self.assertEqual(original['url'],restored['url'])
        self.client.post('/api/congresses/'+self.cid+'/delete',json={'previous_id':self.saved['evaluation_id']})
        self.assertEqual(self.upload().status_code,409);self.assertEqual(self.client.get(self.url).status_code,200)
        self.client.post('/api/congresses/'+self.cid+'/restore',json={})
        p={**self.payload,'congress_id':self.cid,'previous_id':self.saved['evaluation_id']};self.assertEqual(self.client.post('/api/evaluations',json=p).status_code,201)
        self.assertEqual(self.client.get('/api/state').json()['logos'][self.cid]['url'],original['url'])

    def test_failed_discovery_is_cached_and_does_not_erase_existing_upload(self):
        with patch('app.logo_service.discover_logo',side_effect=ValueError('Site unavailable')) as discovery:
            first=self.client.post(self.url+'/discover',json={}).json();self.assertEqual(first['logo']['status'],'missing')
            self.client.post(self.url+'/discover',json={});self.assertEqual(discovery.call_count,1)
            uploaded=self.upload().json()['logo'];self.client.post(self.url+'/discover',json={});self.assertEqual(discovery.call_count,1)
            failed=self.client.post(self.url+'/discover',json={'force':True}).json();self.assertEqual(failed['logo']['url'],uploaded['url']);self.assertIn('unavailable',failed['message'])

    def test_discovered_logo_and_concurrent_upload_precedence(self):
        with patch('app.logo_service.discover_logo',return_value=(raster_logo(png()),'https://conference.example/brand.png','website')):
            response=self.client.post(self.url+'/discover',json={});self.assertEqual(response.json()['logo']['source'],'website')
        def retrieve(website):
            self.app.state.logos.upload(self.cid,base64.b64encode(png(color='red')).decode())
            return raster_logo(png()),'https://conference.example/brand.png','website'
        with patch('app.logo_service.discover_logo',side_effect=retrieve):
            self.assertEqual(self.client.post(self.url+'/discover',json={'force':True}).status_code,409)
        self.assertEqual(self.client.get('/api/state').json()['logos'][self.cid]['source'],'upload')

    def test_invalid_files_and_local_origin_boundary(self):
        for content in ['not-base64',base64.b64encode(b'<svg><script>alert(1)</script></svg>').decode()]:
            self.assertEqual(self.client.post(self.url+'/upload',json={'content':content}).status_code,422)
        self.assertEqual(self.client.post(self.url+'/upload',headers={'Origin':'https://evil.example'},json={'content':'abc'}).status_code,403)
        self.assertEqual(self.client.post(self.url+'/upload',json={'content':'x'*4_100_000}).status_code,413)
        self.assertEqual(self.client.get('/api/state').json()['logos'],{})
        self.assertEqual(self.client.get('/logos.js').status_code,200)

    def test_unsaved_report_can_reuse_only_an_exact_event_website_logo(self):
        self.upload()
        report={'analysis':{'metadata':{}},'sources':[{'kind':'url','url':'https://conference.example/2027/'}]}
        self.assertEqual(self.app.state.logos.report_image(report),self.client.get(self.url).content)
        report['sources'][0]['url']='https://conference.example/other-event'
        self.assertIsNone(self.app.state.logos.report_image(report))
        report['review']={'saved':{'id':self.cid}};self.client.post(self.url+'/hide',json={})
        self.assertIsNone(self.app.state.logos.report_image(report))

    def test_reviewed_ai_history_and_pdf_share_logo_without_new_provider_call(self):
        self.client.post('/api/ai/settings',json={'api_key':'sk-test-not-transmitted','model':'gpt-5-mini'})
        report=self.client.post('/api/ai/analyze',json={'model_id':self.mid,'sources':[{'kind':'text','content':TEXT}],'transfer_consent':True}).json()
        body={'metadata':{'name':'Reviewed Congress','edition':'2027','context':report['context']},'evaluator':'Test','decisions':{f'K{i}':{'action':'approve'} for i in range(1,11)}}
        saved=self.client.post('/api/ai/analyses/'+report['id']+'/review',json=body).json()
        self.client.post('/api/congresses/'+saved['id']+'/logo/upload',json={'content':base64.b64encode(png()).decode()})
        history=self.client.get('/api/ai/analyses').json();self.assertEqual(history[0]['congress_id'],saved['id'])
        response=self.client.get('/api/ai/analyses/'+report['id']+'/pdf');self.assertEqual(response.status_code,200,response.text[:100] if response.status_code!=200 else '')
        reader=PdfReader(io.BytesIO(response.content));self.assertTrue(reader.pages[0]['/Resources'].get('/XObject'))
        self.assertEqual(self.app.state.ai.provider.calls,1)

    def test_schema6_upgrade_adds_logo_table_without_modifying_old_rows(self):
        self.client.__exit__(None,None,None)
        with sqlite3.connect(self.root/'test.db') as db:
            db.execute('drop table congress_logos');db.execute('pragma user_version=6')
            names=[r[0] for r in db.execute("select name from sqlite_master where type='table'")]
            before={name:db.execute('select * from '+name+' order by 1').fetchall() for name in names}
        self.app=create_app(self.root/'test.db',settings_path=self.root/'.env');self.client=TestClient(self.app).__enter__()
        with sqlite3.connect(self.root/'test.db') as db:
            self.assertEqual(before,{name:db.execute('select * from '+name+' order by 1').fetchall() for name in names})
            self.assertEqual(db.execute('pragma user_version').fetchone()[0],7)
        self.assertEqual(self.client.get('/api/state').json()['logos'],{})
