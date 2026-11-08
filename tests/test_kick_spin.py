"""Execute the pinned lowering of Buffy's measured read-only KickOff wait."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from spin_config import verify, verify_arguments


def compiled_check():
    import re
    sys.path.insert(0,str(ROOT/'vendor/xboxrecomp'))
    from tools.recomp import config
    from tools.recomp.translator import FunctionTranslator
    from tools.recomp.spin_waits import SpinWaitConfig,SpinWaitReport
    site=0x596D00
    image=bytes.fromhex('f780100410000000010075f4c3')
    config._install([config.Section('.text',site,len(image),0,len(image),True)],entry_point=site,kernel_thunk_addr=site,origin='synthetic-kick-wait')
    db={site:{'start':hex(site),'end':site+len(image),'_addr':site,'size':len(image)}}
    spin=SpinWaitConfig.load(ROOT/'config/spin-waits.json')
    assert spin.sites=={site} and not spin.auto and spin.sleep=={site:'kick_event'}
    t=FunctionTranslator(image,db);report=SpinWaitReport(spin);t.spin_waits=report
    code=t.translate_function(site,db[site]);assert not report.finish()
    assert code.count('RECOMP_SPIN_WAIT_KICK')==1
    assert 'RECOMP_SPIN_WAIT_KICK(0x00596D00u); goto loc_00596D00;' in code
    # Inspect final lazy comparison state without changing the branch under test.
    code=code.replace('esp += 4; return;', 'observed_fa=_fa; esp += 4; return;')
    hdr=(ROOT/'vendor/xboxrecomp/templates/runtime/recomp_types.h').read_text()
    macro=re.search(r'#define RECOMP_SPIN_WAIT_KICK\(va\)[^\n]*\\\n[^\n]*\n',hdr).group(0)
    fence=re.search(r'#if defined\(_MSC_VER\)\n#  if defined\(_M_ARM64\)\n#    define RECOMP_SEQ_CST_FENCE\(\)[^\n]*\n(?:#[^\n]*\n)*?#endif\n',hdr).group(0)
    source='''#include <stdint.h>
#include <assert.h>
uint32_t eax,ebx,ecx,edx,esi,edi,esp,g_ebp,g_seh_ebp,word,observed_fa;
unsigned waits,reads;
volatile int g_xbox_spin_sleep=1,g_xbox_irq_pending=0,g_xbox_guest_cpu_waiters=0,g_xbox_kick_armed=1;
uint32_t *get_word(uint32_t a) {assert(a==0x120410);reads++;return &word;}
#define MEM32(a) (*get_word(a))
#define CMP_NE(a,b) ((a)!=(b))
void xbox_SpinWaitKick(uint32_t va) {assert(va==0x596d00);waits++;word &= ~0x10000u;}
'''+fence+macro+code+'''
int main(void) {
for(unsigned pending=0;pending<2;pending++) {
 eax=0x20000;ebx=11;ecx=22;edx=33;esi=44;edi=55;esp=0x30000;g_ebp=66;g_seh_ebp=77;
 word=pending?0xa5a50001:0xa5a40001;waits=reads=0;
 sub_00596D00();
 assert(waits==pending && reads==1+pending && word==0xa5a40001);
 assert(eax==0x20000 && ebx==11 && ecx==22 && edx==33 && esi==44 && edi==55);
 assert(esp==0x30004 && g_ebp==66 && g_seh_ebp==77 && observed_fa==0);
}
return 0;
}
'''
    with tempfile.TemporaryDirectory() as folder:
        p=Path(folder);(p/'test.c').write_text(source)
        subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-variable','-Wno-unused-label','-O2',str(p/'test.c'),'-o',str(p/'test')],check=True)
        subprocess.run([str(p/'test')],check=True)
    print('KickOff: compiled first-test/ack/branch/GPR/stack regression passes')


class KickSpinTests(unittest.TestCase):
    def test_manifest_binding(self):
        sha=json.loads((ROOT/'config/title.json').read_text())['xbe_sha256']
        verify(ROOT/'config/spin-waits.json',sha)
        with self.assertRaises(ValueError):verify(ROOT/'config/spin-waits.json','0'*64)
        for args in [['--spin-waits',str(ROOT/'config/spin-waits.json')],
                     ['--spin-waits='+str(ROOT/'config/spin-waits.json')]]:
            verify_arguments(args,sha)
            with self.assertRaises(ValueError):verify_arguments(args,'0'*64)
        with self.assertRaises(ValueError):verify_arguments(['--spin-waits'],sha)

    @unittest.skipUnless((ROOT/'.venv/bin/python').exists(),'toolkit environment absent')
    def test_compiled_kick_wait(self):
        r=subprocess.run([str(ROOT/'.venv/bin/python'),__file__,'--compiled'],capture_output=True,text=True,timeout=30)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)


if __name__=='__main__':
    if sys.argv[1:]==['--compiled']:compiled_check()
    else:unittest.main()
