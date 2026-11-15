#!/usr/bin/env python3
"""Prepare a private stock-outfit game view; never modify the imported game."""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

if __package__:
    from .outfit_resources import compile_menu_pack, compile_play_pack, compile_live_pack, outfit_assets
    from .loadvars_fix import verify_xbe
else:
    from outfit_resources import compile_menu_pack, compile_play_pack, compile_live_pack, outfit_assets
    from loadvars_fix import verify_xbe

MARKER = 'btvs-native-outfits-v1\n'
PROTOCOL = b'BTVS_NATIVE_OUTFITS_PROTOCOL_2'


def _digest(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def _json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>128*1024:
        raise ValueError('Invalid private outfit metadata')
    return json.loads(path.read_text())


def _choice(value):
    if type(value) is not int or not 0<=value<=5:
        raise ValueError('Outfit choice must be an integer from zero through five')
    return value


def saved_choice(cache):
    path=Path(cache)/'choice.json'
    if path.is_symlink():raise ValueError('Invalid private outfit preference')
    if not path.exists():return 0
    data=_json(path)
    if not isinstance(data,dict) or set(data)!={'schema','choice'} or data['schema']!=1:
        raise ValueError('Unrecognized outfit preference')
    return _choice(data['choice'])


def _fingerprint(source,title, *, pause=False):
    files=[title,source/'Default.xbe']+sorted((source/'pak').glob('*.pak'))
    stamps=[(str(p),p.stat().st_size,p.stat().st_mtime_ns) for p in files]
    recipe=[_digest(Path(__file__).with_name(name)) for name in
            ['outfit_install.py','outfit_resources.py','game_resources.py']]
    return hashlib.sha256(json.dumps([stamps,recipe,pause],sort_keys=True).encode()).hexdigest()


def _valid_cache(cache,state,source):
    game=cache/'game'
    for name,item in state['packs'].items():
        if Path(name).name!=name or not name.endswith('.pak'):return False
        path=game/'pak'/name
        if item['source']:
            if not path.is_symlink() or path.resolve()!=source/'pak'/name:return False
        elif (path.is_symlink() or not path.is_file() or path.stat().st_size!=item['size']
              or _digest(path)!=item['sha256']):return False
    return True


def _state(path,source):
    if path.is_symlink():raise ValueError('Invalid private outfit state')
    if not path.exists():return None
    data=_json(path)
    if (not isinstance(data,dict) or set(data)!={'schema','fingerprint','choice','packs'}
        or data['schema']!=1 or not isinstance(data['fingerprint'],str)
        or len(data['fingerprint'])!=64 or not isinstance(data['packs'],dict)
        or set(data['packs'])!={p.name for p in (source/'pak').glob('*.pak')}):
        raise ValueError('Invalid private outfit state')
    _choice(data['choice'])
    for item in data['packs'].values():
        if not isinstance(item,dict) or type(item.get('source')) is not bool:
            raise ValueError('Invalid private outfit pack state')
        if item['source']:
            valid=set(item)=={'source'}
        else:
            valid=(set(item)=={'source','size','sha256'} and type(item['size']) is int
                   and 0<item['size']<=512*1024*1024 and isinstance(item['sha256'],str)
                   and len(item['sha256'])==64)
        if not valid:raise ValueError('Invalid private outfit pack state')
    return data


def select_choice(source, title, cache, choice, *, pause=False):
    """Persist a choice without touching the running game's packs.

    The Pause bridge applies it to its already-loaded cosmetics; the next guest
    process also receives it. Legacy Main-only builds consume it on next launch.
    There is no payload hashing, compilation or publication in this path.
    """
    source,title=Path(source).resolve(),Path(title).resolve()
    cache=Path(cache).absolute()
    selected=_choice(choice)
    if cache.is_symlink():raise ValueError('Outfit cache cannot be a symlink')
    cache=cache.resolve()
    if cache==source or cache in source.parents or source in cache.parents:
        raise ValueError('Outfit cache must be outside the imported game')
    verify_xbe(source/'Default.xbe',json.loads(title.read_text()))
    marker,lock=cache/'OWNER',cache/'prepare.lock'
    if marker.is_symlink() or not marker.is_file() or marker.read_text()!=MARKER:
        raise ValueError('Unrecognized outfit cache')
    if lock.is_symlink() or not lock.is_file():raise ValueError('Invalid outfit cache lock')
    with lock.open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        old=_state(cache/'state.json',source)
        if old is None or old['fingerprint']!=_fingerprint(source,title,pause=pause):
            raise ValueError('Source or outfit recipe changed; restart the game before selecting')
        saved_choice(cache)  # reject replaced or malformed preferences
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',dir=cache,prefix='choice-',delete=False) as stream:
                temporary=Path(stream.name)
                stream.write(json.dumps({'schema':1,'choice':selected})+'\n')
                stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,cache/'choice.json')
        finally:
            if temporary is not None and temporary.exists():temporary.unlink()
    return cache/'game',selected


