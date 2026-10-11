"""Windows entry point; one visible WebView and one managed loopback backend."""
import argparse
import multiprocessing
import os
from pathlib import Path
import secrets
import sys
import threading
import time
from desktop.logging_setup import event
from desktop.startup import Startup, check_resources

def webview2_available():
    import winreg
    key = r'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for view in (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
            try:
                with winreg.OpenKey(hive,key,0,winreg.KEY_READ|view) as handle:
                    version, _ = winreg.QueryValueEx(handle,'pv')
                    if version and version != '0.0.0.0': return True
            except OSError: pass
    return False

def dotnet_available():
    import winreg
    key=r'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full'
    for view in (winreg.KEY_WOW64_32KEY,winreg.KEY_WOW64_64KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,key,0,winreg.KEY_READ|view) as handle:
                release,_=winreg.QueryValueEx(handle,'Release')
                if isinstance(release,int) and release>=394802: return True
        except OSError: pass
    return False

def stop_backend(process, stop):
    stop.set()
    process.join(18)
    if process.is_alive(): process.terminate(); process.join(5)
    if process.is_alive(): process.kill(); process.join(5)
    if not process.is_alive(): process.close()

def main(argv=None):
    parser = argparse.ArgumentParser(description='AHP Congress Analyzer')
    parser.add_argument('--backup', action='store_true')
    parser.add_argument('--restore', type=Path, metavar='YEDEK.db')
    parser.add_argument('--self-test', type=Path, metavar='RAPOR.json')
    parser.add_argument('--smoke-ui', type=Path, metavar='RAPOR.json')
    args = parser.parse_args(argv)
    if args.self_test:
        from desktop.self_test import run
        return run(args.self_test)
    if sys.platform != 'win32':
        print('Masaüstü sürüm Windows x64 içindir. Geliştirme için server.py kullanın.')
        return 1
    if args.smoke_ui:
        # Never run a build check against a developer's existing database/keys.
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix='ahp-ui-test-') as folder:
            with patch.dict(os.environ,{'LOCALAPPDATA':folder,'KONGRE_OFFLINE':'1'}):
                try: return launch(args)
                finally:
                    import logging
                    logging.shutdown()
    return launch(args)

