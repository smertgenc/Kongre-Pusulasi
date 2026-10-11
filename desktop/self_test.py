"""Offline smoke checks inside the frozen application; never touches real user data."""
import base64
import json
import os
from pathlib import Path
import tempfile

def run(report_path):
    checks = []
    old_offline = os.environ.get('KONGRE_OFFLINE')
    os.environ['KONGRE_OFFLINE'] = '1'
    try:
        from fastapi.testclient import TestClient
        from app.main import create_app
        from app.config import VERSION, ROOT
        from desktop.startup import check_resources
        from app.ai_schemas import ProviderOutput
        class OfflineProvider:
            def analyze(self, *args, **kwargs):
                return ProviderOutput.model_validate({'facts':[], 'findings':[
                    {'criterion':f'K{i}','value':None,'status':'not_found','confidence':0,
                     'explanation':'Çevrimdışı paket testi; AI servisine istek gönderilmedi.','evidence':[]}
                    for i in range(1,11)]})
        def ensure(condition, name):
            if not condition: raise RuntimeError(name)
            checks.append(name)
        check_resources(ROOT)
        checks.append('bundled_resources')
        # Import/runtime checks are offline and do not request an API key.
        import certifi
        from app.network import tls_context
        ensure(Path(certifi.where()).is_file() and tls_context().verify_mode!=0,'tls_certificate_resources')
        with tempfile.TemporaryDirectory(prefix='ahp-package-test-') as temporary:
            folder = Path(temporary); db = folder/'test.db'; settings = folder/'test.env'
            def app(): return create_app(db,settings_path=settings,ai_provider=OfflineProvider())
            with TestClient(app()) as client:
                ensure(client.get('/api/health').json()['version']==VERSION,'version')
                for resource in ('/','/styles.css','/app.js','/ai.js','/logos.js','/intelligence.js','/compare.js','/database.js','/research.js'):
                    ensure(client.get(resource).status_code==200,'resource:'+resource)
                state = client.get('/api/state').json()
                ensure(not client.get('/api/ai/settings').json()['configured'] and
                       not client.get('/api/search/settings').json()['configured'],'startup_without_api_keys')
                expected = {'A Kongresi':73.38331160365063,'B kongresi':74.81644136416664,
                            'C Kongresi':94.64248953544231,'D kongresi':40.14684690866672}
                ensure(all(abs(c['evaluations'][0]['result']['total']-expected[c['metadata']['name']])<1e-8
                           for c in state['congresses']) and len(state['congresses'])==4, 'excel_parity')
                from app.research_provenance import code_hashes
                ensure('app/conjoint.py' in code_hashes(ROOT),'research_provenance')
                ensure(not client.get('/api/research/status').json()['enabled'],'research_default_off')
                client.post('/api/research/settings',json={'enabled':True})
                study=client.post('/api/research/studies',json={'title':'Paket CBC testi','kind':'synthetic'}).json()
                estimated=client.post('/api/research/studies/'+study['id']+'/estimate',json={})
                ensure(estimated.status_code==200 and estimated.json()['model']['converged'],'cbc_estimation_offline')
                client.post('/api/research/settings',json={'enabled':False})
                model = state['models'][0]['id']
                saved = client.post('/api/evaluations',json={'model_id':model,'scale':1,'evaluator':'Paket testi',
                    'metadata':{'name':'Paket testi','edition':'1','context':'Test'},
                    'scores':{f'K{i}':1 for i in range(1,11)},'notes':{f'K{i}':'Paket testi' for i in range(1,11)}})
                ensure(saved.status_code==201 and saved.json()['result']['status']=='Yüksek Uygunluk','sqlite_write_and_ahp')
                client.post('/api/ai/settings',json={'api_key':'fixture-not-real','model':'fixture'})
                analyzed = client.post('/api/ai/analyze',json={'model_id':model,'transfer_consent':True,
                    'sources':[{'kind':'text','content':'Paket testi kongresi, program ve bilim kurulu verisi yoktur. Bu içerik yalnızca çevrimdışı paket doğrulamasında kullanılmaktadır.'}]}).json()
                ensure(analyzed.get('status')=='ready','ai_pipeline_offline_fixture')
                pdf = client.get('/api/ai/analyses/'+analyzed['id']+'/pdf')
                ensure(pdf.status_code==200 and pdf.content.startswith(b'%PDF-'),'turkish_pdf_export')
                from app.sources import extract_sources
                from app.ai_schemas import SourceInput
                parsed = extract_sources([SourceInput(kind='pdf',content=base64.b64encode(pdf.content).decode())])
                ensure(bool(parsed[0]['segments']),'pdf_import')
                # Exercise the new packaged adapters offline, with real HTTPX
                # request construction but an in-memory transport, never sockets.
                from unittest.mock import patch
                import httpx
                for provider in ('gemini','tavily','jina'):
                    def reply(request):
                        data={'candidates':[{'content':{'parts':[{'text':'OK'}]}}]} if provider=='gemini' else {
                            'results' if provider=='tavily' else 'data':[{'url':'https://example.org/program',
                            'title':'Program','content':'Academic congress programme used only in a package test.'}]}
                        return httpx.Response(200,json=data)
                    if provider=='gemini':
                        client.post('/api/ai/settings',json={'provider_id':provider,'api_key':'fixture-not-real','model':'fixture'})
                    else:client.post('/api/search/settings',json={'provider_id':provider,'api_key':'fixture-not-real'})
                    mock_client=httpx.Client(transport=httpx.MockTransport(reply))
                    with patch.dict(os.environ,{'KONGRE_OFFLINE':'0'}),patch('app.network.getproxies',return_value={}),patch('httpx.Client',return_value=mock_client):
                        probe=client.post('/api/ai/test' if provider=='gemini' else '/api/search/test',json={})
                    ensure(probe.status_code==200 and probe.json()['provider_id']==provider,'connection_probe_fixture:'+provider)
                # Exercise the actual failover/checkpoint code in the frozen
                # package too. Both requests are intercepted; no live key used.
                client.post('/api/ai/settings',json={'provider_id':'groq','api_key':'fixture-not-real','model':'fixture'})
                client.post('/api/ai/settings',json={'provider_id':'gemini','api_key':'fixture-not-real','model':'fixture'})
                fake_output=OfflineProvider().analyze().model_dump_json()
                client.app.state.ai.provider=None
                try:
                    with patch('app.ai_provider.client_options',return_value={}),patch('httpx.Client.post',side_effect=[
                        httpx.Response(429),httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':fake_output}}]})]):
                        switched=client.request('POST','/api/ai/analyze',json={'provider_id':'gemini','provider_model':'fixture',
                            'fallback_providers':[{'provider_id':'groq','provider_model':'fixture'}],'transfer_consent':True,
                            'sources':[{'kind':'text','content':'Çevrimdışı paket doğrulaması için kongre ve program örnek metni.'}]}).json()
                    ensure(switched.get('status')=='ready' and switched['provider_id']=='groq' and
                           switched['completed_batches']==1 and switched['provider_failures'][0]['code']=='RATE_LIMIT',
                           'ai_failover_checkpoint_fixture')
                finally:client.app.state.ai.provider=OfflineProvider()
            with TestClient(app()) as client:
                ensure(len(client.get('/api/state').json()['congresses'])==5,'restart_persistence')
            from app.backup import snapshot, restore
            backup = snapshot(db,folder/'backups'); restored = folder/'restored.db'
            restore(backup,restored,folder/'backups')
            ensure(restored.is_file(),'backup_restore')
            from app.network import require_online
            try: require_online()
            except ValueError: checks.append('offline_gate')
            else: raise RuntimeError('offline_gate')
            if os.name=='nt':
                from app.windows_ocr import extract_windows_image
                from PIL import Image, ImageDraw, ImageFont
                from io import BytesIO
                image=Image.new('RGB',(1400,240),'white')
                font=ImageFont.truetype(str(Path(os.environ['WINDIR'])/'Fonts/arial.ttf'),44)
                ImageDraw.Draw(image).text((30,70),'AHP Congress Analyzer 2026 Kongre Analizi',font=font,fill='black')
                buffer=BytesIO(); image.save(buffer,format='PNG')
                ocr=extract_windows_image(buffer.getvalue())
                ensure('Congress' in ocr['text'],'bundled_windows_ocr')
        result={'ok':True,'version':VERSION,'checks':checks,'live_ai_verified':False}
    except Exception as error:
        from desktop.logging_setup import startup_diagnostic
        result={'ok':False,'checks':checks,'error_type':type(error).__name__,'diagnostic':startup_diagnostic(error)}
    finally:
        if old_offline is None: os.environ.pop('KONGRE_OFFLINE',None)
        else: os.environ['KONGRE_OFFLINE']=old_offline
    Path(report_path).parent.mkdir(parents=True,exist_ok=True)
    Path(report_path).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if result['ok'] else 1
