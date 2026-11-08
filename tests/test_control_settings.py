from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from control_settings import DEFAULT_KEYS, SUPPORTED_KEYS, validate_controls, control_environment
import play


def default():
    return dict(version=1, keyboard=list(DEFAULT_KEYS), pad=list(range(16)), sticks=[0,1])


class ControlSettingsTests(unittest.TestCase):
    def test_strict_profile_and_menu_recovery(self):
        self.assertEqual(validate_controls(default()),default())
        cases=[]
        for field,value in [('version',True),('keyboard',[1]),('pad',[0]*16),('sticks',[0,99])]:
            p=default();p[field]=value;cases.append(p)
        p=default();p['keyboard'][1]=p['keyboard'][0];cases.append(p)
        p=default();p['keyboard'][0]=0;p['pad'][0]=-1;cases.append(p)
        p=default();p['extra']=0;cases.append(p)
        for p in cases:
            with self.subTest(profile=p),self.assertRaises(ValueError):validate_controls(p)

    def test_owned_environment_and_missing_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.assertEqual(control_environment(root),{})
            p=root/'private/config/controls.json';p.parent.mkdir(parents=True);p.write_text(json.dumps(default()))
            result=control_environment(root)['BUFFY_INPUT_PROFILE'].split(',')
            self.assertEqual(len(result),43);self.assertEqual(list(map(int,result[1:25])),DEFAULT_KEYS)
            with patch.object(play,'ROOT',root):
                env=play.build_environment({},'/hdd',0,{'BUFFY_INPUT_PROFILE':'poison'})
                self.assertNotEqual(env['BUFFY_INPUT_PROFILE'],'poison')
            p.write_text('{"version":1,"version":1}')
            with self.assertRaises(ValueError):control_environment(root)

    def test_runtime_real_keyboard_and_pad_recomposition(self):
        with tempfile.TemporaryDirectory() as folder:
            exe=Path(folder)/'controls';src=ROOT/'vendor/xboxrecomp/src'
            command=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                     '-ffunction-sections','-fdata-sections','-Wl,-dead_strip',
                     '-I',str(ROOT/'src/host'),'-I',str(ROOT/'vendor/xboxrecomp/include'),
                     '-I',str(src),'-I',str(src/'input'),'-I',str(src/'platform'),'-I',str(src/'kernel'),
                     str(ROOT/'tests/controls_remap.c'),str(ROOT/'src/host/controls.c'),
                     str(src/'input/keyboard.c'),str(src/'input/input_names.c'),str(src/'input/input_map.c'),'-lm','-o',str(exe)]
            result=subprocess.run(command,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            profiles=[default()]
            for key in range(256):
                p=default();p['keyboard']=[0]*24;p['keyboard'][0]=key;profiles.append(p)
            encoded=[]
            expected=[]
            for p in profiles:
                encoded.append(','.join(map(str,[p['version']]+p['keyboard']+p['pad']+p['sticks'])))
                try:validate_controls(p);expected.append('1')
                except ValueError:expected.append('0')
            encoded += ['', '1', encoded[0]+',0', ' '+encoded[0], encoded[0].replace('87','9999999999999999999999',1)]
            expected += ['0']*5
            result=subprocess.run([str(exe),'validate'],input='\n'.join(encoded)+'\n',capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout.splitlines(),expected)
