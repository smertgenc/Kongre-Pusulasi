"""Isolated UI test for a 503 followed by success. No external API requests."""
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
import httpx
import uvicorn
from fastapi.testclient import TestClient
from app.main import create_app
from tests.test_ai import TEXT
from tests.test_providers import response_for

if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='kongre-retry-qa-') as tmp:
        root=Path(tmp);app=create_app(root/'qa.db',settings_path=root/'.env')
        with TestClient(app) as client:
            client.post('/api/ai/settings',json={'provider_id':'gemini','api_key':'qa-placeholder-not-a-real-key','model':'gemini-test-fixture'})
            with patch('httpx.Client.post',return_value=httpx.Response(503)),patch('app.ai_provider.time.sleep'):
                result=client.request('POST','/api/ai/analyze',json={'provider_id':'gemini','sources':[{'kind':'text','content':TEXT,'label':'Yalnızca arayüz testi'}],'transfer_consent':True}).json()
            print('QA_REPORT=http://127.0.0.1:8766/#ai-report/'+result['id'],flush=True)
        calls=0
        def respond(*args,**kwargs):
            global calls
            calls+=1
            if calls%2==1:return httpx.Response(503)
            time.sleep(3)
            return httpx.Response(200,json=response_for('gemini'))
        with patch('httpx.Client.post',side_effect=respond):uvicorn.run(app,host='127.0.0.1',port=8766)
