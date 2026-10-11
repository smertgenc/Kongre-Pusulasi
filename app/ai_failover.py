"""Bounded provider failover with durable, citation-checked chunk checkpoints.

Only the explicit job plan may receive text. Credentials remain in memory;
checkpoints contain sources/results, never keys or raw upstream error bodies.
"""
import copy
import hashlib
import json
from app.ai_batches import (split_sources, source_size, checked_output, merge_outputs,
                            SOURCE_CHARS, MIN_SOURCE_CHARS, MAX_BATCH_REQUESTS)
from app.ai_provider import ProviderError, PROMPT_VERSION
from app.ai_schemas import ProviderOutput
from app.services import ConflictError

FAILOVER_CODES = frozenset({
    'RATE_LIMIT', 'QUOTA_EXHAUSTED', 'REQUEST_TOO_LARGE', 'OUTPUT_TOKEN_LIMIT',
    'SERVICE_UNAVAILABLE', 'TIMEOUT', 'CONNECTION_ERROR', 'DNS_ERROR',
    'AUTH_ERROR', 'ACCESS_DENIED', 'MODEL_UNAVAILABLE', 'INVALID_REQUEST', 'OUTPUT_SCHEMA_ERROR',
})


def public_connection(connection):
    return {'provider_id':connection.provider_id, 'provider_name':connection.provider.name,
            'provider_model':connection.model}


class AnalysisRunner:
    def __init__(self, connections, data, *, factory, progress, save):
        self.connections=connections
        self.data=data
        self.factory=factory
        self.progress=progress
        self.save=save
        self.index=0
        self.providers={}
        self.pace=set()

    def emit(self, phase, **event):
        state=self.data['execution']
        self.progress({**public_connection(self.connections[self.index]),
                       'batch':len(state['completed'])+1,
                       'batches':len(state['completed'])+len(state['pending']),
                       'phase':phase, **event})

    def checkpoint(self):
        completed=self.data['execution']['completed']
        self.data['completed_batches']=len(completed)
        used={}
        for item in completed:
            key=(item['provider_id'],item['provider_model'])
            if key not in used:
                used[key]={k:item[k] for k in ('provider_id','provider_name','provider_model')}
                used[key]['batches']=0
            used[key]['batches']+=1
        self.data['providers_used']=list(used.values())
        self.save()

    def run(self):
        # Image bytes stay in the source archive; they must not be copied once
        # per chunk or sent to providers as part of a checkpoint.
        sources=[{k:v for k,v in s.items() if k not in ('image','ocr')} for s in self.data['sources']]
        identity={'sources':sources,'context':self.data['context'],
                  'method':self.data['method'],'prompt_version':PROMPT_VERSION}
        fingerprint=hashlib.sha256(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        state=self.data.get('execution')
        if state is not None:
            if state.get('version')!=1 or state.get('fingerprint')!=fingerprint:
                raise ConflictError('Kayıtlı ilerleme bu kaynak ve AHP yöntemiyle eşleşmiyor. Kaynakları düzenleyerek yeni analiz başlatın.')
        else:
            state={'version':1,'fingerprint':fingerprint,'pending':[copy.deepcopy(sources)],'completed':[]}
            self.data['execution']=state
        self.checkpoint()
        requests=0
        while state['pending']:
            connection=self.connections[self.index]
            self.data.update(public_connection(connection))
            batch=state['pending'][0]
            # Fit Groq before sending; other providers can analyze the full text
            # in one call and only split after a real context/output limit.
            if connection.provider_id=='groq' and source_size(batch)>SOURCE_CHARS:
                state['pending'][:1]=split_sources(batch)
                self.checkpoint()
                batch=state['pending'][0]
            if requests>=MAX_BATCH_REQUESTS:
                raise ProviderError('Bu denemenin istek sınırına ulaşıldı. Tamamlanan parçalar saklandı; kayıtlı kaynaklarla tekrar deneyerek devam edebilirsiniz.',code='REQUEST_BUDGET_EXCEEDED')
            provider=self.providers.get(self.index)
            if provider is None:
                provider=self.factory(connection.provider_id)
                self.providers[self.index]=provider
            provider.prefer_failover=self.index+1<len(self.connections)
            provider.on_progress=lambda event: self.emit(**event)
            self.emit('batch')
            try:
                if self.index in self.pace:
                    self.pace.remove(self.index)
                    provider._pace()
                requests+=1
                output=provider.analyze_chunk(batch,self.data['context'],connection.key,connection.model,
                                              ahp_method=self.data['method'])
                output=checked_output(output,batch)
            except ProviderError as exc:
                code=exc.details['code']
                if code in ('REQUEST_TOO_LARGE','OUTPUT_TOKEN_LIMIT') and source_size(batch)>MIN_SOURCE_CHARS:
                    state['pending'][:1]=split_sources(batch,max(MIN_SOURCE_CHARS,source_size(batch)//2))
                    self.emit('resizing',code=code)
                    self.checkpoint()
                    continue
                # Refusals, SSL/proxy policy failures, malformed local state and
                # programming errors must not be hidden by recipient switching.
                if code not in FAILOVER_CODES:
                    raise
                failure={**public_connection(connection),**exc.details}
                self.data.setdefault('provider_failures',[]).append(failure)
                if self.index+1>=len(self.connections):
                    self.checkpoint()
                    if len(self.connections)==1:raise
                    raise ProviderError('İzin verilen tüm AI sağlayıcıları denendi; şu anda analizi tamamlayabilen servis yok. Tamamlanan parçalar ve kaynaklar saklandı. Kota yenilendiğinde veya bağlantı düzeldiğinde kayıtlı kaynaklarla tekrar deneyerek devam edebilirsiniz.',
                                        code='ALL_PROVIDERS_UNAVAILABLE',retryable=True) from None
                previous=connection.provider.name
                self.index+=1
                self.data.update(public_connection(self.connections[self.index]))
                self.emit('provider_switch',previous_provider=previous,code=code,
                          completed_batches=len(state['completed']))
                continue
            state['completed'].append({**public_connection(connection),'output':output.model_dump()})
            state['pending'].pop(0)
            if connection.provider_id=='groq':self.pace.add(self.index)
            self.checkpoint()
            self.emit('checkpoint',completed_batches=len(state['completed']),
                      batch=len(state['completed']))
        self.emit('merging',batch=len(state['completed']))
        return merge_outputs([ProviderOutput.model_validate(item['output']) for item in state['completed']])
