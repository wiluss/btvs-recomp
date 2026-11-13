from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/launcher'))
import player_support as support

TITLE={'title_id':'45410012','xbe_sha256':'a'*64}


class PlayerSupportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.profile=self.root/'private/profile'
        (self.root/'config').mkdir();(self.root/'config/title.json').write_text(json.dumps(TITLE));(self.root/'VERSION').write_text('0.1.0-alpha.9')
        (self.profile/'hdd/UDATA').mkdir(parents=True)
        (self.profile/'title.json').write_text(json.dumps(TITLE));(self.profile/'hdd/Partition0.img').write_bytes(b'partition table')
        (self.profile/'hdd/Partition1.img.gz').write_bytes(b'opaque compressed disk sentinel')
        self.save=self.profile/'hdd/UDATA/save';self.save.write_bytes(b'first checkpoint')
        self.proc=patch.object(support.subprocess,'run',return_value=subprocess.CompletedProcess([],1));self.proc.start();self.addCleanup(self.proc.stop)

    def test_complete_backup_restore_and_previous_profile_preservation(self):
        first=support.backup(self.root)
        support.verify_archive(self.root/'private/backups'/first['id'],TITLE)
        self.save.write_bytes(b'next checkpoint')
        restored=support.restore(self.root,first['id'])
        self.assertEqual(self.save.read_bytes(),b'first checkpoint')
        self.assertEqual((Path(restored['previous_profile'])/'hdd/UDATA/save').read_bytes(),b'next checkpoint')
        self.assertEqual((self.profile/'hdd/Partition1.img.gz').read_bytes(),b'opaque compressed disk sentinel')

    def test_auto_deduplicates_and_keeps_three_only_after_success(self):
        manual=support.backup(self.root)
        for i in range(5):
            self.save.write_bytes(bytes([i]));support.backup(self.root,True)
        entries=support.list_backups(self.root)
        self.assertEqual(len([e for e in entries if e['automatic']]),3)
        self.assertTrue((self.root/'private/backups'/manual['id']).exists())
        self.assertEqual(support.backup(self.root,True)['status'],'unchanged')
        self.assertEqual(len(support.list_backups(self.root)),4)

    def test_active_game_and_profile_lock_refuse_modifications(self):
        with patch.object(support.subprocess,'run',return_value=subprocess.CompletedProcess([],0)):
            with self.assertRaisesRegex(ValueError,'Close the game'):support.backup(self.root)
        import fcntl
        with (self.root/'private/profile.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError,'in use'):support.backup(self.root)
        self.assertEqual(self.save.read_bytes(),b'first checkpoint')

    def test_expanded_disks_symlinks_and_low_space_preserve_old_backups(self):
        saved=support.backup(self.root)
        disk=self.profile/'hdd/Partition2.img';disk.write_bytes(b'raw')
        with self.assertRaisesRegex(ValueError,'expanded'):support.backup(self.root)
        disk.unlink();link=self.profile/'hdd/link';link.symlink_to(self.root/'VERSION')
        with self.assertRaisesRegex(ValueError,'Symbolic'):support.backup(self.root)
        link.unlink()
        with patch.object(support.shutil,'disk_usage',return_value=type('Space',(),{'free':0})()):
            with self.assertRaisesRegex(ValueError,'free space'):support.backup(self.root)
        self.assertTrue((self.root/'private/backups'/saved['id']).exists())
        self.assertEqual(self.save.read_bytes(),b'first checkpoint')

    def test_corrupt_backup_and_other_title_are_rejected(self):
        result=support.backup(self.root);archive=self.root/'private/backups'/result['id']
        with self.assertRaisesRegex(ValueError,'another game'):support.verify_archive(archive,dict(TITLE,title_id='other'))
        bad=self.root/'bad.zip'
        with zipfile.ZipFile(archive) as source,zipfile.ZipFile(bad,'w') as dest:
            for item in source.infolist():dest.writestr(item,b'changed' if item.filename=='hdd/UDATA/save' else source.read(item))
        os.replace(bad,archive)
        with self.assertRaises(ValueError):support.restore(self.root,result['id'])
        self.assertEqual(self.save.read_bytes(),b'first checkpoint')

    def test_failed_restore_swap_rolls_back_original_profile(self):
        result=support.backup(self.root);self.save.write_bytes(b'new progress')
        original=os.replace
        def fail(src,dst):
            if Path(src).name.startswith('.restore-'):raise OSError('injected publication failure')
            return original(src,dst)
        with patch.object(support.os,'replace',side_effect=fail),self.assertRaises(OSError):support.restore(self.root,result['id'])
        self.assertEqual(self.save.read_bytes(),b'new progress')

    def test_report_omits_paths_raw_errors_and_log_secrets(self):
        folder=self.root/'artifacts';folder.mkdir()
        secret='TOP_SECRET_private_path_123'
        (folder/'play-menu-20261113-120000-123.json').write_text(json.dumps({'mode':'menu','settings':{'scale':2},'hdd':'/Users/Alice/'+secret,'error':secret,'texture_pack':'/Users/Alice/'+secret,'game_exit_code':None}))
        logs=self.root/'logs';logs.mkdir();(logs/'secret.log').write_text(secret)
        with patch.object(support.subprocess,'check_output',side_effect=['Apple M4','17179869184']):result=support.report(self.root)
        self.assertNotIn(secret,result['text']);self.assertNotIn(str(self.root),result['text']);self.assertNotIn('Alice',result['text'])
        self.assertIn('Apple M4',result['text']);self.assertIn('"error_recorded": true',result['text'])
        self.assertIn('"game_exit_code": null',result['text'])
        self.assertEqual(Path(result['path']).read_text(),result['text'])

    def test_first_launch_without_profile_does_not_create_fake_saves(self):
        import shutil
        shutil.rmtree(self.profile)
        self.assertEqual(support.backup(self.root,True)['status'],'absent')
        self.assertFalse(self.profile.exists())

    def test_interrupted_restore_recovers_before_first_launch_backup(self):
        backup=support.backup(self.root)
        previous=self.root/'private/backups/replaced-20261113T120000Z-12345678'
        stage=self.root/'private/.restore-example';stage.mkdir()
        os.replace(self.profile,previous)
        (self.root/'private/profile-restore.json').write_text(json.dumps({'previous':previous.name,'stage':stage.name}))
        support.backup(self.root,True)
        self.assertEqual(self.save.read_bytes(),b'first checkpoint')
        self.assertFalse((self.root/'private/profile-restore.json').exists())
        self.assertFalse(stage.exists())

    def test_extra_profile_metadata_is_preserved(self):
        (self.profile/'.DS_Store').write_bytes(b'finder metadata')
        result=support.backup(self.root)
        (self.profile/'.DS_Store').write_bytes(b'changed')
        support.restore(self.root,result['id'])
        self.assertEqual((self.profile/'.DS_Store').read_bytes(),b'finder metadata')

    def test_traversal_backup_cannot_write_outside_profile(self):
        result=support.backup(self.root);archive=self.root/'private/backups'/result['id'];bad=self.root/'bad.zip'
        with zipfile.ZipFile(archive) as source,zipfile.ZipFile(bad,'w') as dest:
            meta=json.loads(source.read('backup.json'))
            content=b'attack';meta['files']['../escape']={'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}
            for item in source.infolist():
                if item.filename!='backup.json':dest.writestr(item,source.read(item))
            info=zipfile.ZipInfo('../escape');info.external_attr=(0o100600<<16);dest.writestr(info,content)
            dest.writestr('backup.json',json.dumps(meta))
        os.replace(bad,archive)
        with self.assertRaises(ValueError):support.restore(self.root,result['id'])
        self.assertFalse((self.root/'escape').exists())
        self.assertEqual(self.save.read_bytes(),b'first checkpoint')

    def test_malformed_metadata_is_not_listed_as_a_backup(self):
        result=support.backup(self.root);archive=self.root/'private/backups'/result['id']
        with zipfile.ZipFile(archive,'w') as z:z.writestr('backup.json','[]')
        self.assertEqual(support.list_backups(self.root),[])
        with self.assertRaises(ValueError):support.restore(self.root,result['id'])
        self.assertEqual(self.save.read_bytes(),b'first checkpoint')
