"""A skin replaces artwork and preserves the base pack's other payloads."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from text_pack import read_pack
from texture_mod import build
from texture_profiles import verify_local_pack


class TextureModTests(unittest.TestCase):
    def test_skin_composes_and_rejects_bad_size_before_replacing_output(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            inventory = folder / 'inventory.json'
            inventory.write_text(json.dumps({'xbe_sha256':'local','entries':[
                {'hash':1,'width':4,'height':4}, {'hash':2,'width':4,'height':4}]}))
            recipe = folder / 'recipe.json'
            Image.new('RGBA',(8,8),(128,0,0,255)).save(folder/'base.png')
            Image.new('RGBA',(8,8),(0,128,0,255)).save(folder/'skin.png')
            base, output = folder/'base.xrtp', folder/'mod.xrtp'
            recipe.write_text(json.dumps({'scale':2,'entries':[
                {'hash':'1','png':'base.png'}, {'hash':'2','png':'base.png'}]}))
            self.assertEqual(build(recipe, inventory, base, 'local'), 2)
            original = base.read_bytes()
            recipe.write_text(json.dumps({'scale':2,'entries':[{'hash':'1','png':'skin.png'}]}))
            self.assertEqual(build(recipe, inventory, output, 'local', base), 2)
            self.assertEqual(verify_local_pack(output, 'local'), 2)
            base_h, before = read_pack(base)
            mod_h, after = read_pack(output)
            self.assertEqual(base_h, mod_h)
            self.assertEqual(before[2], after[2])
            self.assertEqual(after[1][-1][:4], bytes([0,128,0,255]))
            self.assertEqual(base.read_bytes(), original)
            candidate = output.read_bytes()
            Image.new('RGBA',(8,4)).save(folder/'skin.png')
            with self.assertRaisesRegex(ValueError,'Wrong replacement size'):
                build(recipe, inventory, output, 'local', base)
            self.assertEqual(output.read_bytes(), candidate)
