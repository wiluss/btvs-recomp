"""Compile the actual DMA resolvers with synthetic conflicting page owners."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'vendor/xboxrecomp/src'


def function(source, signature):
    start = source.index(signature)
    return source[start:source.index('\n}', start) + 2]


class ApuImageTests(unittest.TestCase):
    def test_sample_dma_keeps_image_and_descriptor_owners_distinct(self):
        core = (SRC / 'apu/apu_core.c').read_text()
        layout = (SRC / 'kernel/xbox_memory_layout.c').read_text()
        pieces = [function(layout, sig) for sig in (
            'void xbox_PhysNoteRamName(',
            'const volatile uint8_t *xbox_PhysImageNameMap(',
            'const volatile uint8_t *xbox_PhysRamNameMap(')]
        pieces += [function(core, sig) for sig in (
            'static inline uint32_t apu_mapped_ram(',
            'uint8_t *mcpx_apu_phys(', 'const char *mcpx_apu_phys_class(',
            'uint8_t *mcpx_apu_sample_phys(',
            'const char *mcpx_apu_sample_phys_class(')]
        fixture = (ROOT / 'tests/apu_image.c').read_text()
        source = fixture.replace('/* PRODUCTION_FUNCTIONS */', '\n'.join(pieces))
        with tempfile.TemporaryDirectory(prefix='buffy-apu-image-') as folder:
            c = Path(folder) / 'test.c'
            exe = Path(folder) / 'test'
            c.write_text(source)
            build = subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra',
                                    '-Werror', str(c), '-o', str(exe)],
                                   capture_output=True, text=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
