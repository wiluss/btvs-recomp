#!/usr/bin/env python3
"""Build a local campaign pack with the reviewed HUD and current HD text."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from loadvars_fix import verify_xbe
from text_pack import compose as compose_text
from texture_mod import compose
from texture_pilot import decode, upscale, write_pack
from texture_profiles import verify_local_pack
from texture_snapshot_lldb import XBE_SHA256, dxt_extent

ROOT = Path(__file__).resolve().parents[1]


def processing_plan(recipe, decoded_rows):
    """Explicit routing only: no fonts, inferred masks or unlisted textures."""
    if type(recipe['scale']) is not int or recipe['scale'] != 4 or recipe['xbe_sha256'] != XBE_SHA256:
        raise ValueError('Unreviewed HUD scale or XBE')

    def keys(field):
        values = recipe[field]
        if not isinstance(values, list) or any(
                not isinstance(v, str) or not re.fullmatch('[0-9A-Fa-f]{16}', v) for v in values):
            raise ValueError('Invalid HUD identities')
        result = {int(v, 16) for v in values}
        if len(result) != len(values) or 0 in result:
            raise ValueError('Duplicate or zero HUD identity')
        return result

    wanted, ai, masks = (keys(field) for field in ('hashes', 'ai_hashes', 'mask_hashes'))
    if not 1 <= len(wanted) <= 64 or ai & masks or ai | masks != wanted:
        raise ValueError('HUD processing policy must cover every selected identity once')
    if len(decoded_rows) != len(wanted) or {r['hash'] for r in decoded_rows} != wanted:
        raise ValueError('Decoded HUD coverage differs from selection')
    return dict(xbe_sha256=recipe['xbe_sha256'], entries=[
        dict(hash=f"{row['hash']:016X}", width=row['width'], height=row['height'],
             kind='art', method='ai' if row['hash'] in ai else 'lanczos',
             border='clamp', label=f"HUD {row['hash']:016X}") for row in decoded_rows])


def capture_hud(recipe, inventory, archives, folder):
    if recipe['xbe_sha256'] != XBE_SHA256 or inventory['xbe_sha256'] != XBE_SHA256:
        raise ValueError('HUD recipe or inventory for a different XBE')
    wanted = {int(key, 16) for key in recipe['hashes']}
    rows = [r for r in inventory['entries'] if r['hash'] in wanted]
    if len(rows) != len(wanted) or {row['hash'] for row in rows} != wanted:
        raise ValueError('Missing or ambiguous HUD textures')
    manifest = []
    for row in rows:
        if (row.get('ambiguous') or not re.fullmatch(r'res_[\w-]+\.pak', row['pak'])
                or row['path'] != r'interfc\hud.mtx'):
            raise ValueError('Unreviewed HUD source')
        levels = row['levels']
        expected = dxt_extent(row['color'], row['width'], row['height'], len(levels))
        if sum(n for _, n in levels) != expected or row['offset'] < 0 or any(
                offset < 0 or n <= 0 for offset, n in levels):
            raise ValueError('Invalid HUD source extent')
        with (archives / row['pak']).open('rb') as stream:
            chunks = []
            for offset, size in levels:
                stream.seek(row['offset'] + offset)
                chunks.append(stream.read(size))
        raw = b''.join(chunks)
        if hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('HUD source changed')
        name = f"{row['hash']:016X}.bin"
        (folder / name).write_bytes(raw)
        manifest.append(dict(row, file=name, pitch=0, levels=len(row['levels'])))
    (folder / 'manifest.json').write_text(json.dumps({'xbe_sha256': XBE_SHA256, 'entries': manifest}))


def build(root, inventory, base, text, output):
    verify_xbe(root/'private/game/Default.xbe', json.loads((root/'config/title.json').read_text()))
    if output.suffix != '.xrtp' or output.resolve() in (base.resolve(), text.resolve()):
        raise ValueError('Use a separate .xrtp output')
    verify_local_pack(base, XBE_SHA256)
    verify_local_pack(text, XBE_SHA256)
    font_recipe = hashlib.sha256((root/'config/font-hd.json').read_bytes()).hexdigest()
    if json.loads(text.with_suffix('.json').read_text())['font_recipe_sha256'] != font_recipe:
        raise ValueError('The HD text pack needs to be regenerated')
    recipe = json.loads((root/'config/hud-hd.json').read_text())
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        work = Path(temp)
        decoded = work/'decoded'
        capture_hud(recipe, json.loads(inventory.read_text()), root/'private/game/pak', work)
        decode(work, decoded)
        decoded_rows = json.loads((decoded/'manifest.json').read_text())['entries']
        plan = work/'selection.json'
        plan.write_text(json.dumps(processing_plan(recipe, decoded_rows), indent=2)+'\n')
        processed = work/'processed'
        upscale(plan, decoded, processed,
                root/'private/tools/esrgan/realesrgan-ncnn-vulkan-v0.2.0-macos/realesrgan-ncnn-vulkan',
                root/'private/tools/esrgan/official-20220424/models',
                root/'config/texture-upscaler.json')
        hud = work/'hud.xrtp'
        rows = []
        scale = recipe['scale']
        for row in decoded_rows:
            path = processed/f"{row['hash']:016X}-{scale}x.png"
            rows.append(dict(row, kind='art', image=path, mipmaps=False))
        write_pack(rows, hud, scale)
        overlay, candidate = work/'overlay.xrtp', work/'candidate.xrtp'
        compose_text(hud, text, overlay)
        count = compose(base, overlay, candidate, kinds=(0, 1, 2))
        digest = hashlib.sha256()
        with candidate.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        processing = json.loads((processed/'provenance.json').read_text())
        processing.pop('font_hud', None)  # Pilot-specific note does not describe this HUD selection.
        processing['methods'] = {r['hash']:r['method'] for r in json.loads(plan.read_text())['entries']}
        sidecar = candidate.with_suffix('.json')
        sidecar.write_text(json.dumps(dict(xbe_sha256=XBE_SHA256, pack_sha256=digest.hexdigest(),
                                          entries=count, hud=len(rows), font_recipe_sha256=font_recipe,
                                          hud_recipe_sha256=hashlib.sha256((root/'config/hud-hd.json').read_bytes()).hexdigest(),
                                          hud_processing=processing),
                                      indent=2) + '\n')
        verify_local_pack(candidate, XBE_SHA256)
        os.replace(candidate, output)
        os.replace(sidecar, output.with_suffix('.json'))
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=ROOT/'artifacts/texture-full/buffy-full-2x.xrtp')
    parser.add_argument('--inventory', type=Path, default=ROOT/'artifacts/texture-batch/inventory.json')
    parser.add_argument('--text', type=Path, default=ROOT/'private/textures/font-hd.xrtp')
    parser.add_argument('--output', type=Path, default=ROOT/'private/textures/campaign-ui-hd.xrtp')
    args = parser.parse_args()
    print(f'{build(ROOT, args.inventory, args.base, args.text, args.output)} textures')


if __name__ == '__main__':
    main()
