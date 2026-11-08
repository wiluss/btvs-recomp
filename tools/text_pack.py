"""Compose HD fonts and word images with a local XRTPv2 pilot."""
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_extra(path, expected_sha, xbe_sha):
    # Reduced Qwen proposal, reviewed; require a JSON object before .get().
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError('Additional font recipe SHA differs')
    obj = json.loads(raw)
    if not isinstance(obj, dict) or obj.get('xbe_sha256') != xbe_sha:
        raise ValueError('Additional font XBE differs')
    return obj


def additional_recipes(root, recipe):
    extras=recipe.get('additional_fonts',[])
    if not isinstance(extras,list) or len(extras)>4:raise ValueError('Invalid additional fonts')
    result=[];seen=set()
    for spec in extras:
        if not isinstance(spec,dict):raise ValueError('Invalid additional font')
        name=Path(spec['recipe']);expected=spec['recipe_sha256']
        if (name.is_absolute() or '..' in name.parts or len(name.parts)!=2 or name.parts[0]!='config'
            or name in seen or not isinstance(expected,str) or len(expected)!=64
            or any(c not in '0123456789abcdef' for c in expected)):
            raise ValueError('Unreviewed additional font recipe')
        seen.add(name);extra=read_extra(Path(root)/name,expected,recipe['xbe_sha256'])
        if extra.get('additional_fonts'):raise ValueError('Nested font collections refused')
        for key in ('font','atlas','objects'):
            asset=Path(spec[key])
            if asset.is_absolute() or '..' in asset.parts or not asset.parts or asset.parts[0]!='private':
                raise ValueError('Unreviewed additional font asset path')
        result.append((spec,extra))
    return result


def word_recipe(root, recipe):
    expected_sha = recipe.get('word_recipe_sha256')
    if expected_sha is None:
        return None
    words = read_extra(Path(root)/'config/menu-words-hd.json', expected_sha, recipe['xbe_sha256'])
    entries = words.get('entries')
    if words.get('scale') != recipe['scale'] or not isinstance(entries, list) or not 1 <= len(entries) <= 32:
        raise ValueError('Invalid word texture collection')
    return words


def read_pack(path):
    raw=Path(path).read_bytes()
    if not 32<=len(raw)<=256*1024*1024:raise ValueError('Invalid pilot pack size')
    magic,version,count,scale,index,text_scale,reserved=struct.unpack_from('<4sIIIQII',raw)
    if magic!=b'XRTP' or version!=2 or reserved or not 1<=count<=4096 or index<32 or index+32*count>len(raw):
        raise ValueError('Invalid XRTPv2 header')
    entries={};last=-1
    for i in range(count):
        key,w,h,levels,flags,offset=struct.unpack_from('<QIIIIQ',raw,index+i*32)
        if key<=last or not (1<=w<=16384 and 1<=h<=16384 and 1<=levels<=max(w,h).bit_length()) or flags&~0x13 or flags&3==3:
            raise ValueError('Invalid XRTP entry')
        if flags&0x10:
            if w%4 or h%4:raise ValueError('Invalid BC3 dimensions')
            size=sum(((max(1,w>>l)+3)//4)*((max(1,h>>l)+3)//4)*16 for l in range(levels))
        else:size=sum(max(1,w>>l)*max(1,h>>l)*4 for l in range(levels))
        if offset<index+32*count or offset+size>len(raw):raise ValueError('Invalid payload extent')
        entries[key]=(w,h,levels,flags,raw[offset:offset+size]);last=key
    return {'scale':scale,'text_scale':text_scale},entries


def compose(base, text_pack, output):
    """Only text or font entries may override the same kind and aspect."""
    fh,overrides=read_pack(text_pack)
    header,entries=read_pack(base) if base is not None else (fh,{})
    for key,value in overrides.items():
        kind = value[3] & 3
        if kind not in (1, 2):
            raise ValueError('Text override contains art')
        if key in entries:
            old=entries[key]
            if old[3] & 3 != kind or old[0]*value[1] != old[1]*value[0]:
                raise ValueError('Text override kind/aspect mismatch')
        entries[key]=value
    offset=32+32*len(entries);index=[];payload=[]
    for key,(w,h,levels,flags,data) in sorted(entries.items()):
        index.append(struct.pack('<QIIIIQ',key,w,h,levels,flags,offset));payload.append(data);offset+=len(data)
    raw=struct.pack('<4sIIIQII',b'XRTP',2,len(entries),header['scale'],32,fh['text_scale'],0)+b''.join(index)+b''.join(payload)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);temp=None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent,delete=False) as stream:
            temp=Path(stream.name);stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,output)
    finally:
        if temp is not None and temp.exists():temp.unlink()
    return len(entries)


def build_profiles(root, font_pack):
    root = Path(root)
    recipe = root/'config/font-hd.json'
    data = json.loads(recipe.read_text())
    extras = additional_recipes(root, data)
    recipes = [data] + [extra for _, extra in extras]
    words = word_recipe(root, data)
    word_entries = words['entries'] if words else []
    identities = {int(item['texture_hash'], 16): 1 for item in recipes}
    identities.update({int(item['texture_hash'], 16): 2 for item in word_entries})
    header, entries = read_pack(font_pack)
    if (len(identities) != len(recipes) + len(word_entries)
        or {key: entry[3] & 3 for key, entry in entries.items()} != identities
        or header != {'scale': data['scale'], 'text_scale': data['scale']}):
        raise ValueError('Text pack does not match the configured collection')
    for name,scale in [('original',0),('pilot2x',2),('pilot4x',4)]:
        base=root/'private/textures'/('pilot-%dx.xrtp'%scale) if scale else None
        output=root/'private/textures'/(name+'-text-hd.xrtp')
        count=compose(base,font_pack,output)
        proof={'xbe_sha256':json.loads(recipe.read_text())['xbe_sha256'],
            'base_profile':name,'base_pack_sha256':digest(base) if base else None,
            'font_recipe_sha256':digest(recipe),'font_pack_sha256':digest(font_pack),
            'pack_sha256':digest(output),'entries':count,'scale':scale or 8,'text_scale':8}
        output.with_suffix('.json').write_text(json.dumps(proof,indent=2)+'\n')
