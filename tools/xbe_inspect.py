#!/usr/bin/env python3
"""Read-only XBE metadata inspection. No title-specific addresses or game code."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys


def inspect(data):
    def span(offset, size, label, limit=None):
        ceiling = len(data) if limit is None else min(limit, len(data))
        if offset < 0 or size < 0 or offset + size > ceiling:
            raise ValueError('%s is outside its file/header bounds' % label)
        return data[offset:offset + size]

    def u32(offset):
        return struct.unpack('<I', span(offset, 4, '32-bit field'))[0]

    if len(data) < 0x178 or data[:4] != b'XBEH':
        raise ValueError('Not a supported XBEH executable, or truncated image header')
    base, headers, image_size, image_header_size = struct.unpack_from('<4I', data, 0x104)
    if not 0x178 <= image_header_size <= headers <= len(data):
        raise ValueError('Invalid header sizes')
    if image_size < headers or base + image_size > 0x100000000:
        raise ValueError('Invalid 32-bit image extent')

    def header_offset(address, size, label):
        offset = address - base
        span(offset, size, label, headers)
        return offset

    cert = header_offset(u32(0x118), 4, 'certificate')
    cert_size = u32(cert)
    if cert_size < 0x5c:
        raise ValueError('Certificate too short for title fields')
    span(cert, cert_size, 'certificate', headers)
    title = span(cert + 12, 80, 'title', cert + cert_size).decode('utf-16-le').split('\0', 1)[0]
    count = u32(0x11c)
    if count > 4096:
        raise ValueError('Unreasonable section count')
    table = header_offset(u32(0x120), count * 0x38, 'section table') if count else 0
    sections = []
    for i in range(count):
        flags, va, virtual_size, raw_offset, raw_size, name_va = struct.unpack_from('<6I', data, table + i * 0x38)
        if va < base or va + virtual_size > base + image_size:
            raise ValueError('Section %d outside virtual image extent' % i)
        span(raw_offset, raw_size, 'section %d raw bytes' % i)
        name_offset = header_offset(name_va, 1, 'section name')
        end = data.find(b'\0', name_offset, headers)
        if end < 0:
            raise ValueError('Unterminated section name')
        name = data[name_offset:end].decode('ascii', errors='replace')
        sections.append({'name':name, 'flags':'0x%08X' % flags,
                         'virtual_address':'0x%08X' % va, 'virtual_size':virtual_size,
                         'file_offset':raw_offset, 'file_size':raw_size})
    candidates = []
    for kind, key in [('retail', 0xA8FC57AB), ('debug', 0x94859D4B)]:
        entry = u32(0x128) ^ key
        if any(int(s['flags'], 16) & 4 and int(s['virtual_address'], 16) <= entry <
               int(s['virtual_address'], 16) + s['file_size'] for s in sections):
            candidates.append((kind, entry))
    kind, entry = candidates[0] if len(candidates) == 1 else (None, None)
    certificate = {}
    if cert_size >= 0xb0:
        certificate = {'region_mask':'0x%08X' % u32(cert + 160),
                       'disc_number':u32(cert + 168), 'version':u32(cert + 172)}
    return {'format':'XBE', 'sha256':hashlib.sha256(data).hexdigest(), 'file_bytes':len(data),
            'title':title, 'title_id':'%08X' % u32(cert + 8),
            'base_address':'0x%08X' % base, 'headers_bytes':headers,
            'image_bytes':image_size, 'sections':sections,
            'image_timestamp':u32(0x114), 'pe_timestamp':u32(0x148),
            'build_utc':datetime.fromtimestamp(u32(0x114), timezone.utc).isoformat(),
            'executable_type':kind, 'entry_point':'0x%08X' % entry if entry is not None else None,
            'certificate':certificate,
            'signature_verified':False, 'game_executed':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('xbe', type=Path)
    args = parser.parse_args()
    try:
        # Bounded diagnostic, not a universal XBE loader.
        with args.xbe.open('rb') as stream:
            data = stream.read(256 * 1024 * 1024 + 1)
        if len(data) > 256 * 1024 * 1024:
            raise ValueError('File exceeds the 256 MiB inspection limit')
        print(json.dumps(inspect(data), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print('XBE inspection failed: %s' % exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
