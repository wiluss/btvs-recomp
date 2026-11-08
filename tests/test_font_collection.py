"""Two-font composition and provenance rejection, using synthetic pixels only."""
import copy
import json
from pathlib import Path
import sys
import struct
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import text_pack
import texture_pilot
import texture_profiles
import graphics_settings
import play
from texture_snapshot_lldb import XBE_SHA256


class CollectionTests(unittest.TestCase):
    def fixture(self, root):
        (root/'config').mkdir();(root/'private/textures').mkdir(parents=True)
        extra=root/'config/decorative.json'
        extra.write_text(json.dumps({'xbe_sha256':XBE_SHA256,'texture_hash':'2','scale':8}))
        spec={'recipe':'config/decorative.json','recipe_sha256':text_pack.digest(extra),
              'font':'private/font.ttf','atlas':'private/atlas.png','objects':'private/objects.json'}
        recipe={'xbe_sha256':XBE_SHA256,'texture_hash':'1','scale':8,'additional_fonts':[spec]}
        (root/'config/font-hd.json').write_text(json.dumps(recipe))
        (root/'config/texture-pilot.json').write_text('{"entries":[{},{}]}')
        (root/'config/texture-upscaler.json').write_text('{}')
        def row(key, kind, scale):
            path=root/('%d-%d.png'%(key,scale));Image.new('RGBA',(2*scale,2*scale),(key*10,20,30,255)).save(path)
            return {'hash':key,'width':2,'height':2,'kind':kind,'image':path}
        fonts=root/'private/textures/font-hd.xrtp';texture_pilot.write_pack([row(1,'font',8),row(2,'font',8)],fonts,8)
        for scale in (2,4):
            pack=root/('private/textures/pilot-%dx.xrtp'%scale)
            texture_pilot.write_pack([row(1,'font',scale),row(3,'art',scale)],pack,scale)
            proof={'xbe_sha256':XBE_SHA256,'scale':scale,'entries':2,'pack_sha256':text_pack.digest(pack),
                'selection_sha256':text_pack.digest(root/'config/texture-pilot.json'),
                'upscale':{'upscaler_lock_sha256':text_pack.digest(root/'config/texture-upscaler.json')}}
            pack.with_suffix('.json').write_text(json.dumps(proof))
        return recipe,fonts

    def test_two_fonts_in_all_profiles_preserve_art_and_presentation_scale(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);recipe,fonts=self.fixture(root);text_pack.build_profiles(root,fonts)
            for name,scale in [('original',8),('pilot2x',2),('pilot4x',4)]:
                texture_profiles.verify_profile(name,root,text='hd')
                header,entries=text_pack.read_pack(texture_profiles.pack_path(name,root,text='hd'))
                self.assertEqual(header,{'scale':scale,'text_scale':8})
                self.assertEqual(sum(v[3]&3==1 for v in entries.values()),2)
                if name!='original':
                    _,base=text_pack.read_pack(texture_profiles.pack_path(name,root))
                    self.assertEqual(entries[3],base[3])
                self.assertEqual(entries[1][0:3],(16,16,1))
                self.assertEqual(entries[2][0:3],(16,16,1))

    def test_changed_dependency_refused_before_launch_preferences_or_pack_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);recipe,fonts=self.fixture(root);text_pack.build_profiles(root,fonts)
            settings=root/'settings.json';graphics_settings.save_settings(settings,{'scale':4})
            before=settings.read_bytes();packs={p:p.read_bytes() for p in (root/'private/textures').glob('*.xrtp')}
            (root/'config/decorative.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'SHA differs'):text_pack.build_profiles(root,fonts)
            with patch.object(play,'ROOT',root):
                with self.assertRaisesRegex(SystemExit,'Pack de textures refusé'):
                    play.main(['--settings-file',str(settings),'--textures','pilot2x','--text','hd','--save-settings'])
            self.assertEqual(settings.read_bytes(),before)
            self.assertTrue(all(p.read_bytes()==raw for p,raw in packs.items()))
            self.assertFalse((root/'build').exists())

    def test_foreign_xbe_duplicate_and_escaping_dependencies_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);recipe,_=self.fixture(root)
            for name in ['/tmp/other.json','../other.json','private/other.json','config/../../other.json']:
                bad=copy.deepcopy(recipe);bad['additional_fonts'][0]['recipe']=name
                with self.assertRaises(ValueError):text_pack.additional_recipes(root,bad)
            bad=copy.deepcopy(recipe);bad['additional_fonts']*=2
            with self.assertRaises(ValueError):text_pack.additional_recipes(root,bad)
            bad=copy.deepcopy(recipe);bad['additional_fonts'][0]['font']='private/../outside'
            with self.assertRaises(ValueError):text_pack.additional_recipes(root,bad)
            extra=root/'config/decorative.json';extra.write_text('{"xbe_sha256":"other"}')
            recipe['additional_fonts'][0]['recipe_sha256']=text_pack.digest(extra)
            with self.assertRaisesRegex(ValueError,'XBE differs'):text_pack.additional_recipes(root,recipe)

    def test_wrong_font_identity_with_valid_entry_count_preserves_profiles(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, fonts = self.fixture(root)
            text_pack.build_profiles(root, fonts)
            profiles = {p: p.read_bytes() for p in (root/'private/textures').glob('*text-hd.xrtp')}
            candidate = bytearray(fonts.read_bytes())
            struct.pack_into('<Q', candidate, 64, 4)
            wrong = root/'wrong.xrtp'
            wrong.write_bytes(candidate)
            with self.assertRaisesRegex(ValueError, 'configured collection'):
                text_pack.build_profiles(root, wrong)
            self.assertTrue(all(path.read_bytes() == raw for path, raw in profiles.items()))


if __name__=='__main__':unittest.main()
