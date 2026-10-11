"""Startup diagnostics independent of API clients, database and UI imports."""
from pathlib import Path
import tempfile
from app.paths import application_paths
from desktop.logging_setup import configure_logs, event

RESOURCES=('VERSION','static/index.html','static/styles.css','static/app.js','static/ai.js',
           'static/logos.js','static/intelligence.js','static/compare.js','static/database.js',
           'app/intelligence_config.json','analiz/hesaplama_sonuclari.json')

class MissingResourceError(FileNotFoundError):
    def __init__(self,resource):
        self.resource=resource
        super().__init__('BUNDLED_RESOURCE_MISSING')

def check_resources(root):
    for resource in RESOURCES:
        if not (root/resource).is_file(): raise MissingResourceError(resource)

class Startup:
    def __init__(self,component='desktop'):
        self.component=component;self.stage='application_starting';self.paths=None;self.log_directory=None

    def mark(self,stage):
        self.stage=stage
        event('startup_stage',stage=stage,component=self.component)

    def prepare(self):
        self.stage='app_data_directory'
        self.paths=application_paths(desktop=True)
        self.stage='logging_initialization'
        directory=self.paths.logs/'desktop'
        configure_logs(directory);self.log_directory=directory
        self.mark('application_starting')
        self.mark('logging_initialized')
        self.mark('app_data_directory')
        self.paths.prepare()
        self.mark('app_data_directory_ready')

    def failure(self,error):
        if self.log_directory is None:
            try:
                directory=Path(tempfile.mkdtemp(prefix='ahp-startup-'))
                configure_logs(directory);self.log_directory=directory
            except OSError: pass
        event('backend_failed' if self.component=='backend' else 'desktop_failed',
              error,stage=self.stage,component=self.component,startup=True)
        data=str(self.paths.data) if self.paths else 'Kullanıcı veri yolu belirlenemedi.'
        log=str(self.log_directory/'error.log') if self.log_directory else 'Günlük dosyası oluşturulamadı.'
        reason=('Windows .NET Framework bileşeni yüklenemedi.' if self.stage=='netfx_runtime_loading' else
                'Kurulumda gerekli Windows DLL dosyası eksik.' if self.stage=='windows_runtime_files' else
                'Uygulama başlatılamadı.')
        return (reason+'\nAşama: '+self.stage+'\nHata türü: '+type(error).__name__+
                '\nVeriler: '+data+'\nHata kaydı: '+log+'\nBT biriminize bu hata kaydını iletin.')
