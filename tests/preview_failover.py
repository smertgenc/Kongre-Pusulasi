"""Disposable browser QA: Gemini quota failure -> Groq success, no live APIs."""
import tempfile
from pathlib import Path
from unittest.mock import patch
import httpx
import uvicorn
from fastapi.testclient import TestClient
from app.main import create_app
from tests.test_providers import response_for


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='kongre-failover-qa-') as folder:
        root=Path(folder)
        app=create_app(root/'qa.db',settings_path=root/'qa.env')
        with TestClient(app) as client:
            for provider in ('groq','gemini'):
                client.post('/api/ai/settings',json={'provider_id':provider,
                    'api_key':'fixture-not-real','model':'fixture-'+provider})

        def respond(url, **kwargs):
            if url.startswith('https://generativelanguage.googleapis.com/'):
                return httpx.Response(429)
            if url=='https://api.groq.com/openai/v1/chat/completions':
                return httpx.Response(200,json=response_for('groq'))
            raise AssertionError('Unexpected external request in offline QA')

        with patch('app.ai_provider.client_options',return_value={}),patch('httpx.Client.post',side_effect=respond):
            uvicorn.run(app,host='127.0.0.1',port=8767)
