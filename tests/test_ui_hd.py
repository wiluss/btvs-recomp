"""Check explicit HUD processing policy without weights or game data."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from ui_hd import processing_plan
from texture_snapshot_lldb import XBE_SHA256
from texture_profiles import verify_profile


class HudProcessingTests(unittest.TestCase):
    def setUp(self):
        self.recipe = dict(xbe_sha256=XBE_SHA256, scale=4,
                           hashes=['00000000000000AB', '00000000000000CD'],
                           ai_hashes=['00000000000000ab'], mask_hashes=['00000000000000CD'])
        self.rows = [dict(hash=0xAB, width=64, height=16), dict(hash=0xCD, width=8, height=64)]

    def test_rgb_art_and_utility_masks_have_distinct_methods(self):
        before = copy.deepcopy(self.rows)
        plan = processing_plan(self.recipe, self.rows)
        self.assertEqual([e['method'] for e in plan['entries']], ['ai', 'lanczos'])
        self.assertEqual([e['kind'] for e in plan['entries']], ['art', 'art'])
        self.assertEqual([e['hash'] for e in plan['entries']], self.recipe['hashes'])
        self.assertEqual(self.rows, before)

    def test_invalid_or_incomplete_routing_is_rejected(self):
        cases = [dict(ai_hashes=['00000000000000AB', '00000000000000ab']),
                 dict(ai_hashes=['00000000000000CD']),
                 dict(mask_hashes=[]), dict(ai_hashes=['00000000000000EF']),
                 dict(scale=2), dict(scale=4.0), dict(xbe_sha256='different'),
                 dict(hashes=['00000000000000AB', 'not-a-key'])]
        for update in cases:
            with self.subTest(update=update), self.assertRaises(ValueError):
                processing_plan(dict(self.recipe, **update), self.rows)
        for rows in [self.rows[:1], self.rows+[self.rows[0]], [self.rows[0], self.rows[0]]]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                processing_plan(self.recipe, rows)

    def test_campaign_rejects_pack_for_an_older_hud_recipe(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            recipe = root/'config/hud-hd.json'
            recipe.parent.mkdir()
            recipe.write_text('{"scale":4}\n')
            sidecar = root/'private/textures/campaign-ui-hd.json'
            sidecar.parent.mkdir(parents=True)
            sidecar.write_text(json.dumps({'hud_recipe_sha256':'old HUD'}))
            with patch('texture_profiles.verify_local_pack'):
                with self.assertRaisesRegex(ValueError, 'current HD HUD'):
                    verify_profile('campaign2x', root, text='original')
                sidecar.write_text(json.dumps({'hud_recipe_sha256':hashlib.sha256(recipe.read_bytes()).hexdigest()}))
                verify_profile('campaign2x', root, text='original')
