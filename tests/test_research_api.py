import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app

class ResearchAPITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.app=create_app(self.root/'test.db',settings_path=self.root/'.env');self.client=TestClient(self.app).__enter__()
    def tearDown(self):self.client.__exit__(None,None,None);self.temp.cleanup()
    def test_opt_in_isolation_synthetic_fit_and_off(self):
        c=self.client;before=c.get('/api/state').json()
        self.assertFalse(c.get('/api/research/status').json()['enabled']);self.assertFalse(self.app.state.research.path.exists())
        self.assertEqual(c.post('/api/research/studies',json={'title':'Demo'}).status_code,409)
        c.post('/api/research/settings',json={'enabled':True})
        s=c.post('/api/research/studies',json={'title':'Sentetik','kind':'synthetic'}).json()
        fitted=c.post('/api/research/studies/'+s['id']+'/estimate',json={});self.assertEqual(fitted.status_code,200,fitted.text)
        self.assertTrue(fitted.json()['model']['converged']);self.assertEqual(fitted.json()['model']['data_origin'],'synthetic')
        self.assertEqual(before,c.get('/api/state').json())
        self.assertEqual(c.get('/research.js').status_code,200)
        c.post('/api/research/settings',json={'enabled':False});self.assertEqual(c.get('/api/research/studies/'+s['id']).status_code,409)
    def test_real_consent_and_duplicate_and_insufficient(self):
        c=self.client;c.post('/api/research/settings',json={'enabled':True})
        body={'title':'Kurgu izin testi','kind':'research'}
        self.assertEqual(c.post('/api/research/studies',json=body).status_code,422)
        body.update(collection_authorized=True,approval_reference='TEST',consent_version='TEST-v1',consent_text='Kurgu test onamı.',data_management_reference='TEST-plan')
        s=c.post('/api/research/studies',json=body).json();url='/api/research/studies/'+s['id']
        choice={'respondent':'test_001','task':'1','choice':0}
        self.assertEqual(c.post(url+'/responses',json=choice).status_code,422)
        choice.update(consent=True,consent_version='TEST-v1');self.assertEqual(c.post(url+'/responses',json=choice).status_code,200)
        self.assertEqual(c.post(url+'/responses',json=choice).status_code,409)
        self.assertEqual(c.post(url+'/estimate',json={}).status_code,422)
    def test_offline_experiment_saved_separately(self):
        from tests.test_research_experiments import dataset
        c=self.client;c.post('/api/research/settings',json={'enabled':True})
        mid=c.get('/api/state').json()['models'][0]['id']
        r=c.post('/api/research/experiments',json={'dataset':dataset(mid),'minimum_ahp':70,'overlap_acknowledged':True,'protocol_rationale':'Sentetik teknik test protokolü.'})
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['manifest']['live_api_calls'],0)
        self.assertTrue((self.app.state.research.path.with_suffix('.runs')/(r.json()['run_id']+'.json')).is_file())
