"""Disposable UI fixture: real Groq batching, simulated HTTP only, no real key."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import httpx
import uvicorn
from fastapi.testclient import TestClient
from app.main import create_app
from app.ai_batches import source_size
from tests.test_ai import TEXT
from tests.test_batches import response

if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='kongre-batches-qa-') as tmp:
        root=Path(tmp);app=create_app(root/'qa.db',settings_path=root/'.env')
        with TestClient(app) as client:
            client.request('POST','/api/ai/settings',json={'provider_id':'groq','api_key':'TEST_ONLY','model':'openai/gpt-oss-20b'})
            with patch('httpx.Client.post',return_value=httpx.Response(413)),patch('app.ai_provider.time.sleep'):
                result=client.request('POST','/api/ai/analyze',json={'provider_id':'groq','transfer_consent':True,
                    'sources':[{'kind':'text','content':TEXT+' Test belge metni.'*400,'label':'SAHTE API / ARAYÜZ TESTİ'}]}).json()
            print('QA_REPORT=http://127.0.0.1:8766/#ai-report/'+result['id'],flush=True)
        def respond(*args,**kwargs):
            content=json.loads(kwargs['json']['messages'][1]['content'])
            if source_size(content['sources'])>2600:return httpx.Response(413)
            return response(**{'x-ratelimit-reset-tokens':'2s'})
        with patch('httpx.Client.post',side_effect=respond):
            uvicorn.run(app,host='127.0.0.1',port=8766)
