"""Build and audit an explicit source-only release; no Git staging or upload."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import stat
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
CONFIG='release/files.json'
MANIFEST='RELEASE_MANIFEST.json'
BLOCKED_DIRS={'.git','.venv','private','generated','build','artifacts','logs','__pycache__','vendor'}
BLOCKED_SUFFIXES={'.iso','.xiso','.xbe','.map','.ses','.img','.xrtp','.png','.jpg','.jpeg','.bmp',
                  '.ttf','.otf','.icns','.gguf','.safetensors','.mlmodel','.log','.dylib','.a','.o','.pyc','.zip'}
ALLOWED_SUFFIXES={'.md','.txt','.json','.py','.c','.h','.swift','.sh','.patch','.yml','.yaml'}
LOCAL_HOME=str(Path.home()).rstrip('/')+'/'
SECRET=re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{32,})')


def check_text(data,name):
    if data.startswith((b'XBEH',b'XRTP',b'FATX',b'MZ',b'PK\x03\x04',b'\xcf\xfa\xed\xfe')):
        raise ValueError('Binary/game header in source: '+name)
    text=data.decode('utf-8')
    if ('\0' in text or LOCAL_HOME in text or SECRET.search(text)
            or any(p in text for p in ('-----BEGIN '+'PRIVATE KEY-----','-----BEGIN '+'OPENSSH PRIVATE KEY-----'))):
        raise ValueError('Private or binary content in release source: '+name)


def checked_path(value):
    if not isinstance(value,str) or not value or any(ord(c)<32 or c in '\\:' for c in value):
        raise ValueError('Invalid release path')
    p=PurePosixPath(value)
    if (p.is_absolute() or any(s in ('','.','..') for s in value.split('/'))
            or any(s.casefold() in BLOCKED_DIRS for s in p.parts)
            or p.suffix.casefold() in BLOCKED_SUFFIXES):
        raise ValueError('Forbidden release path: '+value)
    if p.suffix.casefold() not in ALLOWED_SUFFIXES and value not in {'LICENSE','VERSION','Makefile','.gitignore','.gitmodules'}:
        raise ValueError('Unexpected release file type: '+value)
    return p


def source_bytes(root,name):
    relative=checked_path(name);path=Path(root)
    for part in relative.parts:
        path=path/part
        if path.is_symlink():raise ValueError('Symbolic release source refused: '+name)
    if not stat.S_ISREG(path.stat().st_mode) or path.stat().st_size>2*1024**2:
        raise ValueError('Unexpected release source: '+name)
    data=path.read_bytes()
    check_text(data,name)
    return data


def entries(root):
    spec=json.loads((Path(root)/CONFIG).read_text())
    if set(spec)!={'version','files'} or spec['version']!=(Path(root)/'VERSION').read_text().strip():
        raise ValueError('Release version/configuration mismatch')
    version=spec['version']
    if not version or len(version)>64 or any(c not in '0123456789abcdefghijklmnopqrstuvwxyz.-' for c in version):
        raise ValueError('Unsafe version')
    seen=set();result={}
    for entry in spec['files']:
        if set(entry)!={'source','path'}:raise ValueError('Invalid release entry')
        source=entry['source'];name=entry['path'];checked_path(name)
        if name.casefold() in seen:raise ValueError('Duplicate release path: '+name)
        seen.add(name.casefold());result[name]=source_bytes(root,source)
    mandatory={CONFIG,'VERSION','LICENSE','README.md','THIRD_PARTY_NOTICES.md','Makefile','CMakeLists.txt',
               'dependencies.lock.json','tools/bootstrap_runtime.py','tools/setup_game.py',
               'release/licenses/XboxRecomp-MIT.txt','release/licenses/XboxRecomp-NOTICE.txt','release/licenses/LGPL-2.1.txt'}
    if not mandatory<=set(result):
        raise ValueError('Missing mandatory release source')
    dependency=json.loads(result['dependencies.lock.json'])['xboxrecomp']
    if not set(dependency['runtime_patches'])<=set(result):raise ValueError('Missing shipped runtime patch')
    # The exported kit rebuilds from its canonical paths. Private maintainer
    # histories are replaced by explicitly listed English public documents.
    normalized={'version':version,'files':[{'source':p,'path':p} for p in sorted(result)]}
    result[CONFIG]=(json.dumps(normalized,indent=2)+'\n').encode()
    return version,result


def build(root,output):
    version,files=entries(root)
    manifest={'version':version,'scope':'project source only; player supplies the ISO',
              'files':{p:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for p,data in sorted(files.items())}}
    files[MANIFEST]=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    archive=output/('Buffy-macOS-v'+version+'-source.zip')
    fd,name=tempfile.mkstemp(prefix='.source-',dir=output);os.close(fd);temp=Path(name)
    try:
        with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for path,data in sorted(files.items()):
                info=zipfile.ZipInfo(path,date_time=(1980,1,1,0,0,0));info.create_system=3
                mode=0o755 if path.endswith('.sh') else 0o644
                info.external_attr=(stat.S_IFREG|mode)<<16;info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        audit(temp)
        os.replace(temp,archive)
    finally:
        if temp.exists():temp.unlink()
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    (output/'SHA256SUMS').write_text(digest+'  '+archive.name+'\n')
    return {'archive':str(archive),'sha256':digest,'files':len(files),'bytes':archive.stat().st_size,'version':version}


def audit(archive):
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        if len(names)!=len(set(n.casefold() for n in names)):raise ValueError('Duplicate ZIP entry')
        if MANIFEST not in names:raise ValueError('Missing release manifest')
        if sum(i.file_size for i in z.infolist())>64*1024**2:raise ValueError('Unexpected archive size')
        manifest=json.loads(z.read(MANIFEST));files=manifest['files']
        if set(names)!=set(files)|{MANIFEST}:raise ValueError('Unlisted ZIP content')
        for info in z.infolist():
            if info.filename==MANIFEST:continue
            checked_path(info.filename)
            if info.file_size>2*1024**2 or not stat.S_ISREG(info.external_attr>>16):raise ValueError('Unexpected ZIP entry')
            data=z.read(info)
            if len(data)!=files[info.filename]['bytes'] or hashlib.sha256(data).hexdigest()!=files[info.filename]['sha256']:
                raise ValueError('ZIP content differs from its manifest')
            check_text(data,info.filename)
    return {'files':len(names),'version':manifest['version'],'verified':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/release-alpha/dist')
    parser.add_argument('--audit',type=Path)
    args=parser.parse_args()
    try:result=audit(args.audit) if args.audit else build(ROOT,args.output)
    except (OSError,ValueError,KeyError,UnicodeError,zipfile.BadZipFile) as exc:raise SystemExit(str(exc))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
