#!/usr/bin/env python3
"""FastAPI launcher plus backwards-compatible Python helpers."""
import argparse
import sqlite3
import threading
import webbrowser
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from app.config import DEFAULT_DB, DEFAULT_PORT
from app.database import Database
from app.database_connection import active_database_path
from app.schemas import EvaluationInput
from app.services import CongressService

DB_PATH = DEFAULT_DB

def connect():
    """SQLite backup compatibility only; application writes use SQLAlchemy."""
    connection = sqlite3.connect(str(active_database_path(DB_PATH)), timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    return connection

def _call(method, *args):
    db = Database(active_database_path(DB_PATH))
    try:
        return getattr(CongressService(db), method)(*args)
    except IntegrityError as error:
        raise sqlite3.IntegrityError('Aynı ad ve edisyonla bir kongre zaten var.') from error
    finally:
        db.close()

def initialize(): return _call('initialize')
def state(): return _call('state')
def save_evaluation(payload): return _call('save_evaluation', EvaluationInput.model_validate(payload))

def main():
    import uvicorn
    from desktop.logging_setup import configure_logs
    from app.config import PATHS
    from app.main import create_app
    parser = argparse.ArgumentParser(description='Kongre Pusulası — FastAPI')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--db', type=Path, default=DB_PATH)
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    if args.open:
        threading.Timer(1, lambda: webbrowser.open(f'http://127.0.0.1:{args.port}')).start()
    configure_logs(PATHS.logs)
    uvicorn.run(create_app(args.db), host='127.0.0.1', port=args.port,log_config=None,access_log=False)

if __name__ == '__main__': main()
