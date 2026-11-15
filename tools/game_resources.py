#!/usr/bin/env python3
"""Read-only inventory of the supported game's resource packs.

Format evidence: the verified user XBE's TResourceManager::ResourceDirectory_Archive,
TStrTable::Serialize, TPackLockHeader serializer and TArchiveReadFile primitives.
No payloads or game assets are exported. See docs/BRINGUP.md.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
import mmap
from pathlib import Path, PureWindowsPath
import struct
import re

VERSION = 0x052014
MAX_PACK_BYTES = 512 * 1024 * 1024
MAX_STRINGS = 65536
MAX_ITEMS = 65536
MAX_RECORDS = 65536
MAX_STRING_BYTES = 4096
MAX_POOL_BYTES = 16 * 1024 * 1024


class ResourceError(ValueError):
    """Malformed or unsupported game resource archive."""


class _Reader:
    def __init__(self, data):
        self.data = data
        self.position = 0

    def take(self, count):
        if count < 0 or count > len(self.data) - self.position:
            raise ResourceError('Truncated resource archive')
        start = self.position
        self.position += count
        return self.data[start:self.position]

    def skip(self, count):
        if count < 0 or count > len(self.data) - self.position:
            raise ResourceError('Truncated resource archive')
        self.position += count

    def u32(self):
        return struct.unpack('<I', self.take(4))[0]

    def u16(self):
        return struct.unpack('<H', self.take(2))[0]

    def count(self, maximum=MAX_ITEMS):
        value = self.u32()
        if value > maximum:
            raise ResourceError('Resource array exceeds its limit')
        return value

    def array_count(self, maximum=MAX_ITEMS):
        capacity, count = self.count(maximum), self.count(maximum)
        if count > capacity:
            raise ResourceError('Resource array count exceeds capacity')
        return count

    def string(self):
        raw = self.take(self.count(MAX_STRING_BYTES))
        if b'\0' in raw or any(c < 32 or c > 126 for c in raw):
            raise ResourceError('Invalid archive string')
        return raw.decode('ascii')


def _directory(reader, size_fields=None, layout=None):
    """Advance over serialized metadata, validating lengths before reading."""
    allocation, used, pool_size = (reader.u32() for _ in range(3))
    if not (used <= allocation <= MAX_PACK_BYTES and pool_size <= min(allocation, MAX_POOL_BYTES)):
        raise ResourceError('Invalid string pool bounds')
    count = reader.array_count(MAX_STRINGS)
    offsets = [reader.u32() for _ in range(count)]
    pool = reader.take(pool_size)
    if layout is not None:
        layout['string_table_end'] = reader.position
    for offset in offsets:
        if offset >= pool_size or pool.find(b'\0', offset, offset + MAX_STRING_BYTES + 1) < 0:
            raise ResourceError('Invalid string pool offset')
    hash_count = reader.array_count()
    # Values are string IDs. They may reference duplicated dictionary strings.
    for _ in range(hash_count):
        value = reader.u16()
        if value != 0xFFFF and value >= count:
            raise ResourceError('Invalid resource dictionary reference')
    capacity_offset = reader.position
    item_capacity = reader.count()
    entry_capacity = reader.count()
    directory_count_offset = reader.position
    directory_count = reader.count()
    directory_offset = reader.position
    reader.skip(directory_count * 36)
    if layout is not None:
        layout.update(item_capacity_offset=capacity_offset,
                      directory_count_offset=directory_count_offset,
                      directory_offset=directory_offset,
                      directory_count=directory_count,
                      directory_end=reader.position)
    seen = set()
    entry_total = item_total = 0
    while True:
        kind = reader.u32()
        if kind == 0xFFFFFFFF:
            return
        if kind >= 19 or kind in seen:
            raise ResourceError('Invalid or duplicate resource type')
        seen.add(kind)
        reader.string()  # extension
        for _ in range(reader.array_count()):
            reader.string()  # search roots
        for _ in range(reader.array_count()):
            entry_total += 1
            if entry_total > entry_capacity:
                raise ResourceError('Resource entry capacity exceeded')
            if reader.u16() >= count or reader.u16() >= count:
                raise ResourceError('Invalid resource entry string')
            item_count_offset = reader.position
            items = reader.count()
            item_total += items
            if item_total > item_capacity:
                raise ResourceError('Resource item capacity exceeded')
            # File directory ID, dictionary ID, number/first resource, file size.
            for _ in range(items):
                record_offset = reader.position
                directory, string = reader.u16(), reader.u16()
                if directory >= directory_count or string >= count:
                    raise ResourceError('Invalid resource item reference')
                reader.skip(4)  # resource count and first dictionary resource
                size_offset = reader.position
                file_size = reader.u32()
                if size_fields is not None:
                    at = offsets[string]
                    end = pool.find(b'\0', at, at + MAX_STRING_BYTES + 1)
                    size_fields.append({'kind': kind, 'name': pool[at:end].decode('ascii'),
                                        'directory': directory, 'offset': size_offset, 'size': file_size,
                                        'count_offset': item_count_offset, 'record_offset': record_offset})


def _relative_path(value):
    path = PureWindowsPath(value)
    if (not value or path.drive or path.root or ':' in value
            or any(part in ('', '.', '..') for part in value.split('\\'))
            or '/' in value):
        raise ResourceError('Unsafe resource path')
    return str(path).lower()


@dataclass(frozen=True)
class ResourceRecord:
    name: str
    resource: str
    header_offset: int
    data_offset: int
    data_size: int
    original_size: int
    manual: bool
    flag: bool


def read_records(path: Path) -> tuple[ResourceRecord, ...]:
    """Inventory one pack without loading its model/texture payloads into RAM."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ResourceError('Resource pack must be a regular, non-symlink file')
    with path.open('rb') as stream:
        size = stream.seek(0, 2)
        if not 4 <= size <= MAX_PACK_BYTES:
            raise ResourceError('Resource pack size exceeds supported bounds')
        stream.seek(0)
        with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
            reader = _Reader(data)
            if reader.u32() != VERSION:
                raise ResourceError('Unsupported resource archive version')
            _directory(reader)
            records = []
            while True:
                start = reader.position
                active, offset, span, original_size, manual = (
                    reader.u32() for _ in range(5))
                name, resource, flag = reader.string(), reader.string(), reader.u32()
                if active not in (0, 1) or manual not in (0, 1) or flag not in (0, 1):
                    raise ResourceError('Invalid resource header boolean')
                if not active:
                    # The inactive header has unused offset/span fields. It may
                    # have a 128-byte opaque trailer; neither is a resource.
                    if (original_size or manual or name or resource
                            or flag or len(data) - reader.position not in (0, 128)):
                        raise ResourceError('Invalid archive terminator')
                    return tuple(records)
                if offset != start or not reader.position <= start + span <= len(data):
                    raise ResourceError('Invalid resource payload span')
                if len(records) >= MAX_RECORDS:
                    raise ResourceError('Too many resource payloads')
                records.append(ResourceRecord(
                    _relative_path(name), resource.lower(), start, reader.position,
                    start + span - reader.position, original_size, bool(manual), bool(flag)))
                reader.position = start + span


