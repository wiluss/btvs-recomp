"""Compile private native wardrobe resources from a verified user installation.

No assets are embedded in this module. The MBF layout is bound to its source
hash; only copied output is changed. Runtime hooks must be enabled separately.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import struct

if __package__:
    from .game_resources import read_records, stock_inventory, ResourceError, directory_size_fields, directory_layout
else:
    from game_resources import read_records, stock_inventory, ResourceError, directory_size_fields, directory_layout

OUTFIT_IDS = (1, 2, 3, 0x83, 0x200, 0x201)
MENU_ID = 16
ENTRY_ID = 0x200
BACK_ID = 0x202
# Filled from the user's supported original MBF, not a redistributed asset.
MBF_SHA256 = 'bc83350230cc005d2e006b63c597482e164b082ca4b8f3be782173d97261d72c'


def _u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def _button(template, name, ident, tab, text, y):
    result = bytearray(template.replace(b'IDC_EXTRAS\0', name.encode() + b'\0'))
    at = result.index(name.encode() + b'\0') + len(name) + 1
    struct.pack_into('<II', result, at, ident, tab)
    at = result.index(b'Offset\0') + 11
    struct.pack_into('<ii', result, at, 69, y)
    at = result.index(b'Extent\0') + 11
    struct.pack_into('<ii', result, at, 225, 35)
    at = result.index(b'Text\0') + 9
    struct.pack_into('<I', result, at, text)
    return bytes(result)


def _wardrobe_label(template,name,ident,text,y,font):
    """Native static text, using the original control/property serializers."""
    result=bytearray(_button(template,name,ident,0,text,y))
    result=result.replace(b'TTextButton\0',b'TStaticText\0',1)
    active=b'Active Font\0'+struct.pack('<II',3,1)
    if result.count(active)!=1:raise ResourceError('Native font template differs')
    result=result.replace(active,b'',1).replace(b'Normal Font\0',b'Font\0',1)
    at=result.index(name.encode()+b'\0')+len(name)+1
    struct.pack_into('<I',result,at+8,7)
    at=result.index(b'Font\0')+9;struct.pack_into('<I',result,at,font)
    at=result.index(b'Extent\0')+11;struct.pack_into('<ii',result,at,285,35)
    return bytes(result)


def _pause_menu(data):
    """Add one native button to the hash-verified retail Pause layout."""
    if (not data.startswith(b'TMenuPause\0IDM_PAUSE\0')
            or _u32(data, 29) != 16 or len(data) != 3091):
        raise ResourceError('Native pause-menu layout differs')
    result = bytearray(data)
    template = data[261:490]
    if not template.startswith(b'TTextButton\0') or b'IDC_PAUSE_OPTIONS\0' not in template:
        raise ResourceError('Native pause-button template differs')
    import re
    for match in re.finditer(rb'IDC_[A-Z_]+\x00', result):
        at = match.end()
        tab = _u32(result, at + 4)
        if tab >= 2:
            struct.pack_into('<I', result, at + 4, tab + 1)
        y = {b'IDC_PAUSE_OPTIONS\0':154, b'IDC_PAUSE_QUIT\0':193}.get(match[0])
        if y is not None:
            struct.pack_into('<i', result, result.index(b'Offset\0', at) + 15, y)
    entry = bytearray(template.replace(b'IDC_PAUSE_OPTIONS\0', b'IDC_PAUSE_OUTFITS\0'))
    at = entry.index(b'IDC_PAUSE_OUTFITS\0') + len(b'IDC_PAUSE_OUTFITS\0')
    struct.pack_into('<II', entry, at, ENTRY_ID, 2)
    struct.pack_into('<I', entry, entry.index(b'Text\0') + 9, 95)
    struct.pack_into('<i', entry, entry.index(b'Offset\0') + 15, 115)
    result = result[:261] + entry + result[261:]
    struct.pack_into('<I', result, 29, 17)
    return bytes(result)


def menu_mbf(data, *, pause=False):
    if hashlib.sha256(data).hexdigest() != MBF_SHA256:
        raise ResourceError('Unreviewed native menu resource')
    string_start = data.index(b'IDS_STARTGAME\0') - 4
    count = _u32(data, string_start)
    if count != 94 or _u32(data, 843416) != 15:
        raise ResourceError('Native menu counts differ')
    end = string_start + 4
    for index in range(count):
        end = data.index(b'\0', end) + 1
        if _u32(data, end) != index + 1:
            raise ResourceError('Non-sequential native string handles')
        end = data.index(b'\0', end + 4) + 1
    labels = ['Outfits', 'Level outfit', 'Bronze', 'Workout', 'Cheerleader', 'Slayer', 'Dark Slayer', 'Back',
              'Wardrobe']
    additions = b''.join(b'IDS_RECOMP_OUTFIT_' + str(i).encode() + b'\0'
                         + struct.pack('<I', count + i + 1) + label.encode() + b'\0'
                         for i, label in enumerate(labels))
    index_start = 843420
    starts = [index_start + 8 * (i + 1) + _u32(data, index_start + 8 * i + 4)
              for i in range(15)]
    if starts[:2] != [843540, 845685]:
        raise ResourceError('Native main-menu directory differs')
    original = data[starts[0]:starts[1]]
    template = data[845111:845333]
    if not template.startswith(b'TTextButton\0') or _u32(original, 27) != 14:
        raise ResourceError('Native text-button template differs')
    entry = _button(template, 'IDC_OUTFITS', ENTRY_ID, 5, count + 1, 404)
    main = bytearray(original[:845333-starts[0]] + entry + original[845333-starts[0]:])
    struct.pack_into('<I', main, 27, 15)
    # Retain background/logo/native controller glyphs, replace only text buttons.
    background = bytearray(original[844243-starts[0]:845111-starts[0]])
    logo=background.index(b'IDC_BUFFY_LOGO\0')
    at=background.index(b'Offset\0',logo)+11
    struct.pack_into('<ii',background,at,54,20)
    at=background.index(b'Extent\0',logo)+11
    struct.pack_into('<ii',background,at,192,96)
    glyphs = original[845333-starts[0]:]
    buttons = b''.join(_button(template, f'IDC_OUTFIT_{i}', ident, i+1,
                               count+2+i, 185+35*i)
                       for i, ident in enumerate(OUTFIT_IDS))
    buttons += _button(template, 'IDC_OUTFIT_BACK', BACK_ID, 7, count+8, 430)
    heading=_wardrobe_label(template,'IDC_WARDROBE_TITLE',0x203,count+9,125,1)
    wardrobe = (b'TMenuMain\0IDM_OUTFITS\0' + struct.pack('<III', MENU_ID, 0, 18)
                + buttons + bytes(background) + heading + glyphs)
    # 7 buttons + 8 images + 1 heading + 2 input glyphs = 18.
    menus = [bytes(main)] + [data[starts[i]:starts[i+1] if i+1<15 else len(data)]
                            for i in range(1, 15)] + [wardrobe]
    if pause:
        menus[8] = _pause_menu(menus[8])
    table = bytearray()
    location = 8 * len(menus)
    for i, menu in enumerate(menus):
        table += struct.pack('<II', i+1, location - 8*(i+1))
        location += len(menu)
    prefix = bytearray(data[:843416])
    struct.pack_into('<I', prefix, string_start, count + len(labels))
    prefix = prefix[:end] + additions + prefix[end:]
    return bytes(prefix) + struct.pack('<I', len(menus)) + bytes(table) + b''.join(menus)


PREVIEW_DIRECTORY = 'recomp_outfits'


def preview_directory(data, *, directory=None):
    """Clone only stock file-directory entries into an isolated menu namespace."""
    directory = PREVIEW_DIRECTORY if directory is None else directory
    if directory not in ('recomp_outfits', 'recomp_live'):
        raise ResourceError('Unreviewed private outfit namespace')
    layout = directory_layout(data)
    offset, count = layout['directory_offset'], layout['directory_count']
    directories = [data[offset+i*36:offset+(i+1)*36] for i in range(count)]
    names = [item[:32].split(b'\0')[0].decode('ascii') for item in directories]
    chars = next((i for i, name in enumerate(names) if name == 'chars'
                  and names[struct.unpack_from('<H',directories[i],34)[0]] == 'meshes'), None)
    slayer = next((i for i, name in enumerate(names) if name == 'slayer'
                   and struct.unpack_from('<H',directories[i],34)[0] == chars), None)
    if chars is None or slayer is None or directory in names or count >= 65535:
        raise ResourceError('Unreviewed preview directory tree')
    wanted = {(4,stem) for stem in ('buffybronze','buffyworkout','buffycheer','buffyslayer','darkslayer')}
    wanted |= {(0,stem) for stem in ('buffybronze','buffysport','buffycheer','buffyslayer','darkslayer')}
    wanted.add((5,'default'))
    fields = [f for f in layout['fields'] if f['directory'] == slayer
              and (f['kind'],f['name']) in wanted]
    if len(fields) != len(wanted) or len({(f['kind'],f['name']) for f in fields}) != len(wanted):
        raise ResourceError('Missing stock preview directory entries')
    result = bytearray(data[:layout['payload_offset']])
    inserts = []
    for field in fields:
        at = field['record_offset']
        copy = bytearray(data[at:at+12])
        struct.pack_into('<H',copy,0,count)
        inserts.append((at+12,bytes(copy)))
        struct.pack_into('<I',result,field['count_offset'],_u32(result,field['count_offset'])+1)
    struct.pack_into('<I',result,layout['item_capacity_offset'],
                     _u32(result,layout['item_capacity_offset'])+len(fields))
    struct.pack_into('<I',result,layout['directory_count_offset'],count+1)
    record = directory.encode().ljust(34,b'\0') + struct.pack('<H',chars)
    inserts.append((layout['directory_end'],record))
    for at, content in sorted(inserts,reverse=True):result[at:at] = content
    return bytes(result)


@dataclass(frozen=True)
class Payload:
    name: str
    resource: str
    original_size: int
    manual: bool
    flag: bool
    data: bytes


def _payload(data, record):
    return Payload(record.name, record.resource, record.original_size, record.manual,
                   record.flag, data[record.data_offset:record.data_offset+record.data_size])


def _encode(payload, offset):
    def string(value):
        b = value.encode('ascii')
        return struct.pack('<I', len(b)) + b
    head = (struct.pack('<5I', 1, offset, 0, payload.original_size, payload.manual)
            + string(payload.name) + string(payload.resource) + struct.pack('<I', payload.flag))
    head = head[:8] + struct.pack('<I', len(head)+len(payload.data)) + head[12:]
    return head + payload.data


def compile_menu_pack(game, title, *, pause=False):
    """Return a private res_null pack; leave every source file untouched."""
    game, title = Path(game), Path(title)
    catalog = stock_inventory(game, title)  # verifies XBE before title-specific edits
    path = game / 'pak/res_null.pak'
    records = read_records(path)
    raw = path.read_bytes()
    original = [_payload(raw, row) for row in records]
    menu_anim = next(row for row in original if row.name == 'meshes\\chars\\guislayer\\buffybronze.ban')
    index = original.index(menu_anim) + 1
    extra = []
    shared_gin = False
    for outfit in catalog['outfits']:
        if not outfit['sources']:
            raise ResourceError('Missing stock outfit: ' + outfit['id'])
        source = next((s for s in outfit['sources'] if len(s['materials']) == 3), None)
        if source is None:
            raise ResourceError('Missing outfit materials: ' + outfit['id'])
        pack = game / 'pak' / source['pack']
        source_records, data = read_records(pack), pack.read_bytes()
        mesh_name = source['model']['name']
        selected = [row for row in source_records if row.name == mesh_name and row.resource == 'base']
        selected += [row for row in source_records if row.name == source['materials'][0]['name']]
        if len(selected) != 4:
            raise ResourceError('Unreviewed stock model/material group')
        extra += [replace(_payload(data,row),name=row.name.replace('chars\\slayer\\','chars\\'+PREVIEW_DIRECTORY+'\\')) for row in selected]
        if not shared_gin:
            # Shared Slayer state definitions are requested once, then cached.
            gin = next(row for row in original if row.name == 'meshes\\chars\\guislayer\\default.gin')
            extra.append(replace(gin, name='meshes\\chars\\'+PREVIEW_DIRECTORY+'\\default.gin'))
            shared_gin = True
        # The four menu animations are already cached by the original GUI model.
        extra.append(replace(menu_anim, name=mesh_name[:-4].replace('chars\\slayer\\','chars\\'+PREVIEW_DIRECTORY+'\\') + '.ban'))
    original[index:index] = extra
    for i, row in enumerate(original):
        if row.name == 'interfc\\buffy.mbf':
            data = menu_mbf(row.data, pause=pause)
            original[i] = replace(row, data=data, original_size=len(data))
    result = bytearray(preview_directory(raw))
    if pause:
        result = bytearray(preview_directory(result, directory='recomp_live'))
    # GUI reads the mounted directory's allocation size, not only the stream
    # header. Keep both lengths consistent when extending the MBF.
    mbf = next(row for row in original if row.name == 'interfc\\buffy.mbf')
    fields = [field for field in directory_size_fields(result)
              if field['kind'] == 13 and field['name'] == 'buffy']
    if len(fields) != 1:
        raise ResourceError('Ambiguous native menu allocation size')
    struct.pack_into('<I', result, fields[0]['offset'], len(mbf.data))
    for row in original:
        result += _encode(row, len(result))
    last = records[-1]
    result += raw[last.data_offset+last.data_size:]
    return bytes(result)


def outfit_assets(game, title, choice):
    """Read a stock high/low model and its three materials from the user's ISO."""
    if not 1 <= choice <= 5:
        raise ResourceError('Stock outfit choice must be between one and five')
    game = Path(game)
    catalog = stock_inventory(game, Path(title))
    selected = catalog['outfits'][choice-1]
    source = next(s for s in selected['sources'] if len(s['materials']) == 3)
    path = game / 'pak' / source['pack']
    records, raw = read_records(path), path.read_bytes()
    mesh = next(r for r in records if r.name == source['model']['name'] and r.resource == 'base')
    materials = tuple(_payload(raw,r) for r in records if r.name == source['materials'][0]['name'])
    if len(materials) != 3:
        raise ResourceError('Unreviewed outfit material count')
    stem = mesh.name.rsplit('\\',1)[1][:-4]
    low = next((r for r in records if r.name == f'meshes\\chars\\slayer\\l_{stem}.msh'), None)
    layout = directory_layout(raw)
    return {'mesh': _payload(raw,mesh), 'low': _payload(raw,low) if low else None,
            'materials': materials, 'dictionary': raw[:layout['string_table_end']]}