def prepare(source, title, cache, choice=None, *, live=False, pause=False):
    if pause and live:
        selected=saved_choice(cache) if choice is None else _choice(choice)
        return select_choice(source,title,cache,selected,pause=True)
    source,title=Path(source).resolve(),Path(title).resolve()
    cache=Path(cache).absolute()
    if cache.is_symlink():raise ValueError('Outfit cache cannot be a symlink')
    cache=cache.resolve()
    if cache==source or cache in source.parents or source in cache.parents:
        raise ValueError('Outfit cache must be outside the imported game')
    verify_xbe(source/'Default.xbe',json.loads(title.read_text()))
    cache.mkdir(parents=True,exist_ok=True,mode=0o700)
    marker=cache/'OWNER'
    if marker.exists():
        if marker.is_symlink() or marker.read_text()!=MARKER:raise ValueError('Unrecognized outfit cache')
    elif any(cache.iterdir()):raise ValueError('Refusing to replace an unowned outfit cache')
    else:marker.write_text(MARKER)
    lock=cache/'prepare.lock'
    if lock.is_symlink():raise ValueError('Invalid outfit cache lock')
    with lock.open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        selected=saved_choice(cache) if choice is None else _choice(choice)
        state_path=cache/'state.json';old=_state(state_path,source)
        fingerprint=_fingerprint(source,title,pause=pause)
        if live and (old is None or old['fingerprint']!=fingerprint):
            raise ValueError('Source or outfit recipe changed; restart the game before applying')
        if live and not _valid_cache(cache,old,source):
            raise ValueError('Outfit cache changed; restart the game to repair it')
        if old and old['fingerprint']==fingerprint and (pause or old['choice']==selected) and _valid_cache(cache,old,source):
            if pause and saved_choice(cache)!=selected:
                with tempfile.NamedTemporaryFile(mode='w',dir=cache,prefix='choice-',delete=False) as stream:
                    pending=Path(stream.name)
                    try:
                        stream.write(json.dumps({'schema':1,'choice':selected})+'\n')
                        stream.flush();os.fsync(stream.fileno())
                    except BaseException:
                        pending.unlink();raise
                try:os.replace(pending,cache/'choice.json')
                finally:
                    if pending.exists():pending.unlink()
            return cache/'game',selected
        game=cache/'game'
        if game.is_symlink() or (game/'pak').is_symlink():raise ValueError('Invalid outfit game view')
        (game/'pak').mkdir(parents=True,exist_ok=True)
        for entry in source.iterdir():
            if entry.name=='pak':continue
            dest=game/entry.name
            if dest.is_symlink():
                if dest.resolve()!=entry:raise ValueError('Outfit source link differs')
            elif dest.exists():raise ValueError('Unowned file in outfit game view')
            else:dest.symlink_to(entry,target_is_directory=entry.is_dir())
        packs=sorted((source/'pak').glob('*.pak'))
        if not packs or len(packs)>256:raise ValueError('Invalid source pack list')
        extra=(len(packs)*4*1024*1024) if pause else 0
        if (selected or pause) and shutil.disk_usage(cache).free<sum(p.stat().st_size for p in packs)+extra+32*1024*1024:
            raise ValueError('Not enough space to prepare the selected outfit')
        assets=([outfit_assets(source,title,c) for c in range(1,6)] if pause
                else outfit_assets(source,title,selected) if selected else None)
        with tempfile.TemporaryDirectory(prefix='prepare-',dir=cache) as work:
            stage=Path(work);new={};publish=[]
            for pack in packs:
                name=pack.name;dest=stage/name
                if name=='res_null.pak':
                    if live:
                        new[name]=old['packs'][name]
                        continue  # the current menu's open stream stays intact
                    data=compile_menu_pack(source,title,pause=True) if pause else compile_menu_pack(source,title)
                elif pause:data=compile_live_pack(pack,assets,source/'pak/res_null.pak')
                else:data=compile_play_pack(pack,assets) if assets else None
                if data is None:
                    dest.symlink_to(pack);new[name]={'source':True}
                else:
                    dest.write_bytes(data)
                    new[name]={'source':False,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
                publish.append((dest,game/'pak'/name))
            state={'schema':1,'fingerprint':fingerprint,'choice':selected,'packs':new}
            (stage/'state.json').write_text(json.dumps(state,sort_keys=True)+'\n')
            (stage/'choice.json').write_text(json.dumps({'schema':1,'choice':selected})+'\n')
            publish += [(stage/'state.json',state_path),(stage/'choice.json',cache/'choice.json')]
            backups=[];installed=[]
            try:
                for index,(candidate,destination) in enumerate(publish):
                    if destination.exists() or destination.is_symlink():
                        if destination.is_dir():raise ValueError('Invalid outfit cache destination')
                        backup=stage/f'previous-{index}';os.replace(destination,backup);backups.append((backup,destination))
                    os.replace(candidate,destination);installed.append(destination)
            except BaseException:
                try:
                    for dest in reversed(installed):dest.unlink()
                    for backup,dest in reversed(backups):os.replace(backup,dest)
                except OSError as error:
                    raise RuntimeError('Outfit cache rollback failed; stop and rebuild the cache') from error
                raise
        return game,selected


def environment(binary, source, title, cache, *, enabled=True):
    """Old game builds retain the original menu; require the native protocol."""
    if not enabled or not Path(binary).is_file() or PROTOCOL not in Path(binary).read_bytes():return {}
    import sys
    game,choice=prepare(source,title,cache,pause=True)
    return {'RECOMP_GAME_FILES':str(game),'BUFFY_NATIVE_OUTFITS':'1',
            'BUFFY_NATIVE_OUTFIT_CHOICE':str(choice),'BUFFY_NATIVE_OUTFITS_PAUSE':'1',
            'BUFFY_OUTFIT_PYTHON':sys.executable,
            'BUFFY_OUTFIT_PREPARER':str(Path(__file__).resolve()),
            'BUFFY_OUTFIT_SOURCE':str(Path(source).resolve()),
            'BUFFY_OUTFIT_TITLE':str(Path(title).resolve()),
            'BUFFY_OUTFIT_CACHE':str(Path(cache).resolve())}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['source','title','cache']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--choice',type=int,choices=range(6))
    parser.add_argument('--pause',action='store_true',help='Use the native Pause wardrobe recipe')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--live',action='store_true')
    mode.add_argument('--select-only',action='store_true')
    args=parser.parse_args()
    try:
        if args.select_only:
            if args.choice is None:raise ValueError('Selection requires --choice')
            game,choice=select_choice(args.source,args.title,args.cache,args.choice,pause=args.pause)
        else:game,choice=prepare(args.source,args.title,args.cache,args.choice,live=args.live,pause=args.pause)
        print(json.dumps({'game':str(game),'choice':choice}))
    except (OSError,ValueError,RuntimeError) as error:parser.exit(1,f'Outfit preparation failed: {error}\n')


if __name__=='__main__':main()
