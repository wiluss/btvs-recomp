"""Fetch only the pinned, public generic toolkit. Never download game content."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def git(*args, cwd=None):
    return subprocess.check_output(['git', *map(str,args)],cwd=cwd,text=True,stderr=subprocess.STDOUT).strip()


def bootstrap(root):
    root=Path(root)
    lock=json.loads((root/'dependencies.lock.json').read_text())['xboxrecomp']
    if lock['path'] != 'vendor/xboxrecomp':
        raise ValueError('Unexpected toolkit destination in dependencies.lock.json')
    revision=lock['revision']
    if len(revision)!=40 or any(c not in '0123456789abcdef' for c in revision):
        raise ValueError('Toolkit revision must be an exact Git commit')
    target=root/lock['path']
    if target.is_symlink():
        raise ValueError('Refusing a symbolic toolkit directory')
    if target.exists() and any(target.iterdir()):
        if not (target/'.git').exists():raise ValueError('Existing toolkit directory is not an initialized Git checkout; it was not changed')
        if git('-C',target,'rev-parse','HEAD') != revision:
            raise ValueError('Existing toolkit has a different revision; it was not changed')
        return target
    target.parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='.toolkit-',dir=target.parent))
    try:
        git('init','--quiet',staging)
        git('-C',staging,'remote','add','origin',lock['repository'])
        git('-C',staging,'fetch','--quiet','--depth','1','origin',revision)
        git('-C',staging,'checkout','--quiet','--detach','FETCH_HEAD')
        if git('-C',staging,'rev-parse','HEAD') != revision:
            raise ValueError('Fetched toolkit does not match the pinned commit')
        if target.exists():
            target.rmdir()  # Only an empty submodule placeholder can be removed.
        if target.exists() or target.is_symlink():
            raise ValueError('Toolkit destination appeared during download')
        # The source-release target is macOS. Use its exclusive directory
        # publication; Linux is supported here for source-only CI as well.
        if os.uname().sysname == 'Darwin':
            from safe_publish import publish_directory
            publish_directory(staging,target)
        else:
            staging.rename(target)
        return target
    finally:
        if staging.exists():shutil.rmtree(staging)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply-patches',action='store_true',help='apply the six shipped runtime patches to a clean pin')
    args=parser.parse_args()
    try:
        target=bootstrap(ROOT)
        print('Generic toolkit ready at pinned revision: '+str(target))
        if args.apply_patches:
            from setup_game import ensure_runtime
            logs=ROOT/'artifacts';logs.mkdir(exist_ok=True)
            with (logs/'runtime-bootstrap.log').open('w') as stream:ensure_runtime(ROOT,stream)
            print('Shipped runtime patches verified.')
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        raise SystemExit(str(exc))


if __name__=='__main__':main()
