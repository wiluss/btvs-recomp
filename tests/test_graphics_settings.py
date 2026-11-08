"""Persistent preferences and the real launch environment/bootstrap contract."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import subprocess
import hashlib
import struct
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import graphics_settings as graphics
import play
import prepare_host
from texture_profiles import verify_local_pack


class GraphicsTests(unittest.TestCase):
    def test_rejects_bad_types_ranges_and_unknown_features(self):
        invalid=[[],None,{'scale':True},{'scale':2.0},{'scale':'2'},{'scale':0},{'scale':5},
                 {'fps':1},{'fullscreen':'false'},{'vsync':None},{'filter':[]},
                 {'filter':'anisotropic'},{'widescreen':True},{'aspect':'21:9'},
                 {'aspect':True},{'hud':'stretch'},{'hud':None}]
        for data in invalid:
            with self.subTest(data=data),self.assertRaises(ValueError):
                graphics.validate_settings(data)
        data={'scale':3};result=graphics.validate_settings(data)
        self.assertEqual(data,{'scale':3})
        self.assertEqual(result['scale'],3)
        self.assertEqual(result['fps'],True)

    def test_round_trip_and_cli_override_missing_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'private/graphics.json'
            args=play.parse_args(['--scale','3','--no-fps','--fullscreen','--no-vsync'])
            settings=play.selected_settings(args,path)
            graphics.save_settings(path,settings)
            self.assertEqual(graphics.load_settings(path),settings)
            self.assertEqual(play.selected_settings(play.parse_args([]),path),settings)
            path.write_text('{"scale":1}')
            self.assertTrue(play.selected_settings(play.parse_args(['--fullscreen']),path)['fullscreen'])

    def test_render_dimensions_follow_the_pinned_padding(self):
        for scale in range(1,5):
            self.assertEqual(graphics.render_dimensions({'scale':scale}), (640*scale,480*scale))
            self.assertEqual(graphics.render_dimensions({'scale':scale,'aspect':'16:9'}), (854*scale,480*scale))

    def test_uhd_uses_a_4k_surface_and_supersampling(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'graphics.json'
            args = play.parse_args(['--resolution', '4k'])
            settings = play.selected_settings(args, path)
            env = graphics.settings_environment(settings)
            self.assertEqual(graphics.render_dimensions(settings), (3840, 2160))
            self.assertEqual(env['RECOMP_RENDER_SCALE'], '5')
            self.assertEqual(env['RECOMP_DISPLAY_ASPECT'], '16:9')
            self.assertEqual(env['RECOMP_PRESENT_SURFACE'], 'uhd')
            graphics.save_settings(path, settings)
            scale4 = play.selected_settings(play.parse_args(['--scale', '4', '--aspect', '4:3']), path)
            self.assertNotIn('RECOMP_PRESENT_SURFACE', graphics.settings_environment(scale4))
            self.assertEqual(graphics.render_dimensions(scale4), (2560, 1920))
            safe = play.selected_settings(play.parse_args(['--resolution','4k','--aspect','4:3']), path)
            self.assertEqual(graphics.settings_environment(safe)['RECOMP_DISPLAY_ASPECT'], '4:3')
            self.assertEqual(graphics.render_dimensions(safe), (3840, 2160))

    def test_menu_defaults_to_arenas_and_keeps_the_mission_aspect(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'graphics.json'
            args = play.parse_args(['menu', '--resolution', '4k'])
            settings = play.selected_settings(args, path)
            env = play.build_environment(settings, '/copy/hdd', 60, {}, mode='menu')
            self.assertEqual(env['BUFFY_UNLOCK_ARENAS'], '1')
            self.assertEqual(env['RECOMP_DISPLAY_ASPECT'], '4:3')
            self.assertEqual(env['RECOMP_PRESENT_SURFACE'], 'uhd')
            self.assertNotIn('RECOMP_PAD_LIVE', env)
            graphics.save_settings(path, settings)
            mission = play.build_environment(graphics.load_settings(path), '/copy/hdd', 60, {})
            self.assertEqual(mission['RECOMP_DISPLAY_ASPECT'], '16:9')
            self.assertEqual(mission['BUFFY_UNLOCK_ARENAS'], '0')
            args = play.parse_args(['menu', '--no-unlock-arenas'])
            disabled = play.selected_settings(args, path)
            self.assertEqual(play.build_environment(disabled, '/copy/hdd', 60, {}, mode='menu')
                             ['BUFFY_UNLOCK_ARENAS'], '0')

    def test_campaign_art_and_text_can_be_enabled_independently(self):
        for name, text, filename, fonts in [
                ('original', 'original', 'none', 'off'),
                ('original', 'hd', 'original-text-hd.xrtp', 'on'),
                ('campaign2x', 'original', 'campaign-ui-hd.xrtp', 'off'),
                ('campaign2x', 'hd', 'campaign-ui-hd.xrtp', 'on')]:
            env = graphics.settings_environment({'textures':name, 'text':text})
            self.assertEqual(Path(env['RECOMP_TEXTURES_PACK']).name, filename)
            self.assertEqual(env['RECOMP_TEXTURES_FONT'], fonts)
            self.assertEqual(env['RECOMP_TEXTURES_TEXT'], fonts)

    def test_local_pack_requires_valid_mips_and_matching_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'skin.xrtp'
            header = struct.pack('<4sIIIQII', b'XRTP', 2, 1, 2, 32, 0, 0)
            for flags, extent in [(0, 84), (16, 48)]:
                entry = struct.pack('<QIIIIQ', 1, 4, 4, 3, flags, 64)
                for data, valid in [(bytes(extent), True), (bytes(extent - 1), False)]:
                    raw = header + entry + data
                    path.write_bytes(raw)
                    path.with_suffix('.json').write_text(json.dumps({
                        'entries': 1, 'xbe_sha256': 'edition',
                        'pack_sha256': hashlib.sha256(raw).hexdigest()}))
                    if valid:
                        self.assertEqual(verify_local_pack(path, 'edition'), 1)
                        with self.assertRaisesRegex(ValueError, 'different XBE'):
                            verify_local_pack(path, 'other')
                        path.write_bytes(raw[:-1] + b'x')
                        with self.assertRaisesRegex(ValueError, 'was changed'):
                            verify_local_pack(path, 'edition')
                    else:
                        with self.assertRaisesRegex(ValueError, 'extent'):
                            verify_local_pack(path, 'edition')

    def test_legacy_profile_and_widescreen_overrides(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'graphics.json'
            path.write_text('{"scale":4,"fps":true,"fullscreen":false,"vsync":true,"filter":"linear"}')
            before=path.read_bytes()
            self.assertEqual(graphics.load_settings(path)['aspect'],'4:3')
            args=play.parse_args(['--aspect','16:9','--hud','edges'])
            settings=play.selected_settings(args,path)
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(settings['scale'],4)
            env=play.build_environment(settings,'/copy/hdd',90,{'BUFFY_HUD':'inherited'})
            self.assertEqual(env['RECOMP_DISPLAY_ASPECT'],'16:9')
            self.assertEqual(env['RECOMP_DISPLAY_MOVIE'],'black')
            self.assertEqual(env['BUFFY_HUD'],'edges')
            graphics.save_settings(path,settings)
            self.assertEqual(graphics.load_settings(path),settings)
            self.assertEqual(play.selected_settings(play.parse_args(['--aspect','4:3']),path)['scale'],4)

    def test_invalid_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'graphics.json';path.write_text('{broken json')
            original=path.read_bytes()
            with self.assertRaises(ValueError):graphics.load_settings(path)
            self.assertEqual(path.read_bytes(),original)
            with self.assertRaises(ValueError):graphics.save_settings(path,{'scale':False})
            self.assertEqual(path.read_bytes(),original)

    def test_atomic_replacement_failure_keeps_original_and_removes_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'graphics.json';graphics.save_settings(path,{'scale':1})
            before=path.read_bytes()
            with patch.object(graphics.os,'replace',side_effect=OSError('synthetic replacement failure')):
                with self.assertRaises(OSError):graphics.save_settings(path,{'scale':3})
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(list(Path(folder).iterdir()),[path])

    def test_environment_preserves_timing_and_isolates_input_and_config(self):
        inherited={'PATH':'/bin','RECOMP_CONFIG':'unrelated.toml','RECOMP_PRESENT_PACING':'sleep',
                   'RECOMP_PAD_SCRIPT':'bad','RECOMP_MOUSE':'1','RECOMP_RENDER_SCALE':'4','RECOMP_DISPLAY_ASPECT':'21:9'}
        before=dict(inherited)
        env=play.build_environment({'scale':2,'fps':False},'/copy/hdd',90,inherited)
        self.assertEqual(inherited,before)
        self.assertEqual(env['PATH'],'/bin')
        self.assertNotIn('RECOMP_PAD_SCRIPT',env)
        for key,value in {'RECOMP_PRESENT_PACING':'spin','RECOMP_CONFIG':'none',
                          'RECOMP_DISPLAY_ASPECT':'4:3','RECOMP_RENDER_SCALE':'2','RECOMP_MOUSE':'0',
                          'RECOMP_KEYBOARD':'1','RECOMP_OVERLAY_STATS':'0','RECOMP_HDD_DIR':'/copy/hdd'}.items():
            self.assertEqual(env[key],value)

    def fixture(self, root):
        files={'config/title.json':{'xbe_sha256':'synthetic','title_id':'45410012'},
               'artifacts/pipeline-recomp.json':{'returncode':0,'xbe_sha256':'synthetic',
                    'letterbox_fix_sha256':hashlib.sha256((ROOT/'tools/letterbox_fix.py').read_bytes()).hexdigest()}}
        for name,data in files.items():
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data))
        (root/'build/game').mkdir(parents=True)
        (root/'build/game/buffy-macos').write_bytes(b'synthetic native placeholder, not executed')
        (root/'build/game/CMakeCache.txt').write_text('XBOXRECOMP_ENHANCE:BOOL=ON\n')
        (root/'build/diagnostic-hdd-baseline-20261028').mkdir()

    def test_dry_check_and_show_never_write_or_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.fixture(root)
            source=root/'Previous session'
            (source/'Cache').mkdir(parents=True)
            (source/'Partition0.img').touch()
            (source/'UDATA/45410012').mkdir(parents=True)
            before={str(f.relative_to(root)):f.read_bytes() for f in root.rglob('*') if f.is_file()}
            with patch.object(play,'ROOT',root),patch.object(play,'verify_xbe'),contextlib.redirect_stdout(io.StringIO()) as output:
                play.main(['menu','--check','--save-settings','--scale','3','--no-unlock-arenas'])
                play.main(['menu','--check','--hdd',str(source),'--no-unlock-arenas'])
                play.main(['--show-settings'])
            after={str(f.relative_to(root)):f.read_bytes() for f in root.rglob('*') if f.is_file()}
            self.assertEqual(before,after)
            self.assertIn('"launched": false',output.getvalue())
            self.assertIn(json.dumps(str(source.resolve())),output.getvalue())
            self.assertFalse((root/'private').exists())

    def test_bad_launch_page_refused_before_hdd_or_settings_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.fixture(root)
            (root/'build/relaunch-capture-hdd').mkdir()
            page=root/'artifacts/relaunch/launch-page.bin';page.parent.mkdir();page.write_bytes(b'not the verified page')
            with patch.object(play,'ROOT',root),patch.object(play,'verify_xbe'):
                with self.assertRaisesRegex(SystemExit,'Capture de lancement différente'):
                    play.main(['mission','--check'])
            self.assertFalse((root/'private').exists())
            self.assertFalse((root/'logs').exists())

    def test_spin_default_precedes_cache_and_keeps_explicit_choice(self):
        original = 'void entry1(void) {\n    recomp_env_init();\n}\nvoid entry2(void) {\n    recomp_env_init();\n}\n'
        with self.assertRaises(ValueError):prepare_host.graphics_defaults('changed template')
        source = r"""
