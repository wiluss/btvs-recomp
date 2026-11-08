"""Synthetic add-on installation: no retail assets, network or user saves."""
import hashlib
import json
from pathlib import Path
import shutil
import stat
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import hd_pack as hd
import loadvars_fix
from texture_profiles import local_asset, pack_path


def fixture(root):
    (root / 'config').mkdir()
    (root / 'private/game').mkdir(parents=True)
    xbe = b'XBEH synthetic HD installer fixture'
    (root / 'private/game/Default.xbe').write_bytes(xbe)
    sha = hashlib.sha256(xbe).hexdigest()
    (root / 'config/title.json').write_text(json.dumps({'xbe_sha256': sha}))
    for name in hd.RECIPES:
        (root / 'config' / name).write_text('{}')
    pixels = bytes(range(16))
    pack = struct.pack('<4sIIIQII', b'XRTP', 2, 1, 2, 32, 8, 0)
    pack += struct.pack('<QIIIIQ', 1, 2, 2, 1, 1, 64) + pixels
    proof = json.dumps({'xbe_sha256': sha, 'entries': 1,
                        'pack_sha256': hashlib.sha256(pack).hexdigest()}).encode()
    data = {name: pack if name.endswith('.xrtp') else proof if name.endswith('.json') else b'synthetic artwork'
            for name in hd.MEMBERS}
    data['README.txt'] = hd.README
    catalog = {'schema': 1, 'id': hd.PACK_ID, 'xbe_sha256': sha,
               'recipes': {name: hd.file_digest(root / 'config' / name) for name in hd.RECIPES},
               'files': {name: {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}
                         for name, value in data.items()}}
    archive = root / hd.ARCHIVE
    write_zip(archive, data, catalog)
    update_archive_pin(root, archive, catalog)
    return archive, catalog, data


def write_zip(archive, data, catalog, extra=None, symbolic=None):
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, value in {**data, hd.MANIFEST: hd.manifest_bytes(catalog)}.items():
            info = zipfile.ZipInfo(name)
            info.external_attr = ((stat.S_IFLNK if name == symbolic else stat.S_IFREG) | 0o644) << 16
            z.writestr(info, value)
        if extra is not None:
            z.writestr(extra, b'unlisted')


def update_archive_pin(root, archive, catalog):
    catalog['archive'] = {'name': hd.ARCHIVE, 'bytes': archive.stat().st_size,
                          'sha256': hd.file_digest(archive)}
    (root / 'config/hd-pack.json').write_text(json.dumps(catalog))


