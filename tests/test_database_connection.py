from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from threading import Event
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import create_app
from app.database_connection import active_database_path, connection_file, connections_dir
from tests.test_ai import FixtureProvider, TEXT

class DatabaseConnectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
        self.base=self.root/'current.db';self.settings=self.root/'settings.env'
        self.app=create_app(self.base,settings_path=self.settings,ai_provider=FixtureProvider())
        self.client=TestClient(self.app).__enter__()
        self.before=self.client.get('/api/state').json()
        self.source=self.root/'source.db'
        with TestClient(create_app(self.source,settings_path=self.root/'other.env')) as other:
            state=other.get('/api/state').json()
            response=other.post('/api/evaluations',json=self.payload(state,'Taşınan Kongre'))
            self.assertEqual(response.status_code,201,response.text)
        self.source_bytes=self.source.read_bytes()

    def tearDown(self):
        self.client.__exit__(None,None,None);self.tmp.cleanup()

    def payload(self,state,name):
        return {'model_id':state['models'][0]['id'],'metadata':{'name':name,'edition':'2027','context':'Test'},
                'scale':1,'evaluator':'Test','scores':{f'K{i}':1 for i in range(1,11)},
                'notes':{f'K{i}':'Kaynak' for i in range(1,11)}}

    def inspect(self,raw=None,name='Kongreler.db'):
        return self.client.post('/api/database/inspect',content=self.source_bytes if raw is None else raw,
            headers={'Content-Type':'application/octet-stream','X-Database-File-Name':name})

    def connect(self,preview=None,**changes):
        preview=preview or self.inspect().json()
        return self.client.post('/api/database/connect',json={'token':preview['token'],
             'database_id':self.before['database_id'],'confirmed':True,**changes})

    def test_preview_is_read_only_for_current_and_original_then_connection_persists(self):
        preview=self.inspect();self.assertEqual(preview.status_code,200,preview.text)
        self.assertEqual(preview.json()['counts']['active_congresses'],5)
        self.assertEqual(self.client.get('/api/state').json(),self.before)
        old=self.base.read_bytes()
        connected=self.connect(preview.json());self.assertEqual(connected.status_code,200,connected.text)
        self.assertEqual(self.source.read_bytes(),self.source_bytes)
        self.assertEqual(self.base.read_bytes(),old)
        self.assertTrue(Path(connected.json()['previous_backup']).is_file())
        current=self.client.get('/api/state').json()
        self.assertEqual(len(current['congresses']),5)
        self.assertNotEqual(current['database_id'],self.before['database_id'])
        self.assertEqual(self.client.post('/api/evaluations',json=self.payload(current,'Yeni bağlantıdaki kayıt')).status_code,201)
        self.client.__exit__(None,None,None)
        self.app=create_app(self.base,settings_path=self.settings)
        self.client=TestClient(self.app).__enter__()
        self.assertEqual(len(self.client.get('/api/state').json()['congresses']),6)
        self.assertEqual(self.client.get('/api/database/status').json()['label'],'Kongreler.db')
        self.assertEqual(self.source.read_bytes(),self.source_bytes)
        self.assertTrue(active_database_path(self.base).is_relative_to(connections_dir(self.base)))

    def test_sqlite_download_is_a_valid_database_and_cleans_server_export(self):
        response=self.client.get('/api/database/backup')
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.content.startswith(b'SQLite format 3\x00'))
        path=self.root/'download.db';path.write_bytes(response.content)
        with closing(sqlite3.connect(path)) as connection:
            self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(connection.execute('SELECT count(*) FROM congresses').fetchone()[0],4)
        self.assertEqual(list((self.root/'exports').glob('*.db')),[])

    def test_bad_foreign_future_schema_and_sql_files_rejected(self):
        foreign=self.root/'foreign.db'
        with closing(sqlite3.connect(foreign)) as connection:
            connection.execute('CREATE TABLE customer (id INTEGER)');connection.commit()
        future=self.root/'future.db';future.write_bytes(self.source_bytes)
        with closing(sqlite3.connect(future)) as connection:connection.execute('PRAGMA user_version=999')
        for raw in (b'SELECT 1;',b'not sqlite',foreign.read_bytes(),future.read_bytes()):
            response=self.inspect(raw)
            self.assertEqual(response.status_code,422,response.text)
            self.assertEqual(self.client.get('/api/state').json(),self.before)
        self.assertFalse(connection_file(self.base).exists())
        self.assertEqual(list(self.app.state.connections.pending_dir.glob('*.db')),[])

    def test_schema_with_trigger_and_incompatible_columns_rejected(self):
        path=self.root/'trigger.db';path.write_bytes(self.source_bytes)
        with closing(sqlite3.connect(path)) as connection:
            connection.execute('CREATE TRIGGER unwanted AFTER INSERT ON congresses BEGIN DELETE FROM evaluations; END;');connection.commit()
        self.assertEqual(self.inspect(path.read_bytes()).status_code,422)
        path=self.root/'columns.db';path.write_bytes(self.source_bytes)
        with closing(sqlite3.connect(path)) as connection:connection.execute('ALTER TABLE congresses ADD COLUMN unwanted TEXT');connection.commit()
        self.assertEqual(self.inspect(path.read_bytes()).status_code,422)

    def test_confirm_token_and_stale_tab_protect_switch(self):
        preview=self.inspect().json()
        self.assertEqual(self.connect(preview,confirmed=False).status_code,422)
        self.assertEqual(self.connect(preview,token='0'*32).status_code,422)
        self.assertEqual(self.connect(preview).status_code,200)
        self.assertEqual(self.connect(preview).status_code,409)
        state=self.client.get('/api/state').json()
        response=self.client.post('/api/evaluations',json=self.payload(state,'Stale tab'),headers={'X-AHP-Database':self.before['database_id']})
        self.assertEqual(response.status_code,409)
        self.assertEqual(len(self.client.get('/api/state').json()['congresses']),5)

    def test_upload_bounds_type_origin_and_expired_preview(self):
        self.assertEqual(self.client.post('/api/database/inspect',json={}).status_code,415)
        with patch('app.main.MAX_DATABASE_BYTES',16):self.assertEqual(self.inspect().status_code,413)
        response=self.client.post('/api/database/inspect',content=self.source_bytes,headers={'content-type':'application/octet-stream','origin':'https://external.example'})
        self.assertEqual(response.status_code,403)
        preview=self.inspect().json();self.app.state.connections.pending[preview['token']]['created']=0
        self.assertEqual(self.connect(preview).status_code,422)
        self.assertEqual(self.client.get('/api/state').json(),self.before)

    def test_manifest_write_failure_keeps_current_connection_and_all_originals(self):
        preview=self.inspect().json()
        import os
        original=os.replace
        def fail_config(source,target):
            if Path(target)==connection_file(self.base):raise OSError('disk error')
            return original(source,target)
        with patch('app.database_connection.os.replace',side_effect=fail_config):
            with self.assertRaises(OSError): self.connect(preview)
        self.assertEqual(self.client.get('/api/state').json(),self.before)
        self.assertEqual(self.source.read_bytes(),self.source_bytes)
        self.assertFalse(connection_file(self.base).exists())
        self.assertEqual(self.connect(preview).status_code,200)

    def test_running_ai_background_task_blocks_connection_until_finished(self):
        started=Event();release=Event();provider=FixtureProvider()
        class WaitingProvider:
            def analyze(self,*args,**kwargs):
                started.set();release.wait(10)
                return provider.analyze(*args,**kwargs)
        self.app.state.ai.provider=WaitingProvider()
        self.client.post('/api/ai/settings',json={'api_key':'fake-test-key','model':'fixture'})
        preview=self.inspect().json()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(self.client.post,'/api/ai/start',json={
                'model_id':self.before['models'][0]['id'],'transfer_consent':True,'sources':[{'kind':'text','content':TEXT}]})
            try:
                self.assertTrue(started.wait(5))
                self.assertEqual(self.connect(preview).status_code,409)
                self.assertEqual(self.client.get('/api/state').json(),self.before)
            finally:release.set()
            self.assertEqual(future.result().status_code,202)
        self.assertEqual(self.connect(preview).status_code,200)

    def test_tampered_connection_path_cannot_open_arbitrary_file(self):
        connection_file(self.base).write_text(json.dumps({'file':'../source.db'}))
        with self.assertRaises(ValueError): active_database_path(self.base)

    def test_invalid_ahp_numbers_and_missing_results_are_rejected(self):
        for table,change in [('models',lambda data:data['weights'].update(K1=-1)),
                             ('evaluations',lambda data:data.pop('result'))]:
            path=self.root/'invalid.db';path.write_bytes(self.source_bytes)
            with closing(sqlite3.connect(path)) as connection:
                row_id,raw=connection.execute(f'SELECT id,data FROM {table} LIMIT 1').fetchone()
                data=json.loads(raw);change(data)
                connection.execute(f'UPDATE {table} SET data=? WHERE id=?',(json.dumps(data),row_id));connection.commit()
            self.assertEqual(self.inspect(path.read_bytes()).status_code,422)
        self.assertEqual(self.client.get('/api/state').json(),self.before)

    def test_staging_failure_can_be_retried_and_keeps_old_database(self):
        preview=self.inspect().json()
        with patch('app.database_connection.tempfile.mkstemp',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.connect(preview)
        self.assertEqual(self.client.get('/api/state').json(),self.before)
        self.assertEqual(self.connect(preview).status_code,200)

if __name__=='__main__':unittest.main()
