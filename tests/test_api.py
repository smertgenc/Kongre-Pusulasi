import copy
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi.testclient import TestClient
import legacy_server
from app.main import create_app
from app.database import Database, SCHEMA_VERSION
from app.schemas import EvaluationInput
from app.services import ConflictError

class APITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'test.db'
        self.app = create_app(self.path)
        self.client = TestClient(self.app).__enter__()
        self.initial = self.client.get('/api/state').json()
        self.mid = self.initial['models'][0]['id']

    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.temp.cleanup()

    def payload(self):
        return {'model_id':self.mid, 'metadata':{'name':'API Kongresi','edition':'2027','context':'Test profili'},
                'scale':1, 'evaluator':'API test', 'scores':{f'K{i}':1 for i in range(1,11)},
                'notes':{f'K{i}':'Doğrulama notu' for i in range(1,11)}}

    def test_static_health_and_openapi(self):
        for path in ('/','/app.js','/compare.js','/styles.css','/openapi.json'):
            self.assertEqual(self.client.get(path).status_code,200)
        self.assertEqual(self.client.get('/api/health').json()['backend'],'fastapi')
        self.assertIn('EvaluationInput',self.client.get('/openapi.json').json()['components']['schemas'])

    def test_actual_excel_outputs(self):
        expected={'A Kongresi':73.38331160365063,'B kongresi':74.81644136416664,
                  'C Kongresi':94.64248953544231,'D kongresi':40.14684690866672}
        for c in self.initial['congresses']:
            self.assertAlmostEqual(c['evaluations'][0]['result']['total'],expected[c['metadata']['name']],places=9)

    def test_save_history_duplicate_and_stale(self):
        p=self.payload();r=self.client.post('/api/evaluations',json=p)
        self.assertEqual(r.status_code,201,r.text)
        self.assertEqual(self.client.post('/api/evaluations',json=p).status_code,409)
        result=r.json();p.update(congress_id=result['id'],previous_id=result['evaluation_id'])
        p['scores']['K1']=None
        response=self.client.post('/api/evaluations',json=p)
        self.assertEqual(response.status_code,201,response.text)
        self.assertIsNone(response.json()['result']['total'])
        self.assertEqual(self.client.post('/api/evaluations',json=p).status_code,409)
        c=next(c for c in self.client.get('/api/state').json()['congresses'] if c['id']==result['id'])
        self.assertEqual(len(c['evaluations']),2)
        self.assertEqual(c['evaluations'][1]['result']['total'],100)

    def test_multiple_participation_formats_survive_save_and_edit_history(self):
        p=self.payload();p['metadata']['format']='Yüz yüze · Çevrim içi'
        saved=self.client.post('/api/evaluations',json=p).json()
        p.update(congress_id=saved['id'],previous_id=saved['evaluation_id'])
        p['metadata']['format']='Çevrim içi · Hibrit'
        self.assertEqual(self.client.post('/api/evaluations',json=p).status_code,201)
        c=next(c for c in self.client.get('/api/state').json()['congresses'] if c['id']==saved['id'])
        self.assertEqual(c['metadata']['format'],'Çevrim içi · Hibrit')
        self.assertEqual(c['evaluations'][1]['metadata']['format'],'Yüz yüze · Çevrim içi')

    def test_strict_validation_and_no_partial_writes(self):
        for value in [True,'1',-1,2,0.5]:
            p=self.payload();p['scores']['K1']=value
            r=self.client.post('/api/evaluations',json=p)
            self.assertEqual(r.status_code,422,r.text)
            self.assertIsInstance(r.json()['error'],str)
        for patch in [{'evaluator':''},{'model_id':'unknown'},{'metadata':{'name':'n','edition':'e','context':'x','website':'javascript:alert(1)'}}]:
            p=self.payload();p.update(patch)
            self.assertIn(self.client.post('/api/evaluations',json=p).status_code,(422,404))
        self.assertEqual(len(self.client.get('/api/state').json()['congresses']),4)

    def test_model_publish_and_conflict(self):
        m=self.initial['models'][0]
        p={'base_id':m['id'],'name':'Yeni model','matrices':m['matrices'],'thresholds':m['thresholds']}
        self.assertEqual(self.client.post('/api/models/preview',json=p).status_code,200)
        r=self.client.post('/api/models',json=p)
        self.assertEqual(r.status_code,201,r.text)
        self.assertEqual(r.json()['version'],2)
        self.assertEqual(self.client.post('/api/models',json=p).status_code,409)
        self.assertEqual(self.client.get('/api/state').json()['congresses'],self.initial['congresses'])

    def test_inconsistent_model_not_published(self):
        m=self.initial['models'][0]
        p={'base_id':m['id'],'name':'Tutarsız','matrices':copy.deepcopy(m['matrices'])}
        p['matrices']['root']=[[1,9,1/9],[1/9,1,9],[9,1/9,1]]
        self.assertFalse(self.client.post('/api/models/preview',json=p).json()['consistent'])
        self.assertEqual(self.client.post('/api/models',json=p).status_code,422)
        self.assertEqual(len(self.client.get('/api/state').json()['models']),1)

    def test_scenario_read_only(self):
        r=self.client.post('/api/scenario',json={'model_id':self.mid,'criterion':'K3','target':.2})
        self.assertEqual(r.status_code,200,r.text)
        a=next(c for c in r.json()['results'] if c['name']=='A Kongresi')
        self.assertAlmostEqual(a['after']['total'],60.88112435509699)
        self.assertEqual(self.initial,self.client.get('/api/state').json())

    def test_csv_and_backup(self):
        csv=self.client.get('/api/export')
        self.assertTrue(csv.text.startswith('\ufeff'))
        self.assertIn('A Kongresi',csv.text)
        with sqlite3.connect(':memory:') as con:
            con.executescript(self.client.get('/api/backup').text)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM evaluations').fetchone()[0],4)

    def test_boundary_and_invalid_json(self):
        self.assertEqual(self.client.post('/api/evaluations',json=self.payload(),headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.get('/api/state',headers={'Host':'evil.example'}).status_code,403)
        self.assertEqual(self.client.post('/api/evaluations',content='x',headers={'Content-Type':'text/plain'}).status_code,415)
        self.assertEqual(self.client.post('/api/evaluations',content='{',headers={'Content-Type':'application/json'}).status_code,422)
        self.assertEqual(self.client.post('/api/evaluations',content='x'*200000,headers={'Content-Type':'application/json'}).status_code,413)

    def test_concurrent_revision_check(self):
        result=self.client.post('/api/evaluations',json=self.payload()).json()
        p=self.payload();p.update(congress_id=result['id'],previous_id=result['evaluation_id'])
        def write():
            try:
                self.app.state.service.save_evaluation(EvaluationInput.model_validate(p))
                return 'saved'
            except ConflictError: return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(lambda _:write(),range(2))),['saved','conflict'])

