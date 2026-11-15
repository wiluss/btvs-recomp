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
    def test_beta_rc_and_stable_ordering(self):
        versions=['0.1.0-alpha.9','0.2.0-alpha.10','0.2.0-beta.1',
                  '0.2.0-beta.2','0.2.0-rc.1','0.2.0','0.2.1-alpha.1']
        self.assertEqual(sorted(versions,key=update.version),versions)
        for bad in ['0.2.0-beta','0.2.0-beta.1/','0.2.0-dev.1']:
            with self.assertRaises(ValueError):update.version(bad)

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
        self.assertIn('tools/play.py',update.plan(self.new,self.old)[2])
        (self.new/'tools/play.py').write_text('unchanged game input');inventory(self.new,'0.1.0-alpha.8',names)
        p.unlink();p.symlink_to(self.new/'README.md')
        with self.assertRaisesRegex(ValueError,'Symbolic'):update.plan(self.new,self.old)
        self.assert_private_kept()

    def full_candidate(self):
        names=json.loads((self.new/update.MANIFEST).read_text())['files']
        (self.new/'tools/play.py').write_text('new game input')
        (self.new/'VERSION').write_text('0.2.0-beta.1\n')
        inventory(self.new,'0.2.0-beta.1',names)
        for name in update.GAME_OUTPUTS:
            path=self.old/name
            if name in ('generated','vendor/xboxrecomp'):
                path.mkdir(exist_ok=True,parents=True);(path/'old.txt').write_text('old '+name)
            elif not path.exists():
                path.parent.mkdir(exist_ok=True,parents=True);path.write_text('old '+name)

    @staticmethod
    def game_build(stage,log,target):
        for name in update.GAME_OUTPUTS:
            path=stage/name;path.parent.mkdir(exist_ok=True,parents=True)
            if name in ('generated','vendor/xboxrecomp'):
                path.mkdir();(path/'new.txt').write_text('new '+name)
            else:path.write_text('new '+name)

    def test_game_update_installs_outputs_and_sources_together_keeps_private_data(self):
        self.full_candidate()
        update.install(self.new,self.old,builder=build,game_builder=self.game_build)
        update.inventory(self.old)
        self.assertEqual((self.old/update.GAME).read_text(),'new '+update.GAME)
        self.assertTrue((self.old/'generated/new.txt').exists())
        self.assertFalse((self.old/'generated/old.txt').exists())
        for name in self.kept:
            if not name.startswith(('generated/','build/game/')):
                self.assertEqual((self.old/name).read_text(),'preserve '+name)
        work=next((self.old/'artifacts').glob('launcher-update-*/backup'))
        self.assertEqual((work/update.GAME).read_text(),'preserve '+update.GAME)
        self.assertTrue((work/'generated/old.txt').exists())

    def test_failed_game_build_does_not_install_new_sources_or_binary(self):
        self.full_candidate()
        def failure(*args):raise ValueError('game compilation failed')
        with self.assertRaisesRegex(ValueError,'game compilation failed'):
            update.install(self.new,self.old,builder=build,game_builder=failure)
        self.assertEqual((self.old/'VERSION').read_text(),'0.1.0-alpha.6\n')
        self.assert_private_kept()

    def test_game_install_failure_restores_binary_generated_runtime_and_receipts(self):
        self.full_candidate();original=os.replace
        def fail(src,dst):
            if str(src).endswith('/stage/artifacts/pipeline-recomp.json'):raise OSError('game receipt failed')
            return original(src,dst)
        with patch.object(update.os,'replace',side_effect=fail),self.assertRaisesRegex(OSError,'receipt failed'):
            update.install(self.new,self.old,builder=build,game_builder=self.game_build)
        self.assert_private_kept();update.inventory(self.old)
        self.assertTrue((self.old/'generated/old.txt').exists())
        self.assertTrue((self.old/'vendor/xboxrecomp/old.txt').exists())
        self.assertFalse((self.old/'generated/new.txt').exists())

    def test_missing_game_output_is_refused_before_source_replacement(self):
        self.full_candidate()
        with self.assertRaisesRegex(ValueError,'Missing staged game output'):
            update.install(self.new,self.old,builder=build,game_builder=lambda *a:None)
        self.assert_private_kept();update.inventory(self.old)

    def test_concurrent_game_rebuild_is_preserved(self):
        self.full_candidate()
        def concurrent(stage,log,target):
            self.game_build(stage,log,target);(target/update.GAME).write_text('local manual rebuild')
        with self.assertRaisesRegex(ValueError,'Installed game changed'):
            update.install(self.new,self.old,builder=build,game_builder=concurrent)
        self.assertEqual((self.old/update.GAME).read_text(),'local manual rebuild')
        self.assertEqual((self.old/'VERSION').read_text(),'0.1.0-alpha.6\n')

    def test_active_game_session_blocks_update(self):
        import fcntl
        path=self.old/'private/hdd-storage.lock'
        with path.open('a') as handle:
            fcntl.flock(handle,fcntl.LOCK_SH|fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError,'Close the game'):
                update.install(self.new,self.old,builder=build)
        self.assert_private_kept();update.inventory(self.old)

    def test_edits_during_build_are_not_overwritten(self):
        def concurrent(source,log):
            build(source,log);(self.old/'README.md').write_text('edit made during build')
        with self.assertRaisesRegex(ValueError,'changed or missing'):update.install(self.new,self.old,builder=concurrent)
        self.assertEqual((self.old/'README.md').read_text(),'edit made during build')
        self.assertEqual((self.old/'VERSION').read_text(),'0.1.0-alpha.6\n')
        self.assert_private_kept()

    def test_interrupted_game_install_recovers_all_owned_outputs(self):
        self.full_candidate()
        work=self.old/'artifacts'/('launcher-update-'+'b'*32);work.mkdir(parents=True)
        names=[update.GAME,'generated','vendor/xboxrecomp']
        for name in names:
            live=self.old/name;backup=work/'backup'/name;backup.parent.mkdir(parents=True,exist_ok=True)
            os.replace(live,backup)
            if name==update.GAME:live.write_text('interrupted new binary')
            else:live.mkdir();(live/'partial').write_text('new partial output')
        update.write_journal(work/'journal.json',{'state':'installing','pending':names,'existed':names})
        lock=self.old/'artifacts/launcher-update.lock';lock.mkdir();(lock/'pid').write_text('99999999');(lock/'work').write_text(work.name)
        with patch.object(update.os,'kill',side_effect=ProcessLookupError):update.recover(self.old)
        self.assert_private_kept();update.inventory(self.old)
        self.assertFalse((self.old/'generated/partial').exists())
        self.assertEqual((work/'rolled-back'/update.GAME).read_text(),'interrupted new binary')

    def test_runtime_patch_additions_are_accepted_but_local_edits_are_preserved(self):
        import subprocess
        with tempfile.TemporaryDirectory(prefix='btvs runtime ') as folder:
            base=Path(folder);target=base/'old';stage=base/'stage'
            live=target/'vendor/xboxrecomp';live.mkdir(parents=True);stage.mkdir()
            def git(*args):return subprocess.check_output(['git','-C',str(live),*args],stderr=subprocess.STDOUT)
            git('init','--quiet');(live/'base.c').write_text('original\n');git('add','base.c')
            git('-c','user.name=Test','-c','user.email=test@example.invalid','-c','commit.gpgsign=false','commit','-qm','fixture')
            head=git('rev-parse','HEAD').decode().strip()
            patch=target/'patches/add.patch';patch.parent.mkdir()
            patch.write_text('diff --git a/extra.c b/extra.c\nnew file mode 100644\n--- /dev/null\n+++ b/extra.c\n@@ -0,0 +1 @@\n+stock patch addition\n')
            git('apply',str(patch))
            lock={'xboxrecomp':{'path':'vendor/xboxrecomp','revision':head,'repository':str(live),'runtime_patches':['patches/add.patch']}}
            (target/'dependencies.lock.json').write_text(json.dumps(lock));(stage/'dependencies.lock.json').write_text(json.dumps(lock))
            before=update.runtime_state(live)
            update.prepare_runtime(stage,target,base/'build.log')
            self.assertEqual(update.runtime_state(live),before)
            self.assertFalse((stage/'vendor/xboxrecomp/extra.c').exists())
            self.assertFalse((stage/'vendor/xboxrecomp/.git/objects/info/alternates').exists())
            (live/'extra.c').write_text('local custom change\n')
            other=base/'other';other.mkdir();(other/'dependencies.lock.json').write_text(json.dumps(lock))
            with self.assertRaisesRegex(ValueError,'Locally edited runtime'):
                update.prepare_runtime(other,target,base/'refused.log')
            self.assertEqual((live/'extra.c').read_text(),'local custom change\n')

    def test_build_interruption_stops_its_child_group(self):
        import subprocess,time
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);pidfile=base/'child.pid'
            code='import subprocess,sys,time,pathlib;p=subprocess.Popen(["/bin/sleep","120"]);pathlib.Path(sys.argv[1]).write_text(str(p.pid));time.sleep(120)'
            original=subprocess.Popen
            def launch(*args,**kwargs):
                child=original(*args,**kwargs);wait=child.wait;first=True
                def interrupt(*a,**k):
                    nonlocal first
                    if first:
                        first=False;deadline=time.monotonic()+5
                        while not pidfile.exists() and time.monotonic()<deadline:time.sleep(.01)
                        self.assertTrue(pidfile.exists());raise KeyboardInterrupt()
                    return wait(*a,**k)
                child.wait=interrupt
                return child
            with patch.object(update.subprocess,'Popen',side_effect=launch),self.assertRaises(KeyboardInterrupt):
                update.run_build([sys.executable,'-c',code,str(pidfile)],base,base/'build.log')
            pid=int(pidfile.read_text());deadline=time.monotonic()+2
            while True:
                state=subprocess.run(['/bin/ps','-p',str(pid),'-o','stat='],capture_output=True,text=True)
                if state.returncode or state.stdout.strip().startswith('Z'):break
                if time.monotonic()>deadline:self.fail('Build descendant survived interruption')
                time.sleep(.02)

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
