from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import bootstrap_runtime as boot


def repository(root):
    root.mkdir()
    subprocess.run(['git','init','--quiet',str(root)],check=True)
    (root/'LICENSE').write_text('synthetic generic toolkit fixture')
    subprocess.run(['git','-C',str(root),'add','LICENSE'],check=True)
    subprocess.run(['git','-C',str(root),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','--quiet','-m','fixture'],check=True)
    return boot.git('-C',root,'rev-parse','HEAD')


class BootstrapRuntimeTests(unittest.TestCase):
    def test_pinned_bootstrap_works_without_a_parent_git_repository(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);origin=root/'origin';revision=repository(origin);project=root/'kit';project.mkdir()
            (project/'dependencies.lock.json').write_text(json.dumps({'xboxrecomp':{'path':'vendor/xboxrecomp','revision':revision,'repository':str(origin)}}))
            target=boot.bootstrap(project)
            self.assertEqual(boot.git('-C',target,'rev-parse','HEAD'),revision)
            (target/'local-note').write_text('preserve me')
            self.assertEqual(boot.bootstrap(project),target)
            self.assertEqual((target/'local-note').read_text(),'preserve me')

    def test_invalid_pin_and_existing_nonempty_directory_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);origin=root/'origin';revision=repository(origin);project=root/'kit';project.mkdir()
            lock={'xboxrecomp':{'path':'vendor/xboxrecomp','revision':revision,'repository':str(origin)}}
            path=project/'dependencies.lock.json';path.write_text(json.dumps(lock))
            target=project/'vendor/xboxrecomp';target.mkdir(parents=True);(target/'precious').write_text('local')
            with self.assertRaises((ValueError,subprocess.SubprocessError)):boot.bootstrap(project)
            self.assertEqual((target/'precious').read_text(),'local')
            lock['xboxrecomp']['revision']='not-a-pin';path.write_text(json.dumps(lock))
            with self.assertRaises(ValueError):boot.bootstrap(project)
            self.assertEqual((target/'precious').read_text(),'local')

    def test_symbolic_target_and_failed_fetch_leave_no_partial_toolkit(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);origin=root/'origin';revision=repository(origin);project=root/'kit';project.mkdir()
            lock={'xboxrecomp':{'path':'vendor/xboxrecomp','revision':revision,'repository':str(origin)}}
            path=project/'dependencies.lock.json';path.write_text(json.dumps(lock))
            (project/'vendor').mkdir();target=project/'vendor/xboxrecomp';target.symlink_to(origin,target_is_directory=True)
            with self.assertRaises(ValueError):boot.bootstrap(project)
            target.unlink();lock['xboxrecomp']['revision']='0'*40;path.write_text(json.dumps(lock))
            with self.assertRaises(subprocess.SubprocessError):boot.bootstrap(project)
            self.assertFalse(target.exists());self.assertFalse(list((project/'vendor').glob('.toolkit-*')))
