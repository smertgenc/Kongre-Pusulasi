"""FastAPI transport preserving the existing browser's /api contract."""
from contextlib import asynccontextmanager
from urllib.parse import urlsplit, unquote
import logging
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from starlette.concurrency import run_in_threadpool
from pydantic import Field
from typing import Literal
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy.exc import IntegrityError
from app.config import ROOT, DEFAULT_DB, VERSION
from app.database import Database, SCHEMA_VERSION
from app.services import CongressService, ConflictError, NotFoundError
from app.schemas import EvaluationInput, ModelInput, PublishModelInput, ScenarioInput, DeleteCongressInput
from app.ai_schemas import AnalysisInput, SettingsInput, ReviewInput, SearchSettingsInput, SearchTestInput, RetryAnalysisInput, AITestInput
from app.connection_errors import ConnectionFailure
from app.connection_probe import test_ai_connection
from app.search import search_web, SEARCH_PROVIDERS
from app.ai_service import AIService
from app.intelligence_service import IntelligenceService
from app.intelligence_schemas import ResearchProfileInput
from app.logo_service import LogoService, LogoUpload, LogoDiscovery
from app.database_connection import DatabaseConnections, DatabaseBoundary, DatabaseGate, active_database_path, MAX_DATABASE_BYTES
from app.input_model import InputModel

class DatabaseConnectInput(InputModel):
    token: str = Field(pattern=r'^[a-f0-9]{32}$')
    database_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    confirmed: Literal[True]

LIMIT = 200_000
SECURITY = {
    'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff', 'Referrer-Policy':'no-referrer',
    'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
}

class LocalBoundary:
    """Local-only request checks and real byte limit (including chunked bodies)."""
    def __init__(self, app): self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope['headers'])
        host = headers.get(b'host', b'').decode('latin1')
        hostname = urlsplit('http://'+host).hostname
        async def reject(status, message):
            await JSONResponse({'error':message}, status_code=status, headers=SECURITY)(scope, receive, send)
        if hostname not in ('localhost','127.0.0.1','testserver'):
            return await reject(403,'Yalnızca yerel erişime izin verilir.')
        # testserver is only used by in-process TestClient, never accepted on TCP.
        if hostname == 'testserver' and scope.get('server', ('',))[0] != 'testserver':
            return await reject(403,'Kaynak doğrulanamadı.')
        if scope['method'] in ('POST','PUT','PATCH','DELETE'):
            origin = headers.get(b'origin', b'').decode('latin1')
            if origin and origin != f'{scope.get("scheme","http")}://{host}':
                return await reject(403,'Kaynak doğrulanamadı.')
            database_upload=scope['path']=='/api/database/inspect' and scope['method']=='POST'
            if database_upload:
                if headers.get(b'content-type',b'').split(b';')[0]!=b'application/octet-stream':
                    return await reject(415,'SQLite dosyası gönderilmelidir.')
                original_receive=receive;received=0
                async def bounded_receive():
                    nonlocal received
                    message=await original_receive()
                    received+=len(message.get('body',b''))
                    if received>MAX_DATABASE_BYTES:raise HTTPException(413,'Veritabanı en fazla 100 MB olabilir.')
                    return message
                receive=bounded_receive
            elif headers.get(b'content-type', b'').split(b';')[0] != b'application/json':
                return await reject(415,'JSON içerik gereklidir.')
            if not database_upload:
                body = bytearray()
                while True:
                    message = await receive()
                    if message['type'] == 'http.disconnect': return
                    body.extend(message.get('body', b''))
                    limit = 22_600_000 if scope['path'] in ('/api/ai/analyze','/api/ai/start') else 4_100_000 if scope['path'].endswith('/logo/upload') else LIMIT
                    if len(body) >= limit:
                        return await reject(413,'İstek boyutu sınırı aşıldı.')
                    if not message.get('more_body'): break
                async def replay():
                    return {'type':'http.request','body':bytes(body),'more_body':False}
                receive = replay
        async def secure_send(message):
            if message['type'] == 'http.response.start':
                message['headers'] = list(message.get('headers', [])) + [(k.lower().encode(),v.encode()) for k,v in SECURITY.items()]
            await send(message)
        await self.app(scope, receive, secure_send)

