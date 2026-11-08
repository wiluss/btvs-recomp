from pathlib import Path
import io
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import setup_game as setup
from fresh_hdd import partition_table, create_hdd


class SetupGameTests(unittest.TestCase):
    def test_blank_partition_table_matches_the_compiled_generic_runtime(self):
        source=(ROOT/'vendor/xboxrecomp/src/kernel/kernel_path.c').read_text()
        start=source.index('static void put_le32(')
        end=source.index('/*\n * A partition device,',start)
        code='#include <stdint.h>\n#include <string.h>\n#include <stdio.h>\n#define XBOX_PART_IN_USE 0x80000000u\n'+source[start:end]
        code+='int main(void){unsigned char b[512];xbox_build_partition_table(b);return fwrite(b,1,512,stdout)==512?0:1;}\n'
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);c=root/'table.c';c.write_text(code);exe=root/'table'
            result=subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run([str(exe)],capture_output=True,check=True)
            self.assertEqual(partition_table(),result.stdout)
            hdd=root/'hdd';create_hdd(hdd,0x45410012)
            with self.assertRaises(FileExistsError):create_hdd(hdd,0x45410012)

    def test_unexpected_runtime_changes_are_never_overwritten(self):
        lock=json.loads((ROOT/'dependencies.lock.json').read_text())['xboxrecomp']
        with patch.object(setup.subprocess,'check_output',side_effect=[lock['revision'],' M changed.c\n']), \
             patch.object(setup.subprocess,'run',return_value=Mock(returncode=1)), \
             patch.object(setup,'run') as mutation:
            with self.assertRaisesRegex(ValueError,'modifiés'):setup.ensure_runtime(ROOT,io.StringIO())
            mutation.assert_not_called()

    def test_failed_build_and_interruption_propagate_without_leaving_a_child(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with (root/'log').open('w') as log:
                with self.assertRaises(ValueError):setup.run([sys.executable,'-c','raise SystemExit(7)'],root,log)
            child=Mock(pid=987654)
            child.wait.side_effect=[KeyboardInterrupt,None]
            child.poll.return_value=None
            with patch.object(setup.subprocess,'Popen',return_value=child),patch.object(setup.os,'killpg') as stop:
                with self.assertRaises(KeyboardInterrupt):setup.run(['fake-build'],root,io.StringIO())
                stop.assert_called_once_with(987654,setup.signal.SIGTERM)

    def test_platform_preflight_refuses_an_unsupported_host(self):
        with patch.object(setup.platform,'machine',return_value='x86_64'):
            with self.assertRaisesRegex(ValueError,'Apple Silicon'):setup.preflight(ROOT)
