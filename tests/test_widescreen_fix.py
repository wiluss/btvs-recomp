from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from widescreen_fix import FUNCTION, SITE, prefix


def compiled_layout_check():
    import recomp_driver
    recomp_driver.install()
    from tools.recomp.disasm import Disassembler
    from tools.recomp.lifter import Lifter
    # Reviewed corner-copy block, including PUSH ebp before the four vectors.
    code = bytes.fromhex(
        '8b4c24108b54246c8bc1894c24348b4c2468895424388b54240c89442440'
        '8bc1894c24448bca8954244c8b54246c55c74424400000803fc744244c0000803f'
        '89442454c74424580000803f894c245c89542460c74424640000803f'
        'c744242000000000c744242400000000c74424280000000033ffbed8417f008d6c2438')
    insns = Disassembler().disassemble_function(code, 0x2A4B00, SITE + 4)
    lifter = Lifter()
    lifter.func_start, lifter.func_end = FUNCTION, 0x2A4C58
    prelude = '\n'.join(line for insn in insns[:-1] for line in lifter.lift_instruction(insn))
    assert insns[-1].address == SITE
    repair = '\n'.join(prefix(FUNCTION, insns[-1]))
    source = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
static union { uint32_t u; float f; } guest[0x840000 / 4];
static unsigned char expected[sizeof guest];
#define MEM32(a) guest[(a)/4].u
#define MEMF(a) guest[(a)/4].f
#define PUSH32(sp,v) do { (sp)-=4; MEM32(sp)=(v); } while(0)
static uint32_t eax,ecx,edx,esp,ebp,esi,edi;
static uint32_t _fa,_fb;
static int32_t _fas,_fbs;
float buffy_CullAspect(void) { return 854.0f/640.0f; }
int main(void) {
    esp=0x2000; ebp=0x1111;
    MEMF(esp+0x10)=-1; MEMF(esp+0xC)=1;
    MEMF(esp+0x6C)=-0.75f; MEMF(esp+0x68)=0.75f;
    MEM32(0x7F425C)=640; MEM32(0x7F4260)=480;
''' + prelude + r'''
    assert(esp==0x1FFC && MEM32(esp)==0x1111);
    assert(MEMF(esp+0x38)==-1 && MEMF(esp+0x44)==-1);
    assert(MEMF(esp+0x50)==1 && MEMF(esp+0x5C)==1);
    assert(MEMF(esp+0x54)==0.75f); /* Y, never X. */
    const uint32_t regs[]={eax,ecx,edx,esp,ebp,esi,edi,_fa,_fb,(uint32_t)_fas,(uint32_t)_fbs};
    memcpy(expected,guest,sizeof guest);
''' + repair + r'''
    const uint32_t after[]={eax,ecx,edx,esp,ebp,esi,edi,_fa,_fb,(uint32_t)_fas,(uint32_t)_fbs};
    assert(memcmp(regs,after,sizeof regs)==0);
    assert(MEMF(esp+0x50)==854.0f/640.0f);
    assert(MEMF(esp+0x54)==0.75f);
    assert(MEMF(esp+0x14)==-1 && MEMF(esp+0x10)==1);
    MEMF(esp+0x38)=MEMF(esp+0x44)=-1;
    MEMF(esp+0x50)=MEMF(esp+0x5C)=1;
    assert(memcmp(expected,guest,sizeof guest)==0);
    return 0;
}
'''
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder)/'layout.c'
        binary = path.with_suffix('')
        path.write_text(source)
        subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2',
                        str(path), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)


class WidescreenVisibilityTests(unittest.TestCase):
    @unittest.skipUnless((ROOT/'.venv/bin/python').exists(), 'toolkit environment absent')
    def test_real_corner_copies_preserve_the_later_projection(self):
        result = subprocess.run([str(ROOT/'.venv/bin/python'), __file__, '--compiled'],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_only_the_reviewed_corner_setup_is_modified(self):
        instruction = SimpleNamespace(address=SITE, mnemonic='lea', bytes_hex='8d6c2438')
        self.assertEqual(prefix(FUNCTION + 1, instruction), [])
        with self.assertRaises(ValueError):
            prefix(FUNCTION, SimpleNamespace(address=SITE, mnemonic='lea', bytes_hex='8d6c2434'))
        injected = '\n'.join(prefix(FUNCTION, instruction))
        source = '''#include <assert.h>
#include <stdint.h>
#include <string.h>
static union { uint32_t u; float f; } guest[0x840000 / 4];
#define MEM32(a) guest[(a)/4].u
#define MEMF(a) guest[(a)/4].f
static float aspect;
float buffy_CullAspect(void) { return aspect; }
static void corners(uint32_t esp) {
''' + injected + '''
}
static unsigned char saved[sizeof guest];
static void setup(uint32_t esp) {
    memset(guest, 0, sizeof guest);
    MEM32(0x7F425C) = 640;
    MEM32(0x7F4260) = 480;
    /* Original projection bounds after PUSH ebp, used again after the loop. */
    MEMF(esp + 0x14) = -1;
    MEMF(esp + 0x10) = 1;
    MEMF(esp + 0x70) = -0.75f;
    MEMF(esp + 0x6C) = 0.75f;
    MEMF(esp + 0x38) = MEMF(esp + 0x44) = -1;
    MEMF(esp + 0x50) = MEMF(esp + 0x5C) = 1;
    MEMF(esp + 0x3C) = MEMF(esp + 0x60) = -0.75f;
    MEMF(esp + 0x48) = MEMF(esp + 0x54) = 0.75f;
    MEMF(esp + 0x40) = MEMF(esp + 0x4C) = 1;
    MEMF(esp + 0x58) = MEMF(esp + 0x64) = 1;
}
int main(void) {
    uint32_t esp = 0x1000;
    setup(esp);
    memcpy(saved, guest, sizeof guest);
    aspect = 1;
    corners(esp);
    assert(memcmp(saved, guest, sizeof guest) == 0);
    aspect = 854.0f / 640.0f;
    corners(esp);
    assert(MEMF(esp + 0x50) > 1.2f && MEMF(esp + 0x50) < 1.5f);
    assert(MEMF(esp + 0x38) == -MEMF(esp + 0x50));
    assert(MEMF(esp + 0x44) == MEMF(esp + 0x38));
    assert(MEMF(esp + 0x5C) == MEMF(esp + 0x50));
    /* A second Hor+ would change these bounds and compress rendered geometry. */
    assert(MEMF(esp + 0x14) == -1 && MEMF(esp + 0x10) == 1);
    assert(2.0f / (MEMF(esp + 0x10) - MEMF(esp + 0x14)) == 1.0f);
    /* Only the four copied X components may change anywhere in guest memory. */
    MEMF(esp + 0x38) = MEMF(esp + 0x44) = -1;
    MEMF(esp + 0x50) = MEMF(esp + 0x5C) = 1;
    assert(memcmp(saved, guest, sizeof guest) == 0);
    MEM32(0x7F4254) = 20;
    memcpy(saved, guest, sizeof guest);
    corners(esp);
    assert(memcmp(saved, guest, sizeof guest) == 0);
    MEM32(0x7F4254) = 0;
    MEM32(0x7F425C) = 320;
    memcpy(saved, guest, sizeof guest);
    corners(esp);
    assert(memcmp(saved, guest, sizeof guest) == 0);
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'visibility.c'
            binary = path.with_suffix('')
            path.write_text(source)
            subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2',
                            str(path), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['--compiled']:
        compiled_layout_check()
    else:
        unittest.main()
