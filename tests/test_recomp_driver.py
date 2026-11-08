from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GeneratorExtensionTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / '.venv/bin/python').exists(), 'isolated toolkit environment absent')
    def test_wbinvd_preserves_live_comparisons_in_compiled_code(self):
        result = subprocess.run([str(ROOT / '.venv/bin/python'), str(ROOT / 'tools/recomp_driver.py'),
                                 '--verify-wbinvd'], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