def create_app(db_path=DEFAULT_DB, *, settings_path=None, ai_provider=None, desktop_session=None):
    db = Database(active_database_path(db_path))
    connections = DatabaseConnections(db_path,db)
    gate = DatabaseGate()
    service = CongressService(db)
    ai = AIService(db, settings_path, ai_provider)
    intelligence = IntelligenceService(db, ai)
    logos = LogoService(db)
    @asynccontextmanager
    async def lifespan(app):
        from desktop.logging_setup import event
        stage='database_initializing'
        try:
            event('startup_stage',stage=stage,component='application')
            service.initialize()
            event('startup_stage',stage='database_initialized',component='application')
            stage='analysis_recovery'
            ai.recover()
            event('startup_stage',stage='ai_services_ready_without_credentials',component='application')
        except Exception as error:
            event('application_startup_failed',error,stage=stage,component='application',startup=True)
            db.close()
            raise
        try: yield
        finally: db.close()
    app = FastAPI(title='Kongre Pusulası API', version=VERSION, lifespan=lifespan,
                  docs_url=None, redoc_url=None)
    app.state.database = db
    app.state.service = service
    app.state.ai = ai
    app.state.intelligence = intelligence
    app.state.logos = logos
    app.state.connections = connections
    app.state.database_gate = gate
    app.add_middleware(DatabaseBoundary,gate=gate,connections=connections)
    app.add_middleware(LocalBoundary)
    if desktop_session:
        from desktop.session import DesktopSession
        app.add_middleware(DesktopSession, **desktop_session)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, error):
        fields = []
        translations = {'Field required':'Bu alan zorunludur.', 'String should have at least 1 character':'Bu alan boş olamaz.'}
        for item in error.errors():
            field = '.'.join(str(x) for x in item['loc'] if x != 'body')
            msg = item['msg'].removeprefix('Value error, ')
            fields.append({'field':field, 'message':translations.get(msg,msg)})
        return JSONResponse({'error':' · '.join(f"{x['field']}: {x['message']}" for x in fields), 'fields':fields},status_code=422)

    @app.exception_handler(ConflictError)
    async def conflict(request, error): return JSONResponse({'error':str(error)},status_code=409)
    @app.exception_handler(ConnectionFailure)
    async def connection_failure(request, error):
        return JSONResponse({'error':str(error),'code':error.code,'http_status':error.http_status,
                             'provider':error.service},status_code=502)
    @app.exception_handler(NotFoundError)
    async def missing(request, error): return JSONResponse({'error':str(error)},status_code=404)
    @app.exception_handler(ValueError)
    async def value_error(request, error): return JSONResponse({'error':str(error)},status_code=422)
    @app.exception_handler(IntegrityError)
    async def duplicate(request, error):
        return JSONResponse({'error':'Aynı ad ve edisyonla bir kongre zaten var veya kayıt ilişkisi geçersiz. Sayfayı yenileyin.'},status_code=409)
    @app.exception_handler(Exception)
    async def unexpected(request, error):
        from desktop.logging_setup import event
        event('request_failed', error)
        return JSONResponse({'error':'İşlem tamamlanamadı. Lütfen tekrar deneyin.'},status_code=500,headers=SECURITY)

    @app.get('/api/health', tags=['Sistem'])
    def health(): return {'status':'ok','backend':'fastapi','version':VERSION,'schema_version':SCHEMA_VERSION}
    @app.get('/api/profile/research', tags=['Araştırma profili'])
    def research_profile(): return intelligence.profiles.get_profile()
    @app.post('/api/profile/research', tags=['Araştırma profili'])
    @app.put('/api/profile/research', tags=['Araştırma profili'])
    def save_research_profile(request: ResearchProfileInput): return intelligence.profiles.save_profile(request)
    @app.post('/api/profile/research/delete', tags=['Araştırma profili'])
    @app.delete('/api/profile/research', tags=['Araştırma profili'])
    def delete_research_profile(): return intelligence.profiles.delete_profile()
    @app.get('/api/congresses/{cid}/insights', tags=['Kongre önerileri'])
    def congress_insights(cid: str, evaluation_id: str | None = None):
        return intelligence.insights(cid, evaluation_id=evaluation_id)
    @app.get('/api/congresses/{cid}/personal-fit', tags=['Kongre önerileri'])
    def congress_personal_fit(cid: str, evaluation_id: str | None = None):
        return intelligence.personal_fit(cid, evaluation_id=evaluation_id)
    @app.get('/api/congresses/{cid}/fingerprint', tags=['Organizasyonel benzerlik'])
    def congress_fingerprint(cid: str, evaluation_id: str | None = None):
        return intelligence.fingerprint(intelligence.congress(cid,evaluation_id))
    @app.get('/api/congresses/{cid}/fingerprint/similar', tags=['Organizasyonel benzerlik'])
    def congress_fingerprint_similar(cid: str, evaluation_id: str | None = None):
        return intelligence.insights(cid,evaluation_id=evaluation_id)['organizational_matches']
    @app.get('/api/congresses/{cid}/recommendations', tags=['Kongre önerileri'])
    def congress_recommendations(cid: str, evaluation_id: str | None = None):
        return intelligence.recommend(cid,evaluation_id=evaluation_id)
    @app.get('/api/ai/analyses/{aid}/insights', tags=['Kongre önerileri'])
    def analysis_insights(aid: str): return intelligence.insights(aid=aid)
    @app.get('/api/state', tags=['Uyumlu API'])
    def state(): return {**service.state(), 'logos': logos.all(), 'database_id':connections.identity}

    @app.get('/api/database/status', tags=['Veritabanı'])
    def database_status(): return connections.status()

    @app.post('/api/database/inspect', tags=['Veritabanı'])
    async def inspect_database(request: Request):
        path=connections.new_upload()
        try:
            with path.open('wb') as stream:
                async for chunk in request.stream():stream.write(chunk)
            label=unquote(request.headers.get('x-database-file-name','SQLite.db'))[:500]
            return await run_in_threadpool(connections.inspect,path,label)
        except BaseException:
            path.unlink(missing_ok=True);raise

    @app.post('/api/database/connect', tags=['Veritabanı'])
    def connect_database(request: DatabaseConnectInput):
        return connections.connect(request.token,request.database_id)

    @app.get('/api/database/backup', tags=['Veritabanı'])
    def database_backup(background_tasks: BackgroundTasks):
        from app.backup import snapshot
        export=connections.base.parent/'exports'
        path=snapshot(db.path,export,prefix='kongre-yedek')
        background_tasks.add_task(path.unlink,missing_ok=True)
        return FileResponse(path,filename=path.name,media_type='application/vnd.sqlite3',background=background_tasks)
    @app.get('/api/congresses/{cid}/logo', tags=['Kongre logoları'])
    def congress_logo(cid: str): return Response(logos.image(cid), media_type='image/png')
    @app.post('/api/congresses/{cid}/logo/upload', tags=['Kongre logoları'])
    def upload_congress_logo(cid: str, request: LogoUpload): return logos.upload(cid, request.content)
    @app.post('/api/congresses/{cid}/logo/discover', tags=['Kongre logoları'])
    def discover_congress_logo(cid: str, request: LogoDiscovery): return logos.discover(cid, request.force)
    @app.post('/api/congresses/{cid}/logo/hide', tags=['Kongre logoları'])
    def hide_congress_logo(cid: str): return logos.hide(cid)
    @app.post('/api/congresses/{cid}/logo/restore', tags=['Kongre logoları'])
    def restore_congress_logo(cid: str): return logos.hide(cid, restore=True)
    @app.post('/api/evaluations', status_code=201, tags=['Değerlendirmeler'])
    def save(request: EvaluationInput): return service.save_evaluation(request)
    @app.get('/api/congresses/trash', tags=['Kongreler'])
    def trash(): return service.trash()
    @app.post('/api/congresses/{cid}/delete', tags=['Kongreler'])
    def delete_congress(cid: str, request: DeleteCongressInput): return service.delete_congress(cid,request.previous_id)
    @app.post('/api/congresses/{cid}/restore', tags=['Kongreler'])
    def restore_congress(cid: str): return service.restore_congress(cid)
    @app.post('/api/models/preview', tags=['AHP modeli'])
    def preview(request: ModelInput): return service.preview_model(request)
    @app.post('/api/models', status_code=201, tags=['AHP modeli'])
    def publish(request: PublishModelInput): return service.publish_model(request)
    @app.post('/api/scenario', tags=['Senaryo'])
    def scenario(request: ScenarioInput): return service.scenario(request)
    @app.get('/api/ai/settings', tags=['Yapay zekâ'])
    def ai_settings(): return ai.settings.public()
    @app.post('/api/ai/settings', tags=['Yapay zekâ'])
    def ai_settings_save(request: SettingsInput): return ai.settings.save(request)
    @app.post('/api/ai/test', tags=['Yapay zekâ'])
    def ai_test(request: AITestInput):
        connection=ai.settings.credentials()
        if (request.provider_id is not None and request.provider_id!=connection.provider_id) or (request.provider_model is not None and request.provider_model!=connection.model):
            raise ConflictError('Kayıtlı AI bağlantısı değişti. Ayarları yenileyip tekrar test edin.')
        return test_ai_connection(connection)
    @app.get('/api/search/settings', tags=['Web araştırması'])
    def search_settings(): return ai.settings.search_public()
    @app.post('/api/search/settings', tags=['Web araştırması'])
    def search_settings_save(request: SearchSettingsInput): return ai.settings.save_search(request)
    @app.post('/api/search/test', tags=['Web araştırması'])
    def search_test(request: SearchTestInput):
        connection=ai.settings.search_credentials()
        if request.provider_id is not None and request.provider_id!=connection.provider_id:
            raise ConflictError('Kayıtlı arama servisi değişti. Ayarları yenileyip tekrar test edin.')
        rows=search_web('academic congress scientific programme',connection)
        return {'ok':True,'message':'Bağlantı başarılı','provider_id':connection.provider_id,
                'provider':SEARCH_PROVIDERS[connection.provider_id],'result_count':len(rows),
                'results':[{'title':r['label'],'url':r['url']} for r in rows]}
    @app.post('/api/ai/analyze', status_code=201, tags=['Yapay zekâ'])
    def ai_analyze(request: AnalysisInput): return ai.analyze(request)
    @app.post('/api/ai/start', status_code=202, tags=['Yapay zekâ'])
    def ai_start(request: AnalysisInput, background_tasks: BackgroundTasks):
        job=ai.prepare_analysis(request)
        background_tasks.add_task(ai.run_analysis,*job)
        return {'id':job[0],'status':'processing'}
    @app.get('/api/ai/analyses', tags=['Yapay zekâ'])
    def ai_history(deleted: bool=False): return ai.list(deleted)
    @app.post('/api/ai/analyses/clear', tags=['Yapay zekâ'])
    def ai_history_clear(): return ai.clear_history()
    @app.post('/api/ai/analyses/{aid}/delete', tags=['Yapay zekâ'])
    def ai_history_delete(aid: str): return ai.delete(aid)
    @app.post('/api/ai/analyses/{aid}/restore', tags=['Yapay zekâ'])
    def ai_history_restore(aid: str): return ai.restore(aid)
    @app.get('/api/ai/analyses/{aid}', tags=['Yapay zekâ'])
    def ai_analysis(aid: str): return ai.get(aid)
    @app.get('/api/ai/analyses/{aid}/progress', tags=['Yapay zekâ'])
    def ai_progress(aid: str): return ai.progress(aid)
    @app.post('/api/ai/analyses/{aid}/retry', status_code=202, tags=['Yapay zekâ'])
    def ai_retry(aid: str, request: RetryAnalysisInput, background_tasks: BackgroundTasks):
        job=ai.prepare_retry(aid,request)
        if job[1] is not None:background_tasks.add_task(ai.run_analysis,*job)
        return {'id':job[0],'status':ai.progress(job[0])['status']}
    @app.get('/api/ai/analyses/{aid}/pdf', tags=['Raporlama'])
    def ai_pdf(aid: str):
        from app.pdf_report import analysis_pdf
        report=ai.get(aid)
        if report['status']!='ready': raise ConflictError('PDF için analizin tamamlanmış olması gerekir.')
        return Response(analysis_pdf(report, logo=logos.report_image(report)),media_type='application/pdf',
                        headers={'Content-Disposition':'attachment; filename="kongre-ahp-raporu.pdf"'})
    @app.get('/api/ai/analyses/{aid}/result', tags=['Yapay zekâ'])
    def ai_result(aid: str):
        report=ai.get(aid).get('analysis',{}).get('report')
        if not report: raise NotFoundError('Bu analiz için yeni formatta sonuç raporu yok.')
        return JSONResponse(report,headers={'Content-Disposition':'attachment; filename="kongre-ai-sonucu.json"'})
    @app.post('/api/ai/analyses/{aid}/review', tags=['Yapay zekâ'])
    def ai_review(aid: str, request: ReviewInput): return ai.review(aid,request)
    @app.get('/api/export', tags=['Raporlama'])
    def export():
        return Response(service.export_csv(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="kongre-degerlendirmeleri.csv"'})
    @app.get('/api/backup', tags=['Raporlama'])
    def backup():
        return Response(db.dump(),media_type='application/sql',headers={'Content-Disposition':'attachment; filename="kongre-yedek.sql"'})
    @app.get('/', include_in_schema=False)
    def index(): return Response((ROOT/'static/index.html').read_text(encoding='utf-8').replace('__APP_VERSION__', VERSION), media_type='text/html')
    @app.get('/app.js', include_in_schema=False)
    def javascript(): return FileResponse(ROOT/'static/app.js',media_type='text/javascript')
    @app.get('/logos.js', include_in_schema=False)
    def logos_javascript(): return FileResponse(ROOT/'static/logos.js',media_type='text/javascript')
    @app.get('/compare.js', include_in_schema=False)
    def compare_javascript(): return FileResponse(ROOT/'static/compare.js',media_type='text/javascript')
    @app.get('/intelligence.js', include_in_schema=False)
    def intelligence_javascript(): return FileResponse(ROOT/'static/intelligence.js',media_type='text/javascript')
    @app.get('/ai.js', include_in_schema=False)
    def ai_javascript(): return FileResponse(ROOT/'static/ai.js',media_type='text/javascript')
    @app.get('/database.js', include_in_schema=False)
    def database_javascript(): return FileResponse(ROOT/'static/database.js',media_type='text/javascript')
    @app.get('/styles.css', include_in_schema=False)
    def stylesheet(): return FileResponse(ROOT/'static/styles.css',media_type='text/css')
    from app.research_api import register_research
    register_research(app,db,service)
    return app
