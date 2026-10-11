"""Read-only application resources and per-user writable data are separate."""
from dataclasses import dataclass
import os
from pathlib import Path
import sys

PRODUCT = 'AHP Congress Analyzer'

@dataclass(frozen=True)
class AppPaths:
    resources: Path
    data: Path

    @property
    def database(self): return self.data / 'database' / 'kongre.db'
    @property
    def backups(self): return self.data / 'backups'
    @property
    def logs(self): return self.data / 'logs'
    @property
    def settings(self): return self.data / 'config' / 'settings.json'

    def prepare(self):
        for name in ('database', 'backups', 'logs', 'exports', 'cache', 'config'):
            (self.data / name).mkdir(parents=True, exist_ok=True)

def is_desktop():
    return bool(getattr(sys, 'frozen', False)) or os.getenv('KONGRE_DESKTOP') == '1'

def application_paths(*, desktop=None, resources=None, local_app_data=None):
    resources = Path(resources or getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent)).resolve()
    desktop = is_desktop() if desktop is None else desktop
    if desktop:
        base = local_app_data or os.getenv('LOCALAPPDATA')
        if not base or not Path(base).is_absolute():
            raise RuntimeError('Windows kullanıcı veri dizini belirlenemedi.')
        data = Path(base).resolve() / PRODUCT
    else:
        data = resources / 'data'
    return AppPaths(resources, data)
