"""Compile the real Pause bridge with hostile callees and synthetic guest data."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from tests.test_native_outfits import HEADER, ROOT


class NativePauseTests(unittest.TestCase):
    def test_pause_resume_cancel_render_bounds_and_two_actor_lifetimes(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            (folder/'recomp_funcs.h').write_text(HEADER)
            (folder/'kernel').mkdir()
            (folder/'kernel/kernel.h').write_text('enum {XBOX_GUEST_CPU_KERNEL,XBOX_GUEST_CPU_SPIN,XBOX_GUEST_CPU_CALLBACK,XBOX_GUEST_CPU_HOST};\nint xbox_GuestCpuRelease(int,uint32_t);\nvoid xbox_GuestCpuAcquire(void);\n')
            source=folder/'test.c'
            source.write_text('#include "'+str(ROOT/'src/game/outfits.c')+'"\n'+(ROOT/'tests/native_outfit_pause.c').read_text())
            binary=folder/'test'
            subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(folder),str(source),'-o',str(binary)],check=True)
            env=dict(os.environ,BUFFY_NATIVE_OUTFITS='1',BUFFY_NATIVE_OUTFITS_PAUSE='1',BUFFY_NATIVE_OUTFITS_PREVIEW_ONLY='1',BUFFY_NATIVE_OUTFIT_CHOICE='0')
            subprocess.run([str(binary)],env=env,check=True)
            bad=subprocess.run([str(binary),'bad'],env=env,capture_output=True)
            self.assertEqual(bad.returncode,3)
            self.assertIn(b'stack contract differs',bad.stderr)