def compile_live_pack(path, stock, menu_path):
    """Derive a level's native wardrobe, retaining its original gameplay assets.

    stock must come from outfit_assets (which verifies the source XBE). Cosmetic
    resources follow all original payloads, in the native loader's request order.
    The short BANs belong to GUI previews only, after the five cosmetic loads.
    """
    path = Path(path)
    records = read_records(path)
    if not any(r.name.startswith('meshes\\chars\\slayer\\') and r.name.endswith('.msh')
               for r in records):
        return None
    raw = path.read_bytes()
    layout = directory_layout(raw)
    if len(stock) != 5 or any(a['dictionary'] != raw[:layout['string_table_end']] for a in stock):
        raise ResourceError('Outfit and level string dictionaries differ')
    original = [_payload(raw, r) for r in records]
    mbfs = [i for i,r in enumerate(original) if r.name == 'interfc\\buffy.mbf']
    if len(mbfs) != 1:
        raise ResourceError('Missing native level menu')
    i = mbfs[0]
    mbf = menu_mbf(original[i].data, pause=True)
    original[i] = replace(original[i], data=mbf, original_size=len(mbf))
    gin = next((r for r in original if r.name == 'meshes\\chars\\slayer\\default.gin'), None)
    if gin is None:
        raise ResourceError('Missing native Slayer GIN')
    extra = []
    for i, assets in enumerate(stock):
        mesh = assets['mesh']
        extra.append(replace(mesh, name=mesh.name.replace('chars\\slayer\\', 'chars\\recomp_live\\')))
        extra.extend(replace(m, name=m.name.replace('chars\\slayer\\', 'chars\\recomp_live\\'))
                     for m in assets['materials'])
        if i == 0:
            extra.append(replace(gin, name='meshes\\chars\\recomp_live\\default.gin'))
    menu_path = Path(menu_path)
    menu_raw, menu_records = menu_path.read_bytes(), read_records(menu_path)
    bones = [r for r in menu_records if r.name.endswith('.boneanim')]
    if len(bones) != 4:
        raise ResourceError('Native wardrobe idle animations differ')
    present = {(r.name,r.resource) for r in original}
    extra.extend(_payload(menu_raw,r) for r in bones if (r.name,r.resource) not in present)
    ban = next((r for r in menu_records if r.name == 'meshes\\chars\\guislayer\\buffybronze.ban'), None)
    if ban is None:
        raise ResourceError('Missing native wardrobe animation table')
    extra.extend(replace(_payload(menu_raw,ban),
                         name=a['mesh'].name[:-4].replace('chars\\slayer\\', 'chars\\recomp_live\\')+'.ban')
                 for a in stock)
    result = bytearray(preview_directory(preview_directory(raw), directory='recomp_live'))
    fields = directory_size_fields(result)
    private = directory_layout(result)['directory_count'] - 1
    for row in extra:
        if row.name.endswith('.msh'):
            stem = row.name.rsplit('\\',1)[1][:-4]
            matches = [f for f in fields if f['kind']==4 and f['directory']==private and f['name']==stem]
            if len(matches) != 1:
                raise ResourceError('Ambiguous cosmetic model allocation size')
            struct.pack_into('<I', result, matches[0]['offset'], row.original_size)
    matches = [f for f in fields if f['kind']==13 and f['name']=='buffy']
    if len(matches) != 1:
        raise ResourceError('Ambiguous native level-menu allocation size')
    struct.pack_into('<I', result, matches[0]['offset'], len(mbf))
    for row in original + extra:
        result += _encode(row, len(result))
    last = records[-1]
    result += raw[last.data_offset+last.data_size:]
    return bytes(result)


