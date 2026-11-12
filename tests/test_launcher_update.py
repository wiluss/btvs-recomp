from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import update_launcher as update


def kit(root,version,launcher):
    files={'VERSION':version+'\n','src/launcher/Main.swift':launcher,'tools/play.py':'unchanged game input',
           'README.md':'source kit '+version}
    for name,text in files.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    inventory(root,version,files)


def inventory(root,version,files):
    (root/update.MANIFEST).write_text(json.dumps({'version':version,'files':{
        name:{'bytes':(root/name).stat().st_size,'sha256':update.digest(root/name)} for name in files}}))


def build(source,log):
    app=source/update.APP/'Contents/MacOS/BuffyLauncher';app.parent.mkdir(parents=True);app.write_text('new launcher');app.chmod(0o755)


class LauncherUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name).resolve();self.old=base/'old';self.new=base/'new'
        kit(self.old,'0.1.0-alpha.6','old launcher source');kit(self.new,'0.1.0-alpha.8','new launcher source')
        build(self.old,None)
        (self.old/update.APP/'Contents/MacOS/BuffyLauncher').write_text('old executable')
        self.kept=['private/profile/save','private/game/Default.xbe','private/hd/pack','generated/game.c','build/game/buffy-macos','vendor/runtime.c']
        for name in self.kept:
            p=self.old/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('preserve '+name)
        self.game=patch.object(update,'game_closed');self.game.start();self.addCleanup(self.game.stop)

    def assert_private_kept(self):
        for name in self.kept:self.assertEqual((self.old/name).read_text(),'preserve '+name)

    def test_install_changes_only_sources_and_launcher_and_keeps_backup(self):
        with patch.object(update,'emit'):
            update.install(self.new,self.old,builder=build)
        self.assertEqual((self.old/'VERSION').read_text(),'0.1.0-alpha.8\n')
        self.assertEqual((self.old/update.APP/'Contents/MacOS/BuffyLauncher').read_text(),'new launcher')
        self.assertTrue(os.access(self.old/update.APP/'Contents/MacOS/BuffyLauncher',os.X_OK))
        self.assert_private_kept();update.inventory(self.old)
        self.assertEqual(len(list((self.old/'artifacts').glob('launcher-update-*/backup/build/btvs-recomp.app'))),1)
        self.assertFalse((self.old/'artifacts/launcher-update.lock').exists())

    def test_failed_build_preserves_previous_installation(self):
        def fail(*args):raise ValueError('compile failed')
        with self.assertRaisesRegex(ValueError,'compile failed'):update.install(self.new,self.old,builder=fail)
        update.inventory(self.old);self.assert_private_kept()
        self.assertEqual((self.old/update.APP/'Contents/MacOS/BuffyLauncher').read_text(),'old executable')

    def test_mid_install_failure_restores_all_sources_and_app(self):
        original=os.replace
        def fail(src,dst):
            if str(src).endswith('/stage/'+update.APP):raise OSError('injected rename failure')
            return original(src,dst)
        with patch.object(update.os,'replace',side_effect=fail),self.assertRaisesRegex(OSError,'injected'):
            update.install(self.new,self.old,builder=build)
        self.assertEqual((self.old/'VERSION').read_text(),'0.1.0-alpha.6\n')
        self.assertEqual((self.old/update.APP/'Contents/MacOS/BuffyLauncher').read_text(),'old executable')
        update.inventory(self.old);self.assert_private_kept()

    def test_local_edits_game_changes_and_symlinks_are_refused(self):
        p=self.old/'README.md';before=p.read_text();p.write_text('local edit')
        with self.assertRaisesRegex(ValueError,'changed or missing'):update.plan(self.new,self.old)
        p.write_text(before)
        (self.new/'tools/play.py').write_text('new game input')
        names=json.loads((self.new/update.MANIFEST).read_text())['files'];inventory(self.new,'0.1.0-alpha.8',names)
        with self.assertRaisesRegex(ValueError,'game/runtime'):update.plan(self.new,self.old)
        (self.new/'tools/play.py').write_text('unchanged game input');inventory(self.new,'0.1.0-alpha.8',names)
        p.unlink();p.symlink_to(self.new/'README.md')
        with self.assertRaisesRegex(ValueError,'Symbolic'):update.plan(self.new,self.old)
        self.assert_private_kept()

    def test_edits_during_build_are_not_overwritten(self):
        def concurrent(source,log):
            build(source,log);(self.old/'README.md').write_text('edit made during build')
        with self.assertRaisesRegex(ValueError,'changed or missing'):update.install(self.new,self.old,builder=concurrent)
        self.assertEqual((self.old/'README.md').read_text(),'edit made during build')
        self.assertEqual((self.old/'VERSION').read_text(),'0.1.0-alpha.6\n')
        self.assert_private_kept()

    def test_download_checksum_and_https_origin_are_required(self):
        info={'tag_name':'v0.1.0-alpha.8','assets':[{'name':'btvs-recomp-v0.1.0-alpha.8-source.zip','browser_download_url':'https://github.com/file','digest':'sha256:'+'0'*64}]}
        with patch.object(update,'fetch',return_value=b'wrong archive'),self.assertRaisesRegex(ValueError,'checksum'):
            update.download_release(info,self.new)
        for url in ['http://github.com/a','https://evil.example/a','https://github.com.evil.example/a','https://user@github.com/a']:
            with self.assertRaises(ValueError):update.checked_url(url)

    def test_recovery_refuses_a_live_updater(self):
        lock=self.old/'artifacts/launcher-update.lock';lock.mkdir(parents=True);(lock/'pid').write_text(str(os.getpid()))
        with self.assertRaisesRegex(ValueError,'still running'):update.recover(self.old)

    def test_update_cannot_downgrade_or_target_its_source(self):
        with self.assertRaises(ValueError):update.plan(self.new,self.new)
        with self.assertRaisesRegex(ValueError,'already'):update.plan(self.old,self.new)

    def test_interrupted_transaction_recovery_restores_old_files(self):
        work=self.old/'artifacts'/('launcher-update-'+'a'*32);work.mkdir(parents=True)
        backup=work/'backup/VERSION';backup.parent.mkdir();os.replace(self.old/'VERSION',backup)
        (self.old/'VERSION').write_text('partial new version')
        journal={'state':'installing','pending':['VERSION'],'existed':['VERSION']}
        update.write_journal(work/'journal.json',journal)
        lock=self.old/'artifacts/launcher-update.lock';lock.mkdir();(lock/'pid').write_text('99999999');(lock/'work').write_text(work.name)
        with patch.object(update.os,'kill',side_effect=ProcessLookupError),patch.object(update,'emit'):
            update.recover(self.old)
        update.inventory(self.old);self.assert_private_kept();self.assertFalse(lock.exists())
        self.assertEqual((work/'rolled-back/VERSION').read_text(),'partial new version')

    def test_changed_file_during_rename_is_restored_without_losing_edit(self):
        original=os.replace
        def race(src,dst):
            if str(src)==str(self.old/'README.md') and '/backup/' in str(dst):Path(src).write_text('concurrent user edit')
            return original(src,dst)
        with patch.object(update.os,'replace',side_effect=race),self.assertRaisesRegex(ValueError,'changed during installation'):
            update.install(self.new,self.old,builder=build)
        self.assertEqual((self.old/'README.md').read_text(),'concurrent user edit')
        self.assertEqual((self.old/'VERSION').read_text(),'0.1.0-alpha.6\n')
        self.assert_private_kept()
