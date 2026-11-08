"""Explicit local pilot presets, checked before launch or preference writes."""
import hashlib
import json
from pathlib import Path
import struct
from text_pack import additional_recipes, word_recipe

from texture_snapshot_lldb import XBE_SHA256

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {'original':0, 'pilot2x':2, 'pilot4x':4, 'campaign2x':2}


def texture_extent(w, h, levels, flags):
    if flags & 0x10:
        return sum(((max(1, w >> i) + 3) // 4) * ((max(1, h >> i) + 3) // 4) * 16
                   for i in range(levels))
    return sum(max(1, w >> i) * max(1, h >> i) * 4 for i in range(levels))


def verify_local_pack(path, xbe_sha256):
    """Validate a user-supplied XRTP without retaining any texels in memory."""
    path = Path(path)
    if path.suffix != '.xrtp':
        raise ValueError('Expected a .xrtp texture pack')
    proof = json.loads(path.with_suffix('.json').read_text())
    if proof['xbe_sha256'] != xbe_sha256:
        raise ValueError('Pack built for a different XBE')
    if type(proof['entries']) is not int:
        raise ValueError('Invalid XRTP manifest entry count')
    with path.open('rb') as stream:
        raw = stream.read(32)
        if len(raw) != 32:
            raise ValueError('Truncated XRTP header')
        magic, version, count, _, index, _, reserved = struct.unpack('<4sIIIQII', raw)
        size = stream.seek(0, 2)
        end_index = index + 32 * count
        if (magic != b'XRTP' or version != 2 or reserved or not 1 <= count <= 1 << 20
                or count != proof['entries'] or index < 32 or end_index > size):
            raise ValueError('Invalid XRTP header')
        stream.seek(index)
        previous = 0
        for _ in range(count):
            key, w, h, levels, flags, offset = struct.unpack('<QIIIIQ', stream.read(32))
            if (key <= previous or not 1 <= w <= 16384 or not 1 <= h <= 16384
                    or not 1 <= levels <= max(w, h).bit_length() or flags & ~0x13 or flags & 3 == 3):
                raise ValueError('Invalid XRTP entry')
            if flags & 0x10 and (w % 4 or h % 4):
                raise ValueError('Invalid BC3 texture dimensions')
            extent = texture_extent(w, h, levels, flags)
            if offset < end_index or offset + extent > size:
                raise ValueError('Invalid XRTP texture extent')
            previous = key
        stream.seek(0)
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != proof['pack_sha256']:
        raise ValueError('Texture pack was changed')
    return count


def pack_path(name, root=ROOT, text='auto'):
    if name not in PROFILES:
        raise ValueError('Unknown texture preset')
    if text not in ('auto','original','hd'):raise ValueError('Unknown text preset')
    if name == 'campaign2x':
        return Path(root)/'private/textures/campaign-ui-hd.xrtp'
    if text=='hd':return Path(root)/'private/textures'/(name+'-text-hd.xrtp')
    scale = PROFILES[name]
    return Path(root)/'private/textures'/('pilot-%dx.xrtp'%scale) if scale else None


def verify_profile(name, root=ROOT, text='auto'):
    if name == 'campaign2x':
        path = pack_path(name, root, text)
        verify_local_pack(path, XBE_SHA256)
        proof = json.loads(path.with_suffix('.json').read_text())
        recipe = Path(root)/'config/hud-hd.json'
        if proof.get('hud_recipe_sha256') != hashlib.sha256(recipe.read_bytes()).hexdigest():
            raise ValueError('The campaign pack needs the current HD HUD')
        if text != 'original':
            recipe = Path(root)/'config/font-hd.json'
            proof = json.loads(path.with_suffix('.json').read_text())
            if proof['font_recipe_sha256'] != hashlib.sha256(recipe.read_bytes()).hexdigest():
                raise ValueError('The campaign pack needs the current HD text')
        return
    if text=='hd':
        verify_profile(name,root)
        root=Path(root);path=pack_path(name,root,text);proof=json.loads(path.with_suffix('.json').read_text())
        base=pack_path(name,root);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        recipe=root/'config/font-hd.json';font_pack=root/'private/textures/font-hd.xrtp'
        recipe_data = json.loads(recipe.read_text())
        extra = additional_recipes(root, recipe_data)
        words = word_recipe(root, recipe_data)
        if (proof['xbe_sha256']!=XBE_SHA256 or proof['base_profile']!=name
            or proof['base_pack_sha256']!=(sha(base) if base else None)
            or proof['font_recipe_sha256']!=sha(recipe) or proof['font_pack_sha256']!=sha(font_pack)
            or proof['pack_sha256']!=sha(path)):
            raise ValueError('HD text composition differs')
        raw=path.read_bytes()
        if len(raw)<32:raise ValueError('Truncated HD text pack')
        header=struct.unpack_from('<4sIIIQII',raw)
        expected_count=(len(json.loads((root/'config/texture-pilot.json').read_text())['entries']) if base else 1)+len(extra)
        if words:
            expected_count += len(words['entries'])
        if header!=(b'XRTP',2,expected_count,PROFILES[name] or 8,32,8,0):
            raise ValueError('HD text header differs')
        return
    path=pack_path(name,root,text)
    if path is None:return
    root=Path(root);proof=json.loads(path.with_suffix('.json').read_text())
    plan=root/'config/texture-pilot.json';lock=root/'config/texture-upscaler.json'
    if (proof['xbe_sha256']!=XBE_SHA256 or proof['scale']!=PROFILES[name]
        or proof['selection_sha256']!=hashlib.sha256(plan.read_bytes()).hexdigest()
        or proof['upscale']['upscaler_lock_sha256']!=hashlib.sha256(lock.read_bytes()).hexdigest()):
        raise ValueError('Texture preset provenance differs')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=proof['pack_sha256']:
        raise ValueError('Texture pack was changed')
    if len(raw)<32:
        raise ValueError('Truncated texture pack')
    magic,version,count,scale,index,text_scale,reserved=struct.unpack_from('<4sIIIQII',raw)
    if ((magic,version,scale,index,text_scale,reserved)!=(b'XRTP',2,PROFILES[name],32,PROFILES[name],0)
        or count!=proof['entries'] or count!=len(json.loads(plan.read_text())['entries'])):
        raise ValueError('Texture preset header differs')
