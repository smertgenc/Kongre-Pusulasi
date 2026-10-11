"""Deterministic, offline regression tests for the three independent layers."""
import copy
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app
from app.database import SCHEMA_VERSION, Database
from app.intelligence_config import load_intelligence_config, weighted_available
from app.intelligence_schemas import ResearchProfileInput
from app.text_similarity import LocalTextSimilarity, normalize_text, jaccard
from app.personalization_service import PersonalizationService
from app.fingerprint_service import generate_fingerprint, calculate_fingerprint_similarity, normalize_domain, normalize_organizer
from app.recommendation_service import RecommendationService
from tests.test_ai import FixtureProvider, TEXT


def congress(cid='target',name='Artificial Intelligence and Data Science Congress',score=75,**extra):
    research={'description':'Machine learning, artificial intelligence, data science and predictive analytics.',
              'research_fields':['Artificial Intelligence','Data Science'],'keywords':['machine learning']}
    research.update(extra.pop('research',{}))
    meta={'name':name,'edition':'2027','context':'same profile','research':research,'organizer':'International Science Organization Ltd.',
          'website':'https://www.example.org/2027','sample':False,**extra}
    text=' '.join([name,research.get('description',''),' '.join(research.get('keywords',[])),' '.join(research.get('research_fields',[]))])
    return {'id':cid,'metadata':meta,'academic_text':text,'source_text':'',
            'evaluation':{'id':'e-'+cid,'model_id':'m1','scale':1},
            'utilities':{f'K{i}':1 for i in range(1,11)},'result':{'total':score,'status':'Orta Uygunluk'}}

