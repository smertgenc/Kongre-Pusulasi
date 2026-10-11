"""Opt-in source-evidence policy. Not an independent index verification service."""
import re
from engine import score
from app.congress_policy import policy_definitions, cpci_confirmed, cpci_direction_conflict, report_projection

VERSION='congress-evidence-v1'
PROFILE='congress-source-evidence-v1'
STATES=('positive','negative','unknown','not_applicable','conflict')

def definitions():
    rules={
        'K1':'Aynı kongre adı, güncel edisyon/yıl, bildiri cildi ve ISBN/DOI kimliğiyle açık gerçekleşmiş CPCI indekslemesi true, açık doğrulanabilir indekslenmeme false. Başvuru, vaat, genel Web of Science veya önceki edisyon yetmez.',
        'K2':'Resmi bilim/düzenleme kurulu veya akademik konuşmacı/uzmanların varlığı true. Açıkça akademik temsiliyet bulunmadığına ilişkin güvenilir kanıt false. Kişisel kabul eşiği aranmaz.',
        'K3':'Yalnız kayıt/katılım ücreti: kategori, para birimi ve güvenilir karşılaştırma göster. Ücretsiz veya belgeli düşük/makul ücret true, belgeli yüksek ücret false. Kişisel bütçe/otel/ulaşım dahil değil; karşılaştırma yoksa null.',
        'K4':'Kaynakla belirtilmiş gerçekleştirilebilir yüz yüze/online/hibrit format true. Açık gerçekleştirilememe kanıtı false. Kişisel tercih koşulu aranmaz.',
        'K5':'Fiziksel yerin erişilebilirliğini kaynakla değerlendir. Merkez/üniversite/ulaşım kanıtını çıkarımdan ayır. Açıkça tamamen online kongrede fiziksel konum uygulanamaz; null bırak.',
        'K6':'Aynı kongrenin en az bir geçmiş gerçekleşmiş edisyonu true. İlk edisyon olduğu doğrulanmışsa false. Yalnız gelecek etkinlik vaadi geçmiş sayılmaz.',
        'K7':'Somut çağrı, oturum ve program üzerinden bilimsel yenilik/anlamlı güncel problem varsa true, açık yüzeysel içerik için gerekçeli false. Anlamsal çıkarımı belirt; yalnız moda kelime veya isme göre karar verme.',
        'K8':'Aynı kongrenin anlamlı eski program/kurul/bildiri/sonuç kayıtlarına gerçekten erişilmişse true. Açık erişilemezlik/şeffaflık yokluğu kanıtı false. Sadece açılmamış arşiv bağlantısı yeterli değil.',
        'K9':'Birden fazla ülkeden fiili katılımcı/akademisyen/kurum kanıtı true. Aksi açıkça doğrulanırsa false. International adı veya davet yeterli değil. Geçmiş verinin yılını belirt.',
        'K10':'Dönemi, kaynağı ve örneklemi belli memnuniyet bulgusu: desteklenmiş olumlu true, güçlü güvenilir olumsuz false. Tek anonim yorum yetmez. Veri yoksa null; varsayılan 1 verme.'}
    return [{**c,'default_score':None,'description':rules[c['code']]+' Kanıt yoksa value=null, status=not_found. Çözülemeyen çelişkide value=null, status=conflict. Varsayılan 0 veya 1 atama.'} for c in policy_definitions()]

def cpci_identity(finding, metadata):
    text=' '.join(e['quote'] for e in finding['evidence']).casefold()
    name=metadata.get('name','').strip().casefold(); edition=metadata.get('edition','').strip().casefold()
    years=set(re.findall(r'\b(?:19|20)\d{2}\b',edition)); quoted=set(re.findall(r'\b(?:19|20)\d{2}\b',text))
    if years and quoted and years!=quoted:return 'conflict'
    edition_ok=bool(edition) and (years.issubset(quoted) if years else edition in text)
    identifier=bool(re.search(r'\b(?:isbn\s*[:\-]?\s*[0-9][0-9\- ]{8,}|(?:doi\s*:?\s*)?10\.\d{4,9}/\S+)',text))
    return 'matched' if name and name in text and edition_ok and identifier and re.search(r'proceedings|bildiri|volume|cilt',text) else 'missing'

