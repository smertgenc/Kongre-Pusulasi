"""Experimental constrained hybrid; the production heuristic is not replaced."""
from engine import score,scenario_weights
from app.conjoint import encode,probabilities

def compare_models(records,ahp,conjoint=None,*,minimum_ahp,overlap_acknowledged):
    if len(records)<2 or len({r['id'] for r in records})!=len(records):raise ValueError('En az iki benzersiz alternatif gerekli.')
    if not 0<=minimum_ahp<=100:raise ValueError('AHP kabul eşiği 0–100 olmalı.')
    signature=lambda r:tuple(r.get(k) for k in ('criteria_profile','policy','context','scale','decision_date'))
    if len({signature(r) for r in records})!=1:raise ValueError('Yalnız aynı profil, politika, bağlam, ölçek ve tarihteki kayıtlar karşılaştırılır.')
    if not overlap_acknowledged:raise ValueError('AHP/CBC ortak özniteliklerin kısıt ve tercih rollerini protokolde gerekçelendirin.')
    rows=[]
    for r in records:
        expert=score(ahp['weights'],r['expert_values'],ahp['thresholds']);ai=score(ahp['weights'],r['ai_values'],ahp['thresholds'])
        rows.append({'id':r['id'],'M1':expert,'M4_ahp':ai,'attributes':r['attributes']})
    def order(values):return [r['id'] for r in sorted(rows,key=lambda r:(-(values.get(r['id']) or 0),r['id'])) if values.get(r['id']) is not None]
    results={'M1':{'ranking':order({r['id']:r['M1']['total'] for r in rows}),'status':'Teknik testleri geçti; araştırma verisi gerekiyor'}}
    if conjoint is None:return {'models':results,'candidates':rows,'fallback':'existing_heuristic','note':'Tercih modeli yok. Mevcut üretim öneri motoru korunur; deney M1 ile sınırlı.'}
    if not conjoint.get('converged'):raise ValueError('Yakınsamış CBC modeli gerekli.')
    probs=probabilities(conjoint['beta'],[encode(conjoint['attributes'],r['attributes']) for r in rows]);values={r['id']:p for r,p in zip(rows,probs)}
    results['M2']={'ranking':order(values),'status':'Teknik testleri geçti; araştırma verisi gerekiyor'}
    for name,field in [('M3','M1'),('M4','M4_ahp')]:
        eligible={r['id']:values[r['id']] for r in rows if r[field]['total'] is not None and r[field]['total']>=minimum_ahp}
        results[name]={'ranking':order(eligible),'status':'Teknik testleri geçti; araştırma verisi gerekiyor','eligible_n':len(eligible)}
    for row,p in zip(rows,probs):row['conjoint_probability_all_candidates']=p
    return {'models':results,'candidates':rows,'fallback':None,'method':'AHP≥tau kısıtı altında CBC faydasıyla sıralama. M3 uzman, M4 kaydedilmiş AI kriterleri. Toplamsal karışım yok; aynı CBC modeli/sabit özellikler kullanılır.',
            'minimum_ahp':minimum_ahp,'overlap_acknowledged':True}

def sensitivity(ahp,utilities,code,targets,thresholds):
    results=[]
    for value in targets:
        weights=scenario_weights(ahp['weights'],code,value)
        for pair in thresholds:
            if set(pair)!={'average','valid'} or not 0<=pair['average']<pair['valid']<=100:raise ValueError('Eşikler geçersiz.')
            results.append({'weight':value,'thresholds':pair,'result':score(weights,utilities,pair)})
    return results
