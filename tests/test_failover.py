"""Real provider adapters with fake HTTP, isolated DBs and no paid API calls."""
import copy
import json
import ssl
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from app.ai_schemas import AnalysisInput, RetryAnalysisInput
from app.main import create_app
from app.models import AIAnalysis
from app.provider_catalog import PROVIDERS
from app.ai_provider import get_provider, ProviderError
from tests.test_ai import TEXT
from tests.test_providers import response_for


def reply(pid, **headers):
    return httpx.Response(200,headers=headers,json=response_for(pid))


class FailoverTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.app=create_app(self.root/'db',settings_path=self.root/'.env')
        self.client=TestClient(self.app);self.client.__enter__()
        self.addCleanup(self.client.__exit__,None,None,None)
        sleep=patch('app.ai_provider.time.sleep');self.sleep=sleep.start();self.addCleanup(sleep.stop)
        self.configure('groq');self.configure('gemini')

    def configure(self, pid, model=None, key=None):
        return self.client.request('POST','/api/ai/settings',json={'provider_id':pid,
            'model':model or PROVIDERS[pid].default_model,'api_key':key or 'PRIVATE-'+pid}).json()

    def body(self, text=TEXT, backups=None):
        s=self.client.get('/api/ai/settings').json()
        return {'provider_id':s['provider_id'],'provider_model':s['model'],'transfer_consent':True,
                'fallback_providers':backups if backups is not None else [
                    {k:p[k] for k in ('provider_id','provider_model')} for p in s['fallback_providers']],
                'sources':[{'kind':'text','content':text}]}

    def analyze(self, body=None):
        response=self.client.request('POST','/api/ai/analyze',json=body or self.body())
        self.assertEqual(response.status_code,201,response.text)
        return response.json()

    def stored(self, aid):
        with self.app.state.database.session() as session:return session.get(AIAnalysis,aid).data

    def test_quota_switches_immediately_to_authorized_backup_and_keeps_ahp(self):
        with patch('httpx.Client.post',side_effect=[httpx.Response(429,headers={'retry-after':'60'}),reply('groq')]) as post:
            report=self.analyze()
        self.assertEqual(report['status'],'ready');self.assertEqual(post.call_count,2)
        self.sleep.assert_not_called()
        self.assertIn('generativelanguage.googleapis.com',post.call_args_list[0].args[0])
        self.assertEqual(post.call_args_list[1].args[0],PROVIDERS['groq'].endpoint)
        self.assertEqual(report['provider_id'],'groq');self.assertEqual(report['requested_provider_id'],'gemini')
        self.assertEqual(report['provider_failures'][0]['code'],'RATE_LIMIT')
        self.assertEqual(report['providers_used'][0]['provider_id'],'groq')
        self.assertAlmostEqual(report['analysis']['result']['total'],100)
        self.assertEqual(report['sources'][0]['segments'][0]['text'],TEXT)
        self.assertEqual(self.client.get('/api/ai/settings').json()['provider_id'],'gemini')
        self.assertNotIn('PRIVATE-',self.stored(report['id']))
        self.assertNotIn('execution',report)

    def test_every_configured_ai_can_be_a_backup_and_exhaustion_is_bounded(self):
        for pid in ('openai','openrouter','aimlapi','gemini'):self.configure(pid)
        settings=self.client.get('/api/ai/settings').json()
        self.assertEqual(len(settings['fallback_providers']),4)
        with patch('httpx.Client.post',return_value=httpx.Response(429,json={'error':{'message':'SECRET-RESPONSE'}})) as post:
            report=self.analyze()
        self.assertEqual(post.call_count,5);self.assertEqual(report['status'],'failed')
        self.assertEqual(report['error_details']['code'],'ALL_PROVIDERS_UNAVAILABLE')
        self.assertEqual(len(report['provider_failures']),5)
        self.assertNotIn('analysis',report)
        raw=self.stored(report['id'])
        self.assertNotIn('SECRET-RESPONSE',raw);self.assertNotIn('PRIVATE-',raw)
        self.assertEqual(json.loads(raw)['execution']['pending'][0][0]['segments'][0]['text'],TEXT)
        self.assertNotIn('PRIVATE-',json.dumps(settings))

    def test_unapproved_saved_key_is_never_used(self):
        body=self.body(backups=[])
        with patch('httpx.Client.post',return_value=httpx.Response(429)) as post:
            report=self.analyze(body)
        self.assertEqual(post.call_count,1);self.assertEqual(report['error_details']['code'],'RATE_LIMIT')
        self.assertEqual(len(report['provider_plan']),1)

    def test_stale_duplicate_or_primary_backup_rejected_before_http(self):
        body=self.body()
        cases=[[*body['fallback_providers'],*body['fallback_providers']],
               [{'provider_id':'gemini','provider_model':PROVIDERS['gemini'].default_model}],
               [{'provider_id':'groq','provider_model':'changed-model'}],
               [{'provider_id':'openai','provider_model':PROVIDERS['openai'].default_model}]]
        for backups in cases:
            with self.subTest(backups=backups),patch('httpx.Client.post') as post:
                result=self.client.request('POST','/api/ai/start',json={**body,'fallback_providers':backups})
            self.assertEqual(result.status_code,409);post.assert_not_called()

    def test_running_job_keeps_credential_snapshot_and_does_not_add_new_keys(self):
        job=self.app.state.ai.prepare_analysis(AnalysisInput(**self.body()))
        self.configure('groq',key='NEW-SECRET');self.configure('openai')
        with patch('httpx.Client.post',side_effect=[httpx.Response(429),reply('groq')]) as post:
            self.app.state.ai.run_analysis(*job)
        self.assertEqual(post.call_args_list[1].kwargs['headers']['Authorization'],'Bearer PRIVATE-groq')
        report=self.app.state.ai.get(job[0]);self.assertEqual(len(report['provider_plan']),2)
        self.assertNotIn('NEW-SECRET',self.stored(job[0]))

    def test_mid_batch_switch_never_resends_completed_passages(self):
        self.configure('groq');long_text=TEXT+' '+('birinci kaynak ayrıntıları '*410)+'SON KAYIT'
        sent=[]
        def respond(url,headers,json):
            if 'api.groq.com' in url:
                passages=__import__('json').loads(json['messages'][1]['content'])['sources'];sent.append(('groq',passages))
                return reply('groq',**{'x-ratelimit-reset-tokens':'1s'}) if len(sent)==1 else httpx.Response(429)
            passages=__import__('json').loads(json['contents'][0]['parts'][0]['text'])['sources'];sent.append(('gemini',passages))
            return reply('gemini')
        with patch('httpx.Client.post',side_effect=respond):report=self.analyze(self.body(long_text))
        self.assertEqual(report['status'],'ready')
        first=sent[0][1][0]['segments'][0]['text']
        for pid,passages in sent[2:]:
            self.assertEqual(pid,'gemini')
            self.assertNotIn(first,json.dumps(passages,ensure_ascii=False))
        self.assertEqual([p['provider_id'] for p in report['providers_used']],['groq','gemini'])
        self.assertEqual(report['sources'][0]['segments'][0]['text'],long_text)
        self.assertEqual(report['completed_batches'],len(sent)-1)
        self.assertTrue(any('SON KAYIT' in json.dumps(s,ensure_ascii=False) for _,s in sent))

    def test_resume_after_all_limits_keeps_completed_output_and_old_record(self):
        self.configure('groq');body=self.body(TEXT+' '+'x '*5000)
        with patch('httpx.Client.post',side_effect=[reply('groq',**{'x-ratelimit-reset-tokens':'1s'}),httpx.Response(429),httpx.Response(429)]):
            failed=self.analyze(body)
        self.assertEqual(failed['status'],'failed');self.assertEqual(failed['completed_batches'],1)
        before=self.stored(failed['id']);pending=len(json.loads(before)['execution']['pending'])
        self.configure('gemini');request={k:v for k,v in self.body(backups=[]).items() if k!='sources'}
        with patch('httpx.Client.post',return_value=reply('gemini')) as post,patch('app.ai_service.extract_sources') as extract,patch('app.ai_service.search_web') as search:
            retried=self.client.request('POST','/api/ai/analyses/'+failed['id']+'/retry',json=request).json()
        self.assertEqual(post.call_count,pending);extract.assert_not_called();search.assert_not_called()
        report=self.app.state.ai.get(retried['id'])
        self.assertEqual(report['status'],'ready');self.assertEqual(report['resumed_batches'],1)
        self.assertEqual(report['method'],failed['method']);self.assertEqual(self.stored(failed['id']),before)
        self.assertEqual(report['completed_batches'],1+pending)
        self.assertAlmostEqual(report['analysis']['result']['total'],100)
        pdf=self.client.get('/api/ai/analyses/'+report['id']+'/pdf')
        self.assertEqual(pdf.status_code,200);self.assertTrue(pdf.content.startswith(b'%PDF'))

    def test_output_token_limit_never_parses_partial_json_and_switches(self):
        partial={'candidates':[{'finishReason':'MAX_TOKENS','content':{'parts':[{'text':'{"findings":'}]}}]}
        with patch('httpx.Client.post',side_effect=[httpx.Response(200,json=partial),reply('groq')]) as post:
            report=self.analyze()
        self.assertEqual(report['status'],'ready');self.assertEqual(post.call_count,2)
        self.assertEqual(report['provider_failures'][0]['code'],'OUTPUT_TOKEN_LIMIT')

    def test_context_limit_splits_without_dropping_tail(self):
        seen=[]
        def respond(url,headers,json):
            text=json['contents'][0]['parts'][0]['text'];seen.append(text)
            return httpx.Response(413) if len(seen)==1 else reply('gemini')
        text=TEXT+' '+'dolgu '*650+' SON KAYNAK'
        with patch('httpx.Client.post',side_effect=respond):report=self.analyze(self.body(text))
        self.assertEqual(report['status'],'ready');self.assertGreater(report['completed_batches'],1)
        self.assertTrue(any('SON KAYNAK' in s for s in seen[1:]))
        self.assertEqual(len(report['providers_used']),1)

    def test_402_then_503_then_success_stays_within_known_plan(self):
        self.configure('openrouter');self.configure('gemini')
        body=self.body(backups=[{'provider_id':'openrouter','provider_model':PROVIDERS['openrouter'].default_model},
                                {'provider_id':'groq','provider_model':PROVIDERS['groq'].default_model}])
        with patch('httpx.Client.post',side_effect=[httpx.Response(503)]*3+[httpx.Response(402),reply('groq')]) as post:
            report=self.analyze(body)
        self.assertEqual(report['status'],'ready');self.assertEqual(post.call_count,5)
        self.assertEqual([p['code'] for p in report['provider_failures']],['SERVICE_UNAVAILABLE','QUOTA_EXHAUSTED'])

    def test_refusal_and_ssl_do_not_switch_recipients(self):
        error=httpx.ConnectError('PRIVATE-transport');error.__cause__=ssl.SSLCertVerificationError('PRIVATE-cert')
        for response in (httpx.Response(200,json={'promptFeedback':{'blockReason':'SAFETY'}}),error):
            with self.subTest(response=type(response).__name__),patch('httpx.Client.post',side_effect=[response]) as post:
                report=self.analyze()
            self.assertEqual(report['status'],'failed');self.assertEqual(post.call_count,1)
            self.assertNotIn('analysis',report);self.assertNotIn('PRIVATE',json.dumps(report))

    def test_mismatched_checkpoint_stops_before_transmission(self):
        with patch('httpx.Client.post',return_value=httpx.Response(429)):failed=self.analyze()
        with self.app.state.database.session(write=True) as session:
            row=session.get(AIAnalysis,failed['id']);data=json.loads(row.data)
            data['execution']['fingerprint']='changed';row.data=json.dumps(data)
        request={k:v for k,v in self.body().items() if k!='sources'}
        with patch('httpx.Client.post') as post:
            result=self.client.request('POST','/api/ai/analyses/'+failed['id']+'/retry',json=request).json()
        report=self.app.state.ai.get(result['id']);post.assert_not_called()
        self.assertEqual(report['status'],'failed');self.assertIn('eşleşmiyor',report['error'])

    def test_duplicate_retry_remains_deduplicated_after_provider_switch(self):
        with patch('httpx.Client.post',return_value=httpx.Response(429)):failed=self.analyze()
        request=RetryAnalysisInput(**{k:v for k,v in self.body().items() if k!='sources'})
        service=self.app.state.ai;job=service.prepare_retry(failed['id'],request)
        with patch('httpx.Client.post',side_effect=[httpx.Response(429),reply('groq')]):service.run_analysis(*job)
        same=service.prepare_retry(failed['id'],request)
        self.assertEqual(same[0],job[0]);self.assertIsNone(same[1])
        self.assertTrue(service.capacity.acquire(blocking=False));self.assertTrue(service.capacity.acquire(blocking=False))
        service.capacity.release();service.capacity.release()

    def test_request_budget_and_app_restart_preserve_completed_chunks(self):
        self.configure('groq')
        with patch('app.ai_failover.MAX_BATCH_REQUESTS',1),patch('httpx.Client.post',return_value=reply('groq')) as post:
            failed=self.analyze(self.body(TEXT+' '+'kaynak '*1500))
        self.assertEqual(post.call_count,1)
        self.assertEqual(failed['error_details']['code'],'REQUEST_BUDGET_EXCEEDED')
        self.assertEqual(failed['completed_batches'],1)
        self.assertNotIn('analysis',failed)
        archived=json.loads(self.stored(failed['id']))
        pending=len(archived['execution']['pending'])
        # Simulate interruption after the durable checkpoint, then open a new
        # service instance against the same DB and recover on startup.
        self.configure('gemini')
        with self.app.state.database.session(write=True) as session:
            session.get(AIAnalysis,failed['id']).status='processing'
        restarted=create_app(self.root/'db',settings_path=self.root/'.env')
        with TestClient(restarted) as client:
            recovered=client.get('/api/ai/analyses/'+failed['id']).json()
            self.assertEqual(recovered['status'],'failed')
            self.assertEqual(recovered['completed_batches'],1)
            request={k:v for k,v in self.body(backups=[]).items() if k!='sources'}
            with patch('httpx.Client.post',return_value=reply('gemini')) as post:
                retried=client.request('POST','/api/ai/analyses/'+failed['id']+'/retry',json=request).json()
            report=client.get('/api/ai/analyses/'+retried['id']).json()
        self.assertEqual(post.call_count,pending)
        self.assertEqual(report['status'],'ready')
        self.assertEqual(report['resumed_batches'],1)
        self.assertEqual(report['method'],archived['method'])


class OutputLimitTests(unittest.TestCase):
    def test_each_adapter_recognizes_truncated_response(self):
        for pid,spec in PROVIDERS.items():
            result=copy.deepcopy(response_for(pid))
            if pid=='openai':result.update(status='incomplete',incomplete_details={'reason':'max_output_tokens'})
            elif pid=='gemini':result['candidates'][0]['finishReason']='MAX_TOKENS'
            else:result['choices'][0]['finish_reason']='length'
            with self.subTest(pid=pid),patch('httpx.Client.post',return_value=httpx.Response(200,json=result)):
                with self.assertRaises(ProviderError) as caught:get_provider(pid).analyze([],'','FAKE',spec.default_model)
            self.assertEqual(caught.exception.details['code'],'OUTPUT_TOKEN_LIMIT')


if __name__=='__main__':unittest.main()
