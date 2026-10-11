"""Deterministic organizational fingerprints; similarity is not congress quality."""
import hashlib
import json
import re
from urllib.parse import urlsplit
from app.text_similarity import normalize_text, normalized_list, jaccard, LocalTextSimilarity
from app.intelligence_config import weighted_available

FINGERPRINT_VERSION='organization-v1'
PUBLIC_EMAIL_DOMAINS={'gmail.com','yahoo.com','hotmail.com','outlook.com','icloud.com','live.com','mail.com'}

def stable_hash(value) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def normalize_domain(value: str) -> str:
    try:
        host=urlsplit(value if '://' in value else '//'+value).hostname or ''
        return host.casefold().removeprefix('www.').rstrip('.').encode('idna').decode('ascii')
    except (ValueError,UnicodeError):return ''

def normalize_organizer(value: str) -> str:
    words=normalize_text(value).replace('organisation','organization').split()
    suffixes={'ltd','limited','inc','incorporated','llc','co','company','sti','sirketi'}
    while words and words[-1] in suffixes:words.pop()
    return ' '.join(words)

def generate_fingerprint(congress: dict, text: LocalTextSimilarity) -> dict:
    meta=congress['metadata'];extra=meta.get('research') or {};raw=congress.get('source_text','')
    emails=extra.get('contact_emails',[])+re.findall(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',raw,re.I)
    emails=sorted({x.strip().casefold() for x in emails if re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',x)})
    phones=extra.get('phones',[])+re.findall(r'(?<!\w)\+\d[\d ()-]{8,22}\d',raw)
    phones=sorted({re.sub(r'\D','',p) for p in phones if 8<=len(re.sub(r'\D','',p))<=15})
    prefixes=extra.get('doi_prefixes',[])+re.findall(r'\b10\.\d{4,9}(?=/|\b)',raw)
    prefixes=sorted({p for p in prefixes if re.fullmatch(r'10\.\d{4,9}',p)})
    host=normalize_domain(meta.get('website',''))
    # Preserve the full host: sibling sites on shared hosting are not merged.
    domains=sorted({normalize_domain(e.split('@')[1]) for e in emails})
    signature=sorted(set(text.tokens(congress.get('academic_text',''))))
    data={
        'version':FINGERPRINT_VERSION,'organizer_normalized':normalize_organizer(meta.get('organizer','')),
        'congress_name_normalized':normalize_text(meta.get('name','')),
        'website_domain':host,'contact_emails':emails,'email_domains':domains,'phones':phones,
        'committee_members_normalized':normalized_list(extra.get('committee_members',[])),
        'speaker_names_normalized':normalized_list(extra.get('speaker_names',[])),
        'address_normalized':normalize_text(extra.get('address','')),
        'country':normalize_text(extra.get('country','')),
        'doi_prefixes':prefixes,'publisher_names':normalized_list(extra.get('publishers',[])),
        'proceedings':normalize_text(extra.get('proceedings','')),
        'fee_structure':normalize_text(extra.get('fee','')),
        'past_congresses':normalized_list(extra.get('past_congresses',[])),
        'past_years':sorted(set(extra.get('past_years',[]))),
        'social_links':sorted(set(extra.get('social_links',[]))),
        'text_signature':signature,
    }
    data['fingerprint_hash']=stable_hash(data)
    return data

def calculate_fingerprint_similarity(a: dict, b: dict, config: dict, text: LocalTextSimilarity) -> dict:
    def exact(key):return (100.0 if a[key]==b[key] else 0.0) if a.get(key) and b.get(key) else None
    publications=[]
    for key in ('doi_prefixes','publisher_names'):
        v=jaccard(a.get(key,[]),b.get(key,[]))
        if v is not None:publications.append(v)
    email_a=set(a.get('email_domains',[]))-PUBLIC_EMAIL_DOMAINS
    email_b=set(b.get('email_domains',[]))-PUBLIC_EMAIL_DOMAINS
    linked = ((a.get('congress_name_normalized') and a['congress_name_normalized'] in b.get('past_congresses',[]))
              or (b.get('congress_name_normalized') and b['congress_name_normalized'] in a.get('past_congresses',[])))
    components={
        'organizer':text.similarity(a.get('organizer_normalized',''),b.get('organizer_normalized','')),
        'domain':exact('website_domain'),'email_domains':jaccard(email_a,email_b),
        'committee':jaccard(a.get('committee_members_normalized',[]),b.get('committee_members_normalized',[])),
        'text':text.similarity(' '.join(a.get('text_signature',[])),' '.join(b.get('text_signature',[]))),
        'address':text.similarity(a.get('address_normalized',''),b.get('address_normalized','')),
        'publication':sum(publications)/len(publications) if publications else None,
        # Shared years alone are not evidence of a shared organization.
        'history':100.0 if linked else jaccard(a.get('past_congresses',[]),b.get('past_congresses',[])),
    }
    total,coverage=weighted_available(components,config['fingerprint_weights'])
    thresholds=config['fingerprint_thresholds']
    level=None if total is None else ['Düşük Benzerlik','Orta Benzerlik','Yüksek Benzerlik','Çok Yüksek Benzerlik'][sum(total>=t for t in thresholds)]
    labels={'organizer':'Organizatör adı','domain':'Web domaini','email_domains':'E-posta domainleri','committee':'Komite üyeleri','text':'Kongre metni','address':'Adres','publication':'DOI / yayınevi','history':'Geçmiş kongre adları'}
    shared=[{'feature':key,'label':labels[key],'similarity':round(value,2)} for key,value in components.items() if value is not None and value>0]
    return {'score':None if total is None else round(total,2),'level':level,'coverage':round(coverage*100,2),
            'components':components,'shared_features':shared,
            'limited_evidence':sum(v is not None for v in components.values())<2 or coverage<.4,
            'message':'Organizasyonel benzerlik, aynı kongre veya yüksek kalite anlamına gelmez.'}
