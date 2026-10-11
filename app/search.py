"""Bounded web search adapters. Search services retrieve evidence, never score AHP."""
from dataclasses import dataclass, field
import ipaddress
import json
from typing import Literal
from urllib.parse import quote, urlsplit
import httpx
from app.network import client_options, NetworkPolicyError
from app.connection_errors import ConnectionFailure, status_failure, transport_failure

SearchProviderId = Literal['jina', 'tavily']
SEARCH_PROVIDERS = {'jina': 'Jina AI Search', 'tavily': 'Tavily'}

@dataclass(frozen=True)
class SearchConnection:
    provider_id: SearchProviderId
    key: str = field(repr=False)

def safe_result_url(value):
    if not isinstance(value, str) or len(value)>2000: return False
    try:
        u=urlsplit(value)
        host=(u.hostname or '').lower().rstrip('.')
        if u.scheme not in ('http','https') or not host or u.username or u.password or u.port not in (None,80,443): return False
        if host in ('localhost','testserver') or host.endswith(('.local','.localhost','.internal')): return False
        try: return ipaddress.ip_address(host).is_global
        except ValueError: return '.' in host
    except ValueError: return False

def search_web(query, connection):
    name=SEARCH_PROVIDERS[connection.provider_id]
    if not connection.key: raise ValueError(name+' API anahtarı kayıtlı değil. AI bağlantısından ekleyin.')
    query=query.strip()
    if not 3<=len(query)<=500: raise ValueError('Arama sorgusu 3–500 karakter olmalıdır.')
    headers={'Authorization':'Bearer '+connection.key,'Accept':'application/json'}
    if connection.provider_id=='jina':
        method='GET';url='https://s.jina.ai/'+quote(query,safe='')
        options={'params':{'count':3}}
    else:
        method='POST';url='https://api.tavily.com/search'
        options={'json':{'query':query,'search_depth':'basic','max_results':3,'include_answer':False,
                         'include_raw_content':'text','include_images':False,'auto_parameters':False}}
    try:
        with httpx.Client(timeout=httpx.Timeout(60,connect=10),follow_redirects=False,**client_options(url)) as client:
            with client.stream(method,url,headers=headers,**options) as response:
                status=response.status_code
                if status!=200: raise status_failure(name,status)
                body=bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body)>2_000_000: raise ConnectionFailure(name,'RESPONSE_TOO_LARGE',message='API yanıtı çok büyük. Daha belirli bir sorgu kullanın.')
        payload=json.loads(body)
    except ConnectionFailure: raise
    except NetworkPolicyError as error: raise ConnectionFailure(name,'NETWORK_POLICY',message=str(error)) from None
    except Exception as error: raise transport_failure(name,error) from None
    rows=payload.get('data' if connection.provider_id=='jina' else 'results') if isinstance(payload,dict) else None
    if not isinstance(rows,list): raise ValueError(name+' arama sonuçları okunamadı.')
    results=[];seen=set()
    for row in rows:
        if not isinstance(row,dict): continue
        url=row.get('url')
        if not safe_result_url(url) or url in seen: continue
        full=row.get('content') if connection.provider_id=='jina' else row.get('raw_content')
        excerpt=row.get('description') if connection.provider_id=='jina' else row.get('content')
        text=full or excerpt
        if not isinstance(text,str) or len(text.strip())<20: continue
        seen.add(url)
        results.append({'url':url,'label':str(row.get('title') or url)[:200],
                        'text':text[:12000],'excerpt_only':not bool(full),
                        'truncated':len(text)>12000,'published_date':str(row.get('published_date') or '')[:80]})
        if len(results)==3:break
    if not results: raise ValueError(name+' bu sorgu için okunabilir kaynak bulamadı. Kongre adı ve yılını belirtin veya doğrudan kaynak ekleyin.')
    return results