class MigrationTests(unittest.TestCase):
    def test_legacy_database_and_state_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            old=legacy_server.DB_PATH
            try:
                legacy_server.DB_PATH=Path(temp)/'legacy.db'
                legacy_server.initialize()
                original=legacy_server.state()
                with sqlite3.connect(str(legacy_server.DB_PATH)) as con:
                    before={t:con.execute('SELECT * FROM '+t+' ORDER BY id').fetchall() for t in ('models','congresses','evaluations')}
                with TestClient(create_app(legacy_server.DB_PATH)) as client:
                    migrated=client.get('/api/state').json()
                self.assertEqual(migrated.pop('logos'),{})
                self.assertRegex(migrated.pop('database_id'),r'^[a-f0-9]{32}$')
                self.assertEqual(migrated,original)
                with sqlite3.connect(str(legacy_server.DB_PATH)) as con:
                    after={t:con.execute('SELECT * FROM '+t+' ORDER BY id').fetchall() for t in before}
                    self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION)
                self.assertEqual(before,after)
            finally: legacy_server.DB_PATH=old

    def test_newer_schema_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'future.db'
            with sqlite3.connect(path) as con:con.execute('PRAGMA user_version=99')
            db=Database(path)
            try:
                with self.assertRaises(RuntimeError):db.initialize()
            finally:db.close()

if __name__=='__main__':unittest.main()
