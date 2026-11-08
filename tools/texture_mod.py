#!/usr/bin/env python3
"""Build a local art/skin XRTP from replacements for known guest textures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile

from loadvars_fix import verify_xbe
from texture_pilot import write_pack
from texture_profiles import texture_extent, verify_local_pack

ROOT = Path(__file__).resolve().parents[1]
HEADER = struct.Struct('<4sIIIQII')
ENTRY = struct.Struct('<QIIIIQ')


def pack_index(stream):
    _, _, count, scale, offset, text_scale, _ = HEADER.unpack(stream.read(HEADER.size))
    stream.seek(offset)
    entries = {row[0]: row[1:] for row in ENTRY.iter_unpack(stream.read(count * ENTRY.size))}
    return scale, text_scale, entries


def compose(base, art, output, kinds=(0,)):
    """Copy verified payloads by blocks, allowing only the selected overlay kinds."""
    with base.open('rb') as source, art.open('rb') as overlay, output.open('wb') as target:
        scale, text_scale, existing = pack_index(source)
        _, _, replacements = pack_index(overlay)
        for key, (w, h, _, flags, _) in replacements.items():
            kind = flags & 3
            if kind not in kinds:
                raise ValueError(f'Unexpected overlay kind: {key:016X}')
            if key in existing:
                old_w, old_h, _, old_flags, _ = existing[key]
                if old_flags & 3 != kind or old_w * h != old_h * w:
                    raise ValueError(f'Artwork would overwrite a different kind or aspect: {key:016X}')
        keys = sorted(existing.keys() | replacements.keys())
        target.write(HEADER.pack(b'XRTP', 2, len(keys), scale, HEADER.size, text_scale, 0))
        offset = HEADER.size + ENTRY.size * len(keys)
        payloads = []
        for key in keys:
            stream, entry = (overlay, replacements[key]) if key in replacements else (source, existing[key])
            w, h, levels, flags, start = entry
            size = texture_extent(w, h, levels, flags)
            target.write(ENTRY.pack(key, w, h, levels, flags, offset))
            payloads.append((stream, start, size))
            offset += size
        for stream, start, remaining in payloads:
            stream.seek(start)
            while remaining:
                block = stream.read(min(remaining, 1024 * 1024))
                if not block:
                    raise ValueError('Truncated texture during composition')
                target.write(block)
                remaining -= len(block)
    return len(keys)


def build(recipe, inventory, output, xbe_sha256, base=None):
    recipe, output = Path(recipe), Path(output)
    if output.suffix != '.xrtp':
        raise ValueError('Expected a .xrtp output path')
    source = json.loads(Path(inventory).read_text())
    if source['xbe_sha256'] != xbe_sha256:
        raise ValueError('Inventory built for a different XBE')
    plan = json.loads(recipe.read_text())
    recipe_dir = recipe.resolve().parent
    if base is not None:
        base = Path(base).resolve()
        if base == output.resolve():
            raise ValueError('Choose a separate output to preserve the base pack')
        verify_local_pack(base, xbe_sha256)
    rows = []
    for row in plan['entries']:
        key = int(row['hash'], 16)
        matches = [e for e in source['entries'] if e['hash'] == key and not e.get('ambiguous')]
        if len(matches) != 1:
            raise ValueError(f'Unknown or ambiguous guest texture: {key:016X}')
        ref = matches[0]
        image = (recipe_dir / row['png']).resolve()
        if not image.is_relative_to(recipe_dir) or image.suffix.lower() != '.png':
            raise ValueError('Use a PNG inside the recipe directory')
        rows.append(dict(hash=key, width=ref['width'], height=ref['height'], kind='art', image=image))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as folder:
        candidate = Path(folder) / 'candidate.xrtp'
        if base is None:
            count = write_pack(rows, candidate, plan['scale'])
        else:
            art = Path(folder) / 'art.xrtp'
            write_pack(rows, art, plan['scale'])
            count = compose(base, art, candidate)
        proof = dict(xbe_sha256=xbe_sha256, entries=count)
        digest = hashlib.sha256()
        with candidate.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        proof['pack_sha256'] = digest.hexdigest()
        sidecar = candidate.with_suffix('.json')
        sidecar.write_text(json.dumps(proof, indent=2) + '\n')
        verify_local_pack(candidate, xbe_sha256)
        os.replace(candidate, output)
        os.replace(sidecar, output.with_suffix('.json'))
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recipe', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--inventory', type=Path, default=ROOT/'artifacts/texture-batch/inventory.json')
    parser.add_argument('--base', type=Path, help='composer le mod au-dessus de ce pack local')
    args = parser.parse_args()
    title = json.loads((ROOT/'config/title.json').read_text())
    verify_xbe(ROOT/'private/game/Default.xbe', title)
    count = build(args.recipe, args.inventory, args.output, title['xbe_sha256'], args.base)
    print(f'{count} texture(s) → {args.output}')


if __name__ == '__main__':
    main()
