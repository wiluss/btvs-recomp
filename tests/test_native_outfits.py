"""Compile the real native bridge against an adversarial guest ABI fixture."""
from pathlib import Path
import os
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from tools.native_outfits_fix import SITES, prefix

ROOT = Path(__file__).resolve().parents[1]

HEADER = r'''
#include <stdint.h>
#include <string.h>
#include <assert.h>
typedef union {uint8_t u[16];} RecompXmm;
typedef union {uint8_t u[8];} RecompMmx;
static uint8_t memory[0x4000000];
#define XBOX_PTR(p) ((uintptr_t)(memory+(uint32_t)(p)))
#define MEM8(p) (*(uint8_t*)(memory+(uint32_t)(p)))
#define MEM16(p) (*(uint16_t*)(memory+(uint32_t)(p)))
#define MEM32(p) (*(uint32_t*)(memory+(uint32_t)(p)))
#define PUSH32(p,v) ((p)-=4,MEM32(p)=(uint32_t)(v))
static _Thread_local uint32_t g_eax,g_ecx,g_edx,g_esp,g_ebx,g_esi,g_edi,g_ebp;
static _Thread_local uint32_t g_seh_ebp,g_fs_base,g_eflags,g_mxcsr;
static _Thread_local int g_df,g_fp_top,g_fp_cmp;
static _Thread_local uint16_t g_fp_control_word,g_fp_cc;
static _Thread_local double g_fp_stack[8];
static _Thread_local RecompXmm g_xmm0,g_xmm1,g_xmm2,g_xmm3,g_xmm4,g_xmm5,g_xmm6,g_xmm7;
static _Thread_local RecompMmx g_mm0,g_mm1,g_mm2,g_mm3,g_mm4,g_mm5,g_mm6,g_mm7;
void sub_002BC1A0(void);void sub_002BC1A8(void);void sub_0021B650(void);
void sub_0021B9D0(void);void sub_0021B740(void);void sub_001EBE00(void);
void sub_00218B70(void);void sub_00218C20(void);void sub_00222470(void);void sub_001EE130(void);void sub_001EA460(void);void sub_001ECB90(void);
void sub_001273F0(void);
void sub_0012DD20(void);
void sub_00285920(void);
void sub_00285D20(void);
void sub_002859A0(void);
void sub_00286150(void);
void sub_00285C10(void);
void sub_0001F7B0(void);
void sub_0001F890(void);
void sub_00093FB0(void);
void sub_000943E0(void);
void sub_0003BBE0(void);
void sub_002B7160(void);
void sub_00043D60(void);
void sub_002ABB50(void);
void sub_00223760(void);
void (*recomp_lookup(uint32_t))(void);

'''

