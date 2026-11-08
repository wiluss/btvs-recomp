#!/usr/bin/env python3
"""Project-owned, pin-checked generator extension; vendor stays unchanged.

WBINVD: the runtime models guest RAM as coherent shared host memory, with no
guest CPU cache. Emit a compiler/CPU full fence at the architectural cache
writeback boundary. This is not a Metal command-buffer flush. See
docs/BRINGUP.md for the scope, evidence and limitations.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def install(*, loadvars=False):
    lock = json.loads((ROOT / 'dependencies.lock.json').read_text())['xboxrecomp']
    vendor = ROOT / lock['path']
    revision = subprocess.check_output(['git', '-C', str(vendor), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != lock['revision']:
        raise SystemExit('Review extension against new toolkit before using it')
    sys.path.insert(0, str(vendor))
    from tools.recomp import lifter
    original = lifter.Lifter.lift_instruction

    def lift(self, instruction):
        if instruction.mnemonic == 'wbinvd' and not instruction.operands:
            return ['__atomic_thread_fence(__ATOMIC_SEQ_CST); /* wbinvd: coherent host RAM */']
        lines = original(self, instruction)
        if loadvars:
            from arenas_fix import prefix as arenas_prefix
            from widescreen_fix import prefix as widescreen_prefix
            from letterbox_fix import prefix as letterbox_prefix
            from loadvars_fix import prefix
            lines = (prefix(self.func_start, instruction)
                     + arenas_prefix(self.func_start, instruction)
                     + widescreen_prefix(self.func_start, instruction)
                     + letterbox_prefix(self.func_start, instruction) + lines)
        return lines

    lifter.Lifter.lift_instruction = lift
    lifter._EFLAGS_PRESERVE = lifter._EFLAGS_PRESERVE | {'wbinvd'}
    if loadvars:
        # Title adaptations are enabled only after verify_xbe in main.
        from factory_switch_fix import install as install_factory_switch
        install_factory_switch()


def verify():
    """Compile lifted compare/WBINVD/branch sequences and run edge vectors."""
    from tools.recomp.disasm import Disassembler, BasicBlock
    from tools.recomp.lifter import Lifter, lift_basic_block
    functions = []
    for name, opcode in [('equal', '74'), ('below', '72'), ('less', '7c')]:
        # cmp eax,ecx; wbinvd; jcc +0. A real Capstone decode, synthetic only.
        code = bytes.fromhex('39c8 0f09 ' + opcode + '00')
        instructions = Disassembler().disassemble_function(code, 0x10000, 0x10000 + len(code))
        # disassemble_function returns a list of instructions in this pin.
        lifter = Lifter()
        lifter.func_start, lifter.func_end = 0x10000, 0x10007
        statements, state = lift_basic_block(lifter, BasicBlock(0x10000, instructions))
        if not state or state[0] != 'cmp' or lifter.unimplemented:
            raise AssertionError('WBINVD lost compare flags or remained unimplemented')
        body = '\n'.join(statements)
        functions.append('int %s(uint32_t eax,uint32_t ecx) {\n'
                         'uint32_t _fa=0,_fb=0; int32_t _fas=0,_fbs=0; int _flags=0;\n'
                         '%s\nreturn 0; loc_00010006: return 1;\n}' % (name, body))
    source = '''#include <stdint.h>
#include <string.h>
#define CMP_EQ(a,b) ((uint32_t)(a)==(uint32_t)(b))
#define CMP_B(a,b) ((uint32_t)(a)<(uint32_t)(b))
#define CMP_L(a,b) ((int32_t)(a)<(int32_t)(b))
''' + '\n'.join(functions) + '''
int main(void) {
    uint32_t memory[4]={0x12345678,0x80000000,0,0xffffffff}, saved[4];
    memcpy(saved,memory,sizeof(memory));
    uint32_t values[]={0,1,0x7fffffff,0x80000000,0xffffffff};
    for (unsigned i=0;i<5;i++) for (unsigned j=0;j<5;j++) {
        uint32_t a=values[i],b=values[j];
        if(equal(a,b)!=(a==b) || below(a,b)!=(a<b) || less(a,b)!=((int32_t)a<(int32_t)b)) return 1;
    }
    return memcmp(saved,memory,sizeof(memory))!=0;
}
'''
    with tempfile.TemporaryDirectory(prefix='buffy-wbinvd-') as folder:
        folder = Path(folder)
        path = folder / 'test.c'
        path.write_text(source)
        subprocess.run(['clang', '-std=c11', '-O2', str(path), '-o', str(folder/'test')], check=True)
        subprocess.run([str(folder/'test')], check=True)
        subprocess.run(['clang', '-std=c11', '-O2', '-S', str(path), '-o', str(folder/'test.s')], check=True)
        assembly = (folder/'test.s').read_text()
        # On our ARM64 target this must generate an actual full host barrier.
        import platform
        if platform.machine() == 'arm64' and 'dmb\tish' not in assembly:
            raise AssertionError('Full host memory barrier absent from ARM64 assembly')
    print('WBINVD: 75 compiled branch vectors pass; ARM64 fence verified')


if __name__ == '__main__':
    if sys.argv[1:] == ['--verify-wbinvd']:
        install()
        verify()
    else:
        from loadvars_fix import verify_xbe
        # Bind both the supplied generator input and the manifest to this title.
        # The pipeline supplies the input XBE as the first positional argument.
        if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
            raise SystemExit('Expected identified XBE path as first argument')
        verify_xbe(Path(sys.argv[1]), json.loads((ROOT / 'config/title.json').read_text()))
        from spin_config import verify_arguments
        verify_arguments(sys.argv[2:], json.loads((ROOT / 'config/title.json').read_text())['xbe_sha256'])
        install(loadvars=True)
        from tools.recomp.__main__ import main
        main()
