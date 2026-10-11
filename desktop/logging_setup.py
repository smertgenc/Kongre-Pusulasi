"""Diagnostic structure without exception messages, URLs, request bodies or locals."""
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re
import traceback
from datetime import datetime, timezone

class SafeFormatter(logging.Formatter):
    def format(self, record):
        event = getattr(record, 'safe_event', 'runtime_message')
        if not re.fullmatch(r'[a-z_]{1,60}', event): event = 'runtime_message'
        result = {'time':datetime.now(timezone.utc).isoformat(), 'level':record.levelname, 'event':event}
        if getattr(record,'safe_exception',None):
            result['exception'] = record.safe_exception
            result['frames'] = record.safe_frames
        for key in ('code','http_status','causes','service','stage','component','diagnostic'):
            value=getattr(record,'safe_'+key,None)
            if value is not None: result[key]=value
        if record.exc_info and record.exc_info[1]:
            result['exception'] = type(record.exc_info[1]).__name__
            result['frames'] = [{'file':Path(f.filename).name, 'line':f.lineno, 'function':f.name}
                                for f in traceback.extract_tb(record.exc_info[2])]
        return json.dumps(result, ensure_ascii=False)

def configure_logs(directory):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    for old in root.handlers[:]: root.removeHandler(old); old.close()
    for filename, level in (('app.log',logging.INFO),('error.log',logging.ERROR)):
        handler = RotatingFileHandler(directory/filename, maxBytes=2_000_000, backupCount=3, encoding='utf-8')
        handler.setFormatter(SafeFormatter()); handler.setLevel(level); root.addHandler(handler)
    root.setLevel(logging.INFO)
    for name in ('httpx','httpcore','webview','urllib3'):
        logging.getLogger(name).setLevel(logging.CRITICAL)

def startup_diagnostic(error):
    """Every traceback frame/cause, without source lines, locals or raw secrets.

    Arbitrary exception messages may contain an Authorization header or API key.
    Preserve known structural messages; represent other messages by their type.
    """
    chain=[];seen=set();current=error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        message='Hata iletisi hassas veri içerebileceğinden gizlendi.'
        if isinstance(current, ImportError) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]{0,150}',current.name or ''):
            message='Modül yüklenemedi: '+current.name
        elif isinstance(current, OSError):
            codes=[f'{key}={getattr(current,key)}' for key in ('errno','winerror')
                   if isinstance(getattr(current,key,None),int)]
            if codes: message='İşletim sistemi hatası: '+', '.join(codes)
            else:
                # CFFI stores LoadLibrary's code in its message, not .winerror.
                # Extract only the numeric code; never copy the path/message.
                match=re.search(r'(?:error|WinError)\s*[=:]?\s*(0x[0-9a-fA-F]{1,8}|[0-9]{1,5})\b',str(current))
                if match:message='DLL yükleme hatası: winerror='+str(int(match.group(1),16 if match.group(1).startswith('0x') else 10))
        elif isinstance(current, UnicodeError):
            message='Metin kodlaması çözümlenemedi.'
        elif str(current) in ('BACKEND_START_TIMEOUT','BACKEND_START_FAILED','UI_LOAD_TIMEOUT',
                              'INSTANCE_LOCK_FAILED','JOB_CREATE_FAILED','JOB_CONFIG_FAILED','JOB_ASSIGN_FAILED',
                              'Windows kullanıcı veri dizini belirlenemedi.'):
            message=str(current)
        frames=[{'file':Path(f.filename).name,'line':f.lineno,'function':f.name}
                for f in traceback.extract_tb(current.__traceback__)]
        item={'type':type(current).__name__,'message':message,'frames':frames}
        resource=getattr(current,'resource',None)
        from desktop.runtime import RUNTIME_FILES
        if resource in RUNTIME_FILES+('VERSION','static/index.html','static/styles.css','static/app.js','static/ai.js',
                        'static/logos.js','static/intelligence.js','static/compare.js','static/database.js',
                        'app/intelligence_config.json','analiz/hesaplama_sonuclari.json'):
            item['resource']=resource
        chain.append(item)
        current=current.__cause__ or (None if current.__suppress_context__ else current.__context__)
    lines=[]
    for item in reversed(chain):
        if lines: lines.append('The above exception caused or preceded this exception:')
        lines.append('Traceback (most recent call last):')
        lines.extend(f'  File "{f["file"]}", line {f["line"]}, in {f["function"]}' for f in item['frames'])
        lines.append(item['type']+': '+item['message'])
    return {'chain':chain,'traceback':'\n'.join(lines),'message_policy':'structural_only_no_secrets'}

def event(name, error=None, *, code=None, http_status=None, service=None, stage=None, component=None, startup=False):
    logger = logging.getLogger('kongre.desktop')
    extra = {'safe_event':name}
    if stage and re.fullmatch(r'[a-z_]{1,60}',stage): extra['safe_stage']=stage
    if component in ('desktop','backend','application','bootstrap','package_test'): extra['safe_component']=component
    if service in ('OpenAI','Gemini','OpenRouter','Groq','AIMLAPI','Tavily','Jina AI Search','Web kaynağı'):
        extra['safe_service']=service
    if code and re.fullmatch(r'[A-Z_]{1,40}',code): extra['safe_code']=code
    if isinstance(http_status,int) and 100<=http_status<=599: extra['safe_http_status']=http_status
    if error:
        extra.update(safe_exception=type(error).__name__, safe_frames=[
            {'file':Path(f.filename).name,'line':f.lineno,'function':f.name}
            for f in traceback.extract_tb(error.__traceback__)])
        causes=[];seen=set();current=error
        while current is not None and id(current) not in seen and len(causes)<12:
            seen.add(id(current));item={'type':type(current).__name__}
            for key in ('errno','winerror','verify_code'):
                value=getattr(current,key,None)
                if isinstance(value,int):item[key]=value
            causes.append(item);current=current.__cause__ or current.__context__
        extra['safe_causes']=causes
        if startup: extra['safe_diagnostic']=startup_diagnostic(error)
    # Development may have a non-safe console handler. Never pass it a raw exception.
    logger.log(logging.ERROR if error else logging.INFO, json.dumps(extra), extra=extra)
