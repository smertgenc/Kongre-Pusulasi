"""Provider contracts use mocked HTTP only; never transmit credentials or test data."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from app.main import create_app
from app.ai_settings import AISettings
from app.ai_schemas import SettingsInput
from app.ai_provider import get_provider, ProviderError, source_input, analysis_instructions
from app.ai_method import method_snapshot
from engine import calculate_model, DEFAULT_MATRICES
from app.provider_catalog import PROVIDERS
from app.services import ConflictError
from tests.test_ai import output_fixture, TEXT

def response_for(pid):
    raw = json.dumps(output_fixture())
    if pid == 'openai':
        return {'status':'completed','output':[{'content':[{'type':'output_text','text':raw}]}]}
    if pid == 'gemini':
        return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'internal thought','thought':True},{'text':raw}]}}]}
    return {'choices':[{'finish_reason':'stop','message':{'content':raw}}]}

class ProviderContractTests(unittest.TestCase):
    def setUp(self):
        sleep=patch("app.ai_provider.time.sleep");sleep.start();self.addCleanup(sleep.stop)

    def test_groq_compact_request_keeps_all_evidence_and_method(self):
        method=method_snapshot({'id':'test-model','version':1,'name':'Excel',**calculate_model(DEFAULT_MATRICES)})
        sources=[{'id':'S1','kind':'url','label':'Congress','url':'https://example.org',
                  'content_hash':'h'*64,'retrieved_at':'2026-09-29T00:00:00','warnings':[],
                  'segments':[{'id':'1','page':None,'text':TEXT},{'id':'2','page':None,'text':'İkinci sayfadaki kanıtlar aynen korunur.'}]}]
        with patch('httpx.Client.post',return_value=httpx.Response(200,json=response_for('groq'))) as post:
            get_provider('groq').analyze(sources,'','private-key','openai/gpt-oss-20b',ahp_method=method)
        body=post.call_args.kwargs['json'];system,user=body['messages'];content=json.loads(user['content'])
        self.assertEqual(content['ahp_method'],method)
        self.assertEqual([p['text'] for p in content['sources'][0]['segments']],[p['text'] for p in sources[0]['segments']])
        for passage in content['sources'][0]['segments']:
            self.assertEqual(passage['source_id'],'S1');self.assertEqual(passage['segment_id'],passage['id'])
        self.assertNotIn('source_id',sources[0]['segments'][0])
        self.assertEqual(content['sources'][0]['id'],'S1')
        self.assertNotIn('content_hash',content['sources'][0]);self.assertNotIn('retrieved_at',content['sources'][0])
        self.assertIn('content_hash',sources[0])  # Saved source snapshot must not be mutated.
        self.assertTrue(body['response_format']['json_schema']['strict'])
        old_size=len(analysis_instructions())+len(source_input(sources,'',method))
        self.assertLess(len(system['content'])+len(user['content']),old_size-1000)
        with patch('httpx.Client.post',return_value=httpx.Response(200,json=response_for('groq'))) as post:
            get_provider('groq').analyze(sources,'','private-key','openai/gpt-oss-20b')
        self.assertIn('Kriter tanımları:',post.call_args.kwargs['json']['messages'][0]['content'])

    def test_groq_size_and_generation_errors_are_actionable_without_leaking_payloads(self):
        cases=[(413,'rate_limit_exceeded','Request too large: org_PRIVATE secret-key','REQUEST_TOO_LARGE',False),
               (400,'context_length_exceeded','secret-key','REQUEST_TOO_LARGE',False),
               (400,'json_validate_failed','Failed to generate JSON. secret-key','OUTPUT_SCHEMA_ERROR',True),
               (400,'invalid_request_error','Generated JSON does not match the expected schema. secret-key','OUTPUT_SCHEMA_ERROR',True)]
        for status,code,message,expected,retryable in cases:
            response=httpx.Response(status,json={'error':{'code':code,'message':message,'failed_generation':'private-source'}})
            with self.subTest(status=status,code=code),patch('httpx.Client.post',return_value=response) as post:
                with self.assertRaises(ProviderError) as caught:
                    get_provider('groq').analyze([],'','secret-key','openai/gpt-oss-20b')
                self.assertEqual(caught.exception.details,{'code':expected,'http_status':status,'retryable':retryable})
                public=str(caught.exception)+json.dumps(caught.exception.details)
                for private in ('secret-key','org_PRIVATE','private-source'):self.assertNotIn(private,public)
                self.assertEqual(post.call_count,1)

    def test_destinations_auth_and_schema(self):
        for pid, spec in PROVIDERS.items():
            with self.subTest(provider=pid), patch('httpx.Client.post',return_value=httpx.Response(200,json=response_for(pid))) as post:
                out = get_provider(pid).analyze([{'id':'S1','segments':[{'id':'1','text':TEXT}]}], 'Test profili', 'test-only-key', spec.default_model)
                self.assertEqual(len(out.findings),10)
                url=post.call_args.args[0]; body=post.call_args.kwargs['json']; headers=post.call_args.kwargs['headers']
                self.assertNotIn('test-only-key',url+json.dumps(body))
                if pid == 'gemini':
                    self.assertEqual(url,spec.endpoint+spec.default_model+':generateContent')
                    self.assertEqual(headers,{'x-goog-api-key':'test-only-key'})
                    self.assertNotIn('responseFormat',body['generationConfig'])
                    self.assertEqual(body['generationConfig']['responseMimeType'],'application/json')
                    schema=body['generationConfig']['responseJsonSchema']
                    self.assertIn(TEXT,body['contents'][0]['parts'][0]['text'])
                else:
                    self.assertEqual(url,spec.endpoint)
                    self.assertEqual(headers,{'Authorization':'Bearer test-only-key'})
                    self.assertEqual(body['model'],spec.default_model)
                    fmt=body['text']['format'] if pid=='openai' else body['response_format']['json_schema']
                    self.assertTrue(fmt['strict']);schema=fmt['schema']
                    if pid=='openrouter':self.assertTrue(body['provider']['require_parameters'])
                self.assertEqual(set(schema['required']),{'facts','findings'})
                self.assertFalse(schema['additionalProperties'])
                self.assertEqual(post.call_count,1)

    def test_provider_errors_are_named_and_do_not_echo_secrets(self):
        for pid,spec in PROVIDERS.items():
            for status in (302,400,401,403,429,500):
                with self.subTest(provider=pid,status=status),patch('httpx.Client.post',return_value=httpx.Response(status,json={'error':'PRIVATE-KEY'})) as post:
                    with self.assertRaises(ConflictError) as error:
                        get_provider(pid).analyze([],'test','PRIVATE-KEY',spec.default_model)
                    self.assertIn(spec.name,str(error.exception))
                    self.assertNotIn('PRIVATE-KEY',str(error.exception))
                    self.assertEqual(post.call_count,3 if status==500 else 1)

    def test_partial_refused_and_malformed_responses_never_score(self):
        for pid,spec in PROVIDERS.items():
            truncated=response_for(pid);refused=response_for(pid)
            if pid=='openai':
                truncated['status']='incomplete'
                refused['output'][0]['content']=[{'type':'refusal'}]
            elif pid=='gemini':
                truncated['candidates'][0]['finishReason']='MAX_TOKENS'
                refused={'promptFeedback':{'blockReason':'SAFETY'}}
            else:
                truncated['choices'][0]['finish_reason']='length'
                refused['choices'][0]['message']['refusal']='not available'
            for data in (truncated,refused,{},None,{'choices':[]},['wrong shape']):
                with self.subTest(provider=pid,data=data),patch('httpx.Client.post',return_value=httpx.Response(200,json=data)):
                    with self.assertRaises(ConflictError):get_provider(pid).analyze([],'test','test-key',spec.default_model)

    def test_read_timeout_is_not_retried_but_connect_failure_is(self):
        for error in (httpx.ReadTimeout('PRIVATE-KEY'),httpx.ConnectError('PRIVATE-KEY')):
            with patch('httpx.Client.post',side_effect=error) as post:
                with self.assertRaises(ConflictError) as caught:get_provider('gemini').analyze([],'test','PRIVATE-KEY','gemini-2.5-flash')
                self.assertNotIn('PRIVATE-KEY',str(caught.exception));self.assertEqual(post.call_count,1 if isinstance(error,httpx.ReadTimeout) else 3)

    def test_gemini_model_cannot_change_destination(self):
        with patch('httpx.Client.post',return_value=httpx.Response(200,json=response_for('gemini'))) as post:
            get_provider('gemini').analyze([],'test','key','models/gemini-2.5-flash')
            self.assertEqual(post.call_args.args[0],PROVIDERS['gemini'].endpoint+'gemini-2.5-flash:generateContent')
            get_provider('gemini').analyze([],'test','key','https://attacker.example/path')
            self.assertEqual(post.call_args.args[0],PROVIDERS['gemini'].endpoint+'https%3A%2F%2Fattacker.example%2Fpath:generateContent')

class MultiProviderSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.app=create_app(self.root/'test.db',settings_path=self.root/'.env')
        self.client=TestClient(self.app).__enter__()
        self.mid=self.client.get('/api/state').json()['models'][0]['id']

    def tearDown(self):
        self.client.__exit__(None,None,None);self.temp.cleanup()

    def save(self,pid,key='',model=None):
        return self.client.post('/api/ai/settings',json={'provider_id':pid,'api_key':key,'model':model or PROVIDERS[pid].default_model})

    def body(self,pid='openai',model=None):
        return {'model_id':self.mid,'provider_id':pid,'provider_model':model or PROVIDERS[pid].default_model,
                'context':'Test profili','sources':[{'kind':'text','content':TEXT}],'transfer_consent':True}

    def test_keys_models_and_active_provider_survive_restart_separately(self):
        for pid in PROVIDERS:
            r=self.save(pid,'PRIVATE-'+pid,PROVIDERS[pid].default_model+':test')
            self.assertEqual(r.status_code,200,r.text)
            self.assertNotIn('PRIVATE-',r.text)
        for pid in PROVIDERS:
            self.save(pid,model=PROVIDERS[pid].default_model+':test')
            restarted=AISettings(self.root/'.env');c=restarted.credentials()
            self.assertEqual(c.provider_id,pid);self.assertEqual(c.key,'PRIVATE-'+pid)
            self.assertEqual(c.model,PROVIDERS[pid].default_model+':test')
            self.assertNotIn('PRIVATE-',repr(c));self.assertNotIn('PRIVATE-',json.dumps(restarted.public()))
        self.assertEqual((self.root/'.env').stat().st_mode&0o777,0o600)
        self.assertNotIn('PRIVATE-',self.client.get('/api/backup').text)

    def test_existing_openai_env_stays_compatible(self):
        (self.root/'.env').write_text('OPENAI_API_KEY=old-private-key\nOPENAI_MODEL=old-model\nKONGRE_PORT=8765\n')
        self.assertEqual(self.app.state.ai.settings.credentials().provider_id,'openai')
        self.save('gemini','google-test-key')
        self.assertIn('KONGRE_PORT=8765',(self.root/'.env').read_text())
        self.save('openai',model='old-model')
        self.assertEqual(self.app.state.ai.settings.credentials().key,'old-private-key')

    def test_unconfigured_provider_never_borrows_another_key(self):
        self.save('openai','PRIVATE-openai')
        r=self.save('gemini');self.assertFalse(r.json()['configured'])
        with patch('httpx.Client.post') as post:
            self.assertEqual(self.client.request('POST','/api/ai/analyze',json=self.body('gemini')).status_code,409)
            post.assert_not_called()
        self.assertEqual(self.app.state.ai.settings.credentials().key,'')
        self.assertEqual(self.client.get('/api/ai/analyses').json(),[])

    def test_analysis_routes_to_selected_provider_and_keeps_snapshot(self):
        for pid in PROVIDERS:
            self.save(pid,'PRIVATE-'+pid)
            with patch('httpx.Client.post',return_value=httpx.Response(200,json=response_for(pid))) as post:
                r=self.client.request('POST','/api/ai/analyze',json=self.body(pid))
            self.assertEqual(r.status_code,201,r.text);d=r.json();self.assertEqual(d['status'],'ready',d.get('error'))
            self.assertEqual(d['provider_id'],pid);self.assertEqual(d['provider_name'],PROVIDERS[pid].name)
            self.assertAlmostEqual(d['analysis']['result']['total'],100)
            self.assertNotIn('PRIVATE-',r.text)
            header='x-goog-api-key' if pid=='gemini' else 'Authorization'
            self.assertIn('PRIVATE-'+pid,post.call_args.kwargs['headers'][header])
        self.save('openai',model='another-model')
        self.assertEqual(self.client.get('/api/ai/analyses/'+d['id']).json()['provider_id'],'aimlapi')
        self.assertEqual(len(self.client.get('/api/state').json()['congresses']),4)
        self.assertNotIn('PRIVATE-',self.client.get('/api/backup').text)

    def test_stale_consent_rejected_before_extraction(self):
        self.save('groq','groq-test-key')
        legacy=self.body();legacy.pop('provider_id');legacy.pop('provider_model')
        for body in (legacy,self.body('openai'),self.body('groq','old-model')):
            with patch('app.ai_service.extract_sources') as extract,patch('httpx.Client.post') as post:
                r=self.client.request('POST','/api/ai/analyze',json=body)
                self.assertEqual(r.status_code,409);extract.assert_not_called();post.assert_not_called()
        self.assertEqual(self.client.get('/api/ai/analyses').json(),[])

    def test_settings_change_during_request_keeps_original_recipient(self):
        self.save('gemini','PRIVATE-gemini')
        def respond(*args,**kwargs):
            self.app.state.ai.settings.save(SettingsInput(provider_id='groq',api_key='PRIVATE-groq',model=PROVIDERS['groq'].default_model))
            return httpx.Response(200,json=response_for('gemini'))
        with patch('httpx.Client.post',side_effect=respond) as post:
            d=self.client.request('POST','/api/ai/analyze',json=self.body('gemini')).json()
            self.assertEqual(post.call_count,1)
        self.assertEqual(d['status'],'ready');self.assertEqual(d['provider_id'],'gemini')
        self.assertEqual(d['provider_model'],PROVIDERS['gemini'].default_model)
        self.assertEqual(self.client.get('/api/ai/settings').json()['provider_id'],'groq')

    def test_bad_settings_fail_without_overwriting_saved_connection(self):
        self.save('gemini','VALID-test-key')
        for body in ({'provider_id':'unknown','model':'x'}, {'provider_id':'groq','model':'x','api_key':'bad key'},
                     {'provider_id':'groq','model':'x','api_key':'bad\nkey'}, {'provider_id':'groq','model':'x','api_key':'anahtarş'},
                     {'provider_id':'groq','model':'../?x'}, {'provider_id':'groq','model':''}):
            r=self.client.post('/api/ai/settings',json=body);self.assertEqual(r.status_code,422,r.text)
            self.assertEqual(self.app.state.ai.settings.credentials().provider_id,'gemini')

if __name__=='__main__':unittest.main()
