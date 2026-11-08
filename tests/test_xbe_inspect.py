import hashlib
import struct
import unittest
from tools.xbe_inspect import inspect


def fixture():
    data = bytearray(0x1000)
    data[:4] = b'XBEH'
    def put(offset, *values):
        struct.pack_into('<' + 'I' * len(values), data, offset, *values)
    put(0x104, 0x10000, 0x800, 0x3000, 0x178)
    put(0x118, 0x10200, 1, 0x10400)
    put(0x200, 0x1d0, 0, 0x12345678)
    title = 'Synthetic é 🦇'.encode('utf-16-le')
    data[0x20c:0x20c + len(title)] = title
    put(0x400, 4, 0x11000, 0x200, 0x800, 0x200, 0x10500)
    data[0x500:0x506] = b'.text\0'
    return data


class XbeInspectionTests(unittest.TestCase):
    def test_retail_debug_entry_and_unknown_are_distinguished(self):
        for key, kind in [(0xA8FC57AB, 'retail'), (0x94859D4B, 'debug')]:
            data = fixture()
            struct.pack_into('<I', data, 0x128, 0x11000 ^ key)
            result = inspect(data)
            self.assertEqual(result['entry_point'], '0x00011000')
            self.assertEqual(result['executable_type'], kind)
        self.assertIsNone(inspect(fixture())['entry_point'])

    def test_synthetic_title_and_section(self):
        data = fixture()
        result = inspect(data)
        self.assertEqual(result['title'], 'Synthetic é 🦇')
        self.assertEqual(result['title_id'], '12345678')
        self.assertEqual(result['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(result['sections'][0]['name'], '.text')
        self.assertFalse(result['game_executed'])

    def test_truncated_header_and_bad_magic(self):
        for data in (b'XBEH', b'NOPE' + bytes(4092)):
            with self.assertRaises(ValueError): inspect(data)

    def test_certificate_address_underflow(self):
        data = fixture(); struct.pack_into('<I',data,0x118,0xffff)
        with self.assertRaises(ValueError): inspect(data)

    def test_certificate_outside_headers(self):
        data = fixture(); struct.pack_into('<I',data,0x200,0x700)
        with self.assertRaises(ValueError): inspect(data)

    def test_section_table_overflow(self):
        data = fixture(); struct.pack_into('<I',data,0x11c,1000)
        with self.assertRaises(ValueError): inspect(data)

    def test_raw_section_truncated(self):
        data = fixture(); struct.pack_into('<I',data,0x410,0x1000)
        with self.assertRaises(ValueError): inspect(data)

    def test_virtual_extent_wraparound(self):
        data = fixture(); struct.pack_into('<I',data,0x404,0xfffffff0)
        with self.assertRaises(ValueError): inspect(data)

    def test_section_name_requires_terminator(self):
        data = fixture(); data[0x500:0x800] = b'A' * 0x300
        with self.assertRaises(ValueError): inspect(data)


if __name__ == '__main__': unittest.main()
