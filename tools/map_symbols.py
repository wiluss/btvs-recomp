#!/usr/bin/env python3
"""Validate a user-supplied MS linker MAP against its XBE; index locally.

Never uses the MAP's PE addresses as Xbox addresses. No external symbol source.
The complete index and seeds belong in ignored generated/, not in Git.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

try:
    from .xbe_inspect import inspect
except ImportError:
    from xbe_inspect import inspect

SECTION = re.compile(r'^\s+([\da-f]{4}):([\da-f]{8})\s+([\da-f]{8})H\s+(\S+)\s+(CODE|DATA)\s*$', re.I)
SYMBOL = re.compile(r'^\s+([\da-f]{4}):([\da-f]{8})\s+(\S+)\s+([\da-f]{8})\s+(.*?)\s*$', re.I)


def index_map(raw_map, xbe):
    text = raw_map.decode('cp1252')
    timestamp = re.search(r'Timestamp is ([\da-f]+)', text, re.I)
    entry = re.search(r'entry point at\s+([\da-f]{4}):([\da-f]{8})', text, re.I)
    if not timestamp or not entry:
        raise ValueError('Not a supported MS linker MAP (timestamp/entry missing)')
    if int(timestamp[1], 16) != xbe['pe_timestamp']:
        raise ValueError('MAP timestamp differs from XBE original PE timestamp')
    subsections, symbols = [], []
    for line in text.splitlines():
        section = SECTION.match(line)
        if section:
            subsections.append((int(section[1], 16), int(section[2], 16), int(section[3], 16), section[4]))
        else:
            symbol = SYMBOL.match(line)
            if symbol:
                symbols.append((int(symbol[1], 16), int(symbol[2], 16), symbol[3],
                                int(symbol[4], 16), symbol[5]))
    # XBE conversion preserves segment order for the resident PE sections.
    # Require all of them to match exactly; appended XBE artwork is excluded.
    resident = [s for s in xbe['sections'] if not s['name'].startswith('$$')]
    mappings = {}
    for number, section in enumerate(resident, 1):
        parts = [p for p in subsections if p[0] == number]
        if not parts or max(p[1] + p[2] for p in parts) != section['virtual_size']:
            raise ValueError('MAP segment %d extent differs from XBE section %s' % (number, section['name']))
        mappings[number] = section
    entry_section = mappings.get(int(entry[1], 16))
    if not entry_section or xbe['entry_point'] is None or (
            int(entry_section['virtual_address'], 16) + int(entry[2], 16) != int(xbe['entry_point'], 16)):
        raise ValueError('MAP entry does not match decoded XBE entry')
    index, skipped, pe_bases = [], 0, {}
    for segment, offset, name, pe_va, tail in symbols:
        section = mappings.get(segment)
        if section is None:
            skipped += 1
            continue
        if offset > section['virtual_size']:
            raise ValueError('MAP symbol outside section extent')
        pe_base = pe_va - offset
        if pe_base < 0 or pe_bases.setdefault(segment, pe_base) != pe_base:
            raise ValueError('Inconsistent MAP PE base within segment')
        va = int(section['virtual_address'], 16) + offset
        function = 'f' in tail.split() and bool(int(section['flags'], 16) & 4) and offset < section['file_size']
        index.append({'address':'0x%08X' % va, 'name':name, 'section':section['name'],
                      'function':function, 'object':tail, 'pe_address':'0x%08X' % pe_va})
    if not index:
        raise ValueError('MAP contains no usable resident symbols')
    seeds = sorted({s['address'] for s in index if s['function']})
    evidence = {'status':'structurally_concordant', 'map_sha256':hashlib.sha256(raw_map).hexdigest(),
                'xbe_sha256':xbe['sha256'], 'pe_timestamp':xbe['pe_timestamp'],
                'entry_point':xbe['entry_point'], 'matched_segments':len(mappings),
                'symbols':len(index), 'function_entries':len(seeds), 'skipped_nonresident_symbols':skipped,
                'mapping':'XBE section VA + MAP segment offset; PE Rva+Base is diagnostic only',
                'limits':'Structural concordance, not cryptographic proof of original linker inputs',
                'segments':[{'segment':n, 'name':s['name'], 'address':s['virtual_address'],
                             'bytes':s['virtual_size']} for n, s in mappings.items()]}
    return evidence, index, [{'start':s, 'source':'user final.map; structurally validated against XBE'} for s in seeds]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('xbe', type=Path)
    parser.add_argument('map', type=Path)
    parser.add_argument('--output', type=Path, default=Path('generated/symbols'))
    args = parser.parse_args()
    evidence, index, seeds = index_map(args.map.read_bytes(), inspect(args.xbe.read_bytes()))
    args.output.mkdir(parents=True, exist_ok=True)
    for name, data in [('report.json', evidence), ('index.json', index), ('seeds.json', seeds)]:
        (args.output / name).write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