def directory_layout(data):
    """Locate reviewed per-file allocation sizes without exposing payloads."""
    reader = _Reader(data)
    if reader.u32() != VERSION:
        raise ResourceError('Unsupported resource archive version')
    fields = []
    layout = {}
    _directory(reader, fields, layout)
    layout.update(fields=fields, payload_offset=reader.position)
    return layout


def directory_size_fields(data):
    return directory_layout(data)['fields']


STOCK_OUTFITS = (
    ('bronze', 'Bronze', 'buffybronze'),
    ('workout', 'Workout', 'buffyworkout'),
    ('cheerleader', 'Cheerleader', 'buffycheer'),
    ('slayer', 'Slayer', 'buffyslayer'),
    ('dark-slayer', 'Dark Slayer', 'darkslayer'),
)


def stock_inventory(game: Path, title: Path) -> dict:
    # The catalog is address-free, but still bound to the supported installation.
    if __package__:
        from .loadvars_fix import verify_xbe
    else:
        from loadvars_fix import verify_xbe
    verify_xbe(game / 'Default.xbe', json.loads(title.read_text()))
    found = {key: [] for key, _, _ in STOCK_OUTFITS}
    packs = sorted((game / 'pak').glob('*.pak'))
    if not packs or len(packs) > 256:
        raise ResourceError('Missing or excessive resource packs')
    for pack in packs:
        records = read_records(pack)
        keys = {(row.name, row.resource) for row in records}
        for key, _, stem in STOCK_OUTFITS:
            mesh = f'meshes\\chars\\slayer\\{stem}.msh'
            matches = [row for row in records if row.name == mesh and row.resource == 'base']
            if matches:
                found[key].append({
                    'pack': pack.name, 'model': asdict(matches[0]),
                    'materials': [asdict(row) for row in records
                                  if row.name == ('meshes\\chars\\slayer\\'
                                      + ('buffysport' if key == 'workout' else stem) + '.mtx')],
                    'animation_table': (f'meshes\\chars\\slayer\\{stem}.ban', '') in keys,
                })
    return {'schema': 1, 'runtime_validated': False,
            'outfits': [{'id': key, 'name': label, 'sources': found[key]}
                        for key, label, _ in STOCK_OUTFITS]}


