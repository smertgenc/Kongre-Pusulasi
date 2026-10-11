import copy
import unittest
from app.conjoint import design,fit,synthetic_responses,encode,probabilities,DEFAULT_ATTRIBUTES

class ConjointTests(unittest.TestCase):
    def test_design_seed_reference_rank(self):
        d=design();self.assertEqual(d,design());self.assertEqual(d['rank'],d['parameters'])
        self.assertEqual(encode(d['attributes'],{a['id']:a['levels'][0] for a in d['attributes']}),[0]*5)
        d=design(forbidden=[{'fee':'Yüksek','format':'Çevrim içi'}])
        self.assertTrue(all(not (a['fee']=='Yüksek' and a['format']=='Çevrim içi') for t in d['tasks'] for a in t['alternatives']))
    def test_validation_and_convergence(self):
        with self.assertRaises(ValueError):design(attributes=[DEFAULT_ATTRIBUTES[0]]*2)
        d=design();rows=synthetic_responses(d,3)
        for data in (rows[:2],rows+[rows[0]]):
            with self.assertRaises(ValueError):fit(d,data)
        with self.assertRaises(ValueError):fit(d,rows,max_iter=0)
    def test_recover_known_utilities_and_holdout_is_not_trained(self):
        d=design();beta=[-.8,-1.4,.5,1.1,.6];rows=synthetic_responses(d,n=140,beta=beta)
        m=fit(d,rows)
        for a,b in zip(m['beta'],beta):self.assertAlmostEqual(a,b,delta=.25)
        self.assertAlmostEqual(sum(m['importance'].values()),1)
        changed=copy.deepcopy(rows);held={t['id'] for t in d['tasks'] if t['split']=='holdout'}
        for r in changed:
            if r['task'] in held:r['choice']=(r['choice']+1)%3
        self.assertEqual(m['beta'],fit(d,changed)['beta'])
        self.assertAlmostEqual(sum(probabilities(m['beta'],[encode(d['attributes'],p) for p in d['tasks'][0]['alternatives']])),1)
