import base64
import copy
import io
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from app.main import create_app
from app.ai_schemas import ProviderOutput, SourceInput
from app.ai_provider import OpenAIProvider
from app.provider_catalog import AIConnection
from app.services import ConflictError
from app.sources import extract_sources, public_target, fetch_page

TEXT='TEST KONGRESI 2027. Program ve bilim kurulu yayimlandi. Iki ulkeden katilim dogrulandi. TEST KONGRESI 2027 proceedings indexed in Conference Proceedings Citation Index (CPCI).'

def output_fixture():
    evidence={'source_id':'S1','segment_id':'1','quote':'Program ve bilim kurulu yayimlandi.'}
    return {'facts':[{'field':'name','value':'TEST KONGRESI','evidence':[evidence]},
                     {'field':'edition','value':'2027','evidence':[{'source_id':'S1','segment_id':'1','quote':'TEST KONGRESI 2027.'}]}],
            'findings':[{'criterion':f'K{i}','value':True,'status':'detected','confidence':.9,
                         'explanation':'Otomatik test sağlayıcısının sabit çıktısı; gerçek AI sonucu değildir.',
                         'evidence':[{'source_id':'S1','segment_id':'1','quote':'TEST KONGRESI 2027 proceedings indexed in Conference Proceedings Citation Index (CPCI).'} if i==1 else evidence]} for i in range(1,11)]}

class FixtureProvider:
    def __init__(self): self.output=output_fixture(); self.calls=0
    def analyze(self,*args,**kwargs):
        self.calls+=1
        return ProviderOutput.model_validate(self.output)

class AITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.provider=FixtureProvider()
        self.app=create_app(self.root/'test.db',settings_path=self.root/'.env',ai_provider=self.provider)
        self.client=TestClient(self.app).__enter__()
        self.mid=self.client.get('/api/state').json()['models'][0]['id']
        self.client.post('/api/ai/settings',json={'api_key':'sk-test-never-transmitted','model':'gpt-5-mini'})

    def tearDown(self):
        self.client.__exit__(None,None,None); self.temp.cleanup()

    def analyze(self):
        r=self.client.post('/api/ai/analyze',json={'model_id':self.mid,'context':'Test profili',
            'sources':[{'kind':'text','content':TEXT}],'transfer_consent':True})
        self.assertEqual(r.status_code,201,r.text)
        return r.json()

    def review_body(self):
        return {'metadata':{'name':'TEST KONGRESI','edition':'2027','context':'Test profili'},
                'evaluator':'Test inceleyen','decisions':{f'K{i}':{'action':'approve'} for i in range(1,11)}}

    def test_ahp_score_review_history_and_snapshot(self):
        d=self.analyze(); self.assertEqual(d['status'],'ready')
        self.assertAlmostEqual(d['analysis']['result']['total'],100)
        self.assertEqual(d['analysis']['completeness'],1)
        self.assertAlmostEqual(d['analysis']['confidence'],.9)
        self.assertEqual(d['sources'][0]['segments'][0]['text'],TEXT)
        self.assertEqual(len(d['sources'][0]['content_hash']),64)
        body=self.review_body();body['decisions']['K1']={'action':'correct','value':False,'note':'Kontrol sonucu karşılamıyor.'}
        r=self.client.post('/api/ai/analyses/'+d['id']+'/review',json=body)
        self.assertEqual(r.status_code,200,r.text)
        self.assertAlmostEqual(r.json()['result']['total'],100-100*d['model']['weights']['K1'])
        reviewed=self.client.get('/api/ai/analyses/'+d['id']).json()
        audit=reviewed['review']['decisions']['K1']
        self.assertTrue(audit['ai_value']);self.assertFalse(audit['user_value']);self.assertFalse(audit['final_value'])
        self.assertTrue(reviewed['raw_output']['findings'][0]['value'])
        self.assertEqual(self.client.post('/api/ai/analyses/'+d['id']+'/review',json=body).json(),r.json())
        congresses=self.client.get('/api/state').json()['congresses']
        self.assertEqual(len(congresses),5)
        e=next(c for c in congresses if c['id']==r.json()['id'])['evaluations'][0]
        self.assertEqual(e['analysis_id'],d['id']);self.assertEqual(e['mode'],'ai_reviewed')
        self.assertEqual(len(self.client.get('/api/ai/analyses').json()),1)
        self.assertNotIn('sk-test',self.client.get('/api/backup').text)

    def test_missing_false_conflict_and_fabricated_quote(self):
        fs=self.provider.output['findings']
        fs[4].update(value=False)
        fs[1].update(value=None,status='not_found',confidence=0,evidence=[])
        fs[2]['evidence']=[{'source_id':'S1','segment_id':'1','quote':'Bu alinti kaynakta yoktur.'}]
        fs[3].update(status='conflict',value=True)
        d=self.analyze();a=d['analysis'];self.assertEqual(a['utilities']['K5'],0)
        for k in ('K2','K3','K4'):self.assertEqual(a['utilities'][k],0)
        self.assertIsNotNone(a['result']['total']);self.assertEqual(a['completeness'],.7)
        self.assertIn('UNVERIFIED_EVIDENCE',a['findings'][2]['flags'])
        self.assertIn('puana katılmadı',a['findings'][2]['explanation'])
        self.assertTrue(any(w.startswith('K3:') for w in a['warnings']))
        self.assertIn('SOURCE_CONFLICT',a['findings'][3]['flags'])
        body=self.review_body()
        for k in ('K2','K3','K4'):body['decisions'][k]={'action':'unknown'}
        result=self.client.post('/api/ai/analyses/'+d['id']+'/review',json=body)
        self.assertEqual(result.status_code,200,result.text);self.assertIsNone(result.json()['result']['total'])

    def test_metadata_conflicts_preserved(self):
        ev=self.provider.output['facts'][0]['evidence']
        self.provider.output['facts'] += [{'field':'start_date','value':'2027-05-12','evidence':ev},
                                         {'field':'start_date','value':'2027-05-10','evidence':ev}]
        a=self.analyze()['analysis']
        self.assertNotIn('start_date',a['metadata']);self.assertEqual(len(a['conflicts']),1)

    def test_settings_secret_and_required_key(self):
        s=self.client.get('/api/ai/settings');self.assertNotIn('sk-test',s.text)
        self.assertTrue(s.json()['configured']);self.assertEqual((self.root/'.env').stat().st_mode&0o777,0o600)
        self.client.post('/api/ai/settings',json={'api_key':'','model':'gpt-5-mini'})
        self.assertTrue(self.client.get('/api/ai/settings').json()['configured'])
        self.app.state.ai.settings.analysis_connections=lambda:('openai',{'openai':AIConnection('openai','','gpt-5-mini')})
        r=self.client.post('/api/ai/analyze',json={'model_id':self.mid,'context':'Test','sources':[{'kind':'text','content':TEXT}],'transfer_consent':True})
        self.assertEqual(r.status_code,409);self.assertEqual(self.provider.calls,0)

    def test_failed_source_not_sent_and_consent_required(self):
        body={'model_id':self.mid,'context':'Test','sources':[{'kind':'text','content':'a'}],'transfer_consent':True}
        result=self.client.post('/api/ai/analyze',json=body).json()
        self.assertEqual(result['status'],'failed');self.assertEqual(self.provider.calls,0)
        body['transfer_consent']=False
        self.assertEqual(self.client.post('/api/ai/analyze',json=body).status_code,422)

    def test_invalid_provider_output_and_review_rollback(self):
        self.provider.output['findings'][0]['criterion']='K2'
        self.assertEqual(self.analyze()['status'],'failed')
        self.provider.output=output_fixture();d=self.analyze();b=self.review_body()
        b['decisions']['K1']={'action':'correct','value':False}
        self.assertEqual(self.client.post('/api/ai/analyses/'+d['id']+'/review',json=b).status_code,422)
        self.assertEqual(len(self.client.get('/api/state').json()['congresses']),4)

