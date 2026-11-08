import copy
import unittest
from tools.map_symbols import index_map


MAP = b''' Timestamp is 1234 (synthetic)
 0001:00000000 00000020H .text CODE
 0002:00000000 00000010H .data DATA
 0001:00000000 _start 00401000 f synthetic.obj
 0001:00000000 _alias 00401000 f synthetic.obj
 0001:00000010 _next 00401010 f synthetic.obj
 0002:00000004 _data 00402004 synthetic.obj
 0000:00000000 _absolute 00000000 <absolute>
 entry point at 0001:00000000
'''


def image():
    return {'sha256':'synthetic', 'pe_timestamp':0x1234, 'entry_point':'0x00011000',
            'sections':[{'name':'.text', 'virtual_address':'0x00011000',
                         'virtual_size':32, 'file_size':32, 'flags':'0x4'},
                        {'name':'.data', 'virtual_address':'0x00012000',
                         'virtual_size':16, 'file_size':8, 'flags':'0x1'}]}


class MapTests(unittest.TestCase):
    def test_relocation_aliases_data_and_absolute(self):
        report, symbols, seeds = index_map(MAP, image())
        self.assertEqual(report['matched_segments'], 2)
        self.assertEqual([s['start'] for s in seeds], ['0x00011000', '0x00011010'])
        self.assertEqual(symbols[3]['address'], '0x00012004')
        self.assertFalse(symbols[3]['function'])
        self.assertEqual(report['skipped_nonresident_symbols'], 1)

    def test_mismatched_timestamp_extent_entry_and_pe_base_rejected(self):
        for old, new in [(b'Timestamp is 1234', b'Timestamp is 1235'),
                         (b'00000020H', b'00000021H'),
                         (b'entry point at 0001:00000000', b'entry point at 0001:00000001'),
                         (b'_next 00401010', b'_next 00401011')]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                index_map(MAP.replace(old, new), image())

    def test_non_file_backed_function_not_seeded(self):
        xbe = copy.deepcopy(image())
        xbe['sections'][0]['file_size'] = 16
        _, _, seeds = index_map(MAP, xbe)
        self.assertEqual(len(seeds), 1)
