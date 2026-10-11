import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app
from app.database import SCHEMA_VERSION
from tests.test_ai import FixtureProvider, TEXT

class TrashTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'db.sqlite'
        self.app=create_app(self.path,settings_path=Path(self.temp.name)/'.env',ai_provider=FixtureProvider())
        self.client=TestClient(self.app).__enter__();self.original=self.client.get('/api/state').json()
        self.c=self.original['congresses'][0];self.cid=self.c['id'];self.mid=self.original['models'][0]['id']
        self.url='/api/congresses/'+self.cid
    def tearDown(self):
        self.client.__exit__(None,None,None);self.temp.cleanup()
    def delete(self):
        return self.client.post(self.url+'/delete',json={'previous_id':self.c['evaluations'][0]['id']})
    def payload(self):
        e=self.c['evaluations'][0]
        return {'model_id':self.mid,'metadata':{k:v for k,v in e['metadata'].items() if k!='sample'},'scale':1,'evaluator':'Test','scores':e['utilities'],'notes':e['notes'],'congress_id':self.cid,'previous_id':e['id']}

    def test_delete_excludes_active_views_and_restore_preserves_entire_history(self):
        self.assertEqual(self.delete().status_code,200)
        self.assertEqual(self.delete().status_code,200)
        self.assertEqual(len(self.client.get('/api/state').json()['congresses']),3)
        self.assertEqual(self.client.get('/api/congresses/trash').json()[0]['id'],self.cid)
        self.assertNotIn(self.c['metadata']['name'],self.client.get('/api/export').text)
        scenario=self.client.post('/api/scenario',json={'model_id':self.mid,'criterion':'K3','target':.2}).json()
        self.assertNotIn(self.cid,[r['id'] for r in scenario['results']])
        with sqlite3.connect(':memory:') as con:
            con.executescript(self.client.get('/api/backup').text)
            self.assertEqual(con.execute('SELECT count(*) FROM congresses').fetchone()[0],4)
            self.assertEqual(con.execute('SELECT count(*) FROM evaluations').fetchone()[0],4)
            self.assertEqual(con.execute('SELECT count(*) FROM congress_deletions').fetchone()[0],1)
        self.assertEqual(self.client.post(self.url+'/restore',json={}).status_code,200)
        self.assertEqual(self.client.post(self.url+'/restore',json={}).status_code,200)
        self.assertEqual(self.client.get('/api/state').json(),self.original)

    def test_stale_delete_and_editing_deleted_record_rejected(self):
        self.assertEqual(self.client.post(self.url+'/delete',json={'previous_id':'stale'}).status_code,409)
        self.assertEqual(self.client.post(self.url+'/delete',json={}).status_code,422)
        self.assertEqual(self.client.get('/api/state').json(),self.original)
        self.delete()
        p=self.payload()
        self.assertEqual(self.client.post('/api/evaluations',json=p).status_code,409)
        p.pop('congress_id');p.pop('previous_id')
        r=self.client.post('/api/evaluations',json=p)
        self.assertEqual(r.status_code,409);self.assertIn('çöp kutusunda',r.json()['error'])
        for action in ('delete','restore'):
            self.assertEqual(self.client.post('/api/congresses/missing/'+action,json={'previous_id':'x'}).status_code,404)

    def test_ai_review_and_defaults_survive_delete_without_mutating_snapshot(self):
        self.client.post('/api/ai/settings',json={'api_key':'test-only','model':'fixture'})
        self.app.state.ai.provider.output['findings'][9].update(value=None,status='not_found',evidence=[])
        a=self.client.post('/api/ai/analyze',json={'sources':[{'kind':'text','content':TEXT}],'transfer_consent':True}).json()
        body={'metadata':{'name':'TEST KONGRESI','edition':'2027','context':a['context']},'evaluator':'Test','decisions':{f'K{i}':{'action':'approve'} for i in range(1,11)}}
        r=self.client.post('/api/ai/analyses/'+a['id']+'/review',json=body)
        self.assertEqual(r.status_code,200,r.text);saved=r.json();self.assertEqual(saved['raw_score'],10)
        with sqlite3.connect(self.path) as con:
            before=con.execute('SELECT data FROM ai_analyses WHERE id=?',(a['id'],)).fetchone()[0]
        self.client.post('/api/congresses/'+saved['id']+'/delete',json={'previous_id':saved['evaluation_id']})
        self.assertTrue(self.client.get('/api/ai/analyses/'+a['id']).json()['review']['saved']['deleted'])
        result=self.client.get('/api/ai/analyses/'+a['id']+'/result').json()
        self.assertEqual(result['scores']['participant_satisfaction']['basis'],'project_default')
        with sqlite3.connect(self.path) as con:
            self.assertEqual(con.execute('SELECT data FROM ai_analyses WHERE id=?',(a['id'],)).fetchone()[0],before)
        another=self.client.post('/api/ai/analyze',json={'sources':[{'kind':'text','content':TEXT}],'transfer_consent':True}).json()
        body.update(congress_id=saved['id'],previous_id=saved['evaluation_id'])
        self.assertEqual(self.client.post('/api/ai/analyses/'+another['id']+'/review',json=body).status_code,409)

    def test_trash_persists_across_restart_and_v2_migration_keeps_rows(self):
        self.delete()
        with TestClient(create_app(self.path)) as client:
            self.assertEqual(len(client.get('/api/state').json()['congresses']),3)
            self.assertEqual(len(client.get('/api/congresses/trash').json()),1)
        self.client.post(self.url+'/restore',json={})
        with sqlite3.connect(self.path) as con:
            tables=['models','congresses','evaluations','ai_analyses','ai_reviews']
            before={t:con.execute('SELECT * FROM '+t+' ORDER BY id').fetchall() for t in tables}
            con.execute('DROP TABLE congress_deletions');con.execute('PRAGMA user_version=2')
        with TestClient(create_app(self.path)) as client:
            self.assertEqual(client.get('/api/state').json(),self.original)
            self.assertEqual(client.get('/api/health').json()['schema_version'],SCHEMA_VERSION)
        with sqlite3.connect(self.path) as con:
            self.assertEqual(before,{t:con.execute('SELECT * FROM '+t+' ORDER BY id').fetchall() for t in tables})

if __name__=='__main__':unittest.main()
