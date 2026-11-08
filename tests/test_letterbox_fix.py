"""Lift the reviewed mask argument setup; check corners and guest state in C."""
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import letterbox_fix as fix

BLOCKS = [
    (0x10851A, '8b484c8b54240c680000803f680000803f53536a015383ec108bc4895804895808'
     '89580cc7000000803fdb44243889542450578d542450d95c2450528d542460c744245c'
     '00002041895c2460895c2464c7442468000020418b0152ff5024'),
    (0x10857D, '8b484c680000803f680000803f53536a015383ec108bc489580489580889580c'
     'c7000000803fdb4424388b44244089442450d95c24588d442458db44243c57c7442464'
     '00002041895c2450d95c2460c7442458000020418b11508d44245450ff5224'),
]


def compiled_check():
    import recomp_driver
    recomp_driver.install()
    from tools.recomp.disasm import Disassembler
    from tools.recomp.lifter import Lifter
    functions = []
    for which, (start, raw) in enumerate(BLOCKS):
        lifter = Lifter()
        lifter.func_start, lifter.func_end = fix.FUNCTION, 0x1085F0
        code = bytes.fromhex(raw)
        insns = Disassembler().disassemble_function(code, start, start+len(code))
        assert insns[-1].address in fix.SITES
        setup = '\n'.join(line for insn in insns[:-1] for line in lifter.lift_instruction(insn))
        patch = '\n'.join(fix.prefix(fix.FUNCTION, insns[-1]))
        functions.append('static void run_%d(int width, int height, float band) {\n' % which
                         + 'setup(width,height,band);\n' + setup
                         + '\ncheck_before(%d, width, height, band);\n' % which
                         + patch + '\ncheck_after(%d, width, height, band);\n}\n' % which)
    source = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
static union { uint32_t u; float f; } ram[4096];
static unsigned char saved[sizeof ram];
#define MEM32(a) ram[(uint32_t)(a)/4].u
#define MEMF(a) ram[(uint32_t)(a)/4].f
#define SMEM32(a) ((int32_t)MEM32(a))
#define PUSH32(sp,v) do { (sp)-=4; MEM32(sp)=(v); } while(0)
#define RECOMP_FP_PC(x) (x)
static double fp[8], saved_fp[8];
static unsigned ft;
#define fp_push(v) do { ft=(ft+7)&7; fp[ft]=(v); } while(0)
#define fp_pop() (ft=(ft+1)&7)
#define fp_top() fp[ft]
static uint32_t esp,eax,ebx,ecx,edx,edi,esi,ebp,_fa,_fb;
static int32_t _fas,_fbs;
static uint32_t before[13];
static void regs(uint32_t r[13]) {
    uint32_t x[]={esp,eax,ebx,ecx,edx,edi,esi,ebp,_fa,_fb,(uint32_t)_fas,(uint32_t)_fbs,ft};
    memcpy(r,x,sizeof x);
}
static void setup(int width,int height,float band) {
    memset(ram,0xA5,sizeof ram); memset(fp,0x3F,sizeof fp); ft=3;
    esp=0x2000; eax=0x1000; ebx=0; edi=7; ecx=11; edx=22; esi=33; ebp=44;
    _fa=55; _fb=66; _fas=-77; _fbs=-88;
    MEM32(eax+0x4C)=0x1100; MEM32(0x1100)=0x1200;
    MEMF(esp+0xC)=band; MEM32(esp+0x10)=width; MEM32(esp+0x14)=height;
    MEMF(esp+0x18)=(float)height-band;
}
static void check_before(int bottom,int width,int height,float band) {
    assert(esp==0x2000-52);
    uint32_t a=MEM32(esp), b=MEM32(esp+4);
    assert(a==0x2000+(bottom?36:48) && b==0x2000+(bottom?48:36));
    assert(MEM32(esp+0x44)==(uint32_t)width && MEM32(esp+0x48)==(uint32_t)height);
    assert(MEMF(a)==0 && MEMF(b)==(float)width);
    assert(MEMF(a+4)==(bottom?(float)height-band:0));
    assert(MEMF(b+4)==(bottom?(float)height:band));
    assert(MEMF(a+8)==10 && MEMF(b+8)==10);
    regs(before); memcpy(saved,ram,sizeof ram); memcpy(saved_fp,fp,sizeof fp);
}
static void check_after(int bottom,int width,int height,float band) {
    uint32_t after[13]; regs(after); assert(!memcmp(before,after,sizeof before));
    assert(!memcmp(saved_fp,fp,sizeof fp));
    uint32_t a=MEM32(esp),b=MEM32(esp+4);
    int active=width==640 && height==480 && band>0 && band<=480;
    assert(MEMF(a)==(active?-1:0));
    assert(MEMF(b)==(active?641:(float)width));
    assert(MEMF(a+4)==(bottom?(float)height-band:active?-1:0));
    assert(MEMF(b+4)==(bottom?(active?481:(float)height):band));
    assert(MEMF(a+8)==10 && MEMF(b+8)==10);
    /* Undo only the three permitted stores, then compare all guest RAM. */
    MEMF(a)=0; MEMF(b)=(float)width;
    if(bottom) MEMF(b+4)=(float)height; else MEMF(a+4)=0;
    assert(!memcmp(saved,ram,sizeof ram));
}
''' + '\n'.join(functions) + r'''
int main(void) {
    float bands[]={0,0.25f,60,120,480};
    for(unsigned i=0;i<sizeof bands/sizeof bands[0];i++) {
        run_0(640,480,bands[i]); run_1(640,480,bands[i]);
    }
    run_0(320,240,30); run_1(320,240,30);
    return 0;
}
'''
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder)/'mask.c'
        path.write_text(source)
        subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', str(path), '-o', str(path.with_suffix(''))], check=True)
        subprocess.run([str(path.with_suffix(''))], check=True)


class LetterboxTests(unittest.TestCase):
    def test_only_reviewed_calls_are_adapted(self):
        for site, code in fix.SITES.items():
            insn = SimpleNamespace(address=site, mnemonic='call', bytes_hex=code)
            self.assertTrue(fix.prefix(fix.FUNCTION, insn))
            self.assertEqual(fix.prefix(fix.FUNCTION+1, insn), [])
            with self.assertRaises(ValueError):
                fix.prefix(fix.FUNCTION, SimpleNamespace(address=site, mnemonic='call', bytes_hex='ff5028'))

    @unittest.skipUnless((ROOT/'.venv/bin/python').exists(), 'toolkit environment absent')
    def test_lifted_arguments_and_only_outer_edges_change(self):
        result = subprocess.run([str(ROOT/'.venv/bin/python'), __file__, '--compiled'],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)


if __name__ == '__main__':
    if sys.argv[1:] == ['--compiled']:
        compiled_check()
    else:
        unittest.main()
