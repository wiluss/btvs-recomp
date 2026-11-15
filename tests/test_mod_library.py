"""Synthetic packs exercise managed imports, persistence and real XRTP composition."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/launcher'))
import mod_library as mods
from text_pack import read_pack

XBE='a'*64


def pack(folder,name,entries,xbe=XBE):
    path=folder/(name+'.xrtp');offset=32+len(entries)*32
    with path.open('wb') as f:
        f.write(struct.pack('<4sIIIQII',b'XRTP',2,len(entries),2,32,8,0))
        for key,w,h,color in entries:
            f.write(struct.pack('<QIIIIQ',key,w,h,1,0,offset));offset+=w*h*4
        for _,w,h,color in entries:f.write(bytes(color)*w*h)
    path.with_suffix('.json').write_text(json.dumps({'xbe_sha256':xbe,'entries':len(entries),'pack_sha256':mods.sha(path)}))
    return path


class ModLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'config').mkdir()
        (self.root/'config/title.json').write_text(json.dumps({'xbe_sha256':XBE}))
        self.sources=self.root/'sources';self.sources.mkdir()
        self.art=pack(self.sources,'Red jacket',[(1,4,4,(255,0,0,255))])
        self.patcher=patch.object(mods.subprocess,'run',return_value=subprocess.CompletedProcess([],1))
        self.patcher.start();self.addCleanup(self.patcher.stop)

    def install(self):
        result=mods.install(self.root,self.art);return result['mods'][0]['id']

    def test_import_copies_validates_and_selection_survives_restart(self):
        mod=self.install();self.assertIsNone(mods.state(self.root)['active'])
        imported=mods.mod_path(self.root,mod);original=imported.read_bytes()
        mods.activate(self.root,mod)
        self.art.unlink();self.art.with_suffix('.json').unlink()
        self.assertEqual(mods.listing(self.root)['active'],mod)
        self.assertEqual(mods.prepare(self.root,'original','original')['pack'],str(imported))
        self.assertEqual(imported.read_bytes(),original)
        mods.activate(self.root,None)
        self.assertEqual(mods.prepare(self.root,'original','original'),{'pack':None})

    def test_same_content_is_deduplicated_and_import_does_not_enable(self):
        mod=self.install();self.assertEqual(len(mods.install(self.root,self.art)['mods']),1)
        self.assertIsNone(mods.state(self.root)['active'])
        mods.activate(self.root,mod)
        other=pack(self.sources,'Other',[(2,4,4,(0,0,0,255))]);mods.install(self.root,other)
        self.assertEqual(mods.state(self.root)['active'],mod)

    def test_wrong_game_missing_sidecar_and_changed_payload_are_refused(self):
        bad=pack(self.sources,'Wrong',[(1,4,4,(0,0,0,255))],xbe='wrong')
        with self.assertRaises(ValueError):mods.install(self.root,bad)
        self.art.with_suffix('.json').unlink()
        with self.assertRaises(ValueError):mods.install(self.root,self.art)
        good=pack(self.sources,'Good',[(1,4,4,(0,0,0,255))]);good.write_bytes(good.read_bytes()+b'x')
        with self.assertRaises(ValueError):mods.install(self.root,good)
        self.assertEqual(mods.listing(self.root)['mods'],[])

    def test_hd_composition_preserves_other_payloads_and_reuses_cache(self):
        mod=self.install();mods.activate(self.root,mod)
        base=pack(self.sources,'Base',[(1,4,4,(0,0,255,255)),(2,4,4,(0,255,0,255))]);before=base.read_bytes()
        with patch.object(mods,'verify_profile') as verify,patch.object(mods,'pack_path',return_value=base):
            output=Path(mods.prepare(self.root,'campaign2x','hd')['pack']);verify.assert_called_once_with('campaign2x',self.root,text='hd')
            _,rows=read_pack(output);_,original=read_pack(base)
            self.assertEqual(rows[1][-1][:4],bytes([255,0,0,255]));self.assertEqual(rows[2],original[2])
            self.assertEqual(base.read_bytes(),before)
            with patch.object(mods,'compose',side_effect=AssertionError('cache not reused')):
                self.assertEqual(mods.prepare(self.root,'campaign2x','hd')['pack'],str(output))

    def test_wrong_aspect_refused_before_publishing_cache(self):
        mod=self.install();mods.activate(self.root,mod)
        base=pack(self.sources,'Base',[(1,8,4,(0,0,0,255))])
        with patch.object(mods,'verify_profile'),patch.object(mods,'pack_path',return_value=base):
            with self.assertRaisesRegex(ValueError,'aspect'):mods.prepare(self.root,'campaign2x','hd')
        self.assertFalse(any(p.name[0]!='.' for p in (self.root/'private/mods/cache').iterdir()))

    def test_failed_import_keeps_previous_active_mod(self):
        mod=self.install();mods.activate(self.root,mod)
        other=pack(self.sources,'Other',[(2,4,4,(0,0,0,255))])
        with patch.object(mods.shutil,'copyfile',side_effect=OSError('disk failed')):
            with self.assertRaises(OSError):mods.install(self.root,other)
        self.assertEqual(mods.state(self.root)['active'],mod)
        self.assertEqual(len(mods.listing(self.root)['mods']),1)

    def test_locks_active_game_low_space_symlinks_and_invalid_ids(self):
        with patch.object(mods.subprocess,'run',return_value=subprocess.CompletedProcess([],0)):
            with self.assertRaises(ValueError):mods.install(self.root,self.art)
        with patch.object(mods.shutil,'disk_usage',return_value=type('Usage',(),{'free':0})()):
            with self.assertRaises(ValueError):mods.install(self.root,self.art)
        (self.root/'private').mkdir(exist_ok=True)
        with (self.root/'private/mods.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(ValueError):mods.install(self.root,self.art)
        for bad in ['../escape','x'*64]:
            with self.assertRaises(ValueError):mods.activate(self.root,bad)
        alias=self.sources/'alias.xrtp';alias.symlink_to(self.art)
        with self.assertRaises(ValueError):mods.install(self.root,alias)

    def test_tampered_managed_pack_and_bad_preferences_fail_closed(self):
        mod=self.install();mods.activate(self.root,mod)
        managed=mods.mod_path(self.root,mod);managed.write_bytes(managed.read_bytes()+b'changed')
        with self.assertRaises(ValueError):mods.prepare(self.root,'original','original')
        (self.root/'private/config/mods.json').write_text('[]')
        with self.assertRaises(ValueError):mods.prepare(self.root,'original','original')
        mods.activate(self.root,None)
        self.assertIsNone(mods.state(self.root)['active'])

    def test_no_mod_leaves_existing_profile_resolution_to_play(self):
        self.assertEqual(mods.prepare(self.root,'campaign2x','hd'),{'pack':None})
        self.assertFalse((self.root/'private/mods/cache').exists())

    def test_symlinked_library_cannot_escape_private(self):
        (self.root/'private/mods').mkdir(parents=True)
        (self.root/'private/mods/library').symlink_to(self.sources)
        before=set(self.sources.iterdir())
        with self.assertRaises(ValueError):mods.install(self.root,self.art)
        self.assertEqual(set(self.sources.iterdir()),before)

    def test_valid_payload_replacement_cannot_change_a_managed_identity(self):
        mod=self.install()
        managed=mods.mod_path(self.root,mod)
        other=pack(self.sources,'Other',[(1,4,4,(0,0,255,255))])
        managed.write_bytes(other.read_bytes());managed.with_suffix('.json').write_bytes(other.with_suffix('.json').read_bytes())
        with self.assertRaisesRegex(ValueError,'identity'):mods.activate(self.root,mod)
        self.assertIsNone(mods.state(self.root)['active'])

    def preview(self,path,width=8,height=4,payload=None):
        # Synthetic test pixels only; this is not a claimed outfit screenshot.
        import zlib
        def chunk(kind,value):return struct.pack('>I',len(value))+kind+value+struct.pack('>I',zlib.crc32(kind+value))
        raw=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))
        raw+=chunk(b'IDAT',zlib.compress(payload if payload is not None else (b'\0'+b'\x90\0\0\xff'*width)*height))+chunk(b'IEND',b'')
        path.write_bytes(raw);return raw

    def test_skin_metadata_and_adjacent_preview_are_copied(self):
        proof=json.loads(self.art.with_suffix('.json').read_text())
        proof['skin']={'name':'Crimson jacket','author':'A creator','description':'A texture-only test'}
        self.art.with_suffix('.json').write_text(json.dumps(proof))
        raw=self.preview(self.art.with_suffix('.png'))
        mod=self.install();row=mods.listing(self.root)['mods'][0]
        self.assertEqual((row['name'],row['author'],row['description']),('Crimson jacket','A creator','A texture-only test'))
        self.assertEqual(Path(row['preview']).read_bytes(),raw)
        self.art.with_suffix('.png').unlink()
        self.assertTrue(Path(mods.listing(self.root)['mods'][0]['preview']).is_file())
        self.assertIsNone(mods.state(self.root)['active'])

    def test_attach_and_replace_preview_preserves_active_pack(self):
        mod=self.install();mods.activate(self.root,mod);before=mods.mod_path(self.root,mod).read_bytes()
        self.assertIsNone(mods.listing(self.root)['mods'][0]['preview'])
        image=self.sources/'screenshot.png';self.preview(image)
        first=mods.attach_preview(self.root,mod,image)['mods'][0]['preview']
        self.preview(image,width=12)
        last=mods.attach_preview(self.root,mod,image)
        self.assertNotEqual(first,last['mods'][0]['preview'])
        self.assertEqual(last['active'],mod)
        self.assertEqual(mods.mod_path(self.root,mod).read_bytes(),before)

    def test_invalid_previews_and_metadata_preserve_library_and_selection(self):
        mod=self.install();mods.activate(self.root,mod)
        invalid=self.sources/'bad.png';invalid.write_bytes(b'not a PNG')
        with self.assertRaises(ValueError):mods.attach_preview(self.root,mod,invalid)
        self.preview(invalid,width=100000,height=1,payload=b'')
        with self.assertRaises(ValueError):mods.attach_preview(self.root,mod,invalid)
        self.preview(invalid,payload=b'wrong expanded pixels')
        with self.assertRaises(ValueError):mods.attach_preview(self.root,mod,invalid)
        self.preview(invalid);invalid.write_bytes(invalid.read_bytes()[:-1]+b'x')
        with self.assertRaises(ValueError):mods.attach_preview(self.root,mod,invalid)
        self.assertEqual(mods.state(self.root)['active'],mod)
        self.assertIsNone(mods.listing(self.root)['mods'][0]['preview'])
        other=pack(self.sources,'Other',[(2,4,4,(0,0,0,255))]);proof=json.loads(other.with_suffix('.json').read_text());proof['skin']={'name':['bad']}
        other.with_suffix('.json').write_text(json.dumps(proof))
        with self.assertRaises(ValueError):mods.install(self.root,other)
        self.assertEqual(len(mods.listing(self.root)['mods']),1)

    def test_preview_import_is_atomic_and_cannot_escape_managed_folder(self):
        self.art.with_suffix('.png').write_bytes(b'invalid')
        with self.assertRaises(ValueError):mods.install(self.root,self.art)
        self.assertEqual(mods.listing(self.root)['mods'],[])
        self.art.with_suffix('.png').unlink();mod=self.install()
        image=self.sources/'screenshot.png';self.preview(image)
        with patch.object(mods.os,'replace',side_effect=OSError('metadata commit failed')):
            with self.assertRaises(OSError):mods.attach_preview(self.root,mod,image)
        self.assertIsNone(mods.listing(self.root)['mods'][0]['preview'])
        meta=mods.mod_path(self.root,mod).parent/'mod.json';meta.write_text(json.dumps({'name':'bad','preview':'../../escape.png'}))
        with self.assertRaises(ValueError):mods.listing(self.root)

    def test_live_catalog_keeps_base_separate_and_contains_verified_skin_paths(self):
        mod=self.install();mods.activate(self.root,mod)
        base=pack(self.sources,'Base',[(1,4,4,(0,0,0,255)),(2,4,4,(0,255,0,255))])
        with patch.object(mods,'verify_profile'),patch.object(mods,'pack_path',return_value=base):
            result=mods.wardrobe(self.root,'campaign2x','hd')
        self.assertEqual(result['pack'],str(base))
        self.assertTrue(Path(result['preferences']).parent.is_dir())
        raw=Path(result['catalog']).read_bytes();self.assertEqual(struct.unpack('<4sII',raw[:12]),(b'BWS1',1,1))
        self.assertIn(str(mods.mod_path(self.root,mod)).encode(),raw)
        self.assertFalse((self.root/'private/mods/cache').exists())

    def test_live_catalog_refuses_incompatible_skins_before_launch(self):
        self.install();base=pack(self.sources,'Wrong aspect',[(1,8,4,(0,0,0,255))])
        with patch.object(mods,'verify_profile'),patch.object(mods,'pack_path',return_value=base):
            with self.assertRaisesRegex(ValueError,'conflicts'):mods.wardrobe(self.root,'campaign2x','hd')
        self.assertFalse((self.root/'private/mods/sessions').exists())
