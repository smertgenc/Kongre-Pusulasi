import copy
import unittest
from app.research_experiments import ExperimentInput,run_experiment
from engine import calculate_model,DEFAULT_MATRICES

def dataset(mid):
    rows=[]
    for i in range(3):
        values={f'K{k}':int(k<=5+i) for k in range(1,11)}
        rows.append({'id':str(i),'congress_id':'synthetic-'+str(i),'edition':'2027','decision_date':'2026-10-10','criteria_profile':'test','policy':'congress-evidence-v1','context':'test','partition':'test','attributes':{},'expert_values':values,'ai_values':values.copy(),'raters':{'r1':values,'r2':values},'ai':{'provider':'fixture','model':'fixture','prompt_version':'fixture-v1'},'relevance':float(i),'decision_rationale':'Sentetik doğrulama, gerçek bilimsel sonuç değildir.'})
    return {'version':'synthetic-v1','origin':'synthetic','ahp_model_id':mid,'records':rows}
class ExperimentTests(unittest.TestCase):
    def test_metrics_and_reproducible_manifest(self):
        m={**calculate_model(DEFAULT_MATRICES),'id':'m1','version':1};r=ExperimentInput(dataset=dataset('m1'),minimum_ahp=70.,overlap_acknowledged=True,protocol_rationale='Sentetik teknik test protokolü.')
        before=copy.deepcopy(m);a=run_experiment(r,m);b=run_experiment(r,m)
        self.assertEqual(a['metrics']['ai_criteria']['f1_positive'],1);self.assertEqual(a['metrics']['expert_ai_paired_scores']['spearman'],1)
        self.assertEqual(a['manifest']['dataset_hash'],b['manifest']['dataset_hash']);self.assertEqual(a['manifest']['live_api_calls'],0)
        self.assertEqual(a['metrics'],b['metrics']);self.assertEqual(m,before)
    def test_series_leak_and_secret_fields_rejected(self):
        d=dataset('m');d['records'][0]['partition']='train';d['records'][0]['congress_id']=d['records'][1]['congress_id']
        for value in (d,{**dataset('m'),'api_key':'fake-do-not-store'}):
            with self.assertRaises(ValueError):ExperimentInput(dataset=value,minimum_ahp=70.,overlap_acknowledged=True,protocol_rationale='Sentetik teknik test protokolü.')
        d=dataset('m');d['records'][0]['sources']=[{'label':'Test','url':'https://example.test/?api_key=forbidden','content_hash':'a'*64,'retrieved_at':'2026-10-10T00:00:00Z'}]
        with self.assertRaises(ValueError):ExperimentInput(dataset=d,minimum_ahp=70.,overlap_acknowledged=True,protocol_rationale='Sentetik teknik test protokolü.')
    def test_frozen_manifest_without_python_source_files(self):
        import tempfile,json
        from pathlib import Path
        from app.research_provenance import code_hashes
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'VERSION').write_text('test')
            with self.assertRaises(ValueError):code_hashes(p)
            hashes={k:'a'*64 for k in ('engine.py','app/conjoint.py','app/research_experiments.py')}
            (p/'research-code-manifest.json').write_text(json.dumps({'version':'test','hashes':hashes}))
            self.assertEqual(code_hashes(p),hashes)
