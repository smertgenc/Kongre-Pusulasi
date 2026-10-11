import os
from pathlib import Path
from threading import Lock
from dotenv import dotenv_values, set_key
from app.config import ROOT, PATHS
from app.paths import is_desktop
from app.provider_catalog import PROVIDERS, AIConnection
from app.search import SEARCH_PROVIDERS, SearchConnection

class AISettings:
    def __init__(self, path=None, *, store=None):
        if store is None and path is None and is_desktop():
            from app.secret_store import DesktopSettingsStore
            store = DesktopSettingsStore(PATHS.settings)
        self.store = store
        self.path = Path(path) if path is not None else ROOT/'.env'
        self.use_environment = path is None
        self.lock = Lock()

    def _values(self):
        return self.store.read() if self.store else (dotenv_values(self.path) if self.path.exists() else {})

    def _value(self, values, name, default=''):
        if self.store:
            value = self.store.get_key(name) if name.endswith('_API_KEY') else values.get(name)
            return (value or default).strip()
        return (values.get(name) or (os.getenv(name, '') if self.use_environment else '') or default).strip()

    def _read(self):
        values = self._values()
        def value(name, default=''):
            return self._value(values, name, default)
        active = value('AI_PROVIDER', 'openai').lower()
        if active not in PROVIDERS:
            raise ValueError('AI_PROVIDER geçersiz. OpenAI, Gemini, OpenRouter, Groq veya AIMLAPI seçin.')
        connections = {p.id: AIConnection(p.id, value(p.key_env), value(p.model_env, p.default_model)) for p in PROVIDERS.values()}
        return active, connections

    def credentials(self):
        # A single snapshot prevents mixing keys/models during a settings change.
        with self.lock:
            active, connections = self._read()
            return connections[active]

    def analysis_connections(self):
        """One credential snapshot for a job, including its authorized backups."""
        with self.lock:
            return self._read()

    def _public(self):
        active, connections = self._read()
        c = connections[active]
        return {'configured':bool(c.key), 'model':c.model, 'provider':c.provider.name, 'provider_id':active,
                'fallback_providers':[{'provider_id':p.id, 'provider_name':p.name,
                                       'provider_model':connections[p.id].model}
                                      for p in PROVIDERS.values() if p.id!=active and connections[p.id].key],
                'providers':[{'id':p.id, 'name':p.name, 'default_model':p.default_model,
                              'model':connections[p.id].model, 'configured':bool(connections[p.id].key),
                              'help':p.help} for p in PROVIDERS.values()]}

    def public(self):
        with self.lock:
            return self._public()

    def save(self, request):
        # No secrets in the database, responses, logs or frontend storage.
        if request.api_key and any(not ('!' <= c <= '~') for c in request.api_key):
            raise ValueError('API anahtarı boşluk veya geçersiz karakter içermemelidir.')
        provider = PROVIDERS[request.provider_id]
        with self.lock:
            if self.store:
                self.store.save({provider.model_env:request.model, 'AI_PROVIDER':provider.id}, provider.key_env, request.api_key)
                return self._public()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.path.exists():
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
            self.path.chmod(0o600)
            if request.api_key: set_key(self.path, provider.key_env, request.api_key)
            set_key(self.path, provider.model_env, request.model)
            set_key(self.path, 'AI_PROVIDER', provider.id)
            self.path.chmod(0o600)
            return self._public()

    def _search_read(self):
        values=self._values()
        def value(name, default=''):
            return self._value(values, name, default)
        active=value('SEARCH_PROVIDER','jina')
        if active not in SEARCH_PROVIDERS: raise ValueError('Web araması için Jina AI Search veya Tavily seçin.')
        return active,{pid:SearchConnection(pid,value(pid.upper()+'_API_KEY')) for pid in SEARCH_PROVIDERS}

    def _search_public(self):
        active,connections=self._search_read()
        return {'provider_id':active,'provider':SEARCH_PROVIDERS[active],
                'configured':bool(connections[active].key),
                'providers':[{'id':pid,'name':name,'configured':bool(connections[pid].key)}
                             for pid,name in SEARCH_PROVIDERS.items()]}

    def search_public(self):
        with self.lock: return self._search_public()

    def search_credentials(self, provider_id=None):
        with self.lock:
            active,connections=self._search_read()
            return connections[provider_id or active]

    def save_search(self, request):
        if request.api_key and any(not ('!'<=c<='~') for c in request.api_key):
            raise ValueError('API anahtarı boşluk veya geçersiz karakter içermemelidir.')
        # Share the same lock with analysis settings: both update the same file.
        with self.lock:
            if self.store:
                self.store.save({'SEARCH_PROVIDER':request.provider_id},request.provider_id.upper()+'_API_KEY',request.api_key)
                return self._search_public()
            self.path.parent.mkdir(parents=True,exist_ok=True)
            if not self.path.exists():
                fd=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
            self.path.chmod(0o600)
            if request.api_key:set_key(self.path,request.provider_id.upper()+'_API_KEY',request.api_key)
            set_key(self.path,'SEARCH_PROVIDER',request.provider_id)
            self.path.chmod(0o600)
            return self._search_public()