def compile_play_pack(path, assets):
    """Replace stock Buffy geometry/materials; preserve scripts and animation data.

    This changes copied pack bytes only. Enemy Dark Slayer meshes and other
    actors are retained. A forced outfit also affects arena actors using the
    same original Buffy mesh; it is not an actor-specific gameplay hook.
    """
    path = Path(path)
    records = read_records(path)
    raw = path.read_bytes()
    layout = directory_layout(raw)
    allowed = {'buffybronze','buffyworkout','buffycheer','buffyslayer',
               'l_buffybronze','l_buffyslayer'}
    changed = [r for r in records if r.name.startswith('meshes\\chars\\slayer\\')
               and r.name.endswith('.msh') and r.resource == 'base'
               and r.name.rsplit('\\',1)[1][:-4] in allowed]
    if not changed:
        return None
    if raw[:layout['string_table_end']] != assets['dictionary']:
        raise ResourceError('Outfit and level string dictionaries differ')
    replacements = {}
    materials = assets['materials']
    target_keys = {(p.name,p.resource) for p in materials}
    emitted = set()
    output = []
    index = 0
    while index < len(records):
        row = records[index]
        if row in changed:
            stem = row.name.rsplit('\\',1)[1][:-4]
            model = (assets['low'] or assets['mesh']) if stem.startswith('l_') else assets['mesh']
            output.append(replace(model,name=row.name,resource=row.resource))
            replacements[stem] = model.original_size
            index += 1
            # Original materials immediately following this model belong to its
            # old appearance. The native model loader will request the target
            # material names encoded in the replacement geometry instead.
            if index+2 < len(records):
                group = records[index:index+3]
                if (all(r.name.startswith('meshes\\chars\\slayer\\') and r.name.endswith('.mtx') for r in group)
                        and len({r.name for r in group}) == 1):
                    index += 3
            for material in materials:
                key = (material.name,material.resource)
                if key not in emitted:
                    output.append(material);emitted.add(key)
            continue
        payload = _payload(raw,row)
        key = (payload.name,payload.resource)
        if key in target_keys:
            if key in emitted:
                original = next(p for p in materials if (p.name,p.resource) == key)
                if payload.data != original.data:
                    raise ResourceError('Conflicting original outfit material data')
                index += 1
                continue
            emitted.add(key)
        output.append(payload)
        index += 1
    result = bytearray(raw[:records[0].header_offset])
    fields = directory_size_fields(raw)
    directories = raw[layout['directory_offset']:layout['directory_end']]
    slayer_dirs = {i for i in range(layout['directory_count'])
                   if directories[i*36:i*36+32].split(b'\0')[0] == b'slayer'}
    for stem, size in replacements.items():
        matches = [f for f in fields if f['kind']==4 and f['name']==stem
                   and f['directory'] in slayer_dirs]
        if len(matches)!=1:
            raise ResourceError('Ambiguous Buffy model allocation size')
        struct.pack_into('<I',result,matches[0]['offset'],size)
    for payload in output:
        result += _encode(payload,len(result))
    last = records[-1]
    result += raw[last.data_offset+last.data_size:]
    return bytes(result)
