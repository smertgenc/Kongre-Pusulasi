"""Versioned congress criteria; evidence extraction is separate from project defaults.

Only the existing AHP engine calculates weights and totals. Stored reports keep
their policy snapshot, so changing this module never rescales historical reports.
"""
import re
from engine import score

POLICY_VERSION = 'congress-binary-v3'
CRITERIA = [
    ('K1', 'cpci_indexing', 'CPCI İndeksleme',
     'İlgili edisyon için güçlü, güvenilir ve açık CPCI / Conference Proceedings Citation Index doğrulaması varsa 1. Mümkünse bağımsız kurumsal kaynaktan doğrula. Genel Web of Science, başvuru, gelecekte indekslenme vaadi, önceki edisyonun indeksi veya belirsizlik yetmez; 0.'),
    ('K2', 'academic_representation', 'Akademik Temsiliyet',
     'Bilim/düzenleme kurulu, akademik uzmanlar, üniversite öğretim üyeleri veya akademik konuşmacılar güvenilir biçimde belirtilmişse 1. Çok kurum/ülke temsili destekler; ayrıca kişisel kabul eşiği gerekmez. Akademik bilgi yoksa 0.'),
    ('K3', 'cost', 'Maliyet',
     'Yalnız kayıt/katılım ücretini değerlendir: öğrenci, akademisyen, bildirili/bildirisiz, online, erken/normal kayıt. Ücretsiz veya güvenilir karşılaştırmayla düşük/makul ücret 1; belirgin yüksek ücret 0. Ücret kategorilerini ve karşılaştırmanın kaynağını açıkla. Ulaşım, otel, yemek ve kişisel bütçeyi katma. Ücret/karşılaştırma bilinmiyorsa 0; piyasa ortalaması uydurma.'),
    ('K4', 'participation_format', 'Katılım Formatı',
     'Geçerli yüz yüze, online veya hibrit formatın her biri 1. Kişisel katılım tercihi gerekmez. Format bilinmiyorsa veya gerçekleştirilebilirliği ciddi şekilde belirsizse 0. Konumu ayrıca K5 değerlendirir.'),
    ('K5', 'location', 'Konum',
     'Büyük/merkezi/akademik veya erişilebilir şehir, bilinen üniversite/kongre merkezi 1. Kaynaktaki adres ile konuma ilişkin çıkarımı ayır. Erişimi ciddi güç ya da bilinmeyen konum 0. Tamamen online ve fiziksel adres yoksa 0 ve uygulanamaz açıklaması.'),
    ('K6', 'continuity', 'Süreklilik Statüsü',
     'En az bir önceki gerçekleşmiş etkinliğe ait güvenilir bilgi veya 2., 5., 20. gibi güvenilir edisyon bilgisi varsa 1. İlk etkinlik veya geçmişi bilinmiyorsa 0. Aynı kongreyi değerlendirdiğini doğrula.'),
    ('K7', 'topic_originality', 'Konu Özgünlüğü',
     'Tema, oturum, program ve çağrı konularını anlamıyla değerlendir. Güncel, anlamlı bilimsel sorunlar, yeni yöntem/teknolojiler veya nitelikli disiplinlerarası içerik 1. Yalnız moda kelimeler yeterli değildir; uzman raporu şart değildir. Yüzeysel, belirsiz veya erişilemeyen içerik 0. Çıkarımını somut başlıklarla gerekçelendir.'),
    ('K8', 'historical_transparency', 'Geçmiş Veri Şeffaflığı',
     'Aynı kongrenin geçmiş programı, proceedings/abstract book, konuşmacı/katılımcıları, fotoğrafları, sonuçları veya eski sitesi gibi anlamlı veriye erişilmişse 1. Sadece açılmamış arşiv bağlantısı kanıt değildir. Doğrulanabilir geçmiş yoksa 0.'),
    ('K9', 'international_scope', 'Uluslararası Kapsam',
     'Birden fazla ülkeden katılımcı, akademisyen, konuşmacı, bilim kurulu üyesi veya kurum güvenilir biçimde belirtilmişse 1. Önceki yılların uluslararası yapısı kullanılabilir; yılı belirt. Yalnız International adı, davet veya temelsiz iddia yetmez; 0.'),
    ('K10', 'participant_satisfaction', 'Katılımcı Memnuniyeti',
     'Güvenilir olumlu memnuniyet verisi 1. Yalnız açık, güvenilir, kayda değer olumsuz veri (örneğin çok sayıda doğrulanabilir katılımcı şikâyeti) 0. Tek anonim yorum yeterli değil. Veri/olumsuz kanıt yoksa proje varsayılanı 1; bu memnuniyetin kanıtı değildir, güven Düşük. Çözülemeyen çelişkide de varsayılanı açıkça belirt.'),
]