class HDPackTests(unittest.TestCase):
    def test_install_idempotence_resolution_and_existing_user_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive, catalog, data = fixture(root)
            save = root / 'private/profile/precious.ses'; save.parent.mkdir(); save.write_bytes(b'user save')
            prefs = root / 'private/config/graphics.json'; prefs.parent.mkdir(); prefs.write_bytes(b'user preferences')
            with patch.object(loadvars_fix, 'XBE_SHA256', catalog['xbe_sha256']):
                self.assertFalse(hd.install(archive, root)['already_present'])
                self.assertTrue(hd.install(archive, root)['already_present'])
            target = root / 'private/hd' / hd.PACK_ID
            for name, value in data.items(): self.assertEqual((target / name).read_bytes(), value)
            self.assertEqual(pack_path('campaign2x', root), target / 'textures/campaign-ui-hd.xrtp')
            self.assertEqual(pack_path('original', root, 'hd'), target / 'textures/original-text-hd.xrtp')
            legacy = root / 'private/textures/campaign-ui-hd.xrtp'
            legacy.parent.mkdir(); legacy.write_bytes(b'existing custom pack')
            self.assertEqual(pack_path('campaign2x', root), legacy)
            self.assertEqual(save.read_bytes(), b'user save')
            self.assertEqual(prefs.read_bytes(), b'user preferences')
            self.assertFalse(list(target.parent.glob('.install-*')))

    def test_wrong_archive_game_recipe_and_conflicting_install_are_preserved(self):
        for case in ('checksum', 'game', 'recipe', 'existing'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as folder:
                root = Path(folder); archive, catalog, _ = fixture(root)
                target = root / 'private/hd' / hd.PACK_ID
                if case == 'checksum':
                    raw = bytearray(archive.read_bytes()); raw[-1] ^= 1; archive.write_bytes(raw)
                elif case == 'game': (root / 'private/game/Default.xbe').write_bytes(b'wrong game')
                elif case == 'recipe': (root / 'config/hud-hd.json').write_text('changed')
                else: target.mkdir(parents=True); (target / 'precious').write_bytes(b'keep')
                with patch.object(loadvars_fix, 'XBE_SHA256', catalog['xbe_sha256']):
                    with self.assertRaises(ValueError): hd.install(archive, root)
                if case == 'existing': self.assertEqual((target / 'precious').read_bytes(), b'keep')
                else: self.assertFalse(target.exists())

    def test_member_traversal_duplicates_symlinks_and_tampering_are_rejected(self):
        for case in ('../escape', '/absolute', 'textures/CAMPAIGN-UI-HD.XRTP', 'symbolic', 'tampered'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as folder:
                root = Path(folder); archive, catalog, data = fixture(root)
                if case == 'tampered':
                    data['textures/font-hd.xrtp'] = b'x' * len(data['textures/font-hd.xrtp'])
                write_zip(archive, data, catalog,
                          extra=None if case in ('symbolic', 'tampered') else case,
                          symbolic='launcher/logo.png' if case == 'symbolic' else None)
                # Re-pin only the archive, to exercise structural/member checks too.
                update_archive_pin(root, archive, catalog)
                with patch.object(loadvars_fix, 'XBE_SHA256', catalog['xbe_sha256']):
                    with self.assertRaises(ValueError): hd.install(archive, root)
                self.assertFalse((root / 'private/hd' / hd.PACK_ID).exists())
                self.assertFalse((root / 'escape').exists())
                self.assertFalse(list((root / 'private/hd').glob('.install-*')))

    def test_interruption_publication_race_and_destination_symlink(self):
        for case in ('interrupt', 'race', 'symlink', 'space'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as folder:
                root = Path(folder); archive, catalog, _ = fixture(root)
                parent = root / 'private/hd'; target = parent / hd.PACK_ID
                if case == 'interrupt':
                    fault = patch.object(hd, 'stream_member', side_effect=KeyboardInterrupt)
                    error = KeyboardInterrupt
                elif case == 'race':
                    real_publish = hd.publish_directory
                    def race(source, dest):
                        dest.mkdir(); (dest / 'precious').write_bytes(b'other installer')
                        real_publish(source, dest)
                    fault = patch.object(hd, 'publish_directory', side_effect=race)
                    error = FileExistsError
                elif case == 'space':
                    fault = patch.object(hd.shutil, 'disk_usage', return_value=shutil._ntuple_diskusage(1, 1, 0))
                    error = ValueError
                else:
                    parent.symlink_to(root / 'private', target_is_directory=True)
                    fault = patch.object(hd, 'PACK_ID', hd.PACK_ID)
                    error = ValueError
                with patch.object(loadvars_fix, 'XBE_SHA256', catalog['xbe_sha256']), fault:
                    with self.assertRaises(error): hd.install(archive, root)
                if case == 'race': self.assertEqual((target / 'precious').read_bytes(), b'other installer')
                else: self.assertFalse(target.exists())
                if case != 'symlink': self.assertFalse(list(parent.glob('.install-*')))

    def test_modified_installed_addon_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); archive, catalog, _ = fixture(root)
            with patch.object(loadvars_fix, 'XBE_SHA256', catalog['xbe_sha256']):
                hd.install(archive, root)
                file = root / 'private/hd' / hd.PACK_ID / 'launcher/logo.png'
                file.write_bytes(b'local modification')
                with self.assertRaises(ValueError): hd.install(archive, root)
                self.assertEqual(file.read_bytes(), b'local modification')
