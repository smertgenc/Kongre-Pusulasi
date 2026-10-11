"""Reference-coded, ridge-regularized pooled conditional multinomial logit.

Choice sets remain intact. A task holdout is fixed before responses are collected.
No standard errors, individual utilities or empirical validity are claimed.
"""
import hashlib
import itertools
import json
import math
import random
import re

VERSION='cbc-mnl-v1'
DEFAULT_ATTRIBUTES=[{'id':'fee','label':'Kayıt ücreti','levels':['Düşük','Orta','Yüksek']},
 {'id':'format','label':'Katılım biçimi','levels':['Çevrim içi','Yüz yüze']},
 {'id':'relevance','label':'Araştırma ilgisi','levels':['Yakın alan','Doğrudan alanım']},
 {'id':'interaction','label':'Akademik etkileşim','levels':['Oturumlar','Oturumlar ve atölye']}]

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def validate_attributes(attributes):
    if not isinstance(attributes,list) or not 2<=len(attributes)<=6:raise ValueError('2–6 öznitelik gereklidir.')
    ids=[]
    for a in attributes:
        if not isinstance(a,dict) or set(a)!={'id','label','levels'}:raise ValueError('Öznitelik: id, label, levels gereklidir.')
        if not isinstance(a['id'],str) or not re.fullmatch('[a-z][a-z0-9_]{0,29}',a['id']):raise ValueError('Öznitelik kimliği geçersiz.')
        if not isinstance(a['label'],str) or not 1<=len(a['label'])<=100:raise ValueError('Öznitelik etiketi gereklidir.')
        levels=a['levels']
        if not isinstance(levels,list) or not 2<=len(levels)<=4 or any(not isinstance(x,str) or not x.strip() or len(x)>100 for x in levels) or len(set(levels))!=len(levels):raise ValueError('Her öznitelik 2–4 benzersiz düzey içermeli.')
        ids.append(a['id'])
    if len(ids)!=len(set(ids)):raise ValueError('Öznitelik kimlikleri benzersiz olmalı.')
    return attributes

def encode(attributes, profile):
    if set(profile)!={a['id'] for a in attributes} or any(profile[a['id']] not in a['levels'] for a in attributes):raise ValueError('Alternatif düzeyleri tasarıma uymuyor.')
    return [float(profile[a['id']]==level) for a in attributes for level in a['levels'][1:]]

def rank(matrix,tolerance=1e-9):
    if not matrix:return 0
    a=[row[:] for row in matrix];r=0
    for col in range(len(a[0])):
        pivot=max(range(r,len(a)),key=lambda i:abs(a[i][col]),default=r)
        if r==len(a) or abs(a[pivot][col])<tolerance:continue
        a[r],a[pivot]=a[pivot],a[r];v=a[r][col];a[r]=[x/v for x in a[r]]
        for i in range(r+1,len(a)):
            v=a[i][col];a[i]=[x-v*y for x,y in zip(a[i],a[r])]
        r+=1
        if r==len(a):break
    return r

def design(attributes=None,seed=42,tasks=24,alternatives=3,forbidden=None):
    attributes=validate_attributes(DEFAULT_ATTRIBUTES if attributes is None else attributes)
    if type(seed)!=int or type(tasks)!=int or not 12<=tasks<=80 or alternatives not in (2,3):raise ValueError('Tasarım: seed tamsayı, 12–80 görev, 2 veya 3 alternatif gereklidir.')
    forbidden=forbidden or []
    if not isinstance(forbidden,list) or len(forbidden)>100:raise ValueError('En fazla 100 yasak kombinasyon.')
    levels={a['id']:a['levels'] for a in attributes}
    for combo in forbidden:
        if not isinstance(combo,dict) or not combo or any(k not in levels or v not in levels[k] for k,v in combo.items()):raise ValueError('Yasak kombinasyon geçersiz.')
    profiles=[dict(zip(levels,values)) for values in itertools.product(*levels.values())]
    profiles=[p for p in profiles if not any(all(p[k]==v for k,v in c.items()) for c in forbidden)]
    if len(profiles)<alternatives or math.comb(len(profiles),alternatives)<tasks:raise ValueError('Yeterli benzersiz seçim seti üretilemiyor.')
    rng=random.Random(seed);sets=[];seen=set();holdout=max(3,round(tasks*.2))
    for _ in range(tasks*500):
        indices=tuple(sorted(rng.sample(range(len(profiles)),alternatives)))
        if indices in seen:continue
        seen.add(indices);indices=list(indices);rng.shuffle(indices)
        sets.append({'id':str(len(sets)+1),'split':'train' if len(sets)<tasks-holdout else 'holdout','alternatives':[profiles[i] for i in indices]})
        if len(sets)==tasks:break
    if len(sets)!=tasks:raise ValueError('Tasarım üretilemedi; daha az görev seçin.')
    rows=[]
    for task in sets:
        if task['split']=='train':
            x=[encode(attributes,p) for p in task['alternatives']]
            rows.extend([[b-a for a,b in zip(x[0],v)] for v in x[1:]])
    p=sum(len(a['levels'])-1 for a in attributes);r=rank(rows)
    if r!=p:raise ValueError('Tasarım tanımlanabilir değil; öznitelikleri/yasakları veya seed değerini değiştirin.')
    result={'version':VERSION,'attributes':attributes,'seed':seed,'tasks':sets,'forbidden':forbidden,'rank':r,'parameters':p,'coding':'first-level-reference','design_method':'seeded random unique sets; not D-optimal'}
    result['hash']=digest(result);return result

def probabilities(beta,x):
    u=[sum(a*b for a,b in zip(beta,row)) for row in x];m=max(u);e=[math.exp(v-m) for v in u];z=sum(e)
    return [v/z for v in e]

