"""Lossless source batching and conservative, citation-checked result merging."""
import copy
from app.ai_schemas import ProviderOutput, Finding
from app.sources import clean
from app.services import ConflictError

SOURCE_CHARS = 5000
MIN_SOURCE_CHARS = 500
MAX_BATCH_REQUESTS = 64

def source_size(sources):
    return sum(len(p['text']) for s in sources for p in s['segments'])

def split_sources(sources, limit=SOURCE_CHARS):
    """Keep IDs and page provenance, overlap cuts so short quotes remain intact.

    Two fragments of the same segment never share a batch: its citation ID must
    identify exactly one passage during per-batch validation.
    """
    batches=[]; batch=[]; size=0; ids=set()
    for source in sources:
        for segment in source['segments']:
            text=segment['text']; start=0
            while start<len(text):
                end=min(len(text),start+limit)
                # Prefer a word boundary without losing any source characters.
                if end<len(text):
                    boundary=text.rfind(' ',start+limit//2,end)
                    if boundary>start:end=boundary
                piece=text[start:end]; pair=(source['id'],segment['id'])
                if batch and (size+len(piece)>limit or pair in ids):
                    batches.append(batch);batch=[];size=0;ids=set()
                target=next((s for s in batch if s['id']==source['id']),None)
                if target is None:
                    target={**copy.deepcopy(source),'segments':[]};batch.append(target)
                target['segments'].append({**segment,'text':piece})
                size+=len(piece);ids.add(pair)
                if end==len(text):break
                start=end-min(220,limit//3)
    if batch:batches.append(batch)
    return batches or [copy.deepcopy(sources)]

def checked_output(output, sources):
    """A response may only cite the fragments actually sent in that request."""
    passages={(s['id'],p['id']):clean(p['text']) for s in sources for p in s['segments']}
    def valid(e):return clean(e.quote) in passages.get((e.source_id,e.segment_id),'')
    facts=[f for f in output.facts if all(valid(e) for e in f.evidence)]
    findings=[]
    for f in output.findings:
        if f.evidence and all(valid(e) for e in f.evidence):findings.append(f)
        else:
            findings.append(Finding(criterion=f.criterion,value=None,status='not_found',confidence=0,
                explanation='Bu parçada doğrulanabilir kanıt bulunamadı.',evidence=[]))
    return ProviderOutput(facts=facts,findings=findings)

def merge_outputs(outputs):
    """Missing evidence is not a negative vote; contradictory findings stay unknown.

    Never ask the model to invent a summary quote or average binary AHP values.
    The existing policy engine still assigns all defaults and calculates scores.
    """
    if len(outputs)==1:return outputs[0]
    facts=[];seen=set()
    for output in outputs:
        for fact in output.facts:
            key=(fact.field,clean(fact.value).casefold())
            if key not in seen:facts.append(fact);seen.add(key)
    if len(facts)>40:
        raise ConflictError('Kaynaklarda çok fazla farklı kongre bilgisi bulundu. Aynı kongre ve edisyona ait kaynaklarla tekrar deneyin; kısmi sonuç puanlanmadı.')
    findings=[]
    for i in range(1,11):
        code=f'K{i}'
        candidates=[f for o in outputs for f in o.findings if f.criterion==code and f.evidence
                    and (f.status=='conflict' or (f.status=='detected' and f.value is not None))]
        if not candidates:
            findings.append(Finding(criterion=code,value=None,status='not_found',confidence=0,
                explanation='İncelenen kaynak parçalarında doğrulanabilir kanıt bulunamadı.',evidence=[]));continue
        conflict=any(f.status=='conflict' for f in candidates) or len({f.value for f in candidates})>1
        # Round-robin by decision preserves both sides of a conflict within 8 citations.
        groups={}
        for f in sorted(candidates,key=lambda f:f.confidence,reverse=True):
            group=groups.setdefault((f.status,f.value),[])
            for e in f.evidence:
                if e not in group:group.append(e)
        evidence=[]
        for pos in range(8):
            for group in groups.values():
                if pos<len(group) and group[pos] not in evidence:evidence.append(group[pos])
        best=max(candidates,key=lambda f:f.confidence)
        explanation=('Kaynak parçalarında çelişen bulgular var; inceleme gereklidir. '
                     if conflict else 'Kaynak parçaları birlikte değerlendirildi. ')
        explanations=list(dict.fromkeys(f.explanation for f in candidates))
        explanation+=' '.join(explanations)
        findings.append(Finding(criterion=code,value=None if conflict else best.value,
            status='conflict' if conflict else 'detected',confidence=0 if conflict else best.confidence,
            explanation=explanation[:2000],evidence=evidence[:8]))
    return ProviderOutput(facts=facts,findings=findings)
