import copy
import unittest
from engine import calculate_model,DEFAULT_MATRICES
from app.conjoint import design,fit,synthetic_responses
from app.research_models import compare_models,sensitivity
from app.research_metrics import binary_metrics,kendall,spearman,kappa,ndcg

class ModelTests(unittest.TestCase):
    def test_models_gate_missing_data_no_heuristic_relabel(self):
        d=design();m=fit(d,synthetic_responses(d));ahp=calculate_model(DEFAULT_MATRICES)
        rows=[{'id':str(i),'expert_values':{f'K{k}':i for k in range(1,11)},'ai_values':{f'K{k}':None for k in range(1,11)},'attributes':d['tasks'][0]['alternatives'][i]} for i in (0,1)]
        before=copy.deepcopy(ahp);r=compare_models(rows,ahp,m,minimum_ahp=70,overlap_acknowledged=True)
        self.assertEqual(r['models']['M3']['ranking'],['1']);self.assertEqual(r['models']['M4']['ranking'],[])
        self.assertEqual(compare_models(rows,ahp,minimum_ahp=70,overlap_acknowledged=True)['fallback'],'existing_heuristic')
        with self.assertRaises(ValueError):compare_models(rows,ahp,m,minimum_ahp=70,overlap_acknowledged=False)
        self.assertEqual(ahp,before)
    def test_metrics_ties_abstention_undefined_and_common_ndcg_pool(self):
        self.assertEqual(kendall([1,2,3],[1,2,3]),1);self.assertEqual(spearman([1,2,3],[3,2,1]),-1)
        self.assertIsNone(kendall([1,1],[1,1]));self.assertIsNone(kappa([1,1],[1,1]))
        self.assertEqual(kappa([0,1],[0,1]),1)
        m=binary_metrics([1,0,1,None],[1,0,None,1]);self.assertEqual(m['recall'],.5);self.assertEqual(m['prediction_coverage'],2/3)
        self.assertLess(ndcg([1],3,[3,2,1]),1);self.assertEqual(ndcg([],3,[3,2,1]),0)
    def test_sensitivity_does_not_change_saved_model(self):
        m=calculate_model(DEFAULT_MATRICES);before=copy.deepcopy(m)
        r=sensitivity(m,{f'K{k}':k%2 for k in range(1,11)},'K1',[.1,.4],[{'average':60,'valid':80},{'average':70,'valid':90}])
        self.assertEqual(len(r),4);self.assertEqual(m,before);self.assertNotEqual(r[0]['result']['total'],r[2]['result']['total'])