def solve(a,b):
    rows=[row[:]+[v] for row,v in zip(a,b)];n=len(b)
    for k in range(n):
        pivot=max(range(k,n),key=lambda i:abs(rows[i][k]))
        if abs(rows[pivot][k])<1e-12:raise ValueError('Model Hessian matrisi tekil.')
        rows[k],rows[pivot]=rows[pivot],rows[k];v=rows[k][k];rows[k]=[x/v for x in rows[k]]
        for i in range(n):
            if i!=k:
                v=rows[i][k];rows[i]=[x-v*y for x,y in zip(rows[i],rows[k])]
    return [row[-1] for row in rows]

def fit(d,responses,*,ridge=.1,max_iter=100):
    if not math.isfinite(ridge) or ridge<=0:raise ValueError('Pozitif ridge katsayısı gereklidir.')
    if not responses or len(responses)>50000:raise ValueError('1–50000 seçim yanıtı gereklidir.')
    taskmap={t['id']:t for t in d['tasks']};train=[];holdout=[];seen=set()
    for r in responses:
        if set(r)!={'respondent','task','choice'} or not isinstance(r['respondent'],str) or not r['respondent'] or len(r['respondent'])>80:raise ValueError('Takma katılımcı kodu, task ve choice gerekli.')
        t=taskmap.get(r['task']);key=(r['respondent'],r['task'])
        if not t or type(r['choice'])!=int or not 0<=r['choice']<len(t['alternatives']) or key in seen:raise ValueError('Yinelenen veya geçersiz seçim yanıtı.')
        seen.add(key);row=([encode(d['attributes'],p) for p in t['alternatives']],r['choice'])
        (train if t['split']=='train' else holdout).append(row)
    p=d['parameters']
    if len(train)<max(20,5*p) or len(holdout)<5:raise ValueError('Yetersiz veri: en az max(20, 5×katsayı) eğitim ve 5 holdout seçimi gerekli; bu teknik alt sınır örneklem büyüklüğü önerisi değildir.')
    if rank([[v-z for v,z in zip(row,x[0])] for x,_ in train for row in x[1:]])!=p:raise ValueError('Yanıtlanan eğitim tasarımı tam rank değil.')
    def objective(beta):
        value=ridge*sum(b*b for b in beta)/2
        for x,y in train:
            u=[sum(a*b for a,b in zip(beta,row)) for row in x];m=max(u)
            value+=m+math.log(sum(math.exp(v-m) for v in u))-u[y]
        return value
    beta=[0.]*p;converged=False
    for iteration in range(max_iter):
        g=[ridge*b for b in beta];h=[[ridge if i==j else 0. for j in range(p)] for i in range(p)]
        for x,y in train:
            pr=probabilities(beta,x);mean=[sum(prob*row[i] for prob,row in zip(pr,x)) for i in range(p)]
            for i in range(p):
                g[i]+=mean[i]-x[y][i]
                for j in range(p):h[i][j]+=sum(prob*row[i]*row[j] for prob,row in zip(pr,x))-mean[i]*mean[j]
        if max(abs(v) for v in g)/len(train)<1e-8:converged=True;break
        delta=solve(h,g);old=objective(beta);step=1.
        while step>1e-8:
            candidate=[b-step*v for b,v in zip(beta,delta)]
            if objective(candidate)<=old-1e-4*step*sum(v*w for v,w in zip(g,delta)):break
            step/=2
        if step<=1e-8:raise ValueError('Model yakınsaması başarısız; sonuç yayınlanmadı.')
        beta=candidate
    if not converged:raise ValueError('Model yakınsamadı; daha fazla/verimli veri veya tasarım gerekir.')
    ranges={};offset=0;coefficients={}
    for a in d['attributes']:
        values=[0.]+beta[offset:offset+len(a['levels'])-1];offset+=len(values)-1
        coefficients[a['id']]=dict(zip(a['levels'],values));ranges[a['id']]=max(values)-min(values)
    total=sum(ranges.values());pred=[(probabilities(beta,x),y) for x,y in holdout]
    return {'version':VERSION,'design_hash':d['hash'],'response_hash':digest(responses),'beta':beta,'coefficients':coefficients,
            'importance':{k:v/total if total else None for k,v in ranges.items()},'attributes':d['attributes'],'references':{a['id']:a['levels'][0] for a in d['attributes']},
            'train_n':len(train),'holdout_n':len(holdout),'respondents':len({r['respondent'] for r in responses}),'parameters':p,'ridge':ridge,'iterations':iteration+1,'converged':True,
            'holdout_accuracy':sum(max(range(len(pr)),key=pr.__getitem__)==y for pr,y in pred)/len(pred),
            'holdout_log_loss':-sum(math.log(max(pr[y],1e-300)) for pr,y in pred)/len(pred),
            'limitations':['Pooled MNL; bireysel fayda tahmini değildir.','Aynı katılımcıların ayrılmış görevleriyle holdout; yeni katılımcı genellemesi ölçülmedi.','IIA, bağımsız hata ve ortak ölçek varsayımları; heterojenlik/standart hata/güven aralığı hesaplanmadı.','Ridge cezası dahil; katsayılar yalnız bu tasarım ve düzey aralıklarında yorumlanır.']}

def synthetic_responses(d,n=60,seed=17,beta=None):
    rng=random.Random(seed);beta=beta if beta is not None else [(-1 if i%2 else 1)*.7 for i in range(d['parameters'])];rows=[]
    for person in range(n):
        for t in d['tasks']:
            pr=probabilities(beta,[encode(d['attributes'],p) for p in t['alternatives']]);choice=rng.choices(range(len(pr)),weights=pr)[0]
            rows.append({'respondent':'synthetic-'+str(person),'task':t['id'],'choice':choice})
    return rows
