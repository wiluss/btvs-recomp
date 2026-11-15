from pathlib import Path
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from tools import outfit_install as install


class OutfitInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source';(self.source/'pak').mkdir(parents=True)
        (self.source/'Default.xbe').write_bytes(b'SYNTHETIC XBE')
        (self.source/'pak/res_null.pak').write_bytes(b'ORIGINAL MENU')
        (self.source/'pak/res_level.pak').write_bytes(b'ORIGINAL LEVEL')
        ((self.source/'pak/res_enemy.pak').resolve()).write_bytes(b'ORIGINAL ENEMY')
        (self.source/'Sound').mkdir();(self.source/'Sound/example.wav').write_bytes(b'ORIGINAL SOUND')
        self.title=self.root/'title.json';self.title.write_text('{}')
        self.cache=self.root/'cache'
        for name,value in [('verify_xbe',None),('compile_menu_pack',b'COMPILED NATIVE MENU')]:
            mock=patch.object(install,name,return_value=value);mock.start();self.addCleanup(mock.stop)
        mock=patch.object(install,'outfit_assets',side_effect=lambda s,t,c:{'choice':c});mock.start();self.addCleanup(mock.stop)
        mock=patch.object(install,'compile_play_pack',side_effect=lambda p,a:(b'OUTFIT '+str(a['choice']).encode()) if p.name=='res_level.pak' else None);mock.start();self.addCleanup(mock.stop)

    def prepare(self,choice=None,live=False):return install.prepare(self.source,self.title,self.cache,choice,live=live)

    def test_disabled_wardrobe_does_not_inspect_or_prepare_resources(self):
        with patch.object(install,'prepare',side_effect=AssertionError('preparation disabled')):
            self.assertEqual(install.environment(Path('/missing-binary'),self.source,self.title,
                                                self.cache,enabled=False),{})

    def test_initial_view_live_selection_restore_and_immutable_source(self):
        original={p:p.read_bytes() for p in self.source.rglob('*') if p.is_file()}
        game,choice=self.prepare();self.assertEqual(choice,0)
        self.assertTrue((game/'Default.xbe').is_symlink())
        self.assertEqual((game/'pak/res_null.pak').read_bytes(),b'COMPILED NATIVE MENU')
        self.assertTrue((game/'pak/res_level.pak').is_symlink())
        self.prepare(5,live=True)
        self.assertEqual(install.saved_choice(self.cache),5)
        self.assertEqual((game/'pak/res_level.pak').read_bytes(),b'OUTFIT 5')
        self.assertEqual((game/'pak/res_enemy.pak').resolve(),(self.source/'pak/res_enemy.pak').resolve())
        self.assertEqual((game/'pak/res_null.pak').read_bytes(),b'COMPILED NATIVE MENU')
        self.prepare(0,live=True)
        self.assertTrue((game/'pak/res_level.pak').is_symlink())
        self.assertTrue(all(p.read_bytes()==data for p,data in original.items()))

    def test_failed_publication_restores_cache_and_preference(self):
        game,_=self.prepare(1)
        before={p.relative_to(self.cache):(os.readlink(p) if p.is_symlink() else p.read_bytes())
                for p in self.cache.rglob('*') if p.is_file() or p.is_symlink() if p.name!='prepare.lock'}
        real=os.replace;calls=0
        def replace(src,dst):
            nonlocal calls
            calls+=1
            if calls==5:raise OSError('synthetic publication failure')
            return real(src,dst)
        with patch.object(install.os,'replace',side_effect=replace),self.assertRaisesRegex(OSError,'publication'):
            self.prepare(2,live=True)
        self.assertEqual(install.saved_choice(self.cache),1)
        for name,value in before.items():
            p=self.cache/name
            self.assertEqual(os.readlink(p) if p.is_symlink() else p.read_bytes(),value)
        self.assertEqual((game/'pak/res_level.pak').read_bytes(),b'OUTFIT 1')

    def test_corrupt_derived_cache_repairs_before_launch_and_live_source_changes_refused(self):
        game,_=self.prepare(3)
        (game/'pak/res_level.pak').write_bytes(b'CORRUPTED')
        self.prepare()
        self.assertEqual((game/'pak/res_level.pak').read_bytes(),b'OUTFIT 3')
        (self.source/'pak/res_level.pak').write_bytes(b'NEW SOURCE')
        with self.assertRaisesRegex(ValueError,'restart'):
            self.prepare(2,live=True)
        self.assertEqual(install.saved_choice(self.cache),3)

    def test_invalid_cache_choices_and_old_binary_do_not_modify_import(self):
        for value in [-1,6,True,'1']:
            with self.assertRaises(ValueError):self.prepare(value)
        with self.assertRaises(ValueError):install.prepare(self.source,self.title,self.source/'nested-cache',0)
        binary=self.root/'old-game';binary.write_bytes(b'old binary without native wardrobe')
        self.assertEqual(install.environment(binary,self.source,self.title,self.cache),{})
        other=self.root/'unowned';other.mkdir();(other/'keep.txt').write_text('keep')
        with self.assertRaisesRegex(ValueError,'unowned'):install.prepare(self.source,self.title,other,0)
        self.assertEqual((other/'keep.txt').read_text(),'keep')

    def test_cache_reuse_malformed_metadata_and_live_corruption(self):
        game,_=self.prepare(2)
        with patch.object(install,'compile_menu_pack',side_effect=AssertionError('Unexpected rebuild')):
            self.prepare(2)
        (game/'pak/res_null.pak').write_bytes(b'BROKEN MENU')
        with self.assertRaisesRegex(ValueError,'restart'):self.prepare(3,live=True)
        self.prepare()
        state=self.cache/'state.json';original=state.read_bytes()
        for bad in [[],{}, {'schema':1,'fingerprint':'x'*64,'choice':2,'packs':{'res_null.pak':{}}}]:
            state.write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError,'state'):self.prepare()
        state.write_bytes(original)
        pref=self.cache/'choice.json';pref.unlink();pref.symlink_to(self.root/'missing')
        with self.assertRaises(ValueError):self.prepare()

    def test_pending_selection_never_reads_or_rewrites_running_pack_payloads(self):
        game,_=self.prepare(1)
        before={p:p.read_bytes() for p in (game/'pak').glob('*.pak')}
        state=(self.cache/'state.json').read_bytes()
        with patch.object(install,'compile_play_pack',side_effect=AssertionError('No live compilation')), \
             patch.object(install,'_valid_cache',side_effect=AssertionError('No live payload scan')):
            install.select_choice(self.source,self.title,self.cache,5)
        self.assertEqual(install.saved_choice(self.cache),5)
        self.assertEqual((self.cache/'state.json').read_bytes(),state)
        self.assertTrue(all(p.read_bytes()==data for p,data in before.items()))
        self.prepare()
        self.assertEqual((game/'pak/res_level.pak').read_bytes(),b'OUTFIT 5')
        install.select_choice(self.source,self.title,self.cache,0)
        self.assertFalse((game/'pak/res_level.pak').is_symlink())
        self.prepare()
        self.assertTrue((game/'pak/res_level.pak').is_symlink())

    def test_pending_selection_failure_preserves_previous_choice(self):
        self.prepare(1)
        with patch.object(install.os,'replace',side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):install.select_choice(self.source,self.title,self.cache,5)
        self.assertEqual(install.saved_choice(self.cache),1)
        (self.title).write_text('{"changed":true}')
        with self.assertRaisesRegex(ValueError,'restart'):install.select_choice(self.source,self.title,self.cache,2)

    def test_pause_recipe_contains_all_outfits_and_choice_changes_reuse_payloads(self):
        with patch.object(install,'compile_live_pack',side_effect=lambda p,a,m:b'ALL FIVE' if p.name=='res_level.pak' else None) as compile_live:
            game,_=install.prepare(self.source,self.title,self.cache,1,pause=True)
            self.assertEqual((game/'pak/res_level.pak').read_bytes(),b'ALL FIVE')
            self.assertEqual(compile_live.call_count,2)
            self.assertEqual(len(compile_live.call_args.args[1]),5)
            previous={p:(p.stat().st_mtime_ns,p.read_bytes()) for p in (game/'pak').glob('*.pak')}
            with patch.object(install,'compile_live_pack',side_effect=AssertionError('Selection must not rebuild')):
                install.select_choice(self.source,self.title,self.cache,5,pause=True)
                self.assertEqual(install.prepare(self.source,self.title,self.cache,pause=True)[1],5)
                install.prepare(self.source,self.title,self.cache,0,pause=True)
            self.assertEqual(install.saved_choice(self.cache),0)
            self.assertTrue(all((p.stat().st_mtime_ns,p.read_bytes())==value for p,value in previous.items()))
            (self.source/'pak/res_level.pak').write_bytes(b'CHANGED SOURCE')
            with self.assertRaisesRegex(ValueError,'restart'):
                install.select_choice(self.source,self.title,self.cache,2,pause=True)

    def test_pause_cache_repair_rollback_and_old_protocol_disabled(self):
        with patch.object(install,'compile_live_pack',return_value=b'ALL FIVE'):
            game,_=install.prepare(self.source,self.title,self.cache,2,pause=True)
            (game/'pak/res_level.pak').write_bytes(b'CORRUPTED')
            before=(self.cache/'state.json').read_bytes()
            real=install.os.replace;calls=0
            def replace(src,dst):
                nonlocal calls
                calls+=1
                if calls==5:raise OSError('synthetic pause publication failure')
                return real(src,dst)
            with patch.object(install.os,'replace',side_effect=replace),self.assertRaises(OSError):
                install.prepare(self.source,self.title,self.cache,5,pause=True)
            self.assertEqual((self.cache/'state.json').read_bytes(),before)
            self.assertEqual(install.saved_choice(self.cache),2)
            install.prepare(self.source,self.title,self.cache,pause=True)
            self.assertEqual((game/'pak/res_level.pak').read_bytes(),b'ALL FIVE')
            binary=self.root/'old-native';binary.write_bytes(b'BTVS_NATIVE_OUTFITS_PROTOCOL_1')
            self.assertEqual(install.environment(binary,self.source,self.title,self.cache),{})


if __name__=='__main__':unittest.main()
