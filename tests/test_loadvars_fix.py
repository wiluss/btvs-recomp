"""Compile the actual lifted call and caller branch against a synthetic File_Read.

No game assets. Tests the caller repair, not the filesystem or full parser.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import loadvars_fix as fix


def compiled_check():
    import recomp_driver
    recomp_driver.install(loadvars=True)
    from tools.recomp.disasm import Disassembler, BasicBlock
    from tools.recomp.lifter import Lifter, lift_basic_block
    lifter = Lifter()
    lifter.func_start, lifter.func_end = fix.FUNCTION, 0x14231
    call = Disassembler().disassemble_function(bytes.fromhex(fix.CALL_BYTES), fix.SITE, fix.SITE + 5)[0]
    body = '\n'.join(lifter.lift_instruction(call))
    # mov eax,[esp+24]; sub eax,18; add esp,10; test eax,eax;
    # mov [esp+14],eax; jg parse. Real caller's branch shape.
    tail = bytes.fromhex('8b44242483e81883c41085c0894424147f0a')
    insns = Disassembler().disassemble_function(tail, 0x140B3, 0x140C5)
    branch = '\n'.join(lift_basic_block(lifter, BasicBlock(0x140B3, insns))[0])
    source = r'''
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
static uint32_t ram[1024], expect[1024];
static uint32_t esp,eax,ebx,ecx,edx,esi,edi,ebp;
static uint32_t _fa,_fb; static int32_t _fas,_fbs; static int _flags;
static int success;
#define MEM32(a) ram[(uint32_t)(a)/4]
#define PUSH32(sp,v) do { (sp)-=4; MEM32(sp)=(v); } while(0)
#define CMP_G(a,b) ((int32_t)(a)>(int32_t)(b))
static void sub_002B46D0(void) {
    assert(esp==0x1fc && MEM32(esp)==0x140b3);
    assert(MEM32(esp+4)==0x800 && MEM32(esp+8)==0x228);
    assert(MEM32(esp+12)==0x224 && MEM32(esp+16)==0);
    assert(eax==11 && ebx==22 && ecx==33 && edx==44 && esi==55 && edi==66 && ebp==77);
    assert(_fa==88 && _fb==99 && _fas==-12 && _fbs==-13 && _flags==123);
    /* Only the two pointees and original CALL's return slot may differ. */
    expect[0x228/4]=0; expect[0x224/4]=0; expect[0x1fc/4]=0x140b3;
    assert(memcmp(ram,expect,sizeof ram)==0);
    if(success) { MEM32(MEM32(esp+8))=0x900; MEM32(MEM32(esp+12))=42; }
    eax=success; esp+=4; /* cdecl return: arguments remain */
}
#define RECOMP_ABI_CALL(va,fn) fn()
static void run(int ok, uint32_t poison) {
    for(unsigned i=0;i<1024;i++) ram[i]=0x5a5a0000+i;
    esp=0x200; eax=11; ebx=22; ecx=33; edx=44; esi=55; edi=66; ebp=77;
    _fa=88; _fb=99; _fas=-12; _fbs=-13; _flags=123; success=ok;
    MEM32(0x200)=0x800; MEM32(0x204)=0x228; MEM32(0x208)=0x224; MEM32(0x20c)=0;
    MEM32(0x228)=poison; MEM32(0x224)=0xffffffff;
    memcpy(expect,ram,sizeof ram);
''' + body + r'''
    assert(esp==0x200);
    assert(MEM32(0x204)==0x228 && MEM32(0x208)==0x224);
    assert(ebx==22 && ecx==33 && edx==44 && esi==55 && edi==66 && ebp==77);
    assert(_fa==88 && _fb==99 && _fas==-12 && _fbs==-13 && _flags==123);
    assert(MEM32(0x224)==(ok?42:0) && MEM32(0x228)==(ok?0x900:0));
''' + branch + r'''
    /* Original failure arm loads [esp+18] for free: it must now be NULL. */
    assert(!ok && esp==0x210 && MEM32(esp+0x18)==0);
    return;
loc_000140CF:
    assert(ok && esp==0x210 && MEM32(esp+0x18)==0x900 && eax==18);
}
int main(void) { run(0,0x0057f5b2); run(0,0xdeadbeef); run(1,0x0057f5b2); run(1,0); puts("LoadVariables: 4 compiled poisoned-output cases pass"); }
'''
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder)
        (path/'check.c').write_text(source)
        subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-O2',str(path/'check.c'),'-o',str(path/'check')], check=True)
        subprocess.run([str(path/'check')], check=True)
        # The same poisoned case must fail without the adaptation.
        (path/'check.c').write_text(source.replace('MEM32(MEM32(esp + 4)) = 0;', '').replace('MEM32(MEM32(esp + 8)) = 0;', ''))
        subprocess.run(['clang','-std=c11','-O2',str(path/'check.c'),'-o',str(path/'unfixed')], check=True)
        result = subprocess.run([str(path/'unfixed')], capture_output=True)
        assert result.returncode != 0, 'Regression did not detect missing repair'


class LoadVariablesTests(unittest.TestCase):
    def test_scope_and_instruction_guard(self):
        insn = SimpleNamespace(address=fix.SITE, mnemonic='call', call_target=fix.TARGET, bytes_hex=fix.CALL_BYTES)
        self.assertEqual(fix.prefix(fix.FUNCTION+1, insn), [])
        insn.address += 1
        self.assertEqual(fix.prefix(fix.FUNCTION, insn), [])
        insn.address = fix.SITE
        insn.call_target += 1
        with self.assertRaises(ValueError):
            fix.prefix(fix.FUNCTION, insn)
        insn.call_target = fix.TARGET
        insn.bytes_hex = 'e800000000'
        with self.assertRaises(ValueError):
            fix.prefix(fix.FUNCTION, insn)

    def test_hash_guard_rejects_unidentified_input(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'synthetic.xbe'
            path.write_bytes(b'not the identified XBE')
            with self.assertRaises(ValueError):
                fix.verify_xbe(path, {'xbe_sha256':fix.XBE_SHA256})
            with self.assertRaises(ValueError):
                fix.verify_xbe(path, {'xbe_sha256':'0'*64})

    @unittest.skipUnless((ROOT/'.venv/bin/python').exists(), 'toolkit environment absent')
    def test_compiled_absent_and_successful_read(self):
        result = subprocess.run([str(ROOT/'.venv/bin/python'), __file__, '--compiled'], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)


if __name__ == '__main__':
    if sys.argv[1:] == ['--compiled']:
        compiled_check()
    else:
        unittest.main()
