"""Local profile backups and a deliberately allowlisted, previewable support report."""
import argparse
from contextlib import contextmanager, ExitStack
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from hdd_storage import storage_lock
from graphics_settings import validate_settings

MAX_BYTES=768*1024**2
MAX_FILES=4096
CHUNK=1024*1024
KIND='btvs-recomp-profile-backup'
BACKUP_ID=re.compile(r'(auto|manual)-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}\.zip')


def now():return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(CHUNK),b''):h.update(block)
    return h.hexdigest()


def path_at(root,relative):
    parts=relative.split('/')
    if any(p in ('','.','..') for p in parts) or '\\' in relative or ':' in relative:raise ValueError('Invalid local path')
    path=Path(root)
    for part in parts:
        path=path/part
        if path.is_symlink():raise ValueError('Symbolic profile/support path refused')
    return path


def read_json(path,limit=1024**2):
    if Path(path).stat().st_size>limit:raise ValueError('Unexpected metadata size')
    return json.loads(Path(path).read_text())


def identity(root):
    data=read_json(path_at(root,'config/title.json'))
    return {key:data[key] for key in ('title_id','xbe_sha256')}


@contextmanager
def profile_lock(root):
    root=Path(root).resolve()
    path_at(root,'private').mkdir(exist_ok=True)
    # Also covers direct launches not participating in the advisory file locks.
    result=subprocess.run(['pgrep','-x','buffy-macos'],capture_output=True)
    if result.returncode!=1:raise ValueError('Close the game before backing up or restoring saves.')
    with ExitStack() as stack:
        path_at(root,'private/hdd-storage.lock')
        stack.enter_context(storage_lock(root,maintenance=True))
        lock=stack.enter_context(path_at(root,'private/profile.lock').open('a'))
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('The save profile is in use.') from None
        recover_restore(root)
        profile=path_at(root,'private/profile')
        if profile.exists() and path_at(profile,'hdd').is_dir():
            disk=stack.enter_context(path_at(profile,'hdd/.buffy-disk.lock').open('a'))
            try:fcntl.flock(disk,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise ValueError('The save disk is in use.') from None
        yield profile


def inventory(profile):
    files={};total=0
    for folder,dirs,names in os.walk(profile,followlinks=False):
        for name in dirs:
            if (Path(folder)/name).is_symlink():raise ValueError('Symbolic profile folder refused')
        for name in names:
            path=Path(folder)/name;relative=path.relative_to(profile).as_posix()
            if name=='.buffy-disk.lock':continue
            if relative=='backup.json':raise ValueError('Reserved backup metadata filename in profile')
            path_at(profile,relative)
            info=path.lstat()
            if not stat.S_ISREG(info.st_mode):raise ValueError('Special profile file refused')
            if re.fullmatch(r'Partition[1-5]\.img',name):
                raise ValueError('Some save disks are still expanded. Finish a normal game session to compact them before creating a backup.')
            total+=info.st_size
            if total>MAX_BYTES or len(files)>=MAX_FILES:raise ValueError('Profile exceeds the backup size limit; existing backups are preserved.')
            files[relative]={'bytes':info.st_size,'sha256':sha(path)}
    if not {'title.json','hdd/Partition0.img'}<=set(files):raise ValueError('Incomplete save profile')
    return files,total


def metadata(archive):
    if archive.is_symlink() or archive.stat().st_size>MAX_BYTES+8*1024**2:raise ValueError('Invalid backup archive')
    with zipfile.ZipFile(archive) as z:
        if z.getinfo('backup.json').file_size>1024**2:raise ValueError('Invalid backup metadata')
        data=json.loads(z.read('backup.json'))
    if not isinstance(data,dict) or data.get('kind')!=KIND or data.get('format')!=1:raise ValueError('Unrecognized backup')
    if type(data.get('automatic')) is not bool or not isinstance(data.get('files'),dict):raise ValueError('Invalid backup metadata')
    return data


def list_backups(root):
    folder=path_at(root,'private/backups');items=[]
    if not folder.exists():return items
    for path in sorted(folder.glob('*.zip'),key=lambda p:p.lstat().st_mtime_ns,reverse=True):
        if not BACKUP_ID.fullmatch(path.name):continue
        try:
            data=metadata(path)
            if data['title']!=identity(root):continue
            items.append({'id':path.name,'created':data['created'],'automatic':data['automatic'],'bytes':path.stat().st_size})
        except (OSError,ValueError,KeyError,zipfile.BadZipFile):continue
    return items


def verify_archive(archive,expected,output=None):
    data=metadata(archive)
    if data['title']!=expected:raise ValueError('Backup belongs to another game edition')
    entries=data['files']
    if len(entries)>MAX_FILES:raise ValueError('Too many backup files')
    total=0
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        if len(names)!=len(set(n.casefold() for n in names)) or set(names)!=set(entries)|{'backup.json'}:
            raise ValueError('Unexpected backup contents')
        if not {'title.json','hdd/Partition0.img'}<=set(entries):raise ValueError('Incomplete backup')
        for name,entry in entries.items():
            # Validate path even when only auditing.
            destination=path_at(output or archive.parent/'audit-only',name)
            info=z.getinfo(name);total+=info.file_size
            if total>MAX_BYTES or info.file_size!=entry['bytes'] or not stat.S_ISREG(info.external_attr>>16):raise ValueError('Invalid backup member')
            h=hashlib.sha256()
            if output:destination.parent.mkdir(parents=True,exist_ok=True)
            with z.open(info) as src, ExitStack() as stack:
                dst=stack.enter_context(destination.open('xb')) if output else None
                for block in iter(lambda:src.read(CHUNK),b''):
                    h.update(block)
                    if dst:dst.write(block)
            if h.hexdigest()!=entry['sha256']:raise ValueError('Backup checksum mismatch')
        if json.loads(z.read('title.json'))!=expected:raise ValueError('Backup title metadata mismatch')
    return data


def backup(root,automatic=False):
    root=Path(root).resolve()
    with profile_lock(root) as profile:
        if not profile.exists():return {'status':'absent','message':'No save profile yet.'}
        title=identity(root)
        if read_json(path_at(profile,'title.json'))!=title:raise ValueError('Profile identity mismatch; current files were preserved.')
        files,total=inventory(profile)
        folder=path_at(root,'private/backups');folder.mkdir(exist_ok=True)
        if automatic:
            for item in list_backups(root):
                if item['automatic']:
                    previous=folder/item['id']
                    if metadata(previous)['files']==files:
                        try:verify_archive(previous,title)
                        except (ValueError,OSError,zipfile.BadZipFile):pass
                        else:return {'status':'unchanged','id':item['id']}
                    break
        if shutil.disk_usage(folder).free<total+64*1024**2:raise ValueError('Not enough free space for a verified backup.')
        stamp=now();name=('auto' if automatic else 'manual')+'-'+stamp+'-'+uuid.uuid4().hex[:8]+'.zip'
        fd,tmp=tempfile.mkstemp(prefix='.backup-',dir=folder);os.close(fd);temp=Path(tmp)
        data={'kind':KIND,'format':1,'created':stamp,'automatic':automatic,'title':title,'files':files}
        try:
            with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
                for relative in files:
                    z.write(path_at(profile,relative),relative,compress_type=zipfile.ZIP_STORED if relative.endswith('.gz') else zipfile.ZIP_DEFLATED)
                z.writestr('backup.json',json.dumps(data))
            verify_archive(temp,title)
            if inventory(profile)[0]!=files:raise ValueError('Profile changed during backup; no new backup was published.')
            with temp.open('rb') as handle:os.fsync(handle.fileno())
            os.replace(temp,folder/name)
        finally:
            if temp.exists():temp.unlink()
        # Rotate only recognized automatic archives after a verified new copy exists.
        if automatic:
            autos=[r for r in list_backups(root) if r['automatic'] and r['id'].startswith('auto-')]
            for old in autos[3:]:path_at(folder,old['id']).unlink()
        return {'status':'complete','id':name,'bytes':(folder/name).stat().st_size}


def recover_restore(root):
    marker=path_at(root,'private/profile-restore.json')
    if not marker.exists():return
    record=read_json(marker)
    if not re.fullmatch(r'\.restore-[A-Za-z0-9_-]+',record.get('stage','')) or not re.fullmatch(r'replaced-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}',record.get('previous','')):
        raise ValueError('Invalid restore recovery record; previous profiles preserved.')
    profile=path_at(root,'private/profile')
    stage=path_at(root,'private/'+record['stage'])
    previous=path_at(root,'private/backups/'+record['previous'])
    if not profile.exists() and previous.exists():os.replace(previous,profile)
    if not profile.exists() and record.get('had_profile',True):raise ValueError('Interrupted restore needs manual recovery; previous files preserved.')
    if stage.exists():shutil.rmtree(stage)
    marker.unlink()


def restore(root,backup_id):
    if not BACKUP_ID.fullmatch(backup_id):raise ValueError('Invalid backup selection')
    root=Path(root).resolve()
    with profile_lock(root) as profile:
        archive=path_at(root,'private/backups/'+backup_id);title=identity(root)
        verify_archive(archive,title)
        stage=Path(tempfile.mkdtemp(prefix='.restore-',dir=path_at(root,'private')))
        previous=path_at(root,'private/backups/replaced-'+now()+'-'+uuid.uuid4().hex[:8])
        moved=False
        marker=path_at(root,'private/profile-restore.json')
        try:
            verify_archive(archive,title,stage)
            with marker.open('x') as f:
                json.dump({'stage':stage.name,'previous':previous.name,'had_profile':profile.exists()},f);f.flush();os.fsync(f.fileno())
            if profile.exists():
                # Keep the previous profile verbatim, even if its metadata is damaged.
                os.replace(profile,previous);moved=True
            try:os.replace(stage,profile)
            except BaseException:
                if moved:os.replace(previous,profile)
                raise
            marker.unlink()
        finally:
            if stage.exists():shutil.rmtree(stage)
        return {'status':'restored','previous_profile':str(previous) if moved else None}


def bounded_settings(data):
    try:return validate_settings(data)
    except (ValueError,TypeError):return {'status':'invalid'}


def report(root):
    root=Path(root).resolve()
    raw=path_at(root,'VERSION').read_text().strip()
    current=raw if re.fullmatch(r'\d+\.\d+\.\d+(?:-alpha\.\d+)?',raw) else 'unknown'
    def sysctl(key):
        try:return subprocess.check_output(['/usr/sbin/sysctl','-n',key],text=True).strip()
        except (OSError,subprocess.CalledProcessError):return ''
    chip=sysctl('machdep.cpu.brand_string')
    chip=chip if re.fullmatch(r'Apple [A-Za-z0-9 +()-]{1,50}',chip) else platform.machine()
    memory=sysctl('hw.memsize');ram=round(int(memory)/1024**3) if memory.isdigit() else None
    graphics=path_at(root,'private/config/graphics.json')
    try:settings=bounded_settings(read_json(graphics)) if graphics.exists() else {'status':'not configured'}
    except (ValueError,OSError):settings={'status':'unreadable'}
    last=None
    artifacts=path_at(root,'artifacts')
    if artifacts.exists():
        candidates=[p for p in artifacts.glob('play-*.json') if not p.is_symlink() and re.fullmatch(r'play-(menu|mission)-[0-9]{8}-[0-9]{6}-[0-9]+\.json',p.name)]
        for path in sorted(candidates,key=lambda p:p.stat().st_mtime,reverse=True)[:5]:
            try:
                data=read_json(path)
                if not isinstance(data,dict):continue
                last={'mode':data.get('mode') if data.get('mode') in ('menu','mission') else 'unknown',
                      'settings':bounded_settings(data.get('settings')),
                      'interrupted':data.get('interrupted') is True,
                      'error_recorded':'error' in data,
                      'custom_pack':bool(data.get('texture_pack'))}
                for key in ('game_exit_code','restarts','seconds_limit'):
                    value=data.get(key)
                    last[key]=value if type(value) is int and -255<=value<=1000000 else None
                break
            except (OSError,ValueError,TypeError):continue
    payload={'version':current,'macOS':platform.mac_ver()[0],'architecture':platform.machine(),
             'chip':chip,'memory_gib':ram,'free_space_gib':int(shutil.disk_usage(root).free/1024**3),
             'graphics_preferences':settings,'last_recorded_session':last,
             'controls_profile_present':path_at(root,'private/config/controls.json').is_file()}
    text='# btvs-recomp support report\n\nDescribe the problem, last checkpoint and steps to reproduce below:\n\n- What happened:\n- Expected result:\n- Steps / checkpoint:\n\n## Installation and last recorded session\n\n```json\n'+json.dumps(payload,indent=2)+'\n```\n\nNo raw logs, personal file paths, save contents, game files or computer serial numbers are included. The recorded session can predate the current launcher session; a missing exit code does not prove a clean game exit. Nothing is uploaded automatically.\n'
    folder=path_at(root,'private/reports');folder.mkdir(parents=True,exist_ok=True)
    path=folder/('support-'+now()+'-'+uuid.uuid4().hex[:8]+'.md');path.write_text(text)
    return {'status':'report','text':text,'path':str(path)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['backup','list','restore','report'])
    parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--auto',action='store_true');parser.add_argument('--id')
    args=parser.parse_args()
    if args.action=='backup':result=backup(args.root,args.auto)
    elif args.action=='restore':result=restore(args.root,args.id or '')
    elif args.action=='list':result={'status':'list','backups':list_backups(args.root)}
    else:result=report(args.root)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'status':'error','message':str(exc)}),flush=True);sys.exit(1)