class IntelligenceUnitTests(unittest.TestCase):
    def setUp(self):
        self.config=load_intelligence_config();self.text=LocalTextSimilarity(self.config['aliases'])
        self.personal=PersonalizationService(None,self.text)
        self.recommend=RecommendationService(self.config,self.text,self.personal)
        self.profile={'enabled':True,'research_fields':['Artificial Intelligence','Data Science'],'keywords':['machine learning']}

    def test_text_aliases_and_normalization(self):
        self.assertEqual(normalize_text('  İSTANBUL / ŞİŞLİ! '),'istanbul sisli')
        self.assertEqual(self.text.similarity('Yapay Zekâ ve Veri Bilimi','Artificial Intelligence and Data Science'),100)
        self.assertIsNone(self.text.similarity('Conference 2027',''))
        self.assertEqual(self.text.similarity('machine learning','medieval archaeology'),0)

    def test_personal_fit_research_keywords_empty_profile_and_empty_description(self):
        match=self.personal.personal_fit(congress(),self.profile)
        self.assertEqual(match['score'],100);self.assertEqual(len(match['matches']),3)
        self.assertIsNone(self.personal.personal_fit(congress(),{})['score'])
        self.assertIsNone(self.personal.personal_fit(congress(),{**self.profile,'enabled':False})['score'])
        self.assertEqual(self.personal.personal_fit(congress(research={'description':''}),self.profile)['score'],100)
        empty=congress();empty['academic_text']=''
        self.assertIsNone(self.personal.personal_fit(empty,self.profile)['score'])
        unrelated=congress();unrelated['academic_text']='medieval archaeology pottery'
        self.assertEqual(self.personal.personal_fit(unrelated,self.profile)['score'],0)

    def test_same_topic_high_unrelated_low_even_when_ahp_identical(self):
        target=congress();similar=congress('similar')
        unrelated=congress('other',name='Medieval Archaeology',research={'description':'Archaeology pottery ancient ruins','research_fields':['Archaeology'],'keywords':['pottery']})
        self.assertGreater(self.recommend.similarity(target,similar)['score'],95)
        self.assertLess(self.recommend.similarity(target,unrelated)['score'],20)
        self.assertEqual(self.recommend.recommend(target,[unrelated]*4,self.profile)['items'],[])

    def test_better_ahp_prioritized_and_no_fake_minimum_fill(self):
        target=congress(score=75);candidates=[congress(str(i),score=score) for i,score in enumerate([70,78,92,80,84,88])]
        before=copy.deepcopy(target)
        result=self.recommend.recommend(target,candidates,self.profile)
        self.assertEqual(len(result['items']),5);self.assertEqual(result['items'][0]['ahp_score'],92)
        self.assertEqual(result['items'][0]['ahp_delta'],17);self.assertEqual(target,before)
        self.assertEqual(self.recommend.recommend(target,candidates[:2],self.profile)['items'],[])
        self.assertEqual(self.recommend.recommend(target,candidates[:2],self.profile)['available_count'],2)

    def test_mixed_model_missing_scores_samples_and_fingerprint_do_not_inflate_ranking(self):
        target=congress();candidates=[congress(str(i)) for i in range(4)]
        candidates[0]['evaluation']['model_id']='m2';candidates[0]['result']['total']=100
        candidates[1]['result']['total']=None
        candidates[2]['metadata']['sample']=True
        result=self.recommend.recommend(target,candidates,{})
        self.assertEqual(len(result['items']),3)
        for item in result['items']:
            self.assertIsNone(item['ranking_components']['personal_fit'])
            if item['id'] in ('0','1'):self.assertIsNone(item['ranking_components']['ahp']);self.assertIsNone(item['ahp_delta'])
        # Matching organizations are not a recommendation quality component.
        self.assertNotIn('fingerprint',result['weights'])
        self.assertEqual(result['items'][0]['id'],'3')

    def test_normalization_domains_organizer_and_hash(self):
        a=congress(research={'committee_members':['Sarah','John'],'speaker_names':['İpek Şen'],'contact_emails':['info@example.org']})
        b=copy.deepcopy(a);b['metadata']['website']='http://example.org/2025'
        b['metadata']['organizer']='International Science Organisation'
        b['metadata']['research']['committee_members']=['John','Sarah','John']
        first=generate_fingerprint(a,self.text);second=generate_fingerprint(b,self.text)
        self.assertEqual(first,second);self.assertEqual(len(first['fingerprint_hash']),64)
        self.assertEqual(normalize_domain('https://www.Example.org/x'),'example.org')
        self.assertNotEqual(normalize_domain('a.shared.org'),normalize_domain('b.shared.org'))
        self.assertEqual(normalize_organizer('Organisation, LTD.'),'organization')

    def test_email_phone_doi_extraction(self):
        record=congress();record['source_text']='Contact: info@example.org, conference@example.org. Tel +90 (212) 123-4567. https://doi.org/10.12345/abc'
        f=generate_fingerprint(record,self.text)
        self.assertEqual(f['email_domains'],['example.org']);self.assertEqual(len(f['contact_emails']),2)
        self.assertIn('902121234567',f['phones']);self.assertEqual(f['doi_prefixes'],['10.12345'])

    def test_domain_and_email_similarity_committee_overlap_missing_components(self):
        a=generate_fingerprint(congress(research={'committee_members':['Ali','Mehmet','John','Sarah'],'contact_emails':['info@example.org']}),self.text)
        b=generate_fingerprint(congress(research={'committee_members':['Ali','John','Sarah','David'],'contact_emails':['conference@example.org']}),self.text)
        r=calculate_fingerprint_similarity(a,b,self.config,self.text)
        self.assertEqual(r['components']['domain'],100);self.assertEqual(r['components']['email_domains'],100)
        self.assertEqual(r['components']['committee'],60);self.assertIsNone(r['components']['publication'])
        b['organizer_normalized']='medieval heritage association'
        self.assertLess(calculate_fingerprint_similarity(a,b,self.config,self.text)['components']['organizer'],20)
        self.assertEqual(jaccard(['a','b'],['b','c']),100/3)
        self.assertIsNone(jaccard([],['b']))

    def test_sparse_data_renormalizes_and_marks_limited_evidence(self):
        r=calculate_fingerprint_similarity({'website_domain':'example.org'},{'website_domain':'example.org'},self.config,self.text)
        self.assertEqual(r['score'],100);self.assertEqual(r['coverage'],20);self.assertTrue(r['limited_evidence'])
        r=calculate_fingerprint_similarity({}, {}, self.config,self.text)
        self.assertIsNone(r['score']);self.assertEqual(r['coverage'],0)
        r=calculate_fingerprint_similarity({'email_domains':['gmail.com']},{'email_domains':['gmail.com']},self.config,self.text)
        self.assertIsNone(r['score'])
        self.assertEqual(weighted_available({'a':80,'b':None},{'a':.2,'b':.8}),(80,.2))

    def test_config_validation_and_profile_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'settings.json'
            for key,value in [('minimum_recommendations',1),('fingerprint_thresholds',[70,40,90]),('recommendation_weights',{'similarity':1})]:
                config=copy.deepcopy(self.config);config[key]=value;p.write_text(json.dumps(config))
                with self.assertRaises(ValueError):load_intelligence_config(p)
        profile=ResearchProfileInput(research_fields=[' Data Science ','data science'])
        self.assertEqual(profile.research_fields,['Data Science'])

    def test_historical_link_and_no_available_ranking_component(self):
        a=generate_fingerprint(congress(name='ABC Congress 2025'),self.text)
        b=generate_fingerprint(congress('next',research={'past_congresses':['ABC Congress 2025']}),self.text)
        self.assertEqual(calculate_fingerprint_similarity(a,b,self.config,self.text)['components']['history'],100)
        self.config['recommendation_weights']={'similarity':0,'ahp':0,'personal_fit':1}
        self.assertEqual(self.recommend.recommend(congress(),[congress(str(i)) for i in range(3)],{})['items'],[])

class IntelligenceAPITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'test.db';self.env=Path(self.temp.name)/'.env'
        self.app=create_app(self.path,settings_path=self.env,ai_provider=FixtureProvider())
        self.client=TestClient(self.app).__enter__();self.initial=self.client.get('/api/state').json();self.mid=self.initial['models'][0]['id']

    def tearDown(self):
        self.client.__exit__(None,None,None);self.temp.cleanup()

    def save(self,i=0,**changes):
        meta={'name':f'Artificial Intelligence and Data Science Congress {i}','edition':'2027','context':'same profile',
              'organizer':'International Science Organization','website':'https://www.example.org',
              'research':{'description':'Machine learning data science artificial intelligence','keywords':['machine learning'],
                          'country':'Türkiye','city':'İstanbul','fee':'300 EUR','committee_members':['Ali','Sarah']}}
        payload={'metadata':meta,'model_id':self.mid,'scale':1,'evaluator':'Test','scores':{f'K{i}':1 for i in range(1,11)},'notes':{f'K{i}':'Test kanıtı' for i in range(1,11)}}
        payload.update(changes);r=self.client.post('/api/evaluations',json=payload);self.assertEqual(r.status_code,201,r.text)
        return r.json()

    def test_profile_crud_restarts_and_no_user_id_override(self):
        self.assertFalse(self.client.get('/api/profile/research').json()['exists'])
        body={'research_fields':['AI'],'keywords':['LLM'],'enabled':True}
        result=self.client.post('/api/profile/research',json=body);self.assertEqual(result.status_code,200,result.text)
        pid=result.json()['id'];body['keywords']=['machine learning']
        self.assertEqual(self.client.put('/api/profile/research',json=body).json()['id'],pid)
        self.assertEqual(self.client.post('/api/profile/research',json={**body,'user_id':'another-user'}).status_code,422)
        self.assertEqual(self.client.post('/api/profile/research',json={'keywords':['x']*41}).status_code,422)
        with sqlite3.connect(self.path) as con:self.assertEqual(con.execute('SELECT count(*) FROM user_research_profiles').fetchone()[0],1)
        self.assertEqual(self.initial,self.client.get('/api/state').json())
        self.assertFalse(self.client.request('DELETE','/api/profile/research',json={}).json()['exists'])
        self.assertFalse(self.client.post('/api/profile/research/delete',json={}).json()['exists'])

    def test_insights_old_records_recommendations_cache_and_deleted_candidates(self):
        saved=[self.save(i) for i in range(5)];cid=saved[0]['id'];base='/api/congresses/'+cid
        self.client.post('/api/profile/research',json={'research_fields':['Yapay Zeka'],'keywords':['machine learning']})
        before=self.client.get('/api/state').json()
        data=self.client.get(base+'/insights').json()
        self.assertEqual(data['personal_fit']['score'],100);self.assertEqual(len(data['recommendations']['items']),4)
        self.assertEqual(data['recommendations']['items'][0]['country'],'Türkiye')
        self.assertTrue(data['organizational_matches']);self.assertEqual(before,self.client.get('/api/state').json())
        self.assertEqual(self.client.get(base+'/personal-fit').json()['score'],100)
        for endpoint in ('/fingerprint','/fingerprint/similar','/recommendations'):self.assertEqual(self.client.get(base+endpoint).status_code,200)
        with sqlite3.connect(self.path) as con:cache=con.execute('SELECT * FROM conference_fingerprints ORDER BY conference_id').fetchall()
        self.client.get(base+'/insights')
        with sqlite3.connect(self.path) as con:self.assertEqual(cache,con.execute('SELECT * FROM conference_fingerprints ORDER BY conference_id').fetchall())
        for item in saved[1:3]:self.client.post('/api/congresses/'+item['id']+'/delete',json={'previous_id':item['evaluation_id']})
        self.assertEqual(self.client.get(base+'/recommendations').json()['available_count'],2)
        self.assertEqual(self.client.get(base+'/recommendations').json()['items'],[])
        self.assertEqual(self.client.get('/api/congresses/'+saved[1]['id']+'/insights').status_code,409)
        self.assertEqual(self.client.get('/api/congresses/missing/insights').status_code,404)
        old=self.initial['congresses'][0]['id']
        self.assertEqual(self.client.get('/api/congresses/'+old+'/fingerprint').status_code,200)
        self.assertEqual(self.client.get('/api/congresses/'+old+'/recommendations').json()['items'],[])

    def test_history_fingerprint_invalidation_and_safe_old_snapshot(self):
        saved=self.save();cid=saved['id'];base='/api/congresses/'+cid
        old=self.client.get(base+'/fingerprint').json()
        meta=self.client.get('/api/state').json()['congresses'][0]['metadata'];meta.pop('sample',None)
        meta['organizer']='Different Academy';meta['research']['description']='Archaeology ancient pottery'
        newer=self.save(0,congress_id=cid,previous_id=saved['evaluation_id'],metadata=meta)
        new=self.client.get(base+'/fingerprint').json();self.assertNotEqual(old['fingerprint_hash'],new['fingerprint_hash'])
        history=self.client.get(base+'/fingerprint?evaluation_id='+saved['evaluation_id']).json()
        self.assertEqual(history,old)
        self.assertEqual(self.client.get(base+'/fingerprint').json(),new)
        self.assertEqual(self.client.get(base+'/insights?evaluation_id=missing').status_code,404)
        with ThreadPoolExecutor(max_workers=4) as pool:
            values=list(pool.map(lambda _:self.app.state.intelligence.insights(cid)['fingerprint']['fingerprint_hash'],range(4)))
        self.assertEqual(set(values),{new['fingerprint_hash']})

    def test_ai_source_only_flow_review_and_personal_profile_never_sent_to_provider(self):
        self.client.post('/api/ai/settings',json={'api_key':'test-only','model':'test'})
        self.client.post('/api/profile/research',json={'research_fields':['Artificial Intelligence']})
        d=self.client.post('/api/ai/analyze',json={'sources':[{'kind':'text','content':TEXT+' Artificial Intelligence contact info@example.org'}],'transfer_consent':True}).json()
        base='/api/ai/analyses/'+d['id'];before=self.client.get(base).json()
        insights=self.client.get(base+'/insights');self.assertEqual(insights.status_code,200,insights.text)
        self.assertEqual(insights.json()['personal_fit']['score'],100)
        self.assertEqual(insights.json()['fingerprint']['email_domains'],['example.org'])
        self.assertEqual(self.client.get(base).json(),before)
        body={'metadata':{'name':'AI analysis congress','edition':'2027','context':d['context'],'research':{'description':'Artificial Intelligence'}},
              'evaluator':'Test','decisions':{f'K{i}':{'action':'approve'} for i in range(1,11)}}
        saved=self.client.post(base+'/review',json=body).json()
        reviewed=self.client.get(base+'/insights').json();self.assertEqual(reviewed['evaluation_id'],saved['evaluation_id'])
        self.assertEqual(self.client.get('/api/congresses/'+saved['id']+'/insights').json()['personal_fit']['score'],100)
        self.assertEqual(len(self.client.get('/api/state').json()['congresses']),5)
        self.assertEqual(self.app.state.ai.provider.calls,1)

    def test_schema_migration_preserves_old_rows_and_profile_fingerprint_backup(self):
        saved=self.save();self.client.get('/api/congresses/'+saved['id']+'/fingerprint')
        self.client.post('/api/profile/research',json={'keywords':['LLM']})
        dump=self.client.get('/api/backup').text
        target=Path(self.temp.name)/'restored.db'
        with sqlite3.connect(target) as con:
            con.executescript(dump);con.execute('PRAGMA user_version=5')
            before={t:con.execute('SELECT * FROM '+t).fetchall() for t in ('models','congresses','evaluations','ai_analyses','ai_reviews')}
        with TestClient(create_app(target,settings_path=self.env)) as client:
            self.assertEqual(client.get('/api/health').json()['schema_version'],SCHEMA_VERSION)
            self.assertEqual(client.get('/api/profile/research').json()['keywords'],['LLM'])
            self.assertEqual(client.get('/api/congresses/'+saved['id']+'/fingerprint').status_code,200)
        with sqlite3.connect(target) as con:
            after={t:con.execute('SELECT * FROM '+t).fetchall() for t in before}
            self.assertEqual(before,after);self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_actual_v5_adds_tables_without_rewriting_existing_rows(self):
        target=Path(self.temp.name)/'old-v5.db'
        with sqlite3.connect(self.path) as source,sqlite3.connect(target) as con:
            source.backup(con)
            con.execute('DROP TABLE conference_fingerprints');con.execute('DROP TABLE user_research_profiles')
            con.execute('PRAGMA user_version=5')
            tables=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            before={t:con.execute('SELECT * FROM '+t).fetchall() for t in tables}
        db=Database(target)
        try:db.initialize()
        finally:db.close()
        with sqlite3.connect(target) as con:
            self.assertEqual(before,{t:con.execute('SELECT * FROM '+t).fetchall() for t in tables})
            self.assertEqual(con.execute('SELECT count(*) FROM user_research_profiles').fetchone()[0],0)
            self.assertEqual(con.execute('SELECT count(*) FROM conference_fingerprints').fetchone()[0],0)

if __name__=='__main__':unittest.main()
