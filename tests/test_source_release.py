from pathlib import Path
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import source_release as release


class SourceReleaseTests(unittest.TestCase):
    def test_real_kit_is_audited_reproducible_and_rebuilds_from_its_export(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);a=release.build(ROOT,root/'first');b=release.build(ROOT,root/'second')
            self.assertEqual(a['sha256'],b['sha256'])
            self.assertTrue(release.audit(a['archive'])['verified'])
            kit=root/'kit'
            with zipfile.ZipFile(a['archive']) as z:
                z.extractall(kit)
                self.assertNotIn('private/game/Default.xbe',z.namelist())
                self.assertNotIn('docs/IA-LOCALE.md',z.namelist())
                self.assertIn('MIT License',z.read('LICENSE').decode())
                self.assertIn('# Provenance',z.read('docs/PROVENANCE.md').decode())
            (kit/'private').mkdir();(kit/'private/Default.xbe').write_bytes(b'XBEHsynthetic private data')
            (kit/'tools/unlisted.py').write_text('must not ship')
            rebuilt=release.build(kit,root/'rebuilt')
            self.assertEqual(a['sha256'],rebuilt['sha256'])

    def test_paths_private_data_and_symlinks_are_refused(self):
        for name in ['../escape.py','private/data.py','build/generated.c','vendor/file.c','safe/../../escape.py','C:escape.py','safe//file.py','image.PNG','save.SES','trace.Log']:
            with self.subTest(name=name),self.assertRaises(ValueError):release.checked_path(name)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'source.py').write_text('print(1)\n');(root/'alias.py').symlink_to(root/'source.py')
            with self.assertRaises(ValueError):release.source_bytes(root,'alias.py')
            (root/'source.py').write_bytes(b'XBEHfake payload')
            with self.assertRaises(ValueError):release.source_bytes(root,'source.py')
            (root/'source.py').write_text(release.LOCAL_HOME+'private')
            with self.assertRaises(ValueError):release.source_bytes(root,'source.py')

    def test_added_private_members_or_modified_payload_fail_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);result=release.build(ROOT,root/'source')
            bad=root/'extra.zip';shutil.copyfile(result['archive'],bad)
            with zipfile.ZipFile(bad,'a') as z:z.writestr('private/leak.txt','do not ship')
            with self.assertRaises(ValueError):release.audit(bad)
            bad=root/'changed.zip'
            with zipfile.ZipFile(result['archive']) as source,zipfile.ZipFile(bad,'w') as z:
                for info in source.infolist():
                    z.writestr(info,b'changed' if info.filename=='README.md' else source.read(info))
            with self.assertRaises(ValueError):release.audit(bad)

    def test_only_approved_branding_images_are_allowed_and_passive(self):
        for name in ['docs/branding/other.png','docs/branding/other.svg','private/logo.png']:
            with self.subTest(name=name),self.assertRaises(ValueError):release.checked_path(name)
        for name in release.BRANDING_PNGS:
            png=(ROOT/name).read_bytes()
            release.check_text(png,name)
            damaged=bytearray(png);damaged[20]^=1
            with self.assertRaises(ValueError):release.check_text(bytes(damaged),name)
            with self.assertRaises(ValueError):release.check_text(png+b'XBEH',name)
        for name in release.BRANDING_SVGS:release.check_text((ROOT/name).read_bytes(),name)
        for svg in ['<svg><script/></svg>','<svg><image href="https://example.com"/></svg>',
                    '<svg onload="alert(1)"/>']:
            with self.assertRaises(ValueError):release.check_text(svg.encode(),'docs/branding/setup.svg')
