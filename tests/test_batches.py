"""Groq size limits, lossless batching, citation merging and quota pacing."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from app.ai_batches import split_sources, source_size, checked_output, merge_outputs
from app.ai_provider import get_provider, ProviderError
from app.ai_schemas import ProviderOutput
from app.main import create_app
from tests.test_ai import TEXT, output_fixture


def sources(text=TEXT):
    return [{'id':'S1','kind':'text','label':'Test','url':'','content_hash':'saved',
             'segments':[{'id':'1','page':2,'text':text}]}]


def response(output=None, **headers):
    return httpx.Response(200,headers=headers,json={'choices':[{'finish_reason':'stop',
        'message':{'content':json.dumps(output or output_fixture())}}]})


class GroqBatchTests(unittest.TestCase):
    def setUp(self):
        self.sleep=patch('app.ai_provider.time.sleep');self.wait=self.sleep.start();self.addCleanup(self.sleep.stop)

    def test_all_text_and_boundary_quotes_survive_without_mutating_archive(self):
        text=' '.join(f'Kelime{i}' for i in range(3000))
        original=sources(text);before=copy.deepcopy(original)
        batches=split_sources(original)
        self.assertGreater(len(batches),1)
        parts=[p['text'] for b in batches for s in b for p in s['segments']]
        for start in range(0,len(text),53):
            self.assertTrue(any(text[start:start+220] in p for p in parts))
        for b in batches:
            self.assertLessEqual(source_size(b),5000)
            self.assertTrue(all(s['id']=='S1' and p['id']=='1' and p['page']==2 for s in b for p in s['segments']))
        self.assertEqual(original,before)

    def test_413_shrinks_request_then_processes_all_fragments_same_provider(self):
        original=sources(TEXT+' A'*4000);before=copy.deepcopy(original);events=[]
        provider=get_provider('groq');provider.on_progress=events.append
        seen=[]
        def accept_small(url,headers,json):
            sent=__import__('json').loads(json['messages'][1]['content'])['sources']
            seen.append(sent)
            self.assertEqual(headers['Authorization'],'Bearer TEST_ONLY')
            self.assertEqual(json['model'],'openai/gpt-oss-20b')
            self.assertEqual(json['max_completion_tokens'],3000)
            self.assertEqual(json['reasoning_effort'],'low')
            if source_size(sent)>2600:return httpx.Response(413,json={'error':{'message':'private org secret'}})
            return response(**{'x-ratelimit-reset-tokens':'2s'})
        with patch('httpx.Client.post',side_effect=accept_small):
            result=provider.analyze(original,'','TEST_ONLY','openai/gpt-oss-20b')
        self.assertEqual(len(result.findings),10);self.assertEqual(original,before)
        accepted=[p['text'] for b in seen if source_size(b)<=2600 for s in b for p in s['segments']]
        self.assertTrue(any(original[0]['segments'][0]['text'][-220:] in p for p in accepted))
        self.assertIn('resizing',[e['phase'] for e in events]);self.assertIn('quota_wait',[e['phase'] for e in events])
        self.assertNotIn('private',__import__('json').dumps(events));self.assertEqual(self.wait.call_args.args[0],2.25)

    def test_permanent_rejection_stops_and_no_partial_result_escapes(self):
        with patch('httpx.Client.post',side_effect=[response(),httpx.Response(401)]) as post:
            with self.assertRaises(ProviderError) as caught:
                get_provider('groq').analyze(sources(TEXT+' A'*4000),'','TEST_ONLY','openai/gpt-oss-20b')
        self.assertEqual(post.call_count,2);self.assertEqual(caught.exception.details['code'],'AUTH_ERROR')

    def test_unsplittable_413_has_bounded_calls_and_no_secret(self):
        with patch('httpx.Client.post',return_value=httpx.Response(413,json={'error':{'message':'SECRET'}})) as post:
            with self.assertRaises(ProviderError) as caught:
                get_provider('groq').analyze(sources('A'*2000),'','TEST_ONLY','openai/gpt-oss-20b')
        self.assertLessEqual(post.call_count,4);self.assertNotIn('SECRET',str(caught.exception))
        self.assertIn('kısmi sonuç puanlanmadı',str(caught.exception))

    def test_quota_retry_waits_up_to_one_minute_without_resizing(self):
        with patch('httpx.Client.post',side_effect=[httpx.Response(429,headers={'retry-after':'60'}),response()]) as post:
            get_provider('groq').analyze(sources(),'','TEST_ONLY','openai/gpt-oss-20b')
        self.assertEqual(post.call_count,2);self.assertEqual(self.wait.call_args.args[0],60)
        self.assertEqual(post.call_args_list[0],post.call_args_list[1])

    def test_only_quotes_in_sent_fragment_survive_and_conflict_keeps_both_sides(self):
        first=ProviderOutput.model_validate(output_fixture())
        second=first.model_copy(deep=True)
        second.findings[0].value=False
        second.findings[0].evidence[0].quote='Program ve bilim kurulu yayimlandi.'
        invalid=checked_output(first,sources('A different passage without these quotes.'))
        self.assertFalse(invalid.facts);self.assertTrue(all(f.value is None for f in invalid.findings))
        merged=merge_outputs([checked_output(first,sources()),checked_output(second,sources()),invalid])
        self.assertEqual(merged.findings[0].status,'conflict');self.assertIsNone(merged.findings[0].value)
        self.assertEqual(len(merged.findings[0].evidence),2)
        self.assertTrue(merged.findings[1].value);self.assertEqual(len(merged.facts),2)

    def test_service_never_scores_a_partially_processed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with TestClient(create_app(root/'db',settings_path=root/'.env')) as client:
                client.request('POST','/api/ai/settings',json={'provider_id':'groq','api_key':'TEST_ONLY','model':'openai/gpt-oss-20b'})
                with patch('httpx.Client.post',side_effect=[response(),httpx.Response(401)]):
                    result=client.request('POST','/api/ai/analyze',json={'provider_id':'groq','transfer_consent':True,
                        'sources':[{'kind':'text','content':TEXT+' A'*4000}]}).json()
                self.assertEqual(result['status'],'failed');self.assertNotIn('analysis',result)
                self.assertEqual(result['sources'][0]['segments'][0]['text'],TEXT+' A'*4000)
                self.assertIn('batch',result['connection_progress'])
