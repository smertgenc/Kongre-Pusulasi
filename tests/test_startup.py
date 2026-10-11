"""Clean-start diagnostics and offline startup without Windows/API credentials."""
from argparse import Namespace
import io
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from app.main import create_app
from app.paths import application_paths
from app.secret_store import DesktopSettingsStore
from desktop.logging_setup import SafeFormatter, event, startup_diagnostic
from desktop.startup import Startup, check_resources, MissingResourceError, RESOURCES

ROOT=Path(__file__).resolve().parents[1]

class StartupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        logger=logging.getLogger();self.handlers=logger.handlers[:];self.level=logger.level;logger.handlers=[]
    def tearDown(self):
        logger=logging.getLogger()
        for handler in logger.handlers: handler.close()
        logger.handlers=self.handlers;logger.setLevel(self.level)
        self.tmp.cleanup()

    def paths(self):
        return application_paths(desktop=True,resources=ROOT,local_app_data=self.root/'Türkçe Kullanıcı')

    def test_boot_logging_precedes_config_and_uses_resolved_user_path(self):
        startup=Startup()
        with patch('desktop.startup.application_paths',return_value=self.paths()):startup.prepare()
        startup.mark('configuration_loading')
        try: raise ModuleNotFoundError("No module named 'missing_runtime'",name='missing_runtime')
        except ModuleNotFoundError as error: message=startup.failure(error)
        self.assertIn(str(self.paths().data),message);self.assertNotIn('%LOCALAPPDATA%',message)
        log=startup.log_directory/'error.log'
        record=json.loads(log.read_text(encoding='utf-8').splitlines()[-1])
        self.assertEqual(record['stage'],'configuration_loading')
        self.assertEqual(record['exception'],'ModuleNotFoundError')
        self.assertIn('missing_runtime',record['diagnostic']['traceback'])
        self.assertIn('test_boot_logging',record['diagnostic']['traceback'])

    def test_failure_before_log_setup_uses_temporary_fallback(self):
        startup=Startup();fallback=self.root/'fallback'
        with patch('desktop.startup.application_paths',side_effect=RuntimeError('Windows kullanıcı veri dizini belirlenemedi.')):
            with self.assertRaises(RuntimeError) as caught:startup.prepare()
        with patch('desktop.startup.tempfile.mkdtemp',return_value=str(fallback)):
            message=startup.failure(caught.exception)
        self.assertTrue((fallback/'error.log').exists());self.assertIn(str(fallback),message)
        self.assertNotIn('%LOCALAPPDATA%',message)

    def test_secret_messages_are_removed_but_all_cause_frames_are_retained(self):
        secret='PRIVATE-GEMINI-TAVILY-JINA-TOKEN'
        def first(): raise PermissionError(13,'Authorization: Bearer '+secret)
        def second():
            try: first()
            except PermissionError as error: raise RuntimeError('https://host/?api_key='+secret) from error
        try: second()
        except RuntimeError as error: result=startup_diagnostic(error)
        text=json.dumps(result)
        self.assertNotIn(secret,text);self.assertNotIn('Authorization',text);self.assertNotIn('https://',text)
        self.assertEqual(len(result['chain']),2)
        self.assertIn('PermissionError',result['traceback']);self.assertIn('first',result['traceback'])
        self.assertIn('second',result['traceback']);self.assertIn('errno=13',result['traceback'])

    def test_resources_checked_and_missing_resource_is_identified(self):
        check_resources(ROOT)
        for resource in RESOURCES:
            p=self.root/resource;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('test',encoding='utf-8')
        (self.root/'static/ai.js').unlink()
        with self.assertRaises(MissingResourceError) as caught:check_resources(self.root)
        self.assertEqual(startup_diagnostic(caught.exception)['chain'][0]['resource'],'static/ai.js')

    def test_missing_keys_or_broken_credential_manager_cannot_block_local_start(self):
        settings_path=self.root/'config/settings.json'
        with patch('app.ai_settings.is_desktop',return_value=True),\
             patch('app.ai_settings.PATHS',SimpleNamespace(settings=settings_path)),\
             patch('app.secret_store.CredentialStore',side_effect=OSError('unavailable')) as keys,\
             patch('app.network.client_options',side_effect=AssertionError('No external startup requests')) as network:
            with TestClient(create_app(self.root/'app.db')) as client:
                self.assertEqual(client.get('/').status_code,200)
                self.assertEqual(client.get('/api/health').status_code,200)
                state=client.get('/api/state').json()
                self.assertEqual(len(state['congresses']),4)
                keys.assert_not_called();network.assert_not_called()
        self.assertFalse(settings_path.exists())

    def test_empty_secure_settings_show_unconfigured_without_plaintext_keys(self):
        class EmptyKeys:
            def get(self,name):return ''
        store=DesktopSettingsStore(self.root/'settings.json',EmptyKeys())
        from app.ai_settings import AISettings
        settings=AISettings(store=store)
        self.assertFalse(settings.public()['configured']);self.assertFalse(settings.search_public()['configured'])

    def test_seed_file_is_always_read_as_utf8(self):
        original=Path.read_text;encodings=[]
        def read(path,*args,**kwargs):
            if path.name=='hesaplama_sonuclari.json':encodings.append(kwargs.get('encoding'))
            return original(path,*args,**kwargs)
        with patch.object(Path,'read_text',read),TestClient(create_app(self.root/'seed.db',settings_path=self.root/'test.env')):
            pass
        self.assertEqual(encodings,['utf-8'])

    def test_database_startup_failure_logs_stage_and_traceback(self):
        stream=io.StringIO();handler=logging.StreamHandler(stream);handler.setFormatter(SafeFormatter())
        logging.getLogger().addHandler(handler);logging.getLogger().setLevel(logging.INFO)
        with patch('app.services.CongressService.initialize',side_effect=RuntimeError('secret should not leak')):
            with self.assertRaises(RuntimeError),TestClient(create_app(self.root/'broken.db',settings_path=self.root/'test.env')):pass
        records=[json.loads(line) for line in stream.getvalue().splitlines()]
        error=next(r for r in records if r['event']=='application_startup_failed')
        self.assertEqual(error['stage'],'database_initializing');self.assertIn('lifespan',error['diagnostic']['traceback'])
        self.assertNotIn('secret should not leak',stream.getvalue())

    def test_development_self_test_from_unrelated_directory_and_without_console(self):
        # Simulates pythonw/PyInstaller stdout/stderr=None; does not fake a Windows binary.
        report=self.root/'report.json'
        command=[sys.executable,'-c',
                 "import sys; sys.path.insert(0,sys.argv[1]); sys.stdout=sys.stderr=None; "
                 "from desktop.self_test import run; raise SystemExit(run(sys.argv[2]))",str(ROOT),str(report)]
        process=subprocess.run(command,cwd=self.root,capture_output=True,timeout=60)
        self.assertEqual(process.returncode,0,process.stderr.decode(errors='replace'))
        result=json.loads(report.read_text(encoding='utf-8'))
        self.assertTrue(result['ok']);self.assertIn('startup_without_api_keys',result['checks'])

    def test_launcher_value_error_is_logged_and_not_exposed_verbatim(self):
        from desktop.launcher import launch
        args=Namespace(backup=False,restore=None,smoke_ui=None)
        with patch.dict(os.environ,{'LOCALAPPDATA':str(self.root)}),\
             patch('desktop.launcher.check_resources',side_effect=ValueError('PRIVATE-API-KEY')),\
             patch('desktop.windows.message') as message:
            self.assertEqual(launch(args),1)
        text=message.call_args.args[0]
        self.assertIn('resources_resolving',text);self.assertNotIn('PRIVATE-API-KEY',text)
        self.assertNotIn('PRIVATE-API-KEY',(self.root/'AHP Congress Analyzer/logs/desktop/error.log').read_text(encoding='utf-8'))

    def test_ui_import_failure_fails_smoke_and_preserves_diagnostics(self):
        from desktop.launcher import launch
        args=Namespace(backup=False,restore=None,smoke_ui=self.root/'smoke.json')
        receiver=Mock();receiver.poll.return_value=True;receiver.recv.return_value={'port':12345}
        process=Mock(pid=42);process.is_alive.return_value=False
        context=Mock();context.Pipe.return_value=(receiver,Mock());context.Process.return_value=process
        with patch.dict(os.environ,{'LOCALAPPDATA':str(self.root)}),\
             patch('app.config.PATHS',self.paths()),\
             patch('desktop.windows.InstanceLock'),patch('desktop.windows.ChildJob'),\
             patch('desktop.windows.message') as message,\
             patch('desktop.launcher.webview2_available',return_value=True),\
             patch('desktop.launcher.dotnet_available',return_value=True),\
             patch('desktop.runtime.initialize_netfx'),\
             patch('desktop.launcher.multiprocessing.get_context',return_value=context),\
             patch.dict(sys.modules,{'webview':None}):
            self.assertEqual(launch(args),1)
        message.assert_not_called()
        report=json.loads(args.smoke_ui.read_text(encoding='utf-8'))
        self.assertFalse(report['ok']);self.assertEqual(report['stage'],'webview_import')
        self.assertEqual(report['error_type'],'ModuleNotFoundError')
        self.assertTrue((args.smoke_ui.with_suffix('.logs')/'desktop/error.log').exists())
        process.close.assert_called_once()

    def test_runtime_uses_explicit_framework_object_without_env_fallback(self):
        from desktop.runtime import initialize_netfx
        runtime=object();loader=SimpleNamespace(get_netfx=Mock(return_value=runtime))
        pythonnet=SimpleNamespace(load=Mock())
        with patch.dict(os.environ,{'PYTHONNET_RUNTIME':'coreclr','PYTHONNET_NETFX_CONFIG_FILE':'unused'}),\
             patch.dict(sys.modules,{'clr_loader':loader,'pythonnet':pythonnet}):
            initialize_netfx()
        loader.get_netfx.assert_called_once_with();pythonnet.load.assert_called_once_with(runtime)

    def test_original_framework_failure_is_not_replaced_by_coreclr(self):
        from desktop.runtime import initialize_netfx
        original=OSError("cannot load library 'SECRET/ClrLoader.dll': error 0x7e")
        loader=SimpleNamespace(get_netfx=Mock(side_effect=original));pythonnet=SimpleNamespace(load=Mock())
        with patch.dict(sys.modules,{'clr_loader':loader,'pythonnet':pythonnet}),self.assertRaises(OSError) as caught:
            initialize_netfx()
        self.assertIs(caught.exception,original);pythonnet.load.assert_not_called()
        diagnostic=startup_diagnostic(original)
        self.assertIn('winerror=126',diagnostic['traceback']);self.assertNotIn('SECRET',json.dumps(diagnostic))

    def test_package_must_contain_all_pinned_clr_and_webview_dlls(self):
        from desktop.runtime import verify_packaged_runtime,RUNTIME_FILES,MissingRuntimeFile
        for resource in RUNTIME_FILES:
            path=self.root/resource;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'dll-fixture')
        verify_packaged_runtime(self.root)
        (self.root/RUNTIME_FILES[0]).unlink()
        with self.assertRaises(MissingRuntimeFile) as caught:verify_packaged_runtime(self.root)
        self.assertEqual(startup_diagnostic(caught.exception)['chain'][0]['resource'],RUNTIME_FILES[0])

    def test_windows_runtime_detection_separates_missing_prerequisites(self):
        import types
        registry=types.SimpleNamespace(HKEY_LOCAL_MACHINE=1,HKEY_CURRENT_USER=2,KEY_WOW64_32KEY=32,
                                      KEY_WOW64_64KEY=64,KEY_READ=8)
        registry.OpenKey=Mock(side_effect=FileNotFoundError())
        with patch.dict(sys.modules,{'winreg':registry}):
            from desktop.launcher import webview2_available,dotnet_available
            self.assertFalse(webview2_available());self.assertFalse(dotnet_available())
        self.assertEqual(registry.OpenKey.call_count,6)

    def test_build_runner_allows_isolated_working_directory(self):
        sys.path.insert(0,str(ROOT/'tools'))
        try:
            from build_windows import run
            with patch('build_windows.subprocess.run') as call:
                run(['executable','--self-test','report.json'],cwd=self.root)
            self.assertEqual(call.call_args.kwargs['cwd'],self.root)
        finally:sys.path.pop(0)

    def test_desktop_ignores_invalid_unused_development_port(self):
        command=[sys.executable,'-c','from app.config import DEFAULT_PORT; print(DEFAULT_PORT)']
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=15,
                              env={**os.environ,'KONGRE_DESKTOP':'1','LOCALAPPDATA':str(self.root),'KONGRE_PORT':'not-a-port'})
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'8765')

    def test_smoke_reports_existing_instance_without_modal_dialog(self):
        from desktop.launcher import launch
        from desktop.windows import AlreadyRunning
        args=Namespace(backup=False,restore=None,smoke_ui=self.root/'smoke.json')
        with patch.dict(os.environ,{'LOCALAPPDATA':str(self.root)}),\
             patch('desktop.windows.InstanceLock',side_effect=AlreadyRunning('Uygulama zaten açık.')),\
             patch('desktop.windows.message') as message:
            self.assertEqual(launch(args),1)
        message.assert_not_called()
        result=json.loads(args.smoke_ui.read_text(encoding='utf-8'))
        self.assertFalse(result['ok']);self.assertEqual(result['error_type'],'ALREADY_RUNNING')
        self.assertEqual(result['stage'],'instance_lock')
