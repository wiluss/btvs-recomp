"""Managed local XRTP mods. No scripts, downloads or original-game edits."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import struct
import zlib
import uuid
import tempfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from texture_profiles import pack_path, verify_local_pack, verify_profile
from texture_mod import compose, pack_index
from player_support import path_at, read_json, sha

MAX_PACK=2*1024**3
ID=re.compile(r'[0-9a-f]{64}')


def title(root):return read_json(path_at(root,'config/title.json'))['xbe_sha256']


def state(root):
    path=path_at(root,'private/config/mods.json')
    data=read_json(path) if path.exists() else {'version':1,'active':None}
    if not isinstance(data,dict) or set(data)!={'version','active'} or data['version']!=1 or (data['active'] is not None and (not isinstance(data['active'],str) or not ID.fullmatch(data['active']))):
        raise ValueError('Invalid mod preferences; disable mods to reset the selection.')
    return data


def save_state(root,active):
    folder=path_at(root,'private/config');folder.mkdir(exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.mods-',dir=folder)
    try:
        with os.fdopen(fd,'w') as f:
            json.dump({'version':1,'active':active},f);f.flush();os.fsync(f.fileno())
        os.replace(name,path_at(root,'private/config/mods.json'))
    finally:
        if os.path.exists(name):os.unlink(name)


@contextmanager
def locked(root):
    path_at(root,'private').mkdir(exist_ok=True)
    result=subprocess.run(['pgrep','-x','buffy-macos'],capture_output=True)
    if result.returncode!=1:raise ValueError('Close the game before changing or preparing mods.')
    with path_at(root,'private/mods.lock').open('a') as f:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Another mod operation is in progress.') from None
        yield


def mod_path(root,mod_id):
    if not isinstance(mod_id,str) or not ID.fullmatch(mod_id):raise ValueError('Invalid mod selection')
    return path_at(root,'private/mods/library/'+mod_id+'/pack.xrtp')


def check_pack(path,xbe):
    if path.is_symlink() or path.with_suffix('.json').is_symlink():raise ValueError('Symbolic mod files refused')
    if not path.is_file() or not path.with_suffix('.json').is_file():raise ValueError('Keep the .xrtp and matching .json together.')
    if path.stat().st_size>MAX_PACK:raise ValueError('Mod pack exceeds the 2 GiB limit')
    proof=read_json(path.with_suffix('.json'))
    if not isinstance(proof,dict):raise ValueError('Invalid mod manifest')
    verify_local_pack(path,xbe)
    return proof


def preview_bytes(source):
    source=Path(source)
    if source.is_symlink() or not source.is_file() or source.stat().st_size>8*1024**2:
        raise ValueError('Choose a PNG screenshot smaller than 8 MiB.')
    raw=source.read_bytes()
    if len(raw)<33 or raw[:8]!=b'\x89PNG\r\n\x1a\n' or raw[12:16]!=b'IHDR' or raw[8:12]!=b'\x00\x00\x00\x0d':raise ValueError('Invalid preview PNG')
    w,h,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',raw[16:29])
    if not (1<=w<=4096 and 1<=h<=4096 and w*h<=8*1024**2 and depth==8 and color in (2,6) and compression==filtering==interlace==0):
        raise ValueError('Preview must be a non-interlaced RGB/RGBA PNG, at most 4096 pixels per side and 8 megapixels.')
    offset=8;compressed=bytearray();seen_end=False
    while offset+12<=len(raw):
        size=struct.unpack_from('>I',raw,offset)[0];end=offset+12+size
        if end>len(raw) or zlib.crc32(raw[offset+4:end-4])!=struct.unpack_from('>I',raw,end-4)[0]:raise ValueError('Damaged preview PNG')
        kind=raw[offset+4:offset+8]
        if kind==b'IDAT':compressed.extend(raw[offset+8:end-4])
        if kind==b'IEND':
            if size or end!=len(raw):raise ValueError('Invalid PNG tail')
            seen_end=True;break
        offset=end
    if not seen_end:raise ValueError('Incomplete preview PNG')
    expected=(w*(4 if color==6 else 3)+1)*h
    decoder=zlib.decompressobj();pixels=decoder.decompress(bytes(compressed),expected+1)
    if len(pixels)!=expected or not decoder.eof or decoder.unused_data:raise ValueError('Invalid PNG pixels')
    return raw


def skin_metadata(proof,source):
    skin=proof.get('skin',{})
    if not isinstance(skin,dict):raise ValueError('Invalid skin metadata')
    values={}
    for key,default,limit in [('name',source.stem,100),('author','',100),('description','',400)]:
        value=skin.get(key,default)
        if not isinstance(value,str) or len(value)>limit or any(ord(c)<32 for c in value):raise ValueError('Invalid skin '+key)
        values[key]=value.strip()
    if not values['name']:raise ValueError('Give the skin a name')
    return values


def attach_preview(root,mod_id,source):
    raw=preview_bytes(source)
    with locked(root):
        pack=mod_path(root,mod_id);check_pack(pack,title(root))
        metadata_path=path_at(pack.parent,'mod.json');metadata=read_json(metadata_path)
        filename='preview-'+uuid.uuid4().hex+'.png'
        target=path_at(pack.parent,filename);target.write_bytes(raw)
        metadata['preview']=filename
        fd,tmp=tempfile.mkstemp(prefix='.metadata-',dir=pack.parent)
        try:
            with os.fdopen(fd,'w') as f:
                json.dump(metadata,f);f.flush();os.fsync(f.fileno())
            os.replace(tmp,metadata_path)
        except BaseException:
            target.unlink();raise
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
        return listing(root)


def listing(root):
    active=state(root)['active'];folder=path_at(root,'private/mods/library');items=[]
    if folder.exists():
        for entry in sorted(folder.iterdir()):
            if not ID.fullmatch(entry.name):continue
            pack=mod_path(root,entry.name)
            # Listing is cheap; full payload integrity is checked at activation and launch.
            proof=read_json(pack.with_suffix('.json'))
            metadata=read_json(path_at(entry,'mod.json'))
            if not isinstance(proof,dict) or not isinstance(metadata,dict):raise ValueError('Damaged mod library metadata')
            preview=None
            if metadata.get('preview'):
                name=metadata['preview']
                if not isinstance(name,str) or not re.fullmatch(r'preview(?:-[0-9a-f]{32})?\.png',name):raise ValueError('Invalid managed preview path')
                preview=str(path_at(entry,name))
            items.append({'id':entry.name,'name':metadata['name'],'author':metadata.get('author',''),
                          'description':metadata.get('description',''),'preview':preview,
                          'entries':proof['entries'],'bytes':pack.stat().st_size})
    return {'mods':items,'active':active}


def install(root,source):
    source=Path(source).absolute()
    if source.suffix!='.xrtp':raise ValueError('Select a .xrtp mod and keep its matching .json beside it.')
    with locked(root):
        proof=check_pack(source,title(root));metadata=skin_metadata(proof,source)
        image=source.with_suffix('.png');preview=preview_bytes(image) if image.exists() or image.is_symlink() else None
        mod_id=proof['pack_sha256'];destination=mod_path(root,mod_id).parent
        if destination.exists():
            check_pack(destination/'pack.xrtp',title(root))
            return listing(root)
        folder=path_at(root,'private/mods/library');folder.mkdir(parents=True,exist_ok=True)
        needed=source.stat().st_size
        if shutil.disk_usage(folder).free<needed+64*1024**2:raise ValueError('Not enough free space to import the mod.')
        stage=Path(tempfile.mkdtemp(prefix='.import-',dir=folder))
        try:
            shutil.copyfile(source,stage/'pack.xrtp')
            # Retain only verified fields; external paths or commands in sidecars are never used.
            clean={k:proof[k] for k in ('xbe_sha256','entries','pack_sha256')}
            (stage/'pack.json').write_text(json.dumps(clean))
            if preview is not None:
                (stage/'preview.png').write_bytes(preview);metadata['preview']='preview.png'
            (stage/'mod.json').write_text(json.dumps(metadata))
            check_pack(stage/'pack.xrtp',title(root))
            os.rename(stage,destination)
        finally:
            if stage.exists():shutil.rmtree(stage)
        return listing(root)


def activate(root,mod_id):
    with locked(root):
        if mod_id is not None:
            pack=mod_path(root,mod_id);check_pack(pack,title(root))
            if sha(pack)!=mod_id:raise ValueError('Managed mod identity mismatch')
        save_state(root,mod_id)
        return listing(root)


def prepare(root,textures,text):
    with locked(root):
        active=state(root)['active']
        if active is None:return {'pack':None}
        mod=mod_path(root,active);check_pack(mod,title(root))
        if sha(mod)!=active:raise ValueError('Managed mod identity mismatch')
        verify_profile(textures,root,text=text)
        base=pack_path(textures,root,text=text)
        if base is None:return {'pack':str(mod)}
        check_pack(base,title(root))
        key=hashlib.sha256((sha(base)+active).encode()).hexdigest()
        folder=path_at(root,'private/mods/cache');folder.mkdir(parents=True,exist_ok=True)
        destination=path_at(folder,key)
        cached=path_at(destination,'pack.xrtp')
        if destination.exists():
            check_pack(cached,title(root));return {'pack':str(cached)}
        if shutil.disk_usage(folder).free<base.stat().st_size+mod.stat().st_size+64*1024**2:
            raise ValueError('Not enough free space to combine the mod with the selected HD pack.')
        # One derived cache at a time, plus the staging candidate. Never remove imported mods.
        stage=Path(tempfile.mkdtemp(prefix='.compose-',dir=folder))
        try:
            output=stage/'pack.xrtp'
            count=compose(base,mod,output,kinds=(0,1,2))
            (stage/'pack.json').write_text(json.dumps({'xbe_sha256':title(root),'entries':count,'pack_sha256':sha(output)}))
            check_pack(output,title(root))
            os.rename(stage,destination)
        finally:
            if stage.exists():shutil.rmtree(stage)
        for old in folder.iterdir():
            if old.name!=key and ID.fullmatch(old.name) and old.is_dir() and not old.is_symlink():shutil.rmtree(old)
        return {'pack':str(cached)}


def wardrobe(root,textures,text):
    """Immutable session catalog; no composition copies and no live file writer."""
    with locked(root):
        library=listing(root);rows=library['mods'];active=library['active']
        if len(rows)>32:raise ValueError('The live wardrobe supports up to 32 imported skins.')
        verify_profile(textures,root,text=text)
        base=pack_path(textures,root,text=text)
        if base is not None:check_pack(base,title(root))
        existing={}
        if base is not None:
            with base.open('rb') as f:existing=pack_index(f)[2]
        selected=0
        payload=bytearray()
        for index,row in enumerate(rows,1):
            pack=mod_path(root,row['id']);check_pack(pack,title(root))
            if sha(pack)!=row['id']:raise ValueError('Managed skin identity mismatch')
            with pack.open('rb') as f:replacements=pack_index(f)[2]
            for key,(w,h,levels,flags,offset) in replacements.items():
                if key in existing:
                    bw,bh,_,bf,_=existing[key]
                    if flags&3!=bf&3 or w*bh!=bw*h:raise ValueError('Skin conflicts with the selected base texture kind/aspect')
            if row['preview']:preview_bytes(Path(row['preview']))
            for value,limit in [(row['name'],512),(str(pack),4096),(row['preview'] or '',4096),(row['id'],64)]:
                raw=value.encode('utf-8')
                if len(raw)>limit or b'\0' in raw:raise ValueError('Skin catalog field exceeds its limit')
                payload.extend(struct.pack('<I',len(raw)));payload.extend(raw)
            if row['id']==active:selected=index
        if active is not None and not selected:raise ValueError('Active skin is missing; select the original outfit first.')
        path_at(root,'private/config').mkdir(exist_ok=True)
        folder=path_at(root,'private/mods/sessions');folder.mkdir(parents=True,exist_ok=True)
        fd,path=tempfile.mkstemp(prefix='wardrobe-',suffix='.bin',dir=folder)
        with os.fdopen(fd,'wb') as f:
            f.write(struct.pack('<4sII',b'BWS1',len(rows),selected));f.write(payload)
        return {'pack':str(base) if base is not None else None,'catalog':path,'preferences':str(path_at(root,'private/config/mods.json'))}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['list','import','activate','disable','prepare','preview','wardrobe'])
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--file',type=Path);parser.add_argument('--id')
    parser.add_argument('--textures',choices=['original','campaign2x'],default='original')
    parser.add_argument('--text',choices=['original','hd'],default='original')
    args=parser.parse_args();root=args.root.resolve()
    if args.action=='list':result=listing(root)
    elif args.action=='import':
        if args.file is None:raise ValueError('Choose a mod file')
        result=install(root,args.file)
    elif args.action=='preview':
        if args.file is None:raise ValueError('Choose a preview PNG')
        result=attach_preview(root,args.id or '',args.file)
    elif args.action=='activate':result=activate(root,args.id or '')
    elif args.action=='disable':result=activate(root,None)
    elif args.action=='wardrobe':result=wardrobe(root,args.textures,args.text)
    else:result=prepare(root,args.textures,args.text)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'error':str(exc)}),flush=True);sys.exit(1)
