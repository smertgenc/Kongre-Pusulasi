"""Project rules exercised against missing, conflicting and malformed evidence."""
import copy
import unittest
from app.ai_method import method_snapshot
from app.ai_provider import analysis_instructions
from app.ai_schemas import ProviderOutput
from app.ai_rules import validate_evidence
from app.congress_policy import apply_policy, policy_definitions
from engine import calculate_model, DEFAULT_MATRICES

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.model={**calculate_model(DEFAULT_MATRICES),'id':'excel','version':1,'name':'Excel'}
        self.output={'facts':[],'findings':[{'criterion':f'K{i}','value':None,'status':'not_found','confidence':0,'explanation':'Kaynak bulunamadı.','evidence':[]} for i in range(1,11)]}
        self.sources=[{'id':'S1','label':'Kongre belgesi','url':'https://conference.example','retrieved_at':'2026-09-30T10:00:00Z','segments':[{'id':'1','page':2,'text':''}]}]

    def finding(self, code, quote, value=True, confidence=.9, status='detected'):
        self.sources[0]['segments'][0]['text']+=' '+quote
        self.output['findings'][int(code[1:])-1].update(value=value,status=status,confidence=confidence,
            explanation='Kaynak metninin anlamsal değerlendirmesi.',evidence=[{'source_id':'S1','segment_id':'1','quote':quote}])

    def analyze(self):
        return apply_policy(validate_evidence(ProviderOutput.model_validate(self.output),self.sources,self.model),self.sources,self.model,'2026-09-30')

    def test_all_missing_is_binary_with_honest_default_and_original_weights(self):
        before=copy.deepcopy(self.model)
        a=self.analyze()
        self.assertEqual(a['raw_score'],1)
        self.assertEqual(a['utilities'],{f'K{i}':int(i==10) for i in range(1,11)})
        self.assertAlmostEqual(a['result']['total'],100*self.model['weights']['K10'])
        self.assertEqual(a['completeness'],0);self.assertIsNone(a['confidence'])
        self.assertAlmostEqual(a['result']['coverage'],1)
        for f in a['findings']:
            self.assertEqual(f['confidence_label'],'Düşük');self.assertEqual(f['basis'],'project_default')
        self.assertIn('memnuniyetin kanıtı değildir',a['findings'][9]['explanation'])
        self.assertEqual(self.model,before)
        self.assertEqual(a['report']['max_score'],10);self.assertEqual(len(a['report']['scores']),10)

    def test_cpci_does_not_accept_general_future_or_uncertain_claim(self):
        for quote,confidence in [('Web of Science indexing is available.',.95),('Proceedings will be submitted to CPCI.',.95),('Indexed in CPCI for 2027.',.6)]:
            with self.subTest(quote=quote):
                self.finding('K1',quote,confidence=confidence)
                a=self.analyze();self.assertEqual(a['utilities']['K1'],0)
                self.assertEqual(a['findings'][0]['basis'],'project_default')
        self.finding('K1','2027 proceedings indexed in Conference Proceedings Citation Index (CPCI).')
        self.assertEqual(self.analyze()['utilities']['K1'],1)

    def test_absence_of_cpci_is_not_a_confirmed_negative_fact(self):
        self.finding('K1','IEEE Xplore indexing services.',value=False)
        a=self.analyze()
        self.assertEqual(a['utilities']['K1'],0)
        self.assertEqual(a['findings'][0]['basis'],'project_default')
        self.assertEqual(a['findings'][0]['confidence_label'],'Düşük')
        self.finding('K1','The 2027 proceedings are not indexed in CPCI.',value=False)
        self.assertEqual(self.analyze()['findings'][0]['basis'],'evidence')

    def test_trustworthy_negative_satisfaction_vs_weak_and_conflicting(self):
        self.finding('K10','2025 katılımcı anketinde 200 kişiden 180 kişi ciddi organizasyon sorunu bildirdi.',value=False)
        self.assertEqual(self.analyze()['utilities']['K10'],0)
        self.output['findings'][9]['confidence']=.6
        self.assertEqual(self.analyze()['utilities']['K10'],1)
        self.output['findings'][9].update(status='conflict',confidence=.95)
        a=self.analyze();self.assertEqual(a['utilities']['K10'],1)
        self.assertIn('SOURCE_CONFLICT',a['findings'][9]['flags'])
        self.finding('K10','2025 katılımcı anketinde 200 kişiden 180 kişi organizasyondan memnundu.')
        self.assertEqual(self.analyze()['findings'][9]['basis'],'evidence')

    def test_citations_dates_and_forged_quote_do_not_get_positive_score(self):
        self.finding('K4','The conference will be held online.')
        self.output['findings'][3]['evidence'][0]['quote']='This text is not in the source.'
        a=self.analyze();self.assertEqual(a['utilities']['K4'],0)
        self.assertEqual(a['report']['scores']['participation_format']['evidence'],'')
        self.finding('K4','The conference will be held online.')
        a=self.analyze();self.assertEqual(a['utilities']['K4'],1)
        ref=a['report']['scores']['participation_format']['references'][0]
        self.assertEqual(ref['page'],2);self.assertEqual(ref['retrieved_at'],'2026-09-30T10:00:00Z')
        self.assertEqual(a['report']['analysis_date'],'2026-09-30')

    def test_method_contract_carries_central_policy_without_personal_preferences(self):
        snapshot=method_snapshot(self.model)
        self.assertEqual([c['code'] for c in policy_definitions()],['K'+str(i) for i in range(1,11)])
        self.assertEqual({c['code']:c['global_weight'] for c in snapshot['criteria']},self.model['weights'])
        self.assertIn('Yalnız kayıt/katılım ücretini',snapshot['criteria'][2]['description'])
        self.assertIn('her biri 1',snapshot['criteria'][3]['description'])
        self.assertEqual(snapshot['criteria'][9]['default_score'],1)
        prompt=analysis_instructions()
        self.assertIn('Kişisel bütçe, katılım tercihi, kullanıcı profili veya ayrı kabul eşiği isteme',prompt)
        self.assertIn('başvuru/vaat yetmez',prompt)

if __name__=='__main__':unittest.main()
