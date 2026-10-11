"""Temporary, explicit UI test server. Never reads or changes the real project DB/key."""
import tempfile
from pathlib import Path
import uvicorn
from fastapi.testclient import TestClient
from app.main import create_app
from tests.test_ai import FixtureProvider, TEXT
from app.ai_schemas import SettingsInput

if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='kongre-ui-qa-') as temp:
        root=Path(temp)
        provider=FixtureProvider()
        provider.output['findings'][0].update(value=None,status='not_found',confidence=0,evidence=[])
        provider.output['findings'][2]['confidence']=.6
        app=create_app(root/'qa.db',settings_path=root/'.env',ai_provider=provider)
        app.state.ai.settings.save(SettingsInput(provider_id='openai',api_key='test-placeholder-not-a-credential',model='test-fixture'))
        with TestClient(app) as client:
            mid=client.get('/api/state').json()['models'][0]['id']
            r=client.post('/api/ai/analyze',json={'model_id':mid,'context':'TEST: gerçek kongre analizi değildir.',
                'sources':[{'kind':'text','content':TEXT}],'transfer_consent':True}).json()
            print('QA_REPORT=http://127.0.0.1:8766/#ai-report/'+r['id'],flush=True)
        uvicorn.run(app,host='127.0.0.1',port=8766)