class ExtractorTests(unittest.TestCase):
    def test_ssrf_all_addresses_checked(self):
        private=(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))
        public=(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443))
        for records in ([private],[public,private]):
            with patch('app.sources.socket.getaddrinfo',return_value=records):
                with self.assertRaises(ValueError):public_target('https://conference.test')
        for url in ('file:///etc/passwd','https://user:pass@host','http://host:1234'):
            with self.assertRaises(ValueError):public_target(url)

    def test_redirect_revalidated(self):
        class Response:
            status=302
            def getheader(self,key): return 'http://127.0.0.1/'
        class Connection:
            def __init__(self,*args):pass
            def request(self,*args,**kwargs):pass
            def getresponse(self):return Response()
            def close(self):pass
        from urllib.parse import urlsplit
        with patch('app.sources.public_target',side_effect=[(urlsplit('https://example.org'),'example.org','8.8.8.8'),ValueError('blocked')]) as target,patch('app.sources.PinnedConnection',Connection):
            with self.assertRaises(ValueError):fetch_page('https://example.org')
            self.assertEqual(target.call_args.args[0],'http://127.0.0.1/')

    def test_pdf_text_pages_and_invalid_file(self):
        writer=PdfWriter();page=writer.add_blank_page(400,400)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
        stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 20 100 Td (Test Congress program and scientific committee.) Tj ET')
        page[NameObject('/Contents')]=writer._add_object(stream)
        out=io.BytesIO();writer.write(out)
        sources=extract_sources([SourceInput(kind='pdf',content=base64.b64encode(out.getvalue()).decode(),label='test.pdf')])
        self.assertIn('Test Congress',sources[0]['segments'][0]['text']);self.assertEqual(sources[0]['segments'][0]['page'],1)
        with self.assertRaises(ValueError):extract_sources([SourceInput(kind='pdf',content=base64.b64encode(b'not pdf').decode())])

class ProviderTests(unittest.TestCase):
    def test_structured_request_and_failure_modes(self):
        response={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(output_fixture())}]}]}
        with patch('httpx.Client.post',return_value=httpx.Response(200,json=response)) as post:
            out=OpenAIProvider().analyze([], 'Profile','fake-key','gpt-5-mini')
            self.assertEqual(len(out.findings),10)
            body=post.call_args.kwargs['json'];self.assertFalse(body['store']);self.assertTrue(body['text']['format']['strict'])
        for status,data in [(401,{}),(429,{}),(200,{'status':'incomplete'}),(200,{'status':'completed','output':[]})]:
            with patch('httpx.Client.post',return_value=httpx.Response(status,json=data)):
                with self.assertRaises(ConflictError):OpenAIProvider().analyze([], 'Profile','fake-key','gpt-5-mini')

if __name__=='__main__':unittest.main()