def launch(args):
    os.environ['KONGRE_DESKTOP'] = '1'
    from desktop.windows import InstanceLock, ChildJob, message, AlreadyRunning
    startup=Startup()
    lock = job = process = stop = None
    receiver=sender=None
    smoke_result={'ok':False,'stage':'application_starting'}
    try:
        startup.prepare()
        startup.mark('configuration_loading')
        from app.config import PATHS, VERSION
        startup.mark('configuration_loaded')
        startup.mark('resources_resolving')
        check_resources(PATHS.resources)
        startup.mark('resources_resolved')
        startup.mark('instance_lock')
        lock = InstanceLock()
        from app.backup import snapshot, restore
        from app.database_connection import active_database_path
        if args.backup:
            path = snapshot(active_database_path(PATHS.database),PATHS.backups)
            message('Yedek oluşturuldu:\n'+str(path)); return 0
        if args.restore:
            if message('Seçilen yedek geri yüklensin mi?\nMevcut veritabanınız önce yedeklenecek.\n\n'+str(args.restore),confirm=True):
                restore(args.restore,active_database_path(PATHS.database),PATHS.backups)
                message('Yedek geri yüklendi. Uygulamayı normal kısayolundan açabilirsiniz.')
            return 0
        startup.mark('webview_runtime_check')
        if not webview2_available():
            event('startup_prerequisite_missing',stage=startup.stage,component='desktop',code='WEBVIEW2_MISSING')
            smoke_result.update(stage=startup.stage,error_type='WEBVIEW2_MISSING')
            if not args.smoke_ui: message('Microsoft Edge WebView2 Runtime bulunamadı. BT biriminizden WebView2 Evergreen x64 Runtime kurulmasını isteyin. Uygulama güvenlik ayarlarını değiştirmez.',error=True)
            return 1
        if not dotnet_available():
            event('startup_prerequisite_missing',stage=startup.stage,component='desktop',code='DOTNET_MISSING')
            smoke_result.update(stage=startup.stage,error_type='DOTNET_MISSING')
            if not args.smoke_ui: message('Microsoft .NET Framework 4.6.2 veya sonrası bulunamadı. BT biriminizden kurulmasını isteyin.',error=True)
            return 1
        from desktop.runtime import initialize_netfx, verify_packaged_runtime
        if getattr(sys,'frozen',False):
            startup.mark('windows_runtime_files')
            verify_packaged_runtime(PATHS.resources)
        startup.mark('netfx_runtime_loading')
        initialize_netfx()
        startup.mark('netfx_runtime_ready')
        # A daily startup copy bounds automatic backup growth without deleting explicit backups.
        startup.mark('database_backup')
        if active_database_path(PATHS.database).is_file():
            from datetime import datetime, timezone
            day = datetime.now(timezone.utc).strftime('%Y%m%d')
            if not list(PATHS.backups.glob('startup_'+day+'*.db')):
                snapshot(active_database_path(PATHS.database),PATHS.backups,prefix='startup')
                for old in sorted(PATHS.backups.glob('startup_*.db'))[:-7]: old.unlink()
        context = multiprocessing.get_context('spawn')
        receiver, sender = context.Pipe(duplex=False); stop = context.Event()
        token = secrets.token_urlsafe(32)
        from desktop.backend import run_backend
        process = context.Process(target=run_backend,args=(sender,stop,str(PATHS.database),token,str(PATHS.logs)),name='AHP backend')
        startup.mark('child_job_creation')
        job = ChildJob()
        startup.mark('backend_starting')
        process.start(); sender.close(); job.assign(process.pid)
        if not receiver.poll(45): raise RuntimeError('BACKEND_START_TIMEOUT')
        ready = receiver.recv(); receiver.close()
        if 'port' not in ready:
            startup.mark('backend_'+ready.get('stage','startup'))
            raise RuntimeError('BACKEND_START_FAILED')
        startup.mark('backend_ready')
        startup.mark('webview_import')
        import webview
        from webview.menu import Menu, MenuAction
        webview.settings['ALLOW_DOWNLOADS'] = True
        webview.settings['ALLOW_FILE_URLS'] = False
        webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True
        webview.settings['IGNORE_SSL_ERRORS'] = False
        url = f"http://127.0.0.1:{ready['port']}/_desktop/start?token={token}"
        window = webview.create_window('AHP Congress Analyzer',url,width=1280,height=850,min_size=(760,600),
                                       confirm_close=True, background_color='#f4f7ff')
        window.events.loaded += lambda:startup.mark('ui_document_loaded')
        window.events.closed += stop.set
        def backup_now():
            try: message('Yedek oluşturuldu:\n'+str(snapshot(active_database_path(PATHS.database),PATHS.backups)))
            except Exception as error: event('backup_failed',error); message('Yedek alınamadı. Disk alanını ve erişim izinlerini kontrol edin.',error=True)
        menu = [Menu('Dosya',[MenuAction('Veritabanını yedekle',backup_now),
                   MenuAction('Veri klasörünü aç',lambda:os.startfile(PATHS.data)),
                   MenuAction('Sürüm bilgisi',lambda:message('AHP Congress Analyzer '+VERSION)),
                   MenuAction('Çıkış',window.destroy)])]
        def monitor():
            while not stop.wait(.5):
                if not process.is_alive():
                    event('backend_stopped_unexpectedly')
                    stop.set()
                    smoke_result.update(ok=False,stage='backend_stopped',error_type='BACKEND_STOPPED_UNEXPECTEDLY')
                    if not args.smoke_ui:
                        message('Yerel uygulama servisi kapandı. Uygulamayı yeniden açın. Kayıtlarınız kullanıcı veri klasöründedir.',error=True)
                    window.confirm_close = False
                    window.destroy(); return
        threading.Thread(target=monitor,daemon=True).start()
        def check_ui():
            try:
                deadline=time.monotonic()+30
                while time.monotonic()<deadline and not stop.is_set():
                    ready=window.evaluate_js("Boolean(document.querySelector('#main h1') && document.querySelector('#nav-count') && !document.querySelector('#retry'))")
                    count=window.evaluate_js("document.querySelector('#nav-count')?.textContent") if ready else None
                    if ready and (not args.smoke_ui or count=='4'):
                        startup.mark('application_ready')
                        smoke_result.update(ok=True,version=VERSION,renderer='edgechromium',stage='application_ready',offline=bool(args.smoke_ui))
                        return
                    time.sleep(.2)
                if not stop.is_set(): raise RuntimeError('UI_LOAD_TIMEOUT')
            except Exception as error:
                event('ui_load_failed',error,stage='ui_load',component='desktop',startup=True)
                smoke_result.update(stage='ui_load',error_type=type(error).__name__)
            finally:
                if args.smoke_ui:
                    window.confirm_close = False
                    window.destroy()
        window.events.loaded += lambda:threading.Thread(target=check_ui,daemon=True).start()
        startup.mark('ui_starting')
        webview.start(gui='edgechromium',debug=False,private_mode=True,storage_path=str(PATHS.data/'cache'/'webview2'),
                      menu=menu,localization={'global.quitConfirmation':'Uygulama kapatılsın mı? Kaydedilmemiş değişiklikler ve süren analizler tamamlanmayabilir.'})
        return 0 if not args.smoke_ui or smoke_result['ok'] else 1
    except AlreadyRunning as error:
        event('startup_already_running',stage=startup.stage,component='desktop',code='ALREADY_RUNNING')
        smoke_result.update(stage=startup.stage,error_type='ALREADY_RUNNING')
        if not args.smoke_ui: message(str(error),error=True)
        return 1
    except Exception as error:
        description=startup.failure(error)
        smoke_result.update(stage=startup.stage,error_type=type(error).__name__)
        if not args.smoke_ui: message(description,error=True)
        return 1
    finally:
        for label,cleanup in (
            ('backend',lambda:stop_backend(process,stop) if process is not None and process.pid is not None else None),
            ('job',lambda:job.close() if job else None),('lock',lambda:lock.close() if lock else None),
            ('pipe',lambda:[p.close() for p in (receiver,sender) if p is not None])):
            try: cleanup()
            except Exception as error: event('shutdown_failed',error,stage='shutdown_'+label,component='desktop',startup=True)
        if args.smoke_ui:
            import json,shutil
            args.smoke_ui.parent.mkdir(parents=True,exist_ok=True)
            args.smoke_ui.write_text(json.dumps(smoke_result,ensure_ascii=False,indent=2),encoding='utf-8')
            if startup.paths and startup.paths.logs.exists():
                shutil.copytree(startup.paths.logs,args.smoke_ui.with_suffix('.logs'),dirs_exist_ok=True)
