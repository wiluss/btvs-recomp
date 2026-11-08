from pathlib import Path
import hashlib
import json
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import disc_import as importer

S = 2048


def entry(name, sector, size, flags=0):
    name = name.encode('ascii')
    data = struct.pack('<HHIIBB',0,0,sector,size,flags,len(name))+name
    return data+bytes(-len(data)%4)


def image(base=0, names=('DEFAULT.XBE','FINAL.MAP'), root_extra=b''):
    payloads = (b'XBEH synthetic test only', b'linker map synthetic test only')
    data = bytearray(base+40*S)
    desc = bytearray(S);magic=importer.xdvdfs.MAGIC
    desc[:len(magic)]=magic;desc[-len(magic):]=magic
    struct.pack_into('<II',desc,20,33,S)
    data[base+32*S:base+33*S]=desc
    root=b''.join(entry(name,34+i,len(payloads[i])) for i,name in enumerate(names))+root_extra
    data[base+33*S:base+33*S+len(root)]=root
    for i,payload in enumerate(payloads):data[base+(34+i)*S:base+(34+i)*S+len(payload)]=payload
    title={'xbe_sha256':hashlib.sha256(payloads[0]).hexdigest(),
           'symbols':{'map_sha256':hashlib.sha256(payloads[1]).hexdigest()}}
    return data,title


class DiscImportTests(unittest.TestCase):
    def test_publication_refuses_even_an_empty_existing_directory_atomically(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'staging';target=root/'existing'
            source.mkdir();target.mkdir();(source/'payload').write_bytes(b'new')
            with self.assertRaises(FileExistsError):importer.publish_directory(source,target)
            self.assertEqual(list(target.iterdir()),[])
            self.assertEqual((source/'payload').read_bytes(),b'new')
    def test_supported_disc_imports_exact_bytes_without_touching_source(self):
        for base in (0,0x30600):
            with self.subTest(base=base),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);data,title=image(base)
                iso=root/'player.iso';iso.write_bytes(data)
                target=root/'private/game'
                report=importer.inspect_disc(iso,title)
                self.assertTrue(report['compatible']);self.assertFalse(target.exists())
                imported=importer.import_disc(iso,target,title)
                self.assertFalse(imported['gameplay_validated'])
                self.assertEqual(hashlib.sha256((target/'Default.xbe').read_bytes()).hexdigest(),title['xbe_sha256'])
                self.assertEqual(hashlib.sha256((target/'final.map').read_bytes()).hexdigest(),title['symbols']['map_sha256'])
                self.assertEqual(iso.read_bytes(),data)

    def test_unknown_title_missing_map_and_existing_install_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data,title=image();iso=root/'player.iso';iso.write_bytes(data)
            target=root/'game'
            bad=json.loads(json.dumps(title));bad['xbe_sha256']='0'*64
            with self.assertRaises(ValueError):importer.import_disc(iso,target,bad)
            self.assertFalse(target.exists())
            data,_=image(names=('DEFAULT.XBE','other.map'));iso.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'final.map'):importer.import_disc(iso,target,title)
            target.mkdir();(target/'precious').write_bytes(b'existing')
            with self.assertRaisesRegex(ValueError,'existe'):importer.import_disc(iso,target,title)
            self.assertEqual((target/'precious').read_bytes(),b'existing')

    def test_paths_collisions_truncation_extents_and_cycles_are_rejected(self):
        extras=[entry('../escape',36,1),entry('sub/file',36,1),entry('bad\\file',36,1),
                entry('default.xbe',36,1),entry('outside',999999,1),entry('loop',33,S,0x10)]
        for extra in extras:
            with self.subTest(extra=extra),tempfile.TemporaryDirectory() as folder:
                data,title=image(root_extra=extra);iso=Path(folder)/'bad.iso';iso.write_bytes(data)
                with self.assertRaises(ValueError):importer.inspect_disc(iso,title)
        with tempfile.TemporaryDirectory() as folder:
            data,title=image();data[33*S+13]=255;iso=Path(folder)/'bad.iso';iso.write_bytes(data)
            with self.assertRaises(ValueError):importer.inspect_disc(iso,title)

    def test_interrupted_extraction_and_modified_source_publish_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data,title=image();iso=root/'player.iso';iso.write_bytes(data);target=root/'game'
            with patch.object(importer.Disc,'extract',side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):importer.import_disc(iso,target,title)
            self.assertFalse(target.exists());self.assertFalse(list(root.glob('.buffy-import-*')))
            def changed(event):
                with iso.open('ab') as stream:stream.write(b'changed')
            with self.assertRaises(ValueError):importer.import_disc(iso,target,title,changed)
            self.assertFalse(target.exists());self.assertFalse(list(root.glob('.buffy-import-*')))

    def test_directory_and_expansion_budgets(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data,title=image();iso=root/'player.iso';iso.write_bytes(data)
            with patch.object(importer,'MAX_TREE_BYTES',1):
                with self.assertRaises(ValueError):importer.inspect_disc(iso,title)
            with patch.object(importer,'MAX_EXTRACTED',1):
                with self.assertRaises(ValueError):importer.inspect_disc(iso,title)
            with patch.object(importer.shutil,'disk_usage') as space:
                space.return_value.free=0
                with self.assertRaisesRegex(ValueError,'Espace'):importer.import_disc(iso,root/'game',title)
            self.assertFalse((root/'game').exists())