def policy_definitions():
    return [{'code':code, 'key':key, 'name':name, 'description':rule,
             'default_score':1 if code=='K10' else 0} for code,key,name,rule in CRITERIA]

def confidence_label(value):
    return 'Yüksek' if value >= .8 else 'Orta' if value >= .5 else 'Düşük'

def cpci_direction_conflict(finding):
    quotes=' '.join(e['quote'] for e in finding['evidence'])
    return finding['value'] is True and bool(re.search(
        r"not (?:currently |yet )?index|never index|not (?:included|covered)|no CPCI|CPCI.{0,40}(?:not|excluded)|indekslenme(?:di|miş|mektedir)|indeksli değil|kapsamında değil", quotes, re.I))

def cpci_confirmed(finding):
    quotes=' '.join(e['quote'] for e in finding['evidence'])
    explicit=re.search(r'\bCPCI(?:-S|-SSH)?\b|Conference Proceedings Citation Index', quotes, re.I)
    pending=re.search(r'will be|may be|submitted|submission|pending|applied|aim to|expected|başvur|gönderile|gönderilmiş|indekslenecek|hedeflen|planlan', quotes, re.I)
    negative=re.search(r'not (?:currently )?index|not (?:included|covered)|no CPCI|CPCI.{0,40}(?:not|excluded)|indekslenme(?:di|miş)|kapsamında değil', quotes, re.I)
    direction_supported=(finding['value'] is True and not cpci_direction_conflict(finding)) or (finding['value'] is False and bool(negative))
    return bool(explicit) and not pending and direction_supported and finding['confidence'] >= .8

