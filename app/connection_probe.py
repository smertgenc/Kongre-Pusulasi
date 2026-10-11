"""One small real request to the saved AI service; no congress data or retries."""
from urllib.parse import quote, urlsplit
import httpx
from app.network import client_options, NetworkPolicyError
from app.connection_errors import ConnectionFailure, status_failure, transport_failure
from app.ai_provider import response_error

def test_ai_connection(connection):
    spec=connection.provider
    if not connection.key: raise ValueError(spec.name+' API anahtarı kayıtlı değil. Önce bağlantı ayarlarını kaydedin.')
    text='Reply with OK only.'
    endpoint=spec.endpoint
    if spec.id=='gemini':
        endpoint+=quote(connection.model.removeprefix('models/'),safe='')+':generateContent'
        headers={'x-goog-api-key':connection.key}
        payload={'contents':[{'parts':[{'text':text}]}],'generationConfig':{'maxOutputTokens':64}}
        output_field='candidates'
    else:
        headers={'Authorization':'Bearer '+connection.key}
        if spec.id=='openai':
            payload={'model':connection.model,'input':text,'store':False,'max_output_tokens':64}
            output_field='output'
        else:
            payload={'model':connection.model,'messages':[{'role':'user','content':text}],
                     'max_completion_tokens' if spec.id=='groq' else 'max_tokens':64}
            output_field='choices'
    try:
        with httpx.Client(timeout=httpx.Timeout(45,connect=10),follow_redirects=False,**client_options(endpoint)) as client:
            response=client.post(endpoint,headers=headers,json=payload)
        if not response.is_success:
            # Gemini sometimes returns HTTP 400 for an invalid API key.
            detail=response_error(spec,response)
            if detail.details['code'] in ('AUTH_ERROR','MODEL_UNAVAILABLE'):
                raise ConnectionFailure(spec.name,detail.details['code'],status=response.status_code,
                                        message=str(detail).removeprefix(spec.name+': ').removeprefix(spec.name+' '))
            raise status_failure(spec.name,response.status_code)
        data=response.json()
        if not isinstance(data,dict) or not isinstance(data.get(output_field),list) or not data[output_field]:
            raise RuntimeError('UNEXPECTED_API_RESPONSE')
    except ConnectionFailure: raise
    except NetworkPolicyError as error: raise ConnectionFailure(spec.name,'NETWORK_POLICY',message=str(error)) from None
    except Exception as error: raise transport_failure(spec.name,error) from None
    return {'ok':True,'message':'Bağlantı başarılı','provider_id':spec.id,'provider':spec.name,
            'model':connection.model,'host':urlsplit(endpoint).hostname}
