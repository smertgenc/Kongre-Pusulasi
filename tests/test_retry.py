import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.ai_provider import get_provider, ProviderError
from app.ai_retry import retry_delay
from app.ai_schemas import RetryAnalysisInput
from app.models import AIAnalysis
from app.main import create_app
from tests.test_ai import TEXT
from tests.test_providers import response_for

class ProviderRetryTests(unittest.TestCase):
    def test_transient_503_recovers_same_request_with_backoff(self):
        provider=get_provider('gemini');events=[];provider.on_progress=events.append
        with patch('httpx.Client.post',side_effect=[httpx.Response(503),httpx.Response(200,json=response_for('gemini'))]) as post,patch('app.ai_provider.time.sleep') as sleep:
            result=provider.analyze([],'test','SECRET','gemini-3.5-flash')
        self.assertEqual(len(result.findings),10);self.assertEqual(post.call_count,2)
        self.assertEqual(post.call_args_list[0],post.call_args_list[1])
        self.assertEqual([e['phase'] for e in events],['request','waiting','request','complete'])
        self.assertGreaterEqual(sleep.call_args.args[0],2);self.assertLess(sleep.call_args.args[0],2.6)
        self.assertNotIn('SECRET',json.dumps(events))

    def test_retries_stop_at_three_and_keep_error_details(self):
        with patch('httpx.Client.post',return_value=httpx.Response(503,json={'error':{'message':'SECRET'}})) as post,patch('app.ai_provider.time.sleep') as sleep:
            with self.assertRaises(ProviderError) as caught:get_provider('gemini').analyze([],'','SECRET','gemini-3.5-flash')
        self.assertEqual(post.call_count,3);self.assertEqual(sleep.call_count,2)
        self.assertEqual(caught.exception.details['attempts'],3);self.assertEqual(caught.exception.details['http_status'],503)
        self.assertNotIn('SECRET',str(caught.exception))

    def test_retry_after_and_permanent_errors(self):
        self.assertEqual(retry_delay(httpx.Response(503,headers={'retry-after':'12'}),1),12)
        for status,header in [(503,'120'),(429,'invalid'),(429,'120'),(503,'nan'),(503,'inf')]:
            self.assertIsNone(retry_delay(httpx.Response(status,headers={'retry-after':header}),1))
        for status in (400,401,402,403,404,413,422,429):
            self.assertIsNone(retry_delay(httpx.Response(status),1))
        with patch('httpx.Client.post',side_effect=[httpx.Response(429,headers={'retry-after':'5'}),httpx.Response(200,json=response_for('gemini'))]) as post,patch('app.ai_provider.time.sleep') as sleep:
            get_provider('gemini').analyze([],'','SECRET','gemini-3.5-flash')
        self.assertEqual(post.call_count,2);self.assertEqual(sleep.call_args.args[0],5)

    def test_elapsed_budget_stops_before_another_request(self):
        with patch('httpx.Client.post',return_value=httpx.Response(503)) as post,patch('app.ai_provider.time.monotonic',side_effect=[0,0,239]),patch('app.ai_provider.time.sleep') as sleep:
            with self.assertRaises(ProviderError):get_provider('gemini').analyze([],'','SECRET','gemini-3.5-flash')
        self.assertEqual(post.call_count,1);sleep.assert_not_called()

class RetryServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.app=create_app(self.root/'db',settings_path=self.root/'.env')
        self.client=TestClient(self.app).__enter__()
        self.client.request('POST','/api/ai/settings',json={'provider_id':'gemini','api_key':'SECRET','model':'gemini-3.5-flash'})
        self.request={'provider_id':'gemini','provider_model':'gemini-3.5-flash','transfer_consent':True}
        self.body={**self.request,'sources':[{'kind':'text','content':TEXT}]}
        self.sleep=patch('app.ai_provider.time.sleep');self.sleep.start()
    def tearDown(self):
        self.sleep.stop();self.client.__exit__(None,None,None);self.tmp.cleanup()
    def failed(self):
        with patch('httpx.Client.post',return_value=httpx.Response(503)):
            r=self.client.request('POST','/api/ai/analyze',json=self.body)
        self.assertEqual(r.status_code,201);return r.json()
    def test_background_start_and_lightweight_progress(self):
        with patch('httpx.Client.post',side_effect=[httpx.Response(503),httpx.Response(200,json=response_for('gemini'))]):
            r=self.client.request('POST','/api/ai/start',json=self.body)
        self.assertEqual(r.status_code,202);aid=r.json()['id']
        status=self.client.get('/api/ai/analyses/'+aid+'/progress')
        self.assertEqual(status.json()['status'],'ready');self.assertNotIn(TEXT,status.text)
        d=self.client.get('/api/ai/analyses/'+aid).json()
        self.assertEqual(d['analysis']['raw_score'],10)
        self.assertEqual(next(e for e in d['connection_events'] if e['phase']=='complete')['attempt'],2)
        self.assertEqual(d['completed_batches'],1)
        self.assertEqual(len([e for e in d['connection_events'] if e['phase']=='waiting']),1)
    def test_retry_reuses_snapshots_without_search_or_extraction(self):
        original=self.failed();aid=original['id']
        with self.app.state.database.session() as session:before=session.get(AIAnalysis,aid).data
        with patch('httpx.Client.post',return_value=httpx.Response(200,json=response_for('gemini'))) as post,patch('app.ai_service.extract_sources') as extract,patch('app.ai_service.search_web') as search:
            r=self.client.request('POST','/api/ai/analyses/'+aid+'/retry',json=self.request)
        self.assertEqual(r.status_code,202,r.text);extract.assert_not_called();search.assert_not_called();self.assertEqual(post.call_count,1)
        new=self.client.get('/api/ai/analyses/'+r.json()['id']).json()
        self.assertEqual(new['sources'],original['sources']);self.assertEqual(new['model'],original['model']);self.assertEqual(new['retry_of'],aid)
        self.assertEqual(new['status'],'ready');self.assertNotIn('SECRET',json.dumps(new))
        with self.app.state.database.session() as session:self.assertEqual(session.get(AIAnalysis,aid).data,before)
        self.assertEqual(self.client.get('/api/ai/analyses/'+aid).json()['latest_retry']['id'],new['id'])
        with patch('httpx.Client.post') as post:
            again=self.client.request('POST','/api/ai/analyses/'+aid+'/retry',json=self.request)
        self.assertEqual(again.json()['id'],new['id']);post.assert_not_called()
    def test_concurrent_retry_click_is_deduplicated_and_capacity_released(self):
        original=self.failed();service=self.app.state.ai;request=RetryAnalysisInput(**self.request)
        job=service.prepare_retry(original['id'],request)
        same=service.prepare_retry(original['id'],request)
        self.assertEqual(same[0],job[0]);self.assertIsNone(same[1])
        with patch('httpx.Client.post',return_value=httpx.Response(200,json=response_for('gemini'))):service.run_analysis(*job)
        self.assertTrue(service.capacity.acquire(blocking=False));self.assertTrue(service.capacity.acquire(blocking=False));self.assertFalse(service.capacity.acquire(blocking=False))
        service.capacity.release();service.capacity.release()
    def test_retry_rejects_stale_consent_deleted_missing_and_empty_sources(self):
        original=self.failed();base='/api/ai/analyses/'+original['id']
        for body in ({**self.request,'provider_id':'groq'},{**self.request,'provider_model':'another'}):
            self.assertEqual(self.client.request('POST',base+'/retry',json=body).status_code,409)
        self.assertEqual(self.client.request('POST',base+'/retry',json={**self.request,'transfer_consent':False}).status_code,422)
        self.client.request('POST',base+'/delete',json={})
        self.assertEqual(self.client.request('POST',base+'/retry',json=self.request).status_code,409)
        self.assertEqual(self.client.request('POST','/api/ai/analyses/missing/retry',json=self.request).status_code,404)
        self.assertEqual(self.client.get('/api/ai/analyses/missing/progress').status_code,404)
    def test_recover_marks_interrupted_retry_without_losing_sources(self):
        original=self.failed();service=self.app.state.ai;job=service.prepare_retry(original['id'],RetryAnalysisInput(**self.request))
        service.recover();interrupted=service.get(job[0]);service.capacity.release()
        self.assertEqual(interrupted['status'],'failed');self.assertEqual(interrupted['sources'],original['sources'])

if __name__=='__main__':unittest.main()
