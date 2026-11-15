"""Synthetic resource-archive contracts; no game payloads enter the tests."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools.game_resources import ResourceError, read_records, stock_inventory, audit_inventory


def words(*values):
    return struct.pack('<' + 'I' * len(values), *values)


def string(value):
    raw = value.encode('ascii')
    return words(len(raw)) + raw


def directory(*, type_id=4, array_count=1, pool_offset=0, duplicate=False):
    # String table, hash refs, resource capacities and one serialized directory.
    pool = b'model\0'
    result = words(0x52014, len(pool), 0, len(pool), 1, 1, pool_offset) + pool
    result += words(1, 1) + struct.pack('<H', 0xffff)
    result += words(2 if duplicate else 1, 2 if duplicate else 1, 1) + bytes(36)
    resource_type = (words(type_id) + string('msh') + words(1, 1) + string('meshes')
                     + words(1, array_count) + struct.pack('<HHI', 0, 0, 1)
                     + struct.pack('<HHHHI', 0, 0, 1, 0, 42))
    return result + resource_type * (2 if duplicate else 1) + words(0xffffffff)


def archive(*, name='meshes\\chars\\slayer\\synthetic.msh',
            active=1, manual=0, flag=0, offset_delta=0, span_delta=0, trailer=b'',
            prefix=None):
    prefix = directory() if prefix is None else prefix
    data = b'\0SYNTHETIC MODEL\xff'
    header = (words(active, len(prefix) + offset_delta, 0, len(data), manual)
              + string(name) + string('base') + words(flag))
    span = len(header) + len(data) + span_delta
    header = header[:8] + words(span & 0xffffffff) + header[12:]
    return prefix + header + data + bytes(32) + trailer


class ResourcePackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'synthetic.pak'

    def read(self, data):
        self.path.write_bytes(data)
        return read_records(self.path)

    def test_records_describe_real_binary_spans_without_exporting_payloads(self):
        data = archive(name='Meshes\\Chars\\Slayer\\Synthetic.msh', trailer=b'x' * 128)
        rows = self.read(data)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.name, 'meshes\\chars\\slayer\\synthetic.msh')
        self.assertEqual(row.resource, 'base')
        self.assertEqual(data[row.data_offset:row.data_offset + row.data_size],
                         b'\0SYNTHETIC MODEL\xff')
        self.assertFalse(row.manual)
        self.assertFalse(row.flag)
        self.assertEqual(list(self.root.iterdir()), [self.path])

    def test_manual_records_and_unused_terminal_offset_span(self):
        data = archive(manual=1)
        data = data[:-32] + words(0, 1234, 5678, 0, 0, 0, 0, 0)
        self.assertTrue(self.read(data)[0].manual)

    def test_version_and_truncated_directory_or_payload_rejected(self):
        data = archive()
        for cut in [0, 3, 4, 10, 25, 47, len(directory()) - 1,
                    len(directory()) + 20, len(data) - 33, len(data) - 1]:
            with self.subTest(cut=cut), self.assertRaises(ResourceError):
                self.read(data[:cut])
        with self.assertRaises(ResourceError):
            self.read(words(0x52015) + data[4:])

    def test_invalid_pool_reference_and_array_counts_rejected(self):
        for prefix in [directory(pool_offset=999), directory(array_count=2),
                       directory(type_id=19), directory(duplicate=True)]:
            with self.subTest(prefix=prefix[:24]), self.assertRaises(ResourceError):
                self.read(archive(prefix=prefix))

    def test_payload_spans_cannot_overlap_headers_or_escape_archive(self):
        for delta in [-999, -1, 1, 999999]:
            with self.subTest(delta=delta), self.assertRaises(ResourceError):
                self.read(archive(span_delta=delta))
        for delta in [-1, 1]:
            with self.assertRaises(ResourceError):
                self.read(archive(offset_delta=delta))

    def test_boolean_fields_and_invalid_terminator_rejected(self):
        for kw in [{'active': 2}, {'manual': 2}, {'flag': 2},
                   {'trailer': b'x' * 127}, {'trailer': b'x' * 129}]:
            with self.subTest(kw=kw), self.assertRaises(ResourceError):
                self.read(archive(**kw))
        data = archive()
        with self.assertRaises(ResourceError):
            self.read(data[:-32] + words(0, 0, 0, 0, 0, 1, 0, 0))

    def test_unsafe_paths_and_control_characters_rejected(self):
        for name in ['', 'C:\\payload', '\\payload', '..\\payload',
                     'meshes\\..\\payload', 'meshes/payload', 'a:stream',
                     'meshes\\\\payload', 'meshes\\.\\payload', 'x\0y']:
            with self.subTest(name=name), self.assertRaises(ResourceError):
                self.read(archive(name=name))

    def test_symlink_and_oversized_file_rejected(self):
        self.path.write_bytes(archive())
        link = self.root / 'alias.pak'
        link.symlink_to(self.path)
        with self.assertRaises(ResourceError):
            read_records(link)
        with self.path.open('wb') as stream:
            stream.truncate(512 * 1024 * 1024 + 1)
        with self.assertRaises(ResourceError):
            read_records(self.path)

    def test_catalog_keeps_sources_and_identity_check_but_claims_no_runtime_success(self):
        game = self.root / 'game'
        (game / 'pak').mkdir(parents=True)
        (game / 'pak/test.pak').write_bytes(archive(name='meshes\\chars\\slayer\\buffycheer.msh'))
        title = self.root / 'title.json'
        title.write_text(json.dumps({'test': True}))
        with patch('tools.loadvars_fix.verify_xbe') as verify:
            result = stock_inventory(game, title)
            verify.assert_called_once_with(game / 'Default.xbe', {'test': True})
        self.assertFalse(result['runtime_validated'])
        cheer = next(row for row in result['outfits'] if row['id'] == 'cheerleader')
        self.assertEqual(cheer['sources'][0]['pack'], 'test.pak')
        self.assertEqual(cheer['sources'][0]['materials'], [])
        self.assertFalse(cheer['sources'][0]['animation_table'])
        with patch('tools.loadvars_fix.verify_xbe', side_effect=ValueError('wrong XBE')):
            with self.assertRaisesRegex(ValueError, 'wrong XBE'):
                stock_inventory(game, title)

    def test_audit_compares_payloads_without_claiming_unused_or_playable(self):
        game=self.root/'game';(game/'pak').mkdir(parents=True)
        original=archive(name='meshes\\chars\\slayer\\buffycheer.msh')
        (game/'pak/a.pak').write_bytes(original)
        (game/'pak/b.pak').write_bytes(original.replace(b'SYNTHETIC MODEL',b'ALTERNATE DATA!'))
        title=self.root/'title.json';title.write_text('{}')
        with patch('tools.loadvars_fix.verify_xbe'):
            result=audit_inventory(game,title)
        self.assertEqual(result['pack_count'],2)
        self.assertEqual(result['unique_base_models'],1)
        self.assertEqual(result['payloads_by_type'],{'msh':2})
        self.assertEqual(len(next(iter(result['buffy_payload_variants'].values()))),2)
        self.assertEqual(result['confirmed_unused'],[])


if __name__ == '__main__':
    unittest.main()