#define _POSIX_C_SOURCE 200809L
#include <stdlib.h>
#include <string.h>
#include <assert.h>
static const char *expected; static int calls;
static void recomp_env_init(void) {
    const char *v=getenv("RECOMP_PRESENT_PACING");
    assert(v && !strcmp(v,expected));calls++;
}
""" + prepare_host.graphics_defaults(original) + r"""
int main(void) {
    setenv("RECOMP_CONFIG","none",1);
    unsetenv("RECOMP_PRESENT_PACING");expected="spin";entry1();
    setenv("RECOMP_PRESENT_PACING","sleep",1);expected="sleep";entry2();
    assert(calls==2);return 0;
}
"""
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);(path/'check.c').write_text(source)
            subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror',str(path/'check.c'),'-o',str(path/'check')],check=True,capture_output=True)
            subprocess.run([str(path/'check')],check=True,capture_output=True)

    def test_bootstrap_records_pid_before_guest_runs_and_detaches(self):
        text=play.mission_script(Path('/page file.bin'),Path('/pid file'),Path('/out file'),Path('/err file'))
        self.assertLess(text.index('write_text(str(lldb'),text.index('\ncontinue\n'))
        self.assertLess(text.index(play.PAGE_SHA256),text.index('WriteMemory('))
        self.assertIn('assert allocated and addr',text)
        self.assertLess(text.index('WriteMemory('),text.index('process detach'))
        self.assertTrue(text.endswith('process detach --keep-stopped false\nquit\n'))
        self.assertNotIn('continue',text[text.index('WriteMemory('):])


if __name__=='__main__':unittest.main()
