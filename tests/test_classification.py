import copy
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from pypdf import PdfReader
from app.database import Database, SCHEMA_VERSION
from app.main import create_app
from engine import classify, calculate_model, score, DEFAULT_MATRICES
from tests.test_ai import FixtureProvider, TEXT

LABELS = {'Geçersiz':'Düşük Uygunluk', 'Ortalama':'Orta Uygunluk', 'Geçerli':'Yüksek Uygunluk'}

class ClassificationTests(unittest.TestCase):
    def test_boundaries_custom_thresholds_and_incomplete(self):
        for thresholds in ({'average':70,'valid':90}, {'average':40,'valid':75}, {'average':0,'valid':100}):
            low,high=thresholds.values()
            for value,expected in [(low-1e-8,'Düşük Uygunluk'),(low,'Orta Uygunluk'),
                                   (high-1e-8,'Orta Uygunluk'),(high,'Yüksek Uygunluk'),(100,'Yüksek Uygunluk')]:
                self.assertEqual(classify(value,thresholds),expected)
        m=calculate_model(DEFAULT_MATRICES)
        utilities={f'K{i}':1 for i in range(1,11)};utilities['K10']=None
        self.assertEqual(score(m['weights'],utilities,m['thresholds'])['status'],'Eksik veri')

    def test_migrate_history_reports_reviews_exports_and_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'history.db';env=Path(tmp)/'.env'
            with TestClient(create_app(path,settings_path=env,ai_provider=FixtureProvider())) as client:
                client.post('/api/ai/settings',json={'api_key':'test-only','model':'test'})
                report=client.post('/api/ai/analyze',json={'sources':[{'kind':'text','content':TEXT}], 'transfer_consent':True}).json()
                base='/api/ai/analyses/'+report['id']
                self.assertEqual(report['analysis']['result']['status'],'Yüksek Uygunluk')
                self.assertEqual(report['analysis']['report']['ahp_result']['status'],'Yüksek Uygunluk')
                body={'metadata':{'name':'Sınıflandırma testi','edition':'2027','context':report['context']},
                      'evaluator':'Test','decisions':{f'K{i}':{'action':'approve'} for i in range(1,11)}}
                saved=client.post(base+'/review',json=body).json()
                # Deleted history must migrate too and remain restorable.
                client.post(base+'/delete',json={})
                client.post('/api/congresses/'+saved['id']+'/delete',json={'previous_id':saved['evaluation_id']})
            # Simulate a v4 backup, including words in source/user text that must not change.
            reverse={v:k for k,v in LABELS.items()}
            expected={}
            with sqlite3.connect(path) as con:
                for table in ('evaluations','ai_analyses','ai_reviews'):
                    for rid,raw in con.execute('SELECT id,data FROM '+table).fetchall():
                        data=json.loads(raw)
                        data['migration_test_note']='Geçerli Ortalama Geçersiz'
                        data['migration_test_source']={'result':{'status':'Geçerli'}}
                        expected[table,rid]=copy.deepcopy(data)
                        if table=='evaluations':results=[data['result']]
                        elif table=='ai_reviews':results=[data['saved']['result']]
                        else:results=[data['analysis']['result'],data['analysis']['report']['ahp_result']]
                        for result in results:result['status']=reverse[result['status']]
                        con.execute('UPDATE '+table+' SET data=? WHERE id=?',(json.dumps(data,ensure_ascii=False),rid))
                con.execute('PRAGMA user_version=4')
            with TestClient(create_app(path,settings_path=env)) as client:
                migrated=client.get(base).json()
                self.assertTrue(migrated['deleted'])
                self.assertEqual(migrated['status'],'ready')
                self.assertEqual(migrated['analysis']['result']['status'],'Yüksek Uygunluk')
                self.assertEqual(migrated['review']['saved']['result']['status'],'Yüksek Uygunluk')
                self.assertEqual(client.get(base+'/result').json()['ahp_result']['status'],'Yüksek Uygunluk')
                pdf=client.get(base+'/pdf');self.assertEqual(pdf.status_code,200)
                text='\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
                self.assertIn('Yüksek Uygunluk',text)
                client.post('/api/congresses/'+saved['id']+'/restore',json={})
                labels={e['result']['status'] for c in client.get('/api/state').json()['congresses'] for e in c['evaluations']}
                self.assertEqual(labels,set(LABELS.values()))
                csv=client.get('/api/export').text
                for label in LABELS.values():self.assertIn(label,csv)
                for label in LABELS:self.assertNotIn(';'+label+';',csv)
                state=client.get('/api/state').json()
                scenarios=client.post('/api/scenario',json={'model_id':state['models'][0]['id'],'criterion':'K3','target':.2}).json()
                for item in scenarios['results']:
                    self.assertIn(item['before']['status'],LABELS.values())
                    self.assertIn(item['after']['status'],LABELS.values())
                backup=client.get('/api/backup').text
            with sqlite3.connect(path) as con:
                self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION)
                for (table,rid),value in expected.items():
                    actual=json.loads(con.execute('SELECT data FROM '+table+' WHERE id=?',(rid,)).fetchone()[0])
                    self.assertEqual(actual,value) # Only the classification changed; scores/evidence/IDs preserved.
                before=list(con.iterdump())
            db=Database(path);db.initialize();db.close()
            with sqlite3.connect(path) as con:self.assertEqual(list(con.iterdump()),before)
            restored=Path(tmp)/'restored.db'
            with sqlite3.connect(restored) as con:con.executescript(backup)
            with TestClient(create_app(restored,settings_path=env)) as client:
                restored_state=client.get('/api/state').json()
                self.assertNotEqual(restored_state.pop('database_id'),state.pop('database_id'))
                self.assertEqual(restored_state,state)

    def test_migration_failure_rolls_back_all_labels_and_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'broken.db'
            with TestClient(create_app(path)):pass
            with sqlite3.connect(path) as con:
                rid,raw=con.execute('SELECT id,data FROM evaluations LIMIT 1').fetchone()
                data=json.loads(raw);data['result']['status']='Geçerli'
                con.execute('UPDATE evaluations SET data=? WHERE id=?',(json.dumps(data),rid))
                mid=con.execute('SELECT id FROM models LIMIT 1').fetchone()[0]
                con.execute('INSERT INTO ai_analyses VALUES (?,?,?,?,?)',('broken',mid,'failed','{invalid','2026-10-03'))
                con.execute('PRAGMA user_version=4')
            db=Database(path)
            try:
                with self.assertRaises(json.JSONDecodeError):db.initialize()
            finally:db.close()
            with sqlite3.connect(path) as con:
                self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0],4)
                self.assertEqual(json.loads(con.execute('SELECT data FROM evaluations WHERE id=?',(rid,)).fetchone()[0])['result']['status'],'Geçerli')
