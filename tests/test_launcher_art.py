"""Malformed private artwork containers must fail before invoking a decoder."""
import struct
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from launcher_art import remove_black_matte, title_texture


def container(count=1):
    payload = b''.join(struct.pack('<I', max(1, (256 >> level) // 4) ** 2 * 8)
                       + bytes(max(1, (256 >> level) // 4) ** 2 * 8) for level in range(8))
    data = bytearray(36 + count * 128)
    data[:8] = b'MULTITEX'
    struct.pack_into('<I', data, 20, count)
    struct.pack_into('<II', data, 28, 24, 128)
    for i in range(count):
        row = 36 + i * 128
        data[row + 24:row + 35] = b'Title_Buffy'
        struct.pack_into('<II', data, row + 88, 256, 256)
        struct.pack_into('<I', data, row + 108, 8)
        struct.pack_into('<III', data, row + 116, 1, len(data), len(payload))
        data.extend(payload)
    return data


class LauncherArtworkTests(unittest.TestCase):
    def test_black_matte_preserves_light_and_soft_edges(self):
        source = bytes((0, 0, 0, 255, 255, 255, 255, 255, 20, 10, 5, 255, 4, 2, 1, 255))
        result = remove_black_matte(source)
        self.assertEqual(result[:8], bytes((0, 0, 0, 0, 255, 255, 255, 255)))
        self.assertEqual(result[11], 20)
        for i in range(0, len(source), 4):
            for channel in range(3):
                self.assertLessEqual(abs(result[i + channel] * result[i + 3] / 255 - source[i + channel]), 1)
        with self.assertRaises(ValueError):
            remove_black_matte(b'bad')

    def test_named_bc1_level(self):
        w, h, raw = title_texture(container())
        self.assertEqual((w, h, len(raw)), (256, 256, 32768))
        self.assertEqual(raw, bytes(32768))

    def test_ambiguous_or_missing_title(self):
        with self.assertRaisesRegex(ValueError, 'Expected one'):
            title_texture(container(2))
        data = container()
        data[60:71] = b'Other_Image'
        with self.assertRaisesRegex(ValueError, 'Expected one'):
            title_texture(data)

    def test_bad_header_and_count(self):
        for at, value in [(20, 0), (20, 0xFFFFFFFF), (28, 25), (32, 127)]:
            with self.subTest(at=at, value=value):
                data = container()
                struct.pack_into('<I', data, at, value)
                with self.assertRaises(ValueError):
                    title_texture(data)
        with self.assertRaises(ValueError):
            title_texture(b'MULTITEX')

    def test_table_truncation(self):
        with self.assertRaisesRegex(ValueError, 'Truncated MULTITEX'):
            title_texture(container()[:80])

    def test_invalid_payload_range(self):
        for offset in [0, 163, 0xFFFFFFFF]:
            data = container()
            struct.pack_into('<I', data, 36 + 120, offset)
            with self.assertRaises(ValueError):
                title_texture(data)
        with self.assertRaises(ValueError):
            title_texture(container()[:-1])

    def test_mip_chain_must_match_dimensions(self):
        data = container()
        struct.pack_into('<I', data, 164, 32769)
        with self.assertRaisesRegex(ValueError, 'mip extent'):
            title_texture(data)
        data = container()
        struct.pack_into('<I', data, 36 + 88, 512)
        with self.assertRaises(ValueError):
            title_texture(data)

    def test_no_unparsed_payload_tail(self):
        data = container()
        size = struct.unpack_from('<I', data, 36 + 124)[0]
        struct.pack_into('<I', data, 36 + 124, size + 1)
        data.append(0)
        with self.assertRaisesRegex(ValueError, 'mip tail'):
            title_texture(data)
