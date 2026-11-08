#!/usr/bin/env python3
"""Prepare private launcher artwork from the user's game and local HD pack.

No artwork is embedded in sources or the launcher bundle. Outputs stay private.
"""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from loadvars_fix import verify_xbe
from texture_mod import pack_index
from texture_profiles import verify_local_pack

ROOT = Path(__file__).resolve().parents[1]
MISTS = {'mist-1.png': 0x6C06564AC4CEBAD6, 'mist-2.png': 0x810F83CBE0ABB91D}


def remove_black_matte(rgba):
    """Convert the title's opaque black matte to coverage, keeping its glow.

    Recomposition over black preserves each source channel within one value;
    unpremultiplication avoids dark fringes on the menu's violet backdrop.
    """
    if len(rgba) % 4:
        raise ValueError('Incomplete RGBA pixels')
    out = bytearray(len(rgba))
    for i in range(0, len(rgba), 4):
        r, g, b, alpha = rgba[i:i + 4]
        coverage = max(r, g, b)
        if coverage and alpha:
            out[i:i + 4] = bytes((round(r * 255 / coverage), round(g * 255 / coverage),
                                  round(b * 255 / coverage), round(coverage * alpha / 255)))
    return bytes(out)


def title_texture(data):
    """Read the named BC1 image in this title's MULTITEX container.

    Container offsets are read from the file table, never guest addresses.
    Reject unreviewed layouts rather than guessing the compression or stride.
    """
    if len(data) < 36 or data[:8] != b'MULTITEX':
        raise ValueError('Expected a MULTITEX title file')
    count = struct.unpack_from('<I', data, 20)[0]
    tag, stride = struct.unpack_from('<II', data, 28)
    if tag != 24 or stride != 128 or not 1 <= count <= 64:
        raise ValueError('Unsupported MULTITEX table')
    table_end = 36 + count * stride
    if table_end > len(data):
        raise ValueError('Truncated MULTITEX table')
    matches = []
    for i in range(count):
        record = 36 + i * stride
        name = data[record + 24:record + 56].split(b'\0', 1)[0]
        if name != b'Title_Buffy':
            continue
        width, height = struct.unpack_from('<II', data, record + 88)
        levels = struct.unpack_from('<I', data, record + 108)[0]
        marker, offset, size = struct.unpack_from('<III', data, record + 116)
        if ((width, height, levels, marker) != (256, 256, 8, 1)
                or offset < table_end or offset + size > len(data)):
            raise ValueError('Unsupported or truncated title texture')
        cursor = offset
        first = None
        for level in range(levels):
            w, h = max(1, width >> level), max(1, height >> level)
            expected = ((w + 3) // 4) * ((h + 3) // 4) * 8
            if cursor + 4 > offset + size:
                raise ValueError('Truncated title mip header')
            extent = struct.unpack_from('<I', data, cursor)[0]
            if extent != expected or cursor + 4 + extent > offset + size:
                raise ValueError('Invalid title mip extent')
            if level == 0:
                first = data[cursor + 4:cursor + 4 + extent]
            cursor += 4 + extent
        if cursor != offset + size:
            raise ValueError('Unexpected title mip tail')
        matches.append((width, height, first))
    if len(matches) != 1:
        raise ValueError('Expected one Title_Buffy texture')
    return matches[0]


def prepare(root=ROOT):
    from PIL import Image
    root = Path(root)
    title = json.loads((root / 'config/title.json').read_text())
    verify_xbe(root / 'private/game/Default.xbe', title)
    source = root / 'private/game/media/Title.mtx'
    width, height, raw = title_texture(source.read_bytes())
    (root / 'build').mkdir(exist_ok=True)
    decoder = root / 'build/launcher-texture-decode'
    subprocess.run(['clang', '-std=c11', '-O2', '-ffunction-sections', '-fdata-sections',
                    '-Wl,-dead_strip', '-I', str(root / 'vendor/xboxrecomp/src/kernel'),
                    '-I', str(root / 'vendor/xboxrecomp/src/d3d'), str(root / 'tools/texture_decode.c'),
                    str(root / 'vendor/xboxrecomp/src/kernel/nv2a_backend_common.c'),
                    '-lm', '-o', str(decoder)], check=True)
    out = root / 'private/launcher'
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root / 'build') as folder:
        incoming, pixels = Path(folder) / 'title.bc1', Path(folder) / 'title.bgra'
        incoming.write_bytes(raw)
        subprocess.run([str(decoder), '12', str(width), str(height), '0', '1',
                        str(incoming), str(pixels)], check=True, capture_output=True)
        image = Image.frombytes('RGBA', (width, height), pixels.read_bytes(), 'raw', 'BGRA')
        Image.frombytes('RGBA', image.size, remove_black_matte(image.tobytes())).save(out / 'logo.png')
    proof = {'xbe_sha256': title['xbe_sha256'], 'title_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
             'logo': 'Title_Buffy, original BC1 base level; no generated logo or AI lettering',
             'logo_alpha': 'black matte converted to max-RGB coverage with unpremultiplied RGB',
             'mists': []}
    pack = root / 'private/textures/campaign-ui-hd.xrtp'
    if pack.is_file():
        verify_local_pack(pack, title['xbe_sha256'])
        with pack.open('rb') as stream:
            _, _, entries = pack_index(stream)
            for name, key in MISTS.items():
                if key not in entries:
                    continue
                w, h, _, flags, offset = entries[key]
                if flags & 0x10:
                    raise ValueError('Launcher expects uncompressed HD mist texels')
                stream.seek(offset)
                raw = stream.read(w * h * 4)
                if len(raw) != w * h * 4:
                    raise ValueError('Truncated HD mist')
                Image.frombytes('RGBA', (w, h), raw, 'raw', 'BGRA').save(out / name)
                proof['mists'].append({'file': name, 'texture_hash': f'{key:016X}', 'dimensions': [w, h]})
    proof['outputs'] = {name: hashlib.sha256((out / name).read_bytes()).hexdigest()
                        for name in ['logo.png'] + [e['file'] for e in proof['mists']]}
    (out / 'provenance.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(f'Private launcher artwork prepared: {out}')


if __name__ == '__main__':
    prepare()
