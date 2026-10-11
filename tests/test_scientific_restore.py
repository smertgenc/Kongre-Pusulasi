import hashlib,json,tempfile,unittest
from pathlib import Path
from tools.restore_scientific import restore
class RestoreTests(unittest.TestCase):
    def test_source_only_check_conflict_and_restore(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'project';backup=Path(d)/'backup';root.mkdir();(backup/'before').mkdir(parents=True)
            (root/'x.py').write_text('new');(backup/'before/x.py').write_text('old');(root/'new.py').write_text('added');(root/'.env').write_text('private');(root/'data').mkdir();(root/'data/test.db').write_bytes(b'untouched')
            sha=lambda x:hashlib.sha256(x.encode()).hexdigest()
            (backup/'changes.json').write_text(json.dumps({'x.py':{'before':sha('old'),'after':sha('new')},'new.py':{'before':None,'after':sha('added')}}))
            self.assertEqual(restore(root,backup),2);self.assertEqual((root/'x.py').read_text(),'new')
            (root/'x.py').write_text('user edit')
            with self.assertRaises(ValueError):restore(root,backup,True)
            (root/'x.py').write_text('new');restore(root,backup,True)
            self.assertEqual((root/'x.py').read_text(),'old');self.assertFalse((root/'new.py').exists())
            self.assertEqual((root/'.env').read_text(),'private');self.assertEqual((root/'data/test.db').read_bytes(),b'untouched')