def apply_scientific_policy(analysis, sources, model, analysis_date):
    for f in analysis['findings']:
        f['ai_explanation']=f['explanation']; state='conflict' if f['status']=='conflict' else 'unknown' if f['value'] is None else 'positive' if f['value'] else 'negative'
        checks={'quote_match':bool(f['evidence']) and 'UNVERIFIED_EVIDENCE' not in f['flags'], 'independent_verification':False}
        if f['criterion']=='K1' and f['value'] is not None:
            identity=cpci_identity(f,analysis['metadata']);checks['publication_identity']=identity
            if cpci_direction_conflict(f) or identity=='conflict':state='conflict'
            elif not cpci_confirmed(f) or identity!='matched':state='unknown'
            if state in ('conflict','unknown'):f['explanation']+=' CPCI edisyon/cilt/kanıt yönü kontrolü kesin puanı desteklemiyor; uzman incelemesi gerekiyor.'
        if f['criterion']=='K10' and f['value'] is False and f['confidence']<.8:state='unknown'
        if f['criterion']=='K5' and state!='conflict':
            fmt=analysis['metadata'].get('format','').casefold()
            k4=next(x for x in analysis['findings'] if x['criterion']=='K4')
            text=' '.join(e['quote'] for e in k4['evidence'])
            if k4['value'] is True and ('online' in fmt or 'çevrim' in fmt) and not any(x in fmt for x in ('hibrit','hybrid','yüz','face','in-person')) and re.search(r'online.only|exclusively online|entirely online|tamamen çevrim|yalnızca çevrim',text,re.I):
                state='not_applicable';f['explanation']='Tamamen çevrim içi kongrede fiziksel konum uygulanamaz. Ağırlıklar yeniden dağıtılmadı; aralık raporlanır.'
        f['state']=state;f['checks']=checks
        if state not in ('positive','negative'):f['value']=None
        f['score']=None if f['value'] is None else int(f['value'])
        f['basis']='evidence' if f['score'] is not None else 'review_required' if state=='conflict' else state
        f['confidence_label']='Kalibre edilmemiş AI tahmini' if f['score'] is not None else 'Yeterli kanıt yok'
    known=[f for f in analysis['findings'] if f['score'] is not None]
    analysis.update(policy_version=VERSION,criteria_profile=PROFILE,decision_date=analysis_date,
                    utilities={f['criterion']:f['score'] for f in analysis['findings']},confidence=None,
                    completeness=len(known)/10,evidence_coverage=sum(model['weights'][f['criterion']] for f in known))
    analysis['result']=score(model['weights'],analysis['utilities'],model['thresholds'])
    analysis['assigned_coverage']=analysis['result']['coverage']
    analysis['raw_score']=sum(analysis['utilities'].values()) if len(known)==10 else None
    analysis['max_score']=10
    analysis['general_explanation']='Bilimsel kanıt politikası: bilinmiyor, uygulanamaz ve çelişkili kriterler null kalır. Sabit AHP ağırlıklarıyla alt/üst sınır gösterilir; eksik kriter ağırlıkları dağıtılmaz. Alıntı eşleşmesi bağımsız kaynak doğrulaması değildir. AI güveni başarı olasılığı değildir.'
    analysis['report']=report_projection(analysis,sources,analysis_date)
    analysis['report'].update(criteria_profile=PROFILE,weights=model['weights'],model_id=model['id'],model_version=model['version'],evidence_coverage=analysis['evidence_coverage'],assigned_coverage=analysis['assigned_coverage'])
    return analysis
