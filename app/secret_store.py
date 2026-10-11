"""Windows Generic Credentials; only non-secret preferences go into JSON."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import tempfile

class CredentialStore:
    PREFIX = 'AHP Congress Analyzer/'

    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('Güvenli anahtar deposu Windows gerektirir.')
        class Credential(ctypes.Structure):
            _fields_ = [('Flags', wintypes.DWORD), ('Type', wintypes.DWORD),
                        ('TargetName', wintypes.LPWSTR), ('Comment', wintypes.LPWSTR),
                        ('LastWritten', wintypes.FILETIME), ('CredentialBlobSize', wintypes.DWORD),
                        ('CredentialBlob', ctypes.POINTER(ctypes.c_ubyte)), ('Persist', wintypes.DWORD),
                        ('AttributeCount', wintypes.DWORD), ('Attributes', ctypes.c_void_p),
                        ('TargetAlias', wintypes.LPWSTR), ('UserName', wintypes.LPWSTR)]
        self.Credential = Credential
        self.api = ctypes.WinDLL('advapi32', use_last_error=True)
        self.api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(Credential))]
        self.api.CredReadW.restype = wintypes.BOOL
        self.api.CredWriteW.argtypes = [ctypes.POINTER(Credential), wintypes.DWORD]
        self.api.CredWriteW.restype = wintypes.BOOL
        self.api.CredFree.argtypes = [ctypes.c_void_p]

    def get(self, name):
        pointer = ctypes.POINTER(self.Credential)()
        if not self.api.CredReadW(self.PREFIX + name, 1, 0, ctypes.byref(pointer)):
            if ctypes.get_last_error() == 1168: return ''
            raise ValueError('Windows anahtar deposu okunamadı. BT biriminize danışın.')
        try:
            c = pointer.contents
            return ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize).decode('utf-8')
        finally:
            self.api.CredFree(pointer)

    def set(self, name, secret):
        raw = secret.encode('utf-8')
        if len(raw) > 2560:
            raise ValueError('API anahtarı Windows güvenli depo sınırını aşıyor.')
        blob = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
        credential = self.Credential(Type=1, TargetName=self.PREFIX + name,
                                     CredentialBlobSize=len(raw), CredentialBlob=blob,
                                     Persist=2, UserName='API')
        try:
            if not self.api.CredWriteW(ctypes.byref(credential), 0):
                raise ValueError('API anahtarı Windows güvenli deposuna kaydedilemedi.')
        finally:
            ctypes.memset(blob, 0, len(raw))

class DesktopSettingsStore:
    def __init__(self, path, credentials=None):
        self.path = Path(path)
        self._credentials = credentials

    @property
    def credentials(self):
        # Local AHP startup must not load Credential Manager or require API keys.
        if self._credentials is None: self._credentials = CredentialStore()
        return self._credentials

    def read(self):
        try:
            values = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {}
        except (OSError, ValueError):
            raise ValueError('Bağlantı ayarları okunamadı. BT biriminizden yardım alın.') from None
        if not isinstance(values, dict): raise ValueError('Bağlantı ayarlarının biçimi hatalı.')
        # Never accept a plaintext key injected into the preferences file.
        return {k: v for k, v in values.items() if not k.endswith('_API_KEY') and isinstance(v, str)}

    def get_key(self, name): return self.credentials.get(name)

    def save(self, preferences, key_name=None, secret=None):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        values = self.read()
        values.update(preferences)
        if any(k.endswith('_API_KEY') for k in values): raise ValueError('Anahtarlar ayar dosyasına yazılamaz.')
        if secret: self.credentials.set(key_name, secret)
        fd, temporary = tempfile.mkstemp(dir=self.path.parent, prefix='.settings-', suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(values, stream, ensure_ascii=False, indent=2)
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            Path(temporary).unlink(missing_ok=True)