def audit_inventory(game: Path, title: Path) -> dict:
    """Report actual payloads and variants, without calling them unused content."""
    if __package__:
        from .loadvars_fix import verify_xbe
    else:
        from loadvars_fix import verify_xbe
    game,title=Path(game),Path(title)
    verify_xbe(game/'Default.xbe',json.loads(title.read_text()))
    packs=sorted((game/'pak').glob('*.pak'))
    if not packs or len(packs)>256:raise ResourceError('Missing or excessive resource packs')
    types=Counter();models={};variants={};named_candidates={}
    for pack in packs:
        with pack.open('rb') as stream:
            for row in read_records(pack):
                extension=row.name.rsplit('.',1)[-1];types[extension]+=1
                if extension=='msh' and row.resource=='base':
                    models.setdefault(row.name,[]).append(pack.name)
                if re.search(r'(^|[\\_.-])(unused|test|prototype|dummy|temp)([\\_.-]|$)',row.name):
                    named_candidates.setdefault(row.name,[]).append(pack.name)
                if (row.name.startswith(('meshes\\chars\\slayer\\','meshes\\chars\\guislayer\\'))
                        and extension in ('msh','mtx')):
                    stream.seek(row.data_offset)
                    digest=hashlib.sha256(stream.read(row.data_size)).hexdigest()
                    variants.setdefault(row.name+'::'+row.resource,{}).setdefault(digest,[]).append(pack.name)
    return {'schema':1,'pack_count':len(packs),'payloads_by_type':dict(types),
            'unique_base_models':len(models),
            'character_models':{name:sources for name,sources in sorted(models.items())
                                if name.startswith('meshes\\chars\\')},
            'buffy_payload_variants':dict(sorted(variants.items())),
            'name_only_candidates':named_candidates,'confirmed_unused':[],
            'limits':'Payload presence and names do not establish unused status, rig compatibility or playability.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, default=Path('private/game'))
    parser.add_argument('--title', type=Path, default=Path('config/title.json'))
    parser.add_argument('--audit', action='store_true', help='inventory actual models/material variants and candidate names')
    args = parser.parse_args()
    try:
        inventory=audit_inventory if args.audit else stock_inventory
        print(json.dumps(inventory(args.game, args.title), indent=2))
    except (ResourceError, OSError, ValueError) as error:
        parser.exit(1, f'Resource inventory failed: {error}\n')


if __name__ == '__main__':
    main()
