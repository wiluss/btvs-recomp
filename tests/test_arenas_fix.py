"""Verify the injected write preserves existing bits and the following read."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from arenas_fix import FUNCTION, SITE, prefix


class ArenasFixTests(unittest.TestCase):
    def test_only_the_reviewed_read_enables_the_four_bits(self):
        instruction = SimpleNamespace(address=SITE, mnemonic='mov', bytes_hex='8b4038')
        self.assertEqual(prefix(FUNCTION + 1, instruction), [])
        with self.assertRaises(ValueError):
            prefix(FUNCTION, SimpleNamespace(address=SITE, mnemonic='mov', bytes_hex='8b4034'))
        injected = '\n'.join(prefix(FUNCTION, instruction))
        source = '''#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
static uint32_t guest[64];
#define MEM32(address) guest[(address)/4]
int main(int argc, char **argv)
{
    uint32_t eax = 0x20;
    (void)argv;
    MEM32(eax + 0x34) = 0x55667788u;
    MEM32(eax + 0x38) = 0xABCD0012u;
''' + injected + '''
    eax = MEM32(eax + 0x38);
    assert(eax == (argc > 1 ? 0xABCD001Fu : 0xABCD0012u));
    assert(MEM32(0x20 + 0x34) == 0x55667788u);
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'probe.c'
            binary = path.with_suffix('')
            path.write_text(source)
            subprocess.run(['clang','-std=c11','-Wall','-Werror',str(path),
                            str(ROOT/'src/host/arenas.c'),'-o',str(binary)], check=True)
            subprocess.run([str(binary)], env=dict(os.environ, BUFFY_UNLOCK_ARENAS='0'), check=True)
            subprocess.run([str(binary), 'enabled'], env=dict(os.environ, BUFFY_UNLOCK_ARENAS='1'), check=True)
