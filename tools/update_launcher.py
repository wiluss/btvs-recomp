"""Launcher-only source updates. Private/game/runtime files are never replaced."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import urllib.parse
import uuid
import zipfile
import source_release

REPO='wiluss/btvs-recomp'
APP='build/btvs-recomp.app'
COMMAND='Update btvs-recomp.command'
MANIFEST='RELEASE_MANIFEST.json'
LIMIT=64*1024**2
HUMAN=False


def emit(**data):
    print(data.get('message',data.get('status','')) if HUMAN else json.dumps(data),flush=True)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def version(text):
    match=re.fullmatch(r'(\d+)\.(\d+)\.(\d+)(?:-alpha\.(\d+))?',text)
    if not match:raise ValueError('Unsupported version: '+text)
    return tuple(int(v) if v is not None else 10**9 for v in match.groups())


def safe_path(root,name):
    if name not in (APP,MANIFEST):source_release.checked_path(name)
    p=Path(root)
    for part in Path(name).parts:
        p=p/part
        if p.is_symlink():raise ValueError('Symbolic path refused: '+name)
    return p


def launcher_only(name):
    return (name.startswith(('src/launcher/','docs/','tests/','release/','.github/'))
            or name in {COMMAND,'VERSION','README.md','AGENTS.md','THIRD_PARTY_NOTICES.md',
                        'tools/build_launcher.sh','tools/launcher_icon.swift',
                        'tools/update_launcher.py','tools/source_release.py'})


def inventory(root):
    manifest=safe_path(root,MANIFEST)
    if not manifest.is_file():
        raise ValueError('Select an extracted official source kit with RELEASE_MANIFEST.json. Git checkouts need a manual update.')
    if manifest.stat().st_size>1024**2:raise ValueError('Unexpected manifest size')
    data=json.loads(manifest.read_text())
    version(data['version'])
    if safe_path(root,'VERSION').read_text().strip()!=data['version']:raise ValueError('Version/manifest mismatch')
    for name,entry in data['files'].items():
        p=safe_path(root,name)
        if not p.is_file() or p.stat().st_size!=entry['bytes'] or digest(p)!=entry['sha256']:
            raise ValueError('Source file changed or missing; preserved: '+name)
    return data


def plan(source,target):
    source=Path(source).resolve();target=Path(target).resolve()
    if source==target or source in target.parents or target in source.parents:
        raise ValueError('Choose the existing installation, separate from the downloaded update folder.')
    new=inventory(source);old=inventory(target)
    if version(new['version'])<=version(old['version']):raise ValueError('This installation is already at this version or newer.')
    names=set(old['files'])|set(new['files'])
    changed=[n for n in sorted(names) if old['files'].get(n)!=new['files'].get(n)]
    for name in changed:
        if not launcher_only(name):raise ValueError('This update changes game/runtime inputs and requires a manual build: '+name)
        p=safe_path(target,name)
        if name not in old['files'] and p.exists():raise ValueError('Untracked local file preserved: '+name)
    app=safe_path(target,APP)
    if not app.is_dir():raise ValueError('No installed launcher found in the selected folder.')
    return new,old,changed


class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,url):
        checked_url(url)
        return super().redirect_request(req,fp,code,msg,headers,url)


def checked_url(url):
    u=urllib.parse.urlsplit(url)
    if u.scheme!='https' or u.hostname not in {'api.github.com','github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'} or u.username or u.password or u.port not in (None,443):
        raise ValueError('Unexpected update download destination')


def fetch(url,limit):
    checked_url(url)
    req=urllib.request.Request(url,headers={'User-Agent':'btvs-recomp-updater','Accept':'application/vnd.github+json' if 'api.github.com/' in url else 'application/octet-stream'})
    with urllib.request.build_opener(Redirects()).open(req,timeout=60) as response:
        data=response.read(limit+1)
    if len(data)>limit:raise ValueError('Update response exceeds size limit')
    return data


def release_info(tag=None):
    path='/releases?per_page=100' if tag is None else '/releases/tags/'+urllib.parse.quote(tag,safe='')
    data=json.loads(fetch('https://api.github.com/repos/'+REPO+path,4*1024**2))
    choices=data if isinstance(data,list) else [data]
    valid=[]
    for item in choices:
        if item.get('draft'):continue
        name=item.get('tag_name','')
        try:key=version(name.removeprefix('v'))
        except ValueError:continue
        valid.append((key,item))
    if not valid:raise ValueError('No supported release found')
    return max(valid,key=lambda pair:pair[0])[1]


def download_release(info,destination):
    tag=info['tag_name'];version(tag.removeprefix('v'))
    name='btvs-recomp-'+tag+'-source.zip'
    assets=[a for a in info['assets'] if a['name']==name]
    if len(assets)!=1:raise ValueError('Missing official source ZIP')
    asset=assets[0];expected=asset.get('digest','')
    if not re.fullmatch('sha256:[0-9a-f]{64}',expected):raise ValueError('GitHub has no SHA-256 digest for this source ZIP')
    data=fetch(asset['browser_download_url'],LIMIT)
    if 'sha256:'+hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Source ZIP checksum mismatch')
    destination=Path(destination);archive=destination/'source.zip';archive.write_bytes(data)
    result=source_release.audit(archive)
    if result['version']!=tag.removeprefix('v'):raise ValueError('Release/ZIP version mismatch')
    source=destination/'source';source.mkdir()
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            p=safe_path(source,item.filename);p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(z.read(item));p.chmod((item.external_attr>>16)&0o777)
    return source


def build_launcher(source,log):
    env=dict(os.environ)
    with open(log,'w') as stream:
        result=subprocess.run(['/bin/sh','tools/build_launcher.sh'],cwd=source,env=env,stdout=stream,stderr=subprocess.STDOUT)
    fallback=Path('/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk')
    if result.returncode and 'SDKROOT' not in env and fallback.is_dir() and 'SwiftUIMacros' in Path(log).read_text():
        env['SDKROOT']=str(fallback)
        with open(log,'a') as stream:
            stream.write('\nRetrying with the installed macOS 26.5 SDK (this build only).\n');stream.flush()
            result=subprocess.run(['/bin/sh','tools/build_launcher.sh'],cwd=source,env=env,stdout=stream,stderr=subprocess.STDOUT)
    if result.returncode:raise ValueError('Launcher build failed. Existing installation preserved. Log: '+str(log))
    if not (source/APP/'Contents/MacOS/BuffyLauncher').is_file():raise ValueError('Launcher build produced no executable')


def write_journal(path,data):
    temp=path.with_suffix('.tmp')
    with temp.open('w') as f:
        json.dump(data,f);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)


def restore(target,work,journal):
    # Move the new versions aside before restoring originals. Never discard them.
    displaced=work/'rolled-back';displaced.mkdir(exist_ok=True)
    for name in reversed(journal['pending']):
        live=safe_path(target,name);backup=safe_path(work/'backup',name)
        if backup.exists():
            if live.exists():
                dst=safe_path(displaced,name);dst.parent.mkdir(parents=True,exist_ok=True);os.replace(live,dst)
            live.parent.mkdir(parents=True,exist_ok=True);os.replace(backup,live)
        elif name not in journal['existed'] and live.exists():
            dst=safe_path(displaced,name);dst.parent.mkdir(parents=True,exist_ok=True);os.replace(live,dst)
    finished=dict(journal,state='rolled-back');write_journal(work/'journal.json',finished)
    journal['state']='rolled-back'


def game_closed():
    listing=subprocess.check_output(['/bin/ps','-axo','comm='],text=True)
    if any(Path(line.strip()).name=='buffy-macos' for line in listing.splitlines()):
        raise ValueError('Close the game before updating.')


def install(source,target,builder=build_launcher):
    source=Path(source).resolve();target=Path(target).resolve()
    new,old,changed=plan(source,target)
    game_closed()
    # One updater at a time; the lock is deliberately retained after a hard kill.
    artifacts=target/'artifacts'
    if artifacts.is_symlink():raise ValueError('Symbolic artifacts folder refused')
    artifacts.mkdir(exist_ok=True)
    lock=artifacts/'launcher-update.lock'
    try:lock.mkdir()
    except FileExistsError:raise ValueError('An update is running or was interrupted. Recover it before retrying.')
    work=artifacts/('launcher-update-'+uuid.uuid4().hex);work.mkdir()
    (lock/'work').write_text(work.name)
    (lock/'pid').write_text(str(os.getpid()))
    journal={'state':'preparing','pending':[],'existed':[],'from':old['version'],'to':new['version']}
    write_journal(work/'journal.json',journal)
    try:
        stage=work/'stage';stage.mkdir()
        for name in new['files']:
            dst=safe_path(stage,name);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(safe_path(source,name),dst)
        shutil.copy2(source/MANIFEST,stage/MANIFEST)
        emit(status='building',message='Building the launcher only. Your game and HD pack are reused.')
        builder(stage,work/'build.log')
        # Revalidate after the build: do not overwrite edits made while it ran.
        plan(source,target)
        game_closed()
        names=changed+[MANIFEST,APP]
        journal['existed']=[n for n in names if safe_path(target,n).exists()]
        journal['state']='installing';write_journal(work/'journal.json',journal)
        for name in names:
            journal['pending'].append(name);write_journal(work/'journal.json',journal)
            live=safe_path(target,name);backup=safe_path(work/'backup',name);incoming=safe_path(stage,name)
            if live.exists():
                backup.parent.mkdir(parents=True,exist_ok=True);os.replace(live,backup)
                if name in old['files'] and digest(backup)!=old['files'][name]['sha256']:
                    raise ValueError('Source changed during installation; rolling back: '+name)
            if incoming.exists():
                live.parent.mkdir(parents=True,exist_ok=True);os.replace(incoming,live)
        journal['state']='complete';write_journal(work/'journal.json',journal)
    except BaseException:
        restore(target,work,journal)
        raise
    finally:
        # Leave recovery information/lock in place if rollback itself failed.
        if journal['state'] in ('complete','rolled-back'):shutil.rmtree(lock)
    emit(status='complete',version=new['version'],message='Update installed. Quit and reopen the launcher.',backup=str(work/'backup'))


def recover(target):
    target=Path(target).resolve();lock=target/'artifacts/launcher-update.lock'
    if lock.is_symlink() or lock.parent.is_symlink():raise ValueError('Symbolic update state refused')
    pid=int((lock/'pid').read_text())
    try:os.kill(pid,0)
    except ProcessLookupError:pass
    else:raise ValueError('The updater process is still running; recovery refused.')
    name=(lock/'work').read_text()
    if not re.fullmatch('launcher-update-[0-9a-f]{32}',name):raise ValueError('Invalid recovery record')
    work=lock.parent/name
    if work.is_symlink():raise ValueError('Symbolic recovery folder refused')
    journal=json.loads((work/'journal.json').read_text())
    if journal['state'] not in ('complete','rolled-back'):restore(target,work,journal)
    shutil.rmtree(lock)
    emit(status='recovered',message='Previous interrupted update recovered.')


def choose_target():
    script='POSIX path of (choose folder with prompt "Choose your EXISTING btvs-recomp project folder (the one containing private, build and tools).")'
    result=subprocess.run(['/usr/bin/osascript','-e',script],capture_output=True,text=True)
    if result.returncode:raise ValueError('Folder selection cancelled')
    return Path(result.stdout.strip())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path);parser.add_argument('--source',type=Path)
    parser.add_argument('--choose-target',action='store_true');parser.add_argument('--check',action='store_true')
    parser.add_argument('--human',action='store_true')
    parser.add_argument('--tag');parser.add_argument('--recover',action='store_true')
    args=parser.parse_args()
    global HUMAN
    HUMAN=args.human
    target=choose_target() if args.choose_target else args.target
    if target is None:parser.error('--target is required')
    if args.recover:return recover(target)
    if args.source:return install(args.source,target)
    info=release_info(args.tag);current=(target/'VERSION').read_text().strip()
    available=version(info['tag_name'].removeprefix('v'))>version(current)
    if args.check:
        emit(status='available' if available else 'current',tag=info['tag_name'],version=info['tag_name'].removeprefix('v'),notes=info.get('body',''),url=info['html_url']);return
    if not available:raise ValueError('Already up to date')
    emit(status='downloading',message='Downloading and verifying the official source update.')
    with tempfile.TemporaryDirectory(prefix='btvs-update-') as folder:
        install(download_release(info,folder),target)


if __name__=='__main__':
    try:main()
    except (Exception,KeyboardInterrupt) as exc:
        emit(status='error',message=str(exc) or 'Update interrupted');sys.exit(1)
