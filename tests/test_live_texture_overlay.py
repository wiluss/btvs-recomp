"""Run the standalone runtime diff under ASan/UBSan with synthetic texels."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from test_mod_library import pack

class LiveTextureOverlayTests(unittest.TestCase):
    def test_runtime_overlay_transaction_and_cpu_payload_lifetimes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'runtime';(source/'src/kernel').mkdir(parents=True)
            vendor=ROOT/'vendor/xboxrecomp'
            for name in ['src/kernel/nv2a_tex_pack.c','src/kernel/nv2a_tex_pack.h']:
                raw=subprocess.check_output(['git','-C',str(vendor),'show','HEAD:'+name])
                (source/name).write_bytes(raw)
            patch=ROOT/'patches/xboxrecomp/0007-live-texture-overlay.patch'
            subprocess.run(['git','apply',str(patch)],cwd=source,check=True,capture_output=True)
            # The only other header is an unmodified generic runtime helper.
            import shutil
            (source/'src/d3d').mkdir();shutil.copy(vendor/'src/d3d/d3d8_swizzle.h',source/'src/d3d')
            base=pack(root,'base',[(1,4,4,(255,0,0,255)),(2,4,4,(0,255,0,255))])
            skin=pack(root,'skin',[(1,4,4,(0,0,255,255))])
            conflict=pack(root,'conflict',[(1,8,4,(0,0,0,255))])
            bad=root/'bad.xrtp';bad.write_bytes(b'bad')
            exe=root/'probe'
            command=['clang','-std=c11','-D_GNU_SOURCE','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                     '-I'+str(source/'src/kernel'),str(ROOT/'tests/live_texture_overlay.c'),str(source/'src/kernel/nv2a_tex_pack.c'),'-o',str(exe)]
            compiled=subprocess.run(command,capture_output=True,text=True,timeout=30)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            result=subprocess.run([str(exe),str(base),str(skin),str(bad),str(conflict)],capture_output=True,text=True,timeout=30,
                                  env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
