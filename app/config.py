from pathlib import Path
import os
from dotenv import load_dotenv
from app.paths import application_paths, is_desktop

PATHS = application_paths()
ROOT = PATHS.resources
VERSION = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
# A release never reads a developer .env or writes into its installation folder.
if not is_desktop():
    load_dotenv(ROOT / '.env')
DEFAULT_DB = PATHS.database if is_desktop() else Path(os.getenv('KONGRE_DB_PATH', str(ROOT / 'data/kongre.db'))).expanduser()
if not DEFAULT_DB.is_absolute():
    DEFAULT_DB = ROOT / DEFAULT_DB
# Desktop binds an OS-assigned loopback port. A stale development setting must
# not prevent its imports or change its endpoint.
DEFAULT_PORT = 8765 if is_desktop() else int(os.getenv('KONGRE_PORT', '8765'))
