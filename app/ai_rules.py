"""Evidence validation and a deterministic binary rule feeding the existing AHP engine."""
from app.sources import clean
from engine import score

RULE_VERSION='binary-evidence-v2'

def validate_evidence(output, sources, model):
    segments={(s['id'],p['id']):p['text'] for s in sources for p in s['segments']}
    def valid(e):
        return clean(e.quote) in segments.get((e.source_id,e.segment_id),'')
    findings=[]; warnings=[]
    for f in sorted(output.findings,key=lambda f:int(f.criterion[1:])):
        item=f.model_dump(); item['flags']=[]
        all_valid=bool(f.evidence) and all(valid(e) for e in f.evidence)
        item['evidence']=[e.model_dump() for e in f.evidence if valid(e)]
        if f.status=='conflict': item['flags'].append('SOURCE_CONFLICT')
        if f.status!='detected' or f.value is None or not all_valid:
            item['value']=None; item['confidence']=0
            if f.status=='detected': item['status']='not_found'
            if not all_valid and f.status=='detected':
                item['flags'].append('UNVERIFIED_EVIDENCE')
                item['explanation']='Alıntı belirtilen kaynakta birebir doğrulanamadığı için bu tespit puana katılmadı. AI açıklaması: '+f.explanation
                warnings.append(f.criterion+': kaynakta doğrulanamayan alıntı nedeniyle kriter bilinmiyor bırakıldı.')
            item['flags'].append('MISSING_INFORMATION')
        elif f.confidence<.75: item['flags'].append('LOW_CONFIDENCE')
        findings.append(item)
    facts=[]; candidates={}
    for f in output.facts:
        if f.evidence and all(valid(e) for e in f.evidence) and f.value.strip():
            facts.append(f.model_dump()); candidates.setdefault(f.field,[]).append(f.value)
        else: warnings.append('Kongre bilgisi için kaynakta eşleşmeyen bir kanıt çıkarıldı.')
    metadata={}; conflicts=[]
    for field,values in candidates.items():
        unique=list(dict.fromkeys(values))
        if len({clean(v).casefold() for v in unique})>1:
            conflicts.append({'field':field,'values':unique,'flag':'SOURCE_CONFLICT'})
        else: metadata[field]=unique[0]
    utilities={f['criterion']:None if f['value'] is None else int(f['value']) for f in findings}
    known=[f for f in findings if f['value'] is not None]
    coverage=sum(model['weights'][f['criterion']] for f in known)
    confidence=sum(f['confidence']*model['weights'][f['criterion']] for f in known)/coverage if coverage else None
    return {'findings':findings,'facts':facts,'metadata':metadata,'conflicts':conflicts,'warnings':warnings,
            'utilities':utilities,'result':score(model['weights'],utilities,model['thresholds']),
            'confidence':confidence,'completeness':len(known)/10,'rule_version':RULE_VERSION}
