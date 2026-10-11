import copy
import unittest
from tests import test_policy

class CPCITests(unittest.TestCase):
    def test_contradictions_do_not_score_positive_or_negative(self):
        for q in ('The 2027 proceedings are not indexed in CPCI.', 'CPCI indexing: not currently indexed.', 'CPCI kapsamında değil.', 'CPCI indekslenmemiştir.'):
            f=test_policy.PolicyTests();f.setUp();f.finding('K1',q)
            a=f.analyze()
            self.assertIsNone(a['utilities']['K1']);self.assertEqual(a['findings'][0]['status'],'conflict')
            self.assertEqual(a['findings'][0]['basis'],'review_required')
            self.assertIsNone(a['raw_score']);self.assertIsNone(a['result']['total'])

class ScientificTests(unittest.TestCase):
    def analyze(self, fixture):
        from app.ai_rules import validate_evidence
        from app.ai_schemas import ProviderOutput
        from app.scientific_policy import apply_scientific_policy
        return apply_scientific_policy(validate_evidence(ProviderOutput.model_validate(fixture.output),fixture.sources,fixture.model),fixture.sources,fixture.model,'2026-10-10')

    def test_unknown_including_satisfaction_and_original_weights(self):
        f=test_policy.PolicyTests();f.setUp();before=copy.deepcopy(f.model);a=self.analyze(f)
        self.assertEqual(set(a['utilities'].values()),{None});self.assertEqual(a['result']['upper'],100)
        self.assertEqual(a['result']['lower'],0);self.assertEqual(f.model,before)
        self.assertEqual(a['report']['policy_version'],'congress-evidence-v1')

    def test_cpci_identity_and_old_edition(self):
        from app.scientific_policy import cpci_identity
        meta={'name':'Test Congress','edition':'2027'}
        for q,expected in [('Test Congress 2026 proceedings indexed CPCI ISBN 978-1234567890.','conflict'),('Test Congress 2027 proceedings indexed CPCI.','missing'),('Test Congress 2027 proceedings indexed CPCI DOI 10.1234/abc.','matched')]:
            self.assertEqual(cpci_identity({'evidence':[{'quote':q}]},meta),expected)

    def test_online_location_is_not_negative(self):
        f=test_policy.PolicyTests();f.setUp();f.finding('K4','This congress is entirely online.')
        f.output['facts']=[{'field':'format','value':'online','evidence':f.output['findings'][3]['evidence']}]
        a=self.analyze(f);self.assertEqual(a['findings'][4]['state'],'not_applicable');self.assertIsNone(a['utilities']['K5'])
        f.output['facts'][0]['value']='Hibrit · Çevrim içi';self.assertNotEqual(self.analyze(f)['findings'][4]['state'],'not_applicable')

    def test_known_matrix_hierarchy_and_invalid_inputs(self):
        from engine import matrix_result,calculate_model,DEFAULT_MATRICES,score
        m=matrix_result([[1,2,4],[.5,1,2],[.25,.5,1]])
        for x,y in zip(m['weights'],[4/7,2/7,1/7]):self.assertAlmostEqual(x,y)
        self.assertAlmostEqual(m['cr'],0);h=calculate_model(DEFAULT_MATRICES);self.assertAlmostEqual(sum(h['weights'].values()),1)
        self.assertAlmostEqual(h['weights']['K1'],h['results']['root']['weights'][0]*h['results']['A']['weights'][0])
        for value in (-1,float('nan'),True):
            with self.assertRaises(ValueError):matrix_result([[1,value,1],[1,1,1],[1,1,1]])
        values={f'K{i}':i%2 for i in range(1,11)};self.assertEqual(score(h['weights'],values,h['thresholds']),score(h['weights'],values,h['thresholds']))

class ScientificAPITests(unittest.TestCase):
    def test_scientific_policy_persists_and_old_analysis_stays_same(self):
        from tests.test_ai import AITests,TEXT
        f=AITests();f.setUp()
        try:
            old=f.analyze();old_snapshot=copy.deepcopy(old['analysis'])
            for finding in f.provider.output['findings']:finding.update(value=None,status='not_found',confidence=0,evidence=[])
            new=f.client.post('/api/ai/analyze',json={'model_id':f.mid,'scoring_policy':'scientific','sources':[{'kind':'text','content':TEXT}],'transfer_consent':True})
            self.assertEqual(new.status_code,201,new.text);d=new.json();self.assertEqual(d['status'],'ready')
            self.assertIsNone(d['analysis']['utilities']['K10']);self.assertIsNone(d['analysis']['result']['total'])
            self.assertEqual(d['method']['policy_version'],'congress-evidence-v1')
            self.assertEqual(f.client.get('/api/ai/analyses/'+old['id']).json()['analysis'],old_snapshot)
            self.assertEqual(f.client.get('/api/ai/analyses/'+d['id']+'/pdf').status_code,200)
            body=f.review_body();body['metadata']['context']=d['context'];body['decisions']={f'K{i}':{'action':'unknown'} for i in range(1,11)}
            reviewed=f.client.post('/api/ai/analyses/'+d['id']+'/review',json=body);self.assertEqual(reviewed.status_code,200,reviewed.text)
            e=next(c for c in f.client.get('/api/state').json()['congresses'] if c['id']==reviewed.json()['id'])['evaluations'][0]
            self.assertEqual(e['criteria_profile'],'congress-source-evidence-v1');self.assertEqual(set(e['criterion_states'].values()),{'unknown'})
        finally:f.tearDown()
