import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
import engine
import server

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.model=engine.calculate_model(copy.deepcopy(engine.DEFAULT_MATRICES))
        self.fixtures=json.loads((Path(__file__).parent/'analiz/hesaplama_sonuclari.json').read_text())
    def test_excel_regression(self):
        for f in self.fixtures['congresses']:
            utilities=dict(zip([c[0] for c in engine.CRITERIA],f['inputs']))
            r=engine.score(self.model['weights'],utilities,self.model['thresholds'])
            self.assertAlmostEqual(r['total'],f['expected'],places=10)
            self.assertEqual(r['status'],f['status'])
    def test_eigenvalue_and_global_sum(self):
        self.assertAlmostEqual(self.model['results']['root']['cr'],.025054971377961043,places=10)
        self.assertAlmostEqual(sum(self.model['weights'].values()),1)
    def test_fourth_column_is_included(self):
        a=[[1,1,1,2],[1,1,1,1],[1,1,1,1],[.5,1,1,1]]
        r=engine.matrix_result(a)
        expected=(1/3.5+1/4+1/4+2/5)/4
        self.assertAlmostEqual(r['weights'][0],expected)
        self.assertNotAlmostEqual(r['weights'][0],r['weights'][1])
        self.assertTrue(r['consistent'])
    def test_missing_not_zero(self):
        values={c[0]:1 for c in engine.CRITERIA}; values['K1']=None
        r=engine.score(self.model['weights'],values,self.model['thresholds'])
        self.assertIsNone(r['total']);self.assertEqual(r['status'],'Eksik veri')
        self.assertAlmostEqual(r['upper'],100)
        self.assertAlmostEqual(r['lower'],70.07342345433335)
    def test_all_binary_patterns_bounded_and_monotonic(self):
        from itertools import product
        for p in product([0,1],repeat=10):
            u=dict(zip([c[0] for c in engine.CRITERIA],p));r=engine.score(self.model['weights'],u,self.model['thresholds'])
            self.assertTrue(0<=r['total']<=100)
            self.assertAlmostEqual(sum(r['contributions'].values()),r['total'])
            u['K1']=1
            self.assertGreaterEqual(engine.score(self.model['weights'],u,self.model['thresholds'])['total'],r['total']-1e-12)
    def test_invalid_inputs(self):
        for val in [-1,1.1,float('nan'),True,'1']:
            u={c[0]:1 for c in engine.CRITERIA};u['K2']=val
            with self.assertRaises(ValueError):engine.score(self.model['weights'],u,self.model['thresholds'])
        a=copy.deepcopy(engine.DEFAULT_MATRICES);a['root'][0][1]=0
        with self.assertRaises(ValueError):engine.calculate_model(a)
    def test_inconsistent_matrix(self):
        self.assertFalse(engine.matrix_result([[1,9,1/9],[1/9,1,9],[9,1/9,1]])['consistent'])
    def test_thresholds(self):
        for v,s in [(69.999999,'Düşük Uygunluk'),(70,'Orta Uygunluk'),(89.99999,'Orta Uygunluk'),(90,'Yüksek Uygunluk')]:
            self.assertEqual(engine.classify(v,self.model['thresholds']),s)
    def test_scenario_does_not_mutate_weights(self):
        original=copy.deepcopy(self.model['weights'])
        w=engine.scenario_weights(original,'K3',.2)
        self.assertEqual(original,self.model['weights']);self.assertAlmostEqual(sum(w.values()),1)
        u=dict(zip([c[0] for c in engine.CRITERIA],self.fixtures['congresses'][0]['inputs']))
        self.assertAlmostEqual(engine.score(w,u,self.model['thresholds'])['total'],60.88112435509699)

class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.original=server.DB_PATH
        server.DB_PATH=Path(self.temp.name)/'test.db';server.initialize()
        self.state=server.state();self.mid=self.state['models'][0]['id']
    def tearDown(self):
        server.DB_PATH=self.original;self.temp.cleanup()
    def payload(self):
        return {'model_id':self.mid,'metadata':{'name':'Test Kongresi','edition':'2026','context':'Aynı bütçe ve alan'},'scale':1,'evaluator':'Test',
                'scores':{c[0]:1 for c in engine.CRITERIA},'notes':{c[0]:'Test kanıtı' for c in engine.CRITERIA}}
    def test_save_reopen_and_history(self):
        p=self.payload();r=server.save_evaluation(p)
        p.update(congress_id=r['id'],previous_id=r['evaluation_id']);p['scores']['K1']=0
        server.save_evaluation(p)
        c=next(c for c in server.state()['congresses'] if c['id']==r['id'])
        self.assertEqual(len(c['evaluations']),2)
        self.assertEqual(c['evaluations'][1]['result']['total'],100)
        self.assertAlmostEqual(c['evaluations'][0]['result']['total'],70.07342345433335)
    def test_duplicate_rejected(self):
        p=self.payload();server.save_evaluation(p)
        with self.assertRaises(sqlite3.IntegrityError):server.save_evaluation(p)
    def test_stale_update_rejected(self):
        p=self.payload();r=server.save_evaluation(p);p.update(congress_id=r['id'],previous_id='wrong')
        with self.assertRaises(ValueError):server.save_evaluation(p)
    def test_evidence_required_and_partial_allowed(self):
        p=self.payload();p['notes']['K1']=''
        with self.assertRaises(ValueError):server.save_evaluation(p)
        p['scores']['K1']=None
        r=server.save_evaluation(p);self.assertIsNone(r['result']['total'])
    def test_graded_scores_normalized(self):
        p=self.payload();p['scale']=5;p['scores']={c[0]:4 for c in engine.CRITERIA}
        r=server.save_evaluation(p);self.assertAlmostEqual(r['result']['total'],80)
    def test_seed_idempotent_and_backup_restores(self):
        server.initialize();self.assertEqual(len(server.state()['congresses']),4)
        with server.connect() as con: dump='\n'.join(con.iterdump())
        with sqlite3.connect(':memory:') as con:
            con.executescript(dump)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM evaluations').fetchone()[0],4)
    def test_date_and_url_validation(self):
        for fields in [{'start_date':'2026-04-03','end_date':'2026-04-02'},{'website':'javascript:alert(1)'},{'start_date':'wrong'}]:
            p=self.payload();p['metadata'].update(fields)
            with self.assertRaises(ValueError):server.save_evaluation(p)

if __name__=='__main__':unittest.main(verbosity=2)
