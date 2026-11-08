from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ScreenWTests(unittest.TestCase):
    def test_host_clip_coordinates_survive_infinite_w(self):
        header = ROOT / 'vendor/xboxrecomp/src/kernel/nv2a_screen_w.h'
        self.assertTrue(header.exists(), 'Apply patches/xboxrecomp/0001-screen-w-infinity.patch first')
        with tempfile.TemporaryDirectory(prefix='buffy-screen-w-') as folder:
            target = str(Path(folder) / 'screen-w')
            build = subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                                    '-I', str(header.parent), str(ROOT / 'tests/screen_w.c'),
                                    '-lm', '-o', target], capture_output=True, text=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([target], capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
