"""UI-independent AHP and congress scoring, no external dependencies."""
import math

LOW_SUITABILITY = 'Düşük Uygunluk'
MEDIUM_SUITABILITY = 'Orta Uygunluk'
HIGH_SUITABILITY = 'Yüksek Uygunluk'
INCOMPLETE = 'Eksik veri'

CRITERIA = [
    ('K1', 'CPCI İndeksleme', 'A', 'İlgili yılın bildiri cildi için doğrulanmış CPCI kaydı bulunuyor mu? Başvuru veya geçmiş yıl kaydı yeterli değildir.'),
    ('K2', 'Akademik Temsiliyet', 'A', 'Bilim kurulunun kurum ve uzmanlık temsili, değerlendirme notunuzda belirttiğiniz koşulu karşılıyor mu?'),
    ('K3', 'Maliyet', 'C', 'Kayıt, ulaşım ve konaklama toplamı belirlediğiniz bütçeye uygun mu? Bütçe ve para birimini not edin.'),
    ('K4', 'Katılım Formatı', 'C', 'Yüz yüze, çevrim içi veya hibrit katılım olanağı ihtiyacınızı karşılıyor mu?'),
    ('K5', 'Konum', 'C', 'Konum erişim gereksinimlerinizi karşılıyor mu? Maliyet etkisini burada tekrar puanlamayın.'),
    ('K6', 'Süreklilik Statüsü', 'B', 'Etkinliğin geçmiş dönemlerde düzenlendiği doğrulanabiliyor mu? Beklediğiniz geçmiş dönem sayısını not edin.'),
    ('K7', 'Konu Özgünlüğü', 'B', 'İçerik, alan uzmanının gerekçeli özgünlük değerlendirmesini karşılıyor mu?'),
    ('K8', 'Geçmiş Veri Şeffaflığı', 'B', 'Geçmiş program, kurul ve bildiri bilgileri erişilebilir ve doğrulanabilir mi?'),
    ('K9', 'Uluslararası Kapsam', 'A', 'Fiilî uluslararası katılım kanıtı, belirttiğiniz kapsam koşulunu karşılıyor mu? İsimde “uluslararası” olması yeterli değildir.'),
    ('K10', 'Katılımcı Memnuniyeti', 'B', 'Kaynağı, dönemi ve örneklemi belli memnuniyet verisi, belirttiğiniz eşiği karşılıyor mu?'),
]
GROUPS = {'root': ['A', 'B', 'C'], 'A': ['K1', 'K2', 'K9'], 'B': ['K6', 'K7', 'K8', 'K10'], 'C': ['K3', 'K4', 'K5']}
DEFAULT_MATRICES = {
    'root': [[1,5,9],[1/5,1,3],[1/9,1/3,1]],
    'A': [[1,1,2],[1,1,2],[.5,.5,1]],
    'B': [[1,1,1,1] for _ in range(4)],
    'C': [[1,2,2],[.5,1,1],[.5,1,1]],
}

def number(x):
    return type(x) in (int, float) and math.isfinite(x)

def matrix_result(a):
    if not isinstance(a, list) or len(a) not in (3,4):
        raise ValueError('Matris boyutu 3 veya 4 olmalıdır.')
    n = len(a)
    if any(not isinstance(row,list) or len(row)!=n for row in a):
        raise ValueError('Matris kare olmalıdır.')
    for i in range(n):
        for j in range(n):
            v = a[i][j]
            if not number(v) or not 1/9-1e-12 <= v <= 9+1e-12:
                raise ValueError('Karşılaştırmalar 1/9 ile 9 arasında sonlu sayılar olmalıdır.')
            if i==j and not math.isclose(v,1,abs_tol=1e-9):
                raise ValueError('Köşegen değerleri 1 olmalıdır.')
            if not number(a[j][i]) or not math.isclose(v*a[j][i],1,abs_tol=1e-9):
                raise ValueError('Karşılıklı değerler birbirinin tersi olmalıdır.')
    totals = [sum(a[i][j] for i in range(n)) for j in range(n)]
    norm = [[a[i][j]/totals[j] for j in range(n)] for i in range(n)]
    weights = [sum(row)/n for row in norm]
    v = [1/n]*n
    for _ in range(10000):
        av = [sum(a[i][j]*v[j] for j in range(n)) for i in range(n)]
        nv = [x/sum(av) for x in av]
        if max(abs(x-y) for x,y in zip(nv,v)) < 1e-14:
            v = nv
            break
        v = nv
    else:
        raise ValueError('Özdeğer hesabı yakınsamadı.')
    lam = sum(sum(a[i][j]*v[j] for j in range(n))/v[i] for i in range(n))/n
    ci = max(0,(lam-n)/(n-1))
    ri = {3:.58,4:.9}[n]
    return {'weights':weights, 'normalized':norm, 'lambda_max':lam, 'ci':ci, 'ri':ri, 'cr':ci/ri, 'consistent':ci/ri<=.1}

