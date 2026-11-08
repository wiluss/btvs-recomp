"""Prepare the player's ISO in this source checkout, never download game data.

--inspect only reads the image. --build installs Python packages into the local
venv, applies the shipped runtime patches to a clean pinned submodule, and
builds locally. No model, private save or previously generated file is needed.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tempfile

from disc_import import import_disc, inspect_disc
from loadvars_fix import verify_xbe

ROOT = Path(__file__).resolve().parents[1]


def event(stage, **values):
    print(json.dumps({'stage': stage, **values}, ensure_ascii=False), flush=True)


def run(command, root, log, *, cwd=None):
    log.write('\n'+repr([str(x) for x in command])+'\n'); log.flush()
    child = subprocess.Popen([str(x) for x in command], cwd=cwd or root,
                             stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        code = child.wait()
        if code:
            raise ValueError('Une étape de préparation a échoué ; consulter le journal')
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()


def ensure_runtime(root, log):
    lock = json.loads((root/'dependencies.lock.json').read_text())['xboxrecomp']
    vendor = root/lock['path']
    head = subprocess.check_output(['git','-C',str(vendor),'rev-parse','HEAD'], text=True).strip()
    if head != lock['revision']:
        raise ValueError('La version des outils Xbox ne correspond pas au projet')
    patched = subprocess.run(['make','runtime-patch-check'], cwd=root, stdout=log, stderr=log)
    if patched.returncode == 0:
        return
    status = subprocess.check_output(['git','-C',str(vendor),'status','--porcelain'], text=True)
    if status.strip():
        raise ValueError('Outils Xbox partiellement modifiés ; aucune modification existante remplacée')
    patches = [root/p for p in lock['runtime_patches']]
    if len(patches) != 6 or not all(p.is_file() for p in patches):
        raise ValueError('Jeu de correctifs runtime incomplet')
    # Exercise the complete sequence on a copy before modifying the submodule.
    with tempfile.TemporaryDirectory(prefix='buffy-patch-check-') as folder:
        candidate = Path(folder)/'runtime'
        shutil.copytree(vendor, candidate, ignore=shutil.ignore_patterns('.git', '__pycache__'))
        for patch in patches:
            run(['git','apply',patch],root,log,cwd=candidate)
    event('patches')
    for patch in patches:
        run(['git','apply',patch],root,log,cwd=vendor)
    run(['make','runtime-patch-check'],root,log)


def preflight(root):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise ValueError('Cette alpha nécessite un Mac Apple Silicon')
    missing = [name for name in ('git','make','clang','cmake','ninja','pkg-config') if not shutil.which(name)]
    python = shutil.which('python3.12') or ('/opt/homebrew/bin/python3.12' if Path('/opt/homebrew/bin/python3.12').is_file() else None)
    if missing or not python:
        raise ValueError('Outils de compilation manquants. Suivre docs/SETUP.md avant de préparer l’ISO')
    pkg_env = dict(os.environ)
    pkg_env['PKG_CONFIG_PATH'] = '/opt/homebrew/opt/openssl@3/lib/pkgconfig' + (':'+pkg_env['PKG_CONFIG_PATH'] if pkg_env.get('PKG_CONFIG_PATH') else '')
    result = subprocess.run(['pkg-config','--exists','sdl3','epoxy','openssl'],env=pkg_env)
    if result.returncode:
        raise ValueError('Bibliothèques SDL3, libepoxy ou OpenSSL manquantes ; suivre docs/SETUP.md')
    if shutil.disk_usage(root).free < 30*1024**3:
        raise ValueError('Prévoir au moins 30 Gio libres pour la préparation et la compilation')
    return Path(python)


def build_game(root, title, log):
    python = preflight(root)
    ensure_runtime(root, log)
    interpreter = root/'.venv/bin/python'
    if not interpreter.is_file():
        event('tools')
        run([python,'-m','venv',root/'.venv'], root, log)
    run([interpreter,'-m','pip','install','--disable-pip-version-check','-r',root/'requirements-toolkit.txt'],root,log)
    # The pipeline verifies both exact inputs again before generation.
    event('generate')
    (root/'artifacts').mkdir(exist_ok=True)
    run([interpreter,root/'tools/pipeline.py'],root,log)
    event('compile')
    run(['make','game-build'],root,log)
    binary = root/'build/game/buffy-macos'
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise ValueError('Compilation incomplète')
    # A new installation uses original graphics until local HD recipes exist.
    prefs = root/'private/config/graphics.json'
    if not prefs.exists():
        from graphics_settings import DEFAULTS, save_settings
        save_settings(prefs, DEFAULTS)
    return hashlib.sha256(binary.read_bytes()).hexdigest()


def main():
    # Finder does not normally inherit the user's Homebrew shell PATH.
    os.environ['PATH'] = '/opt/homebrew/bin:/opt/homebrew/sbin:' + os.environ.get('PATH','/usr/bin:/bin')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('iso', type=Path)
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args()
    title = json.loads((ROOT/'config/title.json').read_text())
    try:
        event('inspect')
        report = inspect_disc(args.iso, title)
        if args.inspect:
            event('inspected', **report)
            return
        if args.build:
            preflight(ROOT)  # Refuse missing build prerequisites before copying.
        work = ROOT/'private/setup'
        work.mkdir(parents=True, exist_ok=True)
        with (work/'setup.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('Une préparation est déjà en cours') from None
            with (work/'setup.log').open('a') as log:
                destination = ROOT/'private/game'
                receipt = work/'import.json'
                if destination.exists():
                    # Resume only our own completed import, never adopt or
                    # overwrite the user's existing development installation.
                    if not receipt.is_file():
                        raise ValueError('Une installation existe déjà ; elle est conservée')
                    saved = json.loads(receipt.read_text())
                    verify_xbe(destination/'Default.xbe', title)
                    if (saved.get('xbe_sha256') != title['xbe_sha256']
                            or hashlib.sha256((destination/'final.map').read_bytes()).hexdigest() != title['symbols']['map_sha256']):
                        raise ValueError('Installation importée différente ; aucune donnée remplacée')
                else:
                    report = import_disc(args.iso,destination,title,progress=lambda e: event(**e))
                    receipt.write_text(json.dumps(report,indent=2)+'\n')
                if args.build:
                    digest = build_game(ROOT,title,log)
                    record = {**report,'binary_sha256':digest,'built':True,'menu_validated':False,'gameplay_validated':False}
                    (work/'build.json').write_text(json.dumps(record,indent=2)+'\n')
                    event('ready')
                else:
                    event('imported')
    except KeyboardInterrupt:
        event('cancelled')
        raise SystemExit(130)
    except (OSError, ValueError, EOFError, subprocess.SubprocessError) as exc:
        event('error', message=str(exc))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