HARNESS = r'''
void sub_001273F0(void){assert(!"Unexpected live native call");}
void sub_0012DD20(void){assert(!"Unexpected live native call");}
void sub_00285920(void){assert(!"Unexpected live native call");}
void sub_00285D20(void){assert(!"Unexpected live native call");}
void sub_002859A0(void){assert(!"Unexpected live native call");}
void sub_00286150(void){assert(!"Unexpected live native call");}
void sub_00285C10(void){assert(!"Unexpected live native call");}
void sub_0001F7B0(void){assert(!"Unexpected live native call");}
void sub_0001F890(void){assert(!"Unexpected live native call");}
void sub_00093FB0(void){assert(!"Unexpected live native call");}
void sub_000943E0(void){assert(!"Unexpected live native call");}
void sub_0003BBE0(void){assert(!"Unexpected live native call");}
void sub_002B7160(void){assert(!"Unexpected live native call");}
void sub_00043D60(void){assert(!"Unexpected live native call");}
void sub_002ABB50(void){assert(!"Unexpected live native call");}
void sub_00223760(void){assert(!"Unexpected live native call");}
void (*recomp_lookup(uint32_t p))(void){(void)p;return 0;}
static int cpu_released;
int xbox_GuestCpuRelease(int kind,uint32_t where){assert(kind==XBOX_GUEST_CPU_HOST&&where==0x2226b0);cpu_released++;return 1;}
void xbox_GuestCpuAcquire(void){assert(cpu_released==1);cpu_released--;}
static uint32_t allocated=0x200000, freed, destroyed, loaded, current_menu, commands;
static void finish(unsigned popped, uint32_t result) {
    uint32_t next=g_esp+popped;
#define SPOIL(t,n) n=(t)21;
    SCALARS(SPOIL)
#undef SPOIL
    memset(g_fp_stack,0xA7,sizeof g_fp_stack);
#define SPOILV(i) memset(&g_xmm##i,0xB9,sizeof g_xmm##i);memset(&g_mm##i,0xCC,sizeof g_mm##i);
    SPOILV(0) SPOILV(1) SPOILV(2) SPOILV(3) SPOILV(4) SPOILV(5) SPOILV(6) SPOILV(7)
    g_esp=next;g_eax=result;
}
void sub_002BC1A0(void){assert(MEM32(g_esp+4)==0x324||MEM32(g_esp+4)==INFO_ALLOCATION);uint32_t p=allocated;allocated+=0x1000;finish(4,p);}
void sub_002BC1A8(void){assert(MEM32(g_esp+4)>=0x200000);freed++;finish(4,0);}
void sub_0021B650(void){MEM32(g_ecx)=CHARACTER_VTABLE;finish(4,g_ecx);}
void sub_0021B9D0(void){assert(MEM32(g_ecx+0x274)==preview_info);assert(MEM32(g_ecx+0x30c)==loaded);loaded++;finish(4,1);}
void sub_0021B740(void){assert(MEM32(g_ecx)==CHARACTER_VTABLE);assert(MEM32(g_esp+4)==0);destroyed++;finish(8,0);}
void sub_001EBE00(void){assert(g_ecx==owner);assert(MEM32(g_esp+8)==1);current_menu=MEM32(g_esp+4);finish(12,0);}
void sub_00218B70(void){assert(MEM32(g_ecx+0x1c)==16);finish(4,0);}
void sub_00218C20(void){finish(8,0);}
void sub_00222470(void){assert(MEM32(g_ecx+0x1c)==1);memory[g_ecx+0x48]=1;finish(4,0);}
void sub_001EE130(void){MEM32(g_ecx+0x24)=MEM32(g_esp+4);finish(8,0);}
void sub_001EA460(void){uint32_t id=MEM32(g_esp+4),node=MEM32(g_ecx+0x30);while(node&&MEM32(MEM32(node)+0x1c)!=id)node=MEM32(node+4);assert(node);MEM32(g_ecx+0x3c)=node;finish(8,0);}
void sub_001ECB90(void){commands++;finish(8,0);}
static void bad_call(void){finish(8,0);}
static void check_cpu(const CpuState *expected) {CpuState after;memset(&after,0,sizeof after);save_cpu(&after);assert(!memcmp(expected,&after,sizeof after));}
int main(int argc,char **argv){
    if(argc>1&&!strcmp(argv[1],"prepare")){prepare_choice(2);assert(!cpu_released);return 0;}
    g_esp=0x1F0000;g_eax=0x1337;g_ecx=0x9876;g_fp_stack[3]=-1.25;g_fp_top=7;g_fp_control_word=0x37F;g_fp_cc=0x4100;g_eflags=0x246;g_df=1;g_mxcsr=0x1F80;
    memset(&g_xmm6,0xB4,sizeof g_xmm6);memset(&g_mm7,0xC3,sizeof g_mm7);
    CpuState expected;memset(&expected,0,sizeof expected);save_cpu(&expected);
    if(argc>1&&!strcmp(argv[1],"bad")){invoke(bad_call,0,0,0,0,0);return 99;}
    uint32_t manager=0x100000, original=0x110000, mainmenu=0x120000, menu=0x130000;
    MEM32(MANAGER_GLOBAL)=manager;MEM32(manager)=MANAGER_VTABLE;MEM32(manager+0x74)=original;MEM32(original)=CHARACTER_VTABLE;
    buffy_OutfitsConstruct(manager);check_cpu(&expected);
    if(!getenv("BUFFY_NATIVE_OUTFITS")||strcmp(getenv("BUFFY_NATIVE_OUTFITS"),"1")){assert(!owner&&!loaded);return 0;}
    assert(loaded==5&&models[0]==original&&MEM32(manager+0x74)==original);
    MEM32(0x170000)=MANAGER_VTABLE;MEM32(0x170000+0x74)=0;
    buffy_OutfitsConstruct(0x170000);assert(loaded==5);check_cpu(&expected);
    MEM32(mainmenu)=MENU_VTABLE;MEM32(mainmenu+0x1c)=1;
    MEM32(menu)=MENU_VTABLE;MEM32(menu+0x1c)=16;
    uint32_t mainbutton=0x160000;MEM32(mainbutton+4)=mainmenu;MEM32(mainbutton+0x1c)=0x200;
    for(unsigned i=0;i<6;i++){uint32_t node=0x140000+i*16,button=0x150000+i*128;MEM32(node)=button;MEM32(node+4)=i==5?0:node+16;MEM32(button+4)=menu;MEM32(button+0x1c)=ids[i];MEM32(button+0x24)=3;}
    MEM32(menu+0x30)=0x140000;
    assert(buffy_OutfitsMessage(mainmenu,mainbutton,5));assert(current_menu==16);check_cpu(&expected);
    assert(buffy_OutfitsLoad(menu));assert(MEM32(menu+0x1c)==16);check_cpu(&expected);
    for(unsigned i=0;i<6;i++)assert(!MEM32(0x150000+i*128+0x24));
    for(unsigned i=0;i<6;i++){MEM32(menu+0x3c)=0x140000+i*16;buffy_OutfitsUpdate(menu);assert(MEM32(manager+0x74)==models[i]);check_cpu(&expected);}
    assert(buffy_OutfitsMessage(menu,0x150000+5*128,5));assert(choice==5&&current_menu==1);check_cpu(&expected);
    assert(buffy_OutfitsCommand(menu,0x29));assert(current_menu==1&&MEM32(manager+0x74)==models[5]);check_cpu(&expected);
    assert(buffy_OutfitsCommand(menu,0x25));assert(commands==1);check_cpu(&expected);
    assert(!buffy_OutfitsMessage(menu,1,5));assert(!buffy_OutfitsMessage(mainmenu,mainbutton,2));
    assert(!buffy_OutfitsLoad(mainmenu));assert(!buffy_OutfitsCommand(mainmenu,0x29));check_cpu(&expected);
    buffy_OutfitsDestroy(manager);assert(!owner&&freed==6&&destroyed==5&&MEM32(manager+0x74)==original);check_cpu(&expected);
    buffy_OutfitsDestroy(manager);assert(freed==6);check_cpu(&expected);
    return 0;
}
'''