def apply_policy(validated, sources, model, analysis_date):
    """Apply defaults only after exact-quote validation; never fabricate evidence."""
    analysis=validated
    for f in analysis['findings']:
        code=f['criterion']
        years=set(re.findall(r'\b(?:19|20)\d{2}\b',analysis['metadata'].get('edition','')))
        quoted_years=set(re.findall(r'\b(?:19|20)\d{2}\b',' '.join(e['quote'] for e in f['evidence'])))
        if code=='K1' and (f['status']=='conflict' or cpci_direction_conflict(f) or (f['value'] is True and years and quoted_years and years!=quoted_years)):
            f.update(value=None, score=None, status='conflict', basis='review_required', confidence=0,
                     confidence_label='Düşük', ai_explanation=f['explanation'],
                     explanation='CPCI kararı kaynak yönü veya edisyonuyla çelişiyor. İnsan incelemesi gerekiyor; puan atanmadı.')
            f['flags'].append('EVIDENCE_DECISION_CONFLICT')
            continue
        usable=f['value'] is not None
        f['ai_explanation']=f['explanation']
        if code=='K1' and usable and not cpci_confirmed(f):
            usable=False
            f['flags'].append('CPCI_NOT_CONFIRMED')
        if code=='K10' and f['value'] is False and f['confidence'] < .8:
            usable=False
            f['flags'].append('NEGATIVE_EVIDENCE_UNCERTAIN')
        f['basis']='evidence' if usable else 'project_default'
        if not usable:
            if f['status']=='detected': f['status']='not_found'
            f['value']=code=='K10'
            f['confidence']=0
            f['flags'].append('PROJECT_DEFAULT')
            reason=('Katılımcı memnuniyetine ilişkin doğrulanabilir olumsuz veri bulunamadığı için proje kuralı gereği 1 verilmiştir. Bu puan memnuniyetin kanıtı değildir.' if code=='K10'
                    else 'Kriterin karşılandığı yeterli kanıtla doğrulanamadığı için proje kuralı gereği 0 verilmiştir. Bilgi eksikliği kesin bir olumsuz bulgu değildir.')
            qualifier=(' Kaynaklar çeliştiği için kesin bir bulgu kabul edilmedi.' if f['status']=='conflict'
                       else ' AI alıntısı belirtilen kaynakta doğrulanamadı; bu tespit puana katılmadı.' if 'UNVERIFIED_EVIDENCE' in f['flags']
                       else ' Açık CPCI indeks kanıtı yok; başka bir indekste bulunmak CPCI durumunu kanıtlamaz.' if code=='K1'
                       else ' Sunulan kaynaklar bu konuda yeterli doğrulanabilir bilgi sağlamadı.')
            f['explanation']=reason+qualifier
        f['score']=int(f['value'])
        f['confidence_label']=confidence_label(f['confidence'])
    known=[f for f in analysis['findings'] if f['basis']=='evidence']
    weight=sum(model['weights'][f['criterion']] for f in known)
    analysis['confidence']=sum(f['confidence']*model['weights'][f['criterion']] for f in known)/weight if weight else None
    analysis['completeness']=len(known)/10
    analysis['evidence_coverage']=weight
    analysis['utilities']={f['criterion']:f['score'] for f in analysis['findings']}
    analysis['result']=score(model['weights'],analysis['utilities'],model['thresholds'])
    analysis['policy_version']=POLICY_VERSION
    analysis['raw_score']=sum(analysis['utilities'].values()) if all(v is not None for v in analysis['utilities'].values()) else None
    analysis['assigned_coverage']=analysis['result']['coverage']
    analysis['max_score']=10
    analysis['general_explanation']=(f"10 kriterin {len(known)} tanesi kaynak kanıtıyla değerlendirildi; {sum(f['basis']=='project_default' for f in analysis['findings'])} tanesine proje varsayılanı uygulandı. Çelişki nedeniyle puansız kalan kriterler ayrıca inceleme gerektirir. "
        'Ham puan 0/1 değerlerinin toplamıdır. AHP puanı mevcut model ağırlıklarıyla ayrıca hesaplanmıştır. Güven, AI değerlendirmesidir; alıntı eşleşmesi bağımsız doğrulama değildir.')
    analysis['warnings']=[w.replace('kriter bilinmiyor bırakıldı.', 'proje varsayılanı uygulandı.') for w in analysis['warnings']]
    analysis['report']=report_projection(analysis,sources,analysis_date)
    return analysis

def report_projection(analysis, sources, analysis_date):
    lookup={(s['id'],p['id']):(s,p) for s in sources for p in s['segments']}
    names={code:key for code,key,_,_ in CRITERIA}
    scores={}
    for f in analysis['findings']:
        refs=[]
        for e in f['evidence']:
            source,segment=lookup[(e['source_id'],e['segment_id'])]
            refs.append({'name':segment.get('label') or source.get('label',''), 'url':segment.get('url') or source.get('url',''),
                         'page':segment.get('page'), 'retrieved_at':source.get('retrieved_at',''), **e})
        scores[names[f['criterion']]]={'score':f['score'],'reason':f['explanation'],
            'evidence':' | '.join(e['quote'] for e in f['evidence']),
            'source':' | '.join(r['url'] or r['name'] or r['source_id'] for r in refs),
            'confidence':f['confidence_label'],'basis':f['basis'],'references':refs,
            'state':f.get('state'), 'checks':f.get('checks',{}), 'contribution':analysis['result']['contributions'][f['criterion']]}
    meta=analysis['metadata']
    return {'congress_name':meta.get('name',''),'congress_year':meta.get('edition',''),
            'analysis_date':analysis_date,'scores':scores,'raw_score':analysis['raw_score'],'max_score':10,
            'general_explanation':analysis['general_explanation'],'policy_version':analysis['policy_version'],
            'ahp_result':analysis['result']}
