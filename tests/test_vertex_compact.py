"""Check remapped shader inputs against the unmodified primitive/decoder path."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT / 'vendor/xboxrecomp/src/kernel'


class VertexCompactTests(unittest.TestCase):
    def test_topology_formats_and_atomic_fallback(self):
        common = (KERNEL / 'nv2a_backend_common.c').read_text()
        a = common.index('uint32_t nv2a_prim_to_list(')
        primitive = common[a:common.index('\n}', a) + 2]
        source = (ROOT / 'tests/vertex_compact.c').read_text().replace('/* PRIMITIVE_EXPANDER */', primitive)
        with tempfile.TemporaryDirectory(prefix='buffy-vertex-compact-') as folder:
            c, exe = Path(folder) / 'test.c', Path(folder) / 'test'
            c.write_text(source)
            result = subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                                     '-I', str(KERNEL), str(c), '-lm', '-o', str(exe)],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
