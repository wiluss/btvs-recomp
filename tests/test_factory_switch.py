"""Synthetic large-switch regression; uses the real toolkit and compiled dispatch."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def verify():
    import struct
    sys.path.insert(0, str(ROOT/'tools'))
    sys.path.insert(0, str(ROOT/'vendor/xboxrecomp'))
    import recomp_driver
    from tools.recomp import config
    from tools.recomp.lifter import Lifter
    from tools.recomp.translator import FunctionTranslator
    from tools.recomp.disasm import Disassembler
    original_read = Lifter._read_jump_table
    original_local = FunctionTranslator._read_local_jump_table
    recomp_driver.install(loadvars=True)
    base, table, other = 0x27C200, 0x283100, 0x284100
    config._SECTIONS = [config.Section('.text', base, 0x9000, 0, 0x9000, True)]
    data = bytearray(b'\xcc'*0x9000)
    targets = [base+0x100+4*i for i in range(535)]
    for start, count in [(table,535),(other,300)]:
        for i in range(count):
            struct.pack_into('<I',data,start-base+4*i,targets[i])
    l = Lifter(); l.xbe_data=bytes(data); l.func_start=base; l.func_end=table
    t = FunctionTranslator.__new__(FunctionTranslator); t.xbe_data=bytes(data)
    assert len(original_read(l,table))==256
    assert len(original_local(t,table,base,table))==256
    assert l._read_jump_table(table)==targets
    assert len(l._read_jump_table(other))==256
    assert t._read_local_jump_table(table,base,table)==targets
    assert len(t._read_local_jump_table(other,base,table))==256
    # The instruction indexes an actual in-function table; no call/ret.
    code=bytes.fromhex('ff248500312800')
    insn=Disassembler().disassemble_function(code,base+0x16,base+0x1d)[0]
    body='\n'.join(l.lift_instruction(insn))
    assert '535 entries' in body
    labels='\n'.join('loc_%08X: result=%du; return;'%(va,i) for i,va in enumerate(targets))
    source='''#include <stdint.h>
#include <stdlib.h>
uint32_t words[535],g_seh_ebp,result;
#define MEM32(a) words[((uint32_t)(a)-0x283100u)/4]
#define RECOMP_ITAIL(a) abort()
void dispatch(uint32_t eax) { uint32_t ebp=123;
'''+body+'\n'+labels+'''
}
int main(void) { for(unsigned i=0;i<535;i++) words[i]=0x27c300+4*i;
for(unsigned i=0;i<535;i++) { dispatch(i); if(result!=i) return 1; }
return g_seh_ebp!=0; }
'''
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder); (path/'test.c').write_text(source)
        subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-O2',str(path/'test.c'),'-o',str(path/'test')],check=True)
        subprocess.run([str(path/'test')],check=True)
    # Invalid arm and truncated input stop scanning; never invent further arms.
    struct.pack_into('<I',data,table-base+4*400,0)
    l.xbe_data=bytes(data)
    assert len(l._analyze_switch_table([insn.operands[0]]))==400
    t.xbe_data=bytes(data)
    assert len(t._read_local_jump_table(table,base,table))==400
    l.xbe_data=bytes(data[:table-base+4*300])
    assert len(l._read_jump_table(table))==300
    print('535 compiled switch arms pass; other-table cap and invalid/truncated bounds pass')


class FactorySwitchTests(unittest.TestCase):
    @unittest.skipUnless((ROOT/'.venv/bin/python').exists(), 'toolkit environment absent')
    def test_large_factory_switch(self):
        result=subprocess.run([str(ROOT/'.venv/bin/python'),__file__,'--verify'],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__':
    if sys.argv[1:]==['--verify']: verify()
    else: unittest.main()
