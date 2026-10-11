"""Real HTTP request paths with simulated upstreams, never live keys or charges."""
from contextlib import contextmanager
import io
import json
import logging
import os
from pathlib import Path
import socket
import ssl
import tempfile
import unittest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from app.main import create_app
from app.network import proxy_for, client_options
from app.connection_errors import MESSAGES, transport_code
from app.ai_provider import get_provider, ProviderError
from desktop.logging_setup import SafeFormatter

SECRET='key-PRIVATE-never-log'

def wrapped(cause):
    error=httpx.ConnectError('PRIVATE https://private.example/?key='+SECRET)
    error.__cause__=cause
    return error

class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.app=create_app(self.root/'test.db',settings_path=self.root/'settings.env')
        self.client=TestClient(self.app).__enter__()
        for pid in ('jina','tavily'):
            self.client.post('/api/search/settings',json={'provider_id':pid,'api_key':SECRET})
        self.client.post('/api/ai/settings',json={'provider_id':'gemini','model':'gemini-3.5-flash','api_key':SECRET})
        self.before=self.client.get('/api/state').json()
        self.before_ai=self.client.get('/api/ai/analyses').json()

    def tearDown(self):
        self.client.__exit__(None,None,None);self.tmp.cleanup()

    @contextmanager
    def upstream(self,pid,*,status=200,error=None,body=None):
        seen=[]
        def respond(request):
            seen.append(request)
            if error:raise error
            data=body
            if data is None:
                data={'candidates':[{'content':{'parts':[{'text':'OK'}]}}]} if pid=='gemini' else {
                    'data' if pid=='jina' else 'results':[{'url':'https://example.org/congress','title':'Program',
                                                       'content':'Academic congress scientific programme and speakers.'}]}
            if status!=200 and body is None:data={'error':{'message':SECRET}}
            return httpx.Response(status,json=data)
        client=httpx.Client(transport=httpx.MockTransport(respond))
        with patch('httpx.Client',return_value=client),patch('app.network.getproxies',return_value={}):
            yield seen

    def select(self,pid):
        if pid!='gemini':
            self.client.post('/api/search/settings',json={'provider_id':pid})

    def check(self,pid,body=None):
        return self.client.post('/api/ai/test' if pid=='gemini' else '/api/search/test',json={} if body is None else body)

    def test_proxyless_api_requests_succeed_for_each_real_destination(self):
        for pid,host in [('gemini','generativelanguage.googleapis.com'),('tavily','api.tavily.com'),('jina','s.jina.ai')]:
            self.select(pid)
            with self.subTest(pid=pid),self.upstream(pid) as seen:
                response=self.check(pid)
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['message'],'Bağlantı başarılı')
            self.assertEqual(response.json()['provider_id'],pid)
            self.assertEqual(len(seen),1);req=seen[0]
            self.assertEqual(req.url.host,host)
            self.assertEqual(req.headers['x-goog-api-key'] if pid=='gemini' else req.headers['authorization'],SECRET if pid=='gemini' else 'Bearer '+SECRET)
            self.assertNotIn(SECRET,str(req.url));self.assertNotIn(SECRET,response.text)
            if pid=='gemini':self.assertTrue(req.url.path.endswith(':generateContent'))
        self.assertEqual(self.client.get('/api/state').json(),self.before)
        self.assertEqual(self.client.get('/api/ai/analyses').json(),self.before_ai)

    def test_each_service_preserves_http_error_status_and_never_echoes_upstream(self):
        codes={401:'AUTH_ERROR',403:'ACCESS_DENIED',429:'RATE_LIMIT',407:'PROXY_ERROR',500:'SERVICE_UNAVAILABLE',400:'HTTP_ERROR'}
        for pid in ('gemini','jina','tavily'):
            self.select(pid)
            for status,code in codes.items():
                with self.subTest(pid=pid,status=status),self.upstream(pid,status=status) as seen:
                    response=self.check(pid)
                self.assertEqual(len(seen),1)
                self.assertEqual(response.status_code,502,response.text)
                self.assertEqual(response.json()['code'],code)
                self.assertEqual(response.json()['http_status'],status)
                self.assertIn(MESSAGES[code],response.json()['error'])
                self.assertNotIn(SECRET,response.text)
                if status!=407:self.assertNotIn('Proxy',response.text)

    def test_each_service_preserves_transport_errors_including_wrapped_ssl_dns(self):
        cases=[(httpx.ReadTimeout(SECRET),'TIMEOUT'),(httpx.ConnectTimeout(SECRET),'TIMEOUT'),
               (wrapped(ssl.SSLCertVerificationError(1,SECRET)),'SSL_ERROR'),
               (wrapped(socket.gaierror(socket.EAI_NONAME,SECRET)),'DNS_ERROR'),
               (httpx.ConnectError('proxy word alone is not evidence '+SECRET),'CONNECTION_ERROR'),
               (ConnectionRefusedError(61,SECRET),'CONNECTION_ERROR'),
               (httpx.ProxyError(SECRET),'PROXY_ERROR'),(RuntimeError(SECRET),'UNKNOWN_ERROR')]
        for pid in ('gemini','jina','tavily'):
            self.select(pid)
            for error,code in cases:
                with self.subTest(pid=pid,code=code),self.upstream(pid,error=error) as seen:
                    response=self.check(pid)
                self.assertEqual(len(seen),1)
                self.assertEqual(response.status_code,502,response.text)
                self.assertEqual(response.json()['code'],code)
                self.assertIn(MESSAGES[code],response.json()['error'])
                self.assertNotIn(SECRET,response.text)
                if code!='PROXY_ERROR':self.assertNotIn('Proxy',response.text)

    def test_saved_search_service_is_authoritative_and_survives_reload(self):
        # Jina has a valid stored key too; an unsaved Jina dropdown cannot select it.
        with self.upstream('tavily') as seen:
            rejected=self.check('tavily',{'provider_id':'jina'})
            self.assertEqual(rejected.status_code,409);self.assertEqual(seen,[])
            response=self.check('tavily',{'provider_id':'tavily'})
        self.assertEqual(response.json()['provider'],'Tavily')
        self.assertEqual(seen[0].url.host,'api.tavily.com')
        self.select('jina')
        self.assertEqual(self.client.get('/api/search/settings').json()['provider_id'],'jina')
        self.client.__exit__(None,None,None)
        self.app=create_app(self.root/'test.db',settings_path=self.root/'settings.env')
        self.client=TestClient(self.app).__enter__()
        with self.upstream('jina') as seen: response=self.check('jina')
        self.assertEqual(response.json()['provider'],'Jina AI Search');self.assertEqual(seen[0].url.host,'s.jina.ai')

    def test_stale_ai_provider_or_model_does_not_send_request(self):
        with self.upstream('gemini') as seen:
            for body in ({'provider_id':'groq'},{'provider_model':'changed-model'}):
                self.assertEqual(self.check('gemini',body).status_code,409)
            self.assertEqual(seen,[])

    def test_gemini_http_400_key_error_is_auth_not_proxy(self):
        with self.upstream('gemini',status=400,body={'error':{'message':'API key not valid. '+SECRET}}):response=self.check('gemini')
        self.assertEqual(response.json()['code'],'AUTH_ERROR');self.assertEqual(response.json()['http_status'],400)
        self.assertNotIn(SECRET,response.text)

    def test_malformed_success_cannot_claim_connection_success(self):
        for pid in ('gemini','jina','tavily'):
            self.select(pid)
            with self.upstream(pid,body={'error':SECRET}):response=self.check(pid)
            self.assertNotEqual(response.status_code,200);self.assertNotIn(SECRET,response.text)

    def test_unknown_error_logs_technical_types_frames_but_no_secrets(self):
        stream=io.StringIO();handler=logging.StreamHandler(stream);handler.setFormatter(SafeFormatter())
        logger=logging.getLogger('kongre.desktop');logger.addHandler(handler)
        try:
            with self.upstream('gemini',error=wrapped(RuntimeError(SECRET))):response=self.check('gemini')
            with self.upstream('tavily',error=RuntimeError('Authorization: Bearer '+SECRET)):response=self.check('tavily')
        finally:logger.removeHandler(handler)
        text=stream.getvalue();self.assertIn('RuntimeError',text);self.assertIn('api_transport_failed',text)
        self.assertIn('frames',text);self.assertIn('causes',text);self.assertIn('UNKNOWN_ERROR',text)
        for private in (SECRET,'private.example','Authorization','/Users/'):
            self.assertNotIn(private,text);self.assertNotIn(private,response.text)

    def test_no_proxy_guess_explicit_proxy_and_no_proxy_bypass(self):
        with patch('app.network.getproxies',return_value={}),patch('app.network.proxy_bypass') as bypass:
            options=client_options('https://api.tavily.com')
            self.assertIsNone(options['proxy']);self.assertFalse(options['trust_env']);bypass.assert_not_called()
            self.assertEqual(options['verify'].verify_mode,ssl.CERT_REQUIRED)
        with patch('app.network.getproxies',return_value={'https':'proxy.example:8080'}),patch('app.network.proxy_bypass',return_value=False):
            self.assertEqual(proxy_for('https://s.jina.ai'),'http://proxy.example:8080')
        with patch('app.network.getproxies',return_value={'all':'http://proxy.example:8080'}),patch('app.network.proxy_bypass',return_value=True):
            self.assertIsNone(proxy_for('https://s.jina.ai'))

    def test_analysis_transport_errors_use_same_classifier_without_wrong_retries(self):
        for exc,code in [(wrapped(ssl.SSLCertVerificationError(1,SECRET)),'SSL_ERROR'),
                         (httpx.ProxyError(SECRET),'PROXY_ERROR'),(httpx.ReadTimeout(SECRET),'TIMEOUT')]:
            with patch('httpx.Client.post',side_effect=exc) as request,patch('app.ai_provider.time.sleep') as sleep:
                with self.assertRaises(ProviderError) as caught:get_provider('gemini').analyze([],'',SECRET,'gemini-3.5-flash')
                self.assertEqual(caught.exception.details['code'],code);self.assertEqual(request.call_count,1);sleep.assert_not_called()

if __name__=='__main__':unittest.main()
