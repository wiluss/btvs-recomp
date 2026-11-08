"""Exercise the runtime placement helper without a GPU or game assets."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT / 'vendor/xboxrecomp/src/kernel'


class HudAnchorTests(unittest.TestCase):
    def test_project_whitelist_and_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as folder:
            exe = Path(folder) / 'selector'
            result = subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                '-fsanitize=address,undefined', '-I', str(KERNEL.parent),
                '-I', str(ROOT/'src/host'), str(ROOT/'tests/hud_selector.c'),
                str(ROOT/'src/host/widescreen.c'), str(KERNEL/'nv2a_hud_anchor.c'),
                '-o', str(exe)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_translation_clipping_and_disabled_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            exe = Path(folder) / 'test'
            result = subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                '-fsanitize=address,undefined', '-I', str(KERNEL),
                str(ROOT/'tests/hud_anchor.c'), str(KERNEL/'nv2a_hud_anchor.c'),
                '-lm', '-o', str(exe)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
