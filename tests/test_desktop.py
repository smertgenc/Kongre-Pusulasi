import base64
import ctypes
import hashlib
import io
import json
import logging
import multiprocessing
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.request
from fastapi.testclient import TestClient
from PIL import Image
from app.main import create_app
from app.paths import application_paths
from app.backup import snapshot, restore
from app.secret_store import DesktopSettingsStore
from app.ai_settings import AISettings
from app.ai_schemas import SettingsInput, SearchSettingsInput
from app.network import proxy_for, require_online, NetworkPolicyError
from desktop.logging_setup import SafeFormatter, configure_logs

class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def app(self, **kwargs): return create_app(self.root/'test.db',settings_path=self.root/'test.env',**kwargs)

    def test_paths_keep_resources_and_user_writes_separate(self):
        paths=application_paths(desktop=True,resources=self.root/'Program Files',local_app_data=self.root/'User')
        paths.prepare()
        self.assertFalse(paths.resources.exists())
        self.assertTrue(paths.database.parent.exists())
        self.assertTrue(paths.settings.is_relative_to(paths.data))
        with patch.dict(os.environ,{'LOCALAPPDATA':''}),self.assertRaises(RuntimeError):
            application_paths(desktop=True)

    def test_secure_settings_keys_never_enter_json_or_public_output(self):
        class Keys:
            def __init__(self): self.values={}
            def get(self,k): return self.values.get(k,'')
            def set(self,k,v): self.values[k]=v
        keys=Keys();path=self.root/'config/settings.json'
        settings=AISettings(store=DesktopSettingsStore(path,keys))
        settings.save(SettingsInput(provider_id='groq',model='openai/gpt-oss-20b',api_key='SECRET-GROQ'))
        settings.save(SettingsInput(provider_id='groq',model='openai/gpt-oss-20b',api_key=''))
        settings.save_search(SearchSettingsInput(provider_id='tavily',api_key='SECRET-TAVILY'))
        settings2=AISettings(store=DesktopSettingsStore(path,keys))
        self.assertEqual(settings2.credentials().key,'SECRET-GROQ')
        self.assertEqual(settings2.search_credentials('tavily').key,'SECRET-TAVILY')
        self.assertNotIn('SECRET',path.read_text())
        self.assertNotIn('SECRET',json.dumps(settings2.public()))
        self.assertNotIn('SECRET',json.dumps(settings2.search_public()))
        self.assertEqual(list(path.parent.glob('*.tmp')),[])

    def test_desktop_session_blocks_unauthenticated_local_and_cross_origin_requests(self):
        token=secrets.token_urlsafe(32)
        app=self.app(desktop_session={'token':token,'host':'127.0.0.1:43210'})
        with TestClient(app,base_url='http://127.0.0.1:43210') as client:
            self.assertEqual(client.get('/api/state').status_code,403)
            self.assertEqual(client.get('/_desktop/start?token=wrong').status_code,403)
            self.assertEqual(client.get('/_desktop/start?token=%C4%B1').status_code,403)
            started=client.get('/_desktop/start?token='+token,follow_redirects=False)
            self.assertEqual(started.status_code,303)
            self.assertIn('HttpOnly',started.headers['set-cookie']);self.assertIn('SameSite=strict',started.headers['set-cookie'])
            self.assertEqual(client.get('/api/state').status_code,200)
            self.assertEqual(client.get('/_desktop/start?token='+token).status_code,403)
            self.assertEqual(client.get('/api/state',headers={'origin':'https://evil.example'}).status_code,403)
            self.assertEqual(client.get('/api/state',headers={'host':'localhost:43210'}).status_code,403)

    def test_snapshot_restore_and_failed_restore_preserve_current_database(self):
        with TestClient(self.app()) as client: state=client.get('/api/state').json()
        original=self.root/'test.db';backup=snapshot(original,self.root/'backups')
        with sqlite3.connect(original) as connection: connection.execute('UPDATE congresses SET created_at=?',('changed',))
        restore(backup,original,self.root/'backups')
        with TestClient(self.app()) as client: self.assertEqual(client.get('/api/state').json(),state)
        before=original.read_bytes();(self.root/'invalid.db').write_text('not SQLite')
        with self.assertRaises(sqlite3.DatabaseError): restore(self.root/'invalid.db',original,self.root/'backups')
        self.assertEqual(before,original.read_bytes())
        self.assertEqual(len(list((self.root/'backups').glob('before-restore_*.db'))),1)

    def test_future_backup_rejected_and_upgrade_creates_recovery_copy(self):
        with TestClient(self.app()): pass
        path=self.root/'test.db'
        with sqlite3.connect(path) as c: c.execute('PRAGMA user_version=6')
        with TestClient(self.app()): pass
        self.assertEqual(len(list((self.root/'backups').glob('before-migration_*.db'))),1)
        copy=snapshot(path,self.root/'backups')
        with sqlite3.connect(copy) as c: c.execute('PRAGMA user_version=999')
        before=path.read_bytes()
        with self.assertRaises(ValueError): restore(copy,path,self.root/'backups')
        self.assertEqual(before,path.read_bytes())

    def test_offline_no_proxy_or_dns_request(self):
        with patch.dict(os.environ,{'KONGRE_OFFLINE':'1'}),patch('app.network.getproxies') as lookup:
            with self.assertRaisesRegex(NetworkPolicyError,'Çevrimdışı'): proxy_for('https://example.org')
            lookup.assert_not_called()
        from app.sources import public_target
        with patch.dict(os.environ,{'KONGRE_OFFLINE':'1'}),patch('app.sources.socket.getaddrinfo') as dns:
            with self.assertRaisesRegex(NetworkPolicyError,'Çevrimdışı'): public_target('https://example.org')
            dns.assert_not_called()

    def test_system_proxy_used_and_absent_proxy_does_not_block_requests(self):
        with patch('app.network.getproxies',return_value={'https':'http://corp-proxy:8080'}),patch('app.network.proxy_bypass',return_value=False):
            self.assertEqual(proxy_for('https://api.example.org'),'http://corp-proxy:8080')
        with patch('app.network.getproxies',return_value={}):
            self.assertIsNone(proxy_for('https://example.org'))

    def test_malformed_proxy_error_never_echoes_secret(self):
        with patch('app.network.getproxies',return_value={'https':'ftp://secret@proxy'}),patch('app.network.proxy_bypass',return_value=False):
            with self.assertRaises(NetworkPolicyError) as caught: proxy_for('https://example.org')
            self.assertNotIn('secret',str(caught.exception))

    def test_logs_exclude_exception_values_source_paths_and_record_messages(self):
        try: raise ValueError('SECRET-KEY user profile text https://private.example')
        except ValueError:
            record=logging.LogRecord('private','ERROR',__file__,1,'SECRET-KEY',(),sys.exc_info())
        record.safe_event='request_failed'
        result=SafeFormatter().format(record)
        self.assertNotIn('SECRET',result);self.assertNotIn('private.example',result)
        self.assertNotIn(str(self.root),result);self.assertNotIn('/Users/',result)
        self.assertIn('ValueError',result);self.assertIn('frames',result)
        from desktop.logging_setup import event
        stream=io.StringIO();handler=logging.StreamHandler(stream)
        logger=logging.getLogger('kongre.desktop');previous=logger.handlers[:];propagate=logger.propagate
        logger.handlers=[handler];logger.propagate=False
        try:
            event('request_failed',record.exc_info[1])
            self.assertNotIn('SECRET',stream.getvalue());self.assertIn('ValueError',stream.getvalue())
        finally:
            logger.handlers=previous;logger.propagate=propagate;handler.close()

    def test_log_rotation_configured(self):
        logger=logging.getLogger();previous=logger.handlers[:];logger.handlers=[];level=logger.level
        try:
            configure_logs(self.root/'logs')
            self.assertEqual(len(logger.handlers),2)
            self.assertTrue(all(h.maxBytes==2_000_000 and h.backupCount==3 for h in logger.handlers))
        finally:
            for handler in logger.handlers: handler.close()
            logger.handlers=previous;logger.setLevel(level)

    def test_windows_ocr_reads_validated_local_image_with_fixed_arguments(self):
        from app.windows_ocr import extract_windows_image
        runtime=self.root/'ocr';(runtime/'tessdata').mkdir(parents=True)
        for relative in ('tesseract.exe','tessdata/eng.traineddata','tessdata/tur.traineddata'):(runtime/relative).write_bytes(b'fixture')
        image=Image.new('RGB',(100,100),'white');buffer=io.BytesIO();image.save(buffer,format='PNG')
        tsv='level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n5\t1\t1\t1\t1\t1\t5\t6\t40\t10\t95\tKongre\n'
        import subprocess
        with patch('app.windows_ocr.subprocess.run',return_value=subprocess.CompletedProcess([],0,tsv.encode(),b'')) as call:
            data=extract_windows_image(buffer.getvalue(),runtime=runtime)
        self.assertEqual(data['text'],'Kongre');self.assertEqual(data['lines'][0]['confidence'],.95)
        self.assertEqual(data['lines'][0]['box'],[.05,.84,.4,.1])
        self.assertEqual(call.call_args.args[0][0],str(runtime/'tesseract.exe'))
        self.assertIn('tur+eng',call.call_args.args[0]);self.assertEqual(call.call_args.kwargs['timeout'],60)

    def test_windows_ocr_missing_component_stops_before_subprocess(self):
        from app.windows_ocr import extract_windows_image
        with patch('app.windows_ocr.subprocess.run') as run,self.assertRaisesRegex(ValueError,'eksik'):
            extract_windows_image(b'',runtime=self.root)
        run.assert_not_called()

    def test_release_manifest_rejects_tampered_ocr_and_private_files(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
        try:
            from prepare_ocr import prepare,verify
            from build_windows import reject_private_files
            source=self.root/'source';(source/'tessdata').mkdir(parents=True)
            for name in ('tesseract.exe','runtime.dll','tessdata/tur.traineddata','tessdata/eng.traineddata'):(source/name).write_bytes(b'fixture')
            licenses=self.root/'licenses';licenses.mkdir();(licenses/'LICENSE.txt').write_text('test license')
            target=self.root/'vendor'
            prepare(source,licenses,'5.5.0','https://example.org/approved',target)
            verify(target)
            (target/'runtime.dll').write_bytes(b'tampered')
            with self.assertRaises(ValueError): verify(target)
            dist=self.root/'dist';dist.mkdir();(dist/'.env').write_text('SECRET=fixture')
            with self.assertRaisesRegex(RuntimeError,'özel'): reject_private_files(dist)
        finally: sys.path.pop(0)

@unittest.skipUnless(os.getenv('RUN_DESKTOP_PROCESS_TEST')=='1','Explicit local socket/process integration test')
class BackendProcessTests(unittest.TestCase):
    def test_dynamic_loopback_auth_and_clean_shutdown(self):
        from desktop.backend import run_backend
        from desktop.launcher import stop_backend
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);ctx=multiprocessing.get_context('spawn');stop=ctx.Event();read,write=ctx.Pipe(duplex=False)
            token=secrets.token_urlsafe(32)
            process=ctx.Process(target=run_backend,args=(write,stop,str(root/'test.db'),token,str(root/'logs')))
            process.start();write.close()
            port=None
            try:
                self.assertTrue(read.poll(30));message=read.recv();port=message['port']
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor())
                with self.assertRaises(urllib.error.HTTPError) as caught: opener.open(f'http://127.0.0.1:{port}/api/state')
                self.assertEqual(caught.exception.code,403)
                with opener.open(f'http://127.0.0.1:{port}/_desktop/start?token={token}') as response:self.assertEqual(response.status,200)
                with opener.open(f'http://127.0.0.1:{port}/api/state') as response:self.assertEqual(len(json.load(response)['congresses']),4)
            finally:
                read.close();stop_backend(process,stop)
            with socket.socket() as connection: self.assertNotEqual(connection.connect_ex(('127.0.0.1',port)),0)
