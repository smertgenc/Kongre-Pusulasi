import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bs4 import BeautifulSoup
import httpx
from fastapi.testclient import TestClient
from app.main import create_app
from app.ai_provider import GeminiProvider, ProviderError, gemini_response_schema
from app.services import ConflictError
from app.ai_method import DEFAULT_CONTEXT
from app.sources import related_links, fetch_site
from tests.test_ai import FixtureProvider, TEXT, output_fixture

class AHPFlowTests(unittest.TestCase):
    def test_gemini_compact_schema_preserves_types_and_full_local_validation(self):
        schema=gemini_response_schema()
        finding=schema['properties']['findings']['items']
        self.assertEqual(finding['properties']['value']['anyOf'],[{'type':'boolean'},{'type':'null'}])
        self.assertEqual(finding['properties']['criterion']['enum'],['K'+str(i) for i in range(1,11)])
        self.assertNotIn('$ref',json.dumps(schema))
        self.assertNotIn('maxItems',json.dumps(schema))
        # Decoding is simpler, but extra criteria/oversized fields are still rejected.
        wrong_count=output_fixture();wrong_count['findings'].pop()
        oversized=output_fixture();oversized['findings'][0]['explanation']='x'*2001
        for output in (wrong_count,oversized):
            response={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(output)}]}}]}
            with patch('app.ai_provider.time.sleep'),patch('httpx.Client.post',return_value=httpx.Response(200,json=response)):
                with self.assertRaises(ConflictError):GeminiProvider().analyze([],'','test-key','gemini-3.1-flash-lite')

    def test_source_only_request_uses_original_excel_model_and_sends_method(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider=FixtureProvider();app=create_app(Path(tmp)/'test.db',settings_path=Path(tmp)/'.env',ai_provider=provider)
            with TestClient(app) as client:
                client.post('/api/ai/settings',json={'api_key':'test-only','model':'test'})
                models=client.get('/api/state').json()['models'];original=min(models,key=lambda m:m['version'])
                newer=client.post('/api/models',json={'name':'Başka model','base_id':original['id'],'matrices':original['matrices'],'thresholds':{'average':60,'valid':80}})
                self.assertEqual(newer.status_code,201,newer.text)
                with patch.object(provider,'analyze',wraps=provider.analyze) as analyze:
                    result=client.post('/api/ai/analyze',json={'sources':[{'kind':'text','content':TEXT}],'transfer_consent':True})
                self.assertEqual(result.status_code,201,result.text);data=result.json()
                self.assertEqual(data['status'],'ready',data.get('error'))
                self.assertEqual(data['model']['id'],original['id']);self.assertEqual(data['context'],DEFAULT_CONTEXT)
                contract=analyze.call_args.kwargs['ahp_method']
                self.assertEqual(contract,data['method']);self.assertEqual(len(contract['criteria']),10)
                self.assertEqual({c['code']:c['global_weight'] for c in contract['criteria']},original['weights'])
                self.assertEqual(contract['thresholds'],original['thresholds'])
                self.assertAlmostEqual(data['analysis']['result']['total'],100)

    def test_gemini_real_error_regressions_have_safe_actionable_details(self):
        cases=[(400,{'message':'Invalid value at generation_config.response_format.text.mime_type: application/json'},'INVALID_REQUEST'),
               (404,{'message':'This model is no longer available to new users. PRIVATE-SECRET'},'MODEL_UNAVAILABLE'),
               (503,{'message':'This model is currently experiencing high demand. PRIVATE-SECRET'},'SERVICE_UNAVAILABLE')]
        for status,error,code in cases:
            with self.subTest(status=status),patch('app.ai_provider.time.sleep'),patch('httpx.Client.post',return_value=httpx.Response(status,json={'error':error})) as post:
                with self.assertRaises(ProviderError) as caught:GeminiProvider().analyze([],'','PRIVATE-SECRET','gemini-3.8-flash')
                self.assertEqual(caught.exception.details['http_status'],status)
                self.assertEqual(caught.exception.details['code'],code)
                self.assertNotIn('PRIVATE-SECRET',str(caught.exception));self.assertEqual(post.call_count,3 if status==503 else 1)

    def test_provider_error_details_are_saved_without_key_or_upstream_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=create_app(Path(tmp)/'test.db',settings_path=Path(tmp)/'.env')
            with TestClient(app) as client:
                client.post('/api/ai/settings',json={'provider_id':'gemini','api_key':'PRIVATE-SECRET','model':'gemini-3.8-flash'})
                with patch('app.ai_provider.time.sleep'),patch('httpx.Client.post',return_value=httpx.Response(503,json={'error':{'message':'PRIVATE-SECRET'}})):
                    r=client.request('POST','/api/ai/analyze',json={'provider_id':'gemini','sources':[{'kind':'text','content':TEXT}],'transfer_consent':True})
                d=r.json();self.assertEqual(d['status'],'failed');self.assertEqual(d['error_details']['code'],'SERVICE_UNAVAILABLE')
                self.assertTrue(d['error_details']['retryable']);self.assertEqual(d['sources'][0]['segments'][0]['text'],TEXT)
                self.assertNotIn('PRIVATE-SECRET',r.text)

class RelatedPageTests(unittest.TestCase):
    def test_links_stay_in_same_event_and_origin_and_are_bounded(self):
        html='''<a href="/tr/event/committee">Bilim kurulu</a><a href="/tr/event/program">Program</a>
        <a href="https://other.example/about">About</a><a href="/tr/other/about">Hakkında</a>
        <a href="#">Program</a><a href="/tr/event/file.pdf">Program PDF</a>
        <a href="http://localhost/about">About</a><a href="https://[invalid/about">About</a><a href="/tr/event/committee#again">Bilim</a>
        <a href="/tr/event/fees">Ücretler</a><a href="/tr/event/history">Geçmiş</a><a href="/tr/event/extra">Topics</a>'''
        links=related_links(BeautifulSoup(html,'html.parser'),'https://conf.example/tr/event')
        self.assertEqual([x['url'] for x in links],['https://conf.example/tr/event/'+p for p in ('committee','program','fees','history')])

    def test_empty_landing_page_follows_real_links_and_keeps_quote_locations(self):
        base='https://conf.example/event';about=base+'/about';committee=base+'/committee'
        pages=[('Başlık','Sadece başlık',base,[{'url':about,'label':'Hakkında'},{'url':committee,'label':'Bilim Kurulu'}]),
               ('Hakkında','Sempozyum 8 Mayıs tarihinde düzenlenir. '*4,about,[]),
               ('Bilim Kurulu','Bilim kurulunda akademisyenler yer almaktadır. '*4,committee,[])]
        with patch('app.sources.fetch_page',side_effect=pages) as fetch:
            title,segments,url,warnings=fetch_site(base)
        self.assertEqual(len(segments),2);self.assertEqual(segments[1]['url'],committee)
        self.assertEqual(segments[1]['id'],'2');self.assertTrue(warnings)
        self.assertEqual(fetch.call_args_list[1].kwargs['allowed_origin'],('https','conf.example'))

    def test_title_only_is_rejected_and_failed_child_does_not_discard_good_evidence(self):
        base='https://conf.example/event'
        with patch('app.sources.fetch_page',return_value=('Title','Title',base,[])):
            with self.assertRaisesRegex(ValueError,'AI isteği gönderilmedi'):fetch_site(base)
        with patch('app.sources.fetch_page',side_effect=[('Title','Valid congress text. '*10,base,[{'url':base+'/about','label':'About'}]),ValueError('Blocked')]):
            _,segments,_,warnings=fetch_site(base)
        self.assertEqual(len(segments),1);self.assertIn('Blocked',warnings[0])

if __name__=='__main__':unittest.main()
