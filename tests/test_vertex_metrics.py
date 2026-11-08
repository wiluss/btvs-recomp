"""Exercise the real optional Metal vertex counter without a GPU or assets."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VertexMetricsTests(unittest.TestCase):
    def test_unique_indices_bounds_and_reset(self):
        header = ROOT / 'vendor/xboxrecomp/src/kernel'
        source = r'''
#include "nv2a_vertex_metrics.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    const uint32_t repeated[] = {3, 0, 3, 1, 0};
    const uint32_t sparse[] = {0, 65535, 0, 63, 64, 65535};
    const uint32_t invalid[] = {0, 8};
    const uint32_t last[] = {65535};
    assert(vertex_unique(NULL, 0, 0) == 0);
    assert(vertex_unique(repeated, 5, 4) == 3);
    assert(vertex_unique(repeated, 5, 4) == 3); /* independent draw */
    assert(vertex_unique(sparse, 6, 65536) == 4);
    assert(vertex_unique(last, 1, 65536) == 1);
    assert(vertex_unique(invalid, 2, 8) == UINT32_MAX);
    assert(vertex_unique(repeated, 5, 65537) == UINT32_MAX);
    assert(vertex_unique(last, 1, 0) == UINT32_MAX);
    assert(vertex_unique(repeated, 5, 4) == 3); /* after invalid/large draw */
    puts("vertex metrics: bounds, duplicates, sparse span and reset passed");
    return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix='buffy-vertex-metrics-') as folder:
            c = Path(folder) / 'test.c'
            exe = Path(folder) / 'test'
            c.write_text(source)
            result = subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra',
                                     '-Werror', '-I', str(header), str(c), '-o', str(exe)],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
