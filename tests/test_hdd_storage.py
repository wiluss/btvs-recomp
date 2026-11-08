"""Lossless dormant-device storage, with no title assets or user saves."""
from pathlib import Path
import gzip
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import hdd_storage as storage


class HddStorageTests(unittest.TestCase):
    def test_round_trip_multiple_members_and_ordinary_files_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = bytes(storage.CHUNK) + b'FATX'+bytes(65532) + bytes(123)
            p = root/'Partition5.img'
            p.write_bytes(data)
            p.chmod(0o640)
            (root/'Partition0.img').write_bytes(b'partition table')
            (root/'UDATA').mkdir()
            save = root/'UDATA/checkpoint.ses'
            save.write_bytes(b'progress')
            with patch.dict(storage.SIZES, {5: len(data)}, clear=True):
                records = storage.pack_hdd(root)
                archive = p.with_suffix('.img.gz')
                self.assertFalse(p.exists())
                self.assertLess(records[0]['packed_bytes'], len(data)//100)
                self.assertEqual(gzip.decompress(archive.read_bytes()), data)
                # Independent standard gzip reader accepts concatenated members.
                result = subprocess.run(['gzip', '-dc', str(archive)], capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, data)
                storage.restore_hdd(root)
            self.assertEqual(p.read_bytes(), data)
            self.assertEqual(p.stat().st_mode & 0o777, 0o640)
            self.assertFalse(archive.exists())
            self.assertEqual((root/'Partition0.img').read_bytes(), b'partition table')
            self.assertEqual(save.read_bytes(), b'progress')

    def test_corrupt_truncated_and_oversized_archives_never_publish_an_image(self):
        cases = [b'invalid gzip', gzip.compress(b'x'*20)[:-3], gzip.compress(b'x'*11), gzip.compress(b'x'*9)]
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'Partition1.img.gz'
            with patch.dict(storage.SIZES, {1: 10}, clear=True):
                for data in cases:
                    p.write_bytes(data)
                    with self.subTest(data=data), self.assertRaises((OSError, ValueError, EOFError)):
                        storage.restore_hdd(p.parent)
                    self.assertEqual(p.read_bytes(), data)
                    self.assertFalse(p.with_suffix('').exists())
                    self.assertEqual(len(list(p.parent.iterdir())), 1)

    def test_size_conflicts_symlinks_and_source_changes_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            p = root/'Partition1.img'
            p.write_bytes(b'0123456789')
            archive = p.with_suffix('.img.gz')
            with self.assertRaises(ValueError):
                storage._pack(p, 11)
            archive.write_bytes(b'existing archive')
            with self.assertRaises(ValueError):
                storage._pack(p, 10)
            self.assertEqual(archive.read_bytes(), b'existing archive')
            archive.unlink()
            symlink = root/'alias'
            symlink.symlink_to(p)
            with self.assertRaises(ValueError):
                storage._pack(symlink, 10)
            original = storage.gzip.compress
            def changed(data, **kwargs):
                p.write_bytes(b'new data!!')
                return original(data, **kwargs)
            with patch.object(storage.gzip, 'compress', side_effect=changed):
                with self.assertRaisesRegex(ValueError, 'modifiée'):
                    storage._pack(p, 10)
            self.assertEqual(p.read_bytes(), b'new data!!')
            self.assertFalse(archive.exists())

    def test_storage_and_device_locks_prevent_concurrent_maintenance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with storage.storage_lock(root):
                with self.assertRaises(ValueError):
                    with storage.storage_lock(root, maintenance=True):
                        self.fail('maintenance opened during play')
            with storage.storage_lock(root, maintenance=True):
                with self.assertRaises(ValueError):
                    with storage.storage_lock(root):
                        self.fail('play opened during maintenance')
            with storage.prepared_hdd(root):
                with self.assertRaises(ValueError):
                    with storage.prepared_hdd(root):
                        self.fail('two writers on same HDD')

    def test_failed_write_preserves_source_and_removes_partial_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'Partition1.img'
            data = b'irreplaceable device bytes'
            p.write_bytes(data)
            with patch.object(storage.os, 'fsync', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    storage._pack(p, len(data))
            self.assertEqual(p.read_bytes(), data)
            self.assertEqual(list(p.parent.iterdir()), [p])

    def test_prepared_disk_restores_before_use_and_packs_after_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root/'Partition1.img.gz'
            archive.write_bytes(gzip.compress(b'old progress'))
            with patch.dict(storage.SIZES, {1: 12}, clear=True):
                with self.assertRaisesRegex(RuntimeError, 'test interruption'):
                    with storage.prepared_hdd(root):
                        p = root/'Partition1.img'
                        self.assertEqual(p.read_bytes(), b'old progress')
                        p.write_bytes(b'new progress')
                        raise RuntimeError('test interruption')
                self.assertFalse(p.exists())
                self.assertEqual(gzip.decompress(archive.read_bytes()), b'new progress')


if __name__ == '__main__':
    unittest.main()