class NativeOutfitTests(unittest.TestCase):
    def test_reviewed_generator_sites_reject_different_bytes_or_instructions(self):
        for (function, address), site in SITES.items():
            instruction = SimpleNamespace(address=address,mnemonic=site[0],bytes_hex=site[1])
            self.assertTrue(prefix(function,instruction))
            self.assertEqual(prefix(function+1,instruction),[])
            with self.assertRaises(ValueError):
                prefix(function,SimpleNamespace(address=address,mnemonic='wrong',bytes_hex=site[1]))
            with self.assertRaises(ValueError):
                prefix(function,SimpleNamespace(address=address,mnemonic=site[0],bytes_hex='90'))

    def test_real_bridge_preserves_guest_cpu_and_releases_only_owned_models(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            (folder/'recomp_funcs.h').write_text(HEADER)
            (folder/'kernel').mkdir()
            (folder/'kernel/kernel.h').write_text('enum {XBOX_GUEST_CPU_KERNEL,XBOX_GUEST_CPU_SPIN,XBOX_GUEST_CPU_CALLBACK,XBOX_GUEST_CPU_HOST};\nint xbox_GuestCpuRelease(int,uint32_t);\nvoid xbox_GuestCpuAcquire(void);\n')
            source=folder/'test.c'
            source.write_text('#include "'+str(ROOT/'src/game/outfits.c')+'"\n'+HARNESS)
            binary=folder/'test'
            subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(folder),str(source),'-o',str(binary)],check=True)
            for enabled in ['0','1']:
                subprocess.run([str(binary)],env=dict(os.environ,BUFFY_NATIVE_OUTFITS=enabled,BUFFY_NATIVE_OUTFITS_PREVIEW_ONLY="1",BUFFY_NATIVE_OUTFIT_CHOICE="0",BUFFY_NATIVE_OUTFITS_PAUSE="0"),check=True)
            result=subprocess.run([str(binary),'bad'],capture_output=True)
            self.assertEqual(result.returncode,3)
            self.assertIn(b'stack contract differs',result.stderr)
            script=folder/'prepare.py'
            script.write_text('import sys\nassert sys.argv[1:]==["--source","source path","--title","title path","--cache","cache path","--choice","2","--select-only"]\n')
            import sys
            env=dict(os.environ,BUFFY_NATIVE_OUTFITS_PREVIEW_ONLY='0',BUFFY_OUTFIT_PYTHON=sys.executable,
                     BUFFY_OUTFIT_PREPARER=str(script),BUFFY_OUTFIT_SOURCE='source path',
                     BUFFY_OUTFIT_TITLE='title path',BUFFY_OUTFIT_CACHE='cache path')
            subprocess.run([str(binary),'prepare'],env=env,check=True)
            script.write_text('raise SystemExit(7)\n')
            result=subprocess.run([str(binary),'prepare'],env=env,capture_output=True)
            self.assertEqual(result.returncode,3)
            self.assertIn(b'Outfit selection could not be saved',result.stderr)


if __name__=='__main__':unittest.main()