def calculate_model(matrices, thresholds=None):
    if not isinstance(matrices,dict) or set(matrices)!=set(GROUPS):
        raise ValueError('Dört grubun karşılaştırma matrisleri gereklidir.')
    results = {}
    for key, members in GROUPS.items():
        if not isinstance(matrices[key],list) or len(matrices[key])!=len(members):
            raise ValueError('Grup matrisi yanlış boyutta: '+key)
        results[key] = matrix_result(matrices[key])
    thresholds = thresholds or {'average':70,'valid':90}
    if not isinstance(thresholds,dict) or set(thresholds)!={'average','valid'} or not all(number(v) for v in thresholds.values()) or not 0<=thresholds['average']<thresholds['valid']<=100:
        raise ValueError('Eşikler 0 ≤ Orta Uygunluk < Yüksek Uygunluk ≤ 100 olmalıdır.')
    weights = {}
    for gi,g in enumerate(GROUPS['root']):
        for i,c in enumerate(GROUPS[g]):
            weights[c] = results['root']['weights'][gi]*results[g]['weights'][i]
    return {'matrices':matrices,'results':results,'weights':weights,'thresholds':thresholds,
            'consistent':all(r['consistent'] for r in results.values()),'method':'column_mean_v1','engine_version':'1.0.0'}

def classify(score, thresholds):
    # Keep persisted/API threshold keys compatible with existing model versions.
    return HIGH_SUITABILITY if score>=thresholds['valid'] else MEDIUM_SUITABILITY if score>=thresholds['average'] else LOW_SUITABILITY

def score(weights, utilities, thresholds):
    codes = {c[0] for c in CRITERIA}
    if not isinstance(utilities,dict) or set(utilities)!=codes or set(weights)!=codes:
        raise ValueError('K1–K10 kriterlerinin tamamı bulunmalıdır; bilinmeyenler null olmalıdır.')
    if any(not number(v) or v<0 for v in weights.values()) or not math.isclose(sum(weights.values()),1,abs_tol=1e-9):
        raise ValueError('Ağırlıklar geçerli olmalı ve toplamları 1 olmalıdır.')
    if any(v is not None and (not number(v) or not 0<=v<=1) for v in utilities.values()):
        raise ValueError('Kriter faydaları 0–1 arasında olmalıdır.')
    missing = [c for c in weights if utilities[c] is None]
    contributions = {c:None if utilities[c] is None else 100*weights[c]*utilities[c] for c in weights}
    lower = sum(v for v in contributions.values() if v is not None)
    upper = min(100, lower + sum(100*weights[c] for c in missing))
    total = None if missing else min(100,max(0,lower))
    return {'total':total,'lower':lower,'upper':upper,'coverage':sum(weights[c] for c in weights if c not in missing),
            'missing':missing,'contributions':contributions,'status':INCOMPLETE if missing else classify(total,thresholds)}

def scenario_weights(weights, code, target):
    if code not in weights or not number(target) or not 0<=target<=1 or weights[code]>=1:
        raise ValueError('Senaryo kriteri veya ağırlığı geçersiz.')
    return {k:target if k==code else v*(1-target)/(1-weights[code]) for k,v in weights.items()}
