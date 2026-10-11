"""Topic-first recommendations; AHP and personal fit remain separate measures."""
from app.intelligence_config import weighted_available
from app.text_similarity import LocalTextSimilarity


def comparable_ahp(a: dict, b: dict) -> bool:
    def signature(c):
        e=c.get('evaluation',{});m=c['metadata']
        return (e.get('model_id'),m.get('context'),e.get('scale'),e.get('policy_version') or e.get('mode') or 'manual',bool(m.get('sample')))
    sa,sb=signature(a),signature(b)
    return bool(sa[0]) and sa==sb

class RecommendationService:
    def __init__(self, config: dict, text: LocalTextSimilarity, personalization):
        self.config,self.text,self.personalization=config,text,personalization

    def similarity(self, a: dict, b: dict) -> dict:
        ar,br=a['metadata'].get('research') or {},b['metadata'].get('research') or {}
        criteria=None
        if comparable_ahp(a,b):
            au,bu=a.get('utilities',{}),b.get('utilities',{})
            pairs=[(v,bu[k]) for k,v in au.items() if v is not None and bu.get(k) is not None]
            if pairs:criteria=100*sum(1-abs(x-y) for x,y in pairs)/len(pairs)
        parts={'text':self.text.similarity(a.get('academic_text',''),b.get('academic_text','')),
               'tags':self.text.tag_similarity(ar.get('keywords',[])+ar.get('topics',[]),br.get('keywords',[])+br.get('topics',[])),
               'fields':self.text.tag_similarity(ar.get('research_fields',[]),br.get('research_fields',[])),
               'criteria':criteria}
        score,coverage=weighted_available(parts,self.config['similarity_weights'])
        topic,_=weighted_available({k:v for k,v in parts.items() if k!='criteria'},self.config['similarity_weights'])
        return {'score':score,'topic_score':topic,'coverage':coverage*100,'components':parts}

    def recommend(self, target: dict, candidates: list[dict], profile: dict) -> dict:
        rows=[]
        for candidate in candidates:
            if candidate['id']==target['id'] or candidate['metadata'].get('sample'):continue
            if target['metadata'].get('sample'):continue
            similarity=self.similarity(target,candidate)
            if similarity['topic_score'] is None or similarity['topic_score']<self.config['minimum_topic_similarity'] or similarity['score']<self.config['minimum_similarity']:continue
            fit=self.personalization.personal_fit(candidate,profile)
            ahp=candidate.get('result',{}).get('total');base_ahp=target.get('result',{}).get('total')
            comparable=comparable_ahp(target,candidate)
            delta=ahp-base_ahp if comparable and ahp is not None and base_ahp is not None else None
            components={'similarity':similarity['score'],'ahp':ahp if comparable and base_ahp is not None else None,'personal_fit':fit['score']}
            ranking,coverage=weighted_available(components,self.config['recommendation_weights'])
            if ranking is None:continue
            reasons=['Kongre metni, alan veya anahtar kelimelerinde benzerlik.']
            shared=sorted(set(self.text.tokens(target['academic_text']))&set(self.text.tokens(candidate['academic_text'])))
            if delta is not None and delta>1e-8:reasons.append(f'Aynı değerlendirme koşullarında AHP puanı {delta:.2f} puan daha yüksek.')
            if comparable and candidate.get('utilities',{}).get('K2') is not None and target.get('utilities',{}).get('K2') is not None and candidate['utilities']['K2']>target['utilities']['K2']:
                reasons.append('Kayıtlı akademik temsiliyet kriteri daha güçlü.')
            if fit['score'] is not None:reasons.append('Araştırma profilinizle alan ve anahtar kelime eşleşmesi sıralamaya katıldı.')
            if not comparable:reasons.append('Model veya değerlendirme koşulları farklı; AHP puanı sıralamaya ve puan farkına katılmadı.')
            meta=candidate['metadata'];extra=meta.get('research') or {}
            rows.append({'id':candidate['id'],'evaluation_id':candidate['evaluation'].get('id'),'name':meta.get('name',''),
                         'edition':meta.get('edition',''),'country':extra.get('country') or None,'city':extra.get('city') or None,
                         'location':meta.get('location') or None,'date':meta.get('start_date') or None,'fee':extra.get('fee') or None,
                         'similarity_score':round(similarity['score'],2),'similarity_components':similarity['components'],
                         'ahp_score':ahp,'suitability':candidate.get('result',{}).get('status','Eksik veri'),
                         'personal_fit':fit,'recommendation_score':round(ranking,2),'ranking_components':components,
                         'ranking_coverage':round(coverage*100,2),'ahp_comparable':comparable,
                         'ahp_delta':None if delta is None else round(delta,2),'reasons':reasons,'shared_terms':shared[:12]})
        # Do not compare composite scores with different available component sets.
        # Prefer genuinely comparable improvements, then comparable/complete results,
        # and finally topic-only alternatives; ranking happens within each cohort.
        def order(r):
            cohort=0 if r['ahp_delta'] is not None and r['ahp_delta']>0 else 1 if r['ranking_components']['ahp'] is not None else 2
            return cohort,-r['recommendation_score'],-r['similarity_score'],r['id']
        rows.sort(key=order)
        enough=len(rows)>=self.config['minimum_recommendations']
        return {'items':rows[:self.config['maximum_recommendations']] if enough else [],'available_count':len(rows),
                'message':f'{min(len(rows),self.config["maximum_recommendations"])} benzer alternatif bulundu.' if enough else 'Yeterli düzeyde benzer kongre bulunamadı.',
                'scope':'Kayıtlı aktif kongreler; Excel örnekleri önerilmez. Yeni web araması yapılmaz.',
                'weights':self.config['recommendation_weights'],'method':self.text.version}
