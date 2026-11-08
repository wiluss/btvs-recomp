"""Keep dormant Xbox partition devices in standard gzip files, without changing bytes.

Partition0, saves, caches and ordinary files are never packed. Restore before
running the native executable directly; play.py handles this automatically.
"""
import argparse
from contextlib import contextmanager
import fcntl
import gzip
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SIZES = {1: 0x465400 * 512, 2: 0xFA000 * 512,
         3: 0x177000 * 512, 4: 0x177000 * 512, 5: 0x177000 * 512}
CHUNK = 8 * 1024 * 1024
ZERO = bytes(CHUNK)
_zero_members = {}


@contextmanager
def storage_lock(root, *, maintenance=False):
    path = Path(root) / 'private/hdd-storage.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as handle:
        try:
            fcntl.flock(handle, (fcntl.LOCK_EX if maintenance else fcntl.LOCK_SH) | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Disques en cours d’utilisation ou de maintenance') from None
        yield


def _identity(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def _regular(path):
    s = path.lstat()
    if not stat.S_ISREG(s.st_mode):
        raise ValueError('Fichier de partition non régulier : ' + str(path))
    return s


def _publish(temp, target, source, before):
    if target.exists() or target.is_symlink():
        raise ValueError('Les deux versions de la partition existent : ' + str(target))
    if _identity(_regular(source)) != _identity(before):
        raise ValueError('Partition modifiée pendant la maintenance : ' + str(source))
    shutil.copystat(source, temp, follow_symlinks=False)
    # Same-directory publication, no overwrite of an existing file.
    os.link(temp, target)
    temp.unlink()
    source.unlink()


def _pack(path, expected):
    before = _regular(path)
    if before.st_size != expected:
        raise ValueError('Taille de partition inattendue : ' + str(path))
    target = path.with_suffix('.img.gz')
    if target.exists() or target.is_symlink():
        raise ValueError('Archive déjà présente : ' + str(target))
    fd, name = tempfile.mkstemp(prefix='.partition-', dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, 'wb') as output, path.open('rb') as source:
            if _identity(os.fstat(source.fileno())) != _identity(before):
                raise ValueError('Partition remplacée pendant la maintenance')
            while True:
                block = source.read(CHUNK)
                if not block:
                    break
                zero = block == ZERO[:len(block)]
                member = _zero_members.get(len(block)) if zero else None
                if member is None:
                    member = gzip.compress(block, compresslevel=6, mtime=0)
                    if gzip.decompress(member) != block:
                        raise ValueError('Échec de vérification gzip')
                    if zero:
                        _zero_members[len(block)] = member
                output.write(member)
            output.flush()
            os.fsync(output.fileno())
        _publish(temp, target, path, before)
        return {'path': str(path), 'logical_bytes': expected, 'packed_bytes': target.stat().st_size}
    finally:
        if temp.exists():
            temp.unlink()


def _restore(archive, expected):
    before = _regular(archive)
    target = archive.with_suffix('')
    if target.exists() or target.is_symlink():
        raise ValueError('Image et archive présentes ; conservation des deux : ' + str(target))
    fd, name = tempfile.mkstemp(prefix='.partition-', dir=archive.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, 'wb') as output, archive.open('rb') as raw:
            if _identity(os.fstat(raw.fileno())) != _identity(before):
                raise ValueError('Archive remplacée pendant la maintenance')
            # Size first, and skip zero runs below. Actual extent allocation
            # remains filesystem-dependent; idle gzip size is the guarantee.
            output.truncate(expected)
            with gzip.GzipFile(fileobj=raw, mode='rb') as source:
                total = 0
                while True:
                    block = source.read(CHUNK)
                    if not block:
                        break
                    total += len(block)
                    if total > expected:
                        raise ValueError('Archive de partition trop grande')
                    if block == ZERO[:len(block)]:
                        output.seek(len(block), os.SEEK_CUR)
                    else:
                        output.write(block)
                if total != expected:
                    raise ValueError('Archive de partition tronquée')
                output.flush()
                os.fsync(output.fileno())
        _publish(temp, target, archive, before)
    finally:
        if temp.exists():
            temp.unlink()


def pack_hdd(hdd):
    records = []
    for part, size in SIZES.items():
        path = Path(hdd) / ('Partition%d.img' % part)
        if path.exists() or path.is_symlink():
            records.append(_pack(path, size))
    return records


def restore_hdd(hdd):
    for part, size in SIZES.items():
        archive = Path(hdd) / ('Partition%d.img.gz' % part)
        if archive.exists() or archive.is_symlink():
            _restore(archive, size)


@contextmanager
def prepared_hdd(hdd):
    """Caller holds storage_lock; all game writers must stop before exit."""
    hdd = Path(hdd)
    with (hdd/'.buffy-disk.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Ce disque est déjà ouvert') from None
        restore_hdd(hdd)
        try:
            yield
        finally:
            try:
                pack_hdd(hdd)
            except (OSError, ValueError, EOFError) as exc:
                # Keep the raw file on failure. Never turn a successful save
                # into a launch error just because compaction was unavailable.
                print('Compaction différée, disques conservés : '+str(exc), file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['pack', 'restore'])
    parser.add_argument('hdd', nargs='*', type=Path)
    parser.add_argument('--all-local', action='store_true', help='disques locaux sous build, artifacts et private/profile')
    parser.add_argument('--apply', action='store_true', help='sans cette option : inventaire seulement')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if not args.hdd and not args.all_local:
        parser.error('Choisir un dossier HDD ou --all-local')
    # Also catch direct diagnostic launches that do not take storage_lock.
    running = subprocess.run(['pgrep', '-x', 'buffy-macos'], capture_output=True)
    if running.returncode != 1:
        raise SystemExit('Fermer le jeu avant la maintenance des disques')
    result = {'action': args.action, 'applied': args.apply, 'disks': [], 'errors': []}
    with storage_lock(ROOT, maintenance=True):
        folders = set(args.hdd)
        if args.all_local:
            for base in (ROOT/'build', ROOT/'artifacts', ROOT/'private/profile'):
                for folder, dirs, files in os.walk(base, followlinks=False):
                    if 'Partition0.img' in files:
                        folders.add(Path(folder))
        for i, folder in enumerate(sorted(folders), 1):
            try:
                if folder.is_symlink():
                    raise ValueError('Dossier HDD symbolique refusé')
                if args.apply:
                    details = pack_hdd(folder) if args.action == 'pack' else restore_hdd(folder)
                else:
                    details = [str(p) for p in folder.glob('Partition[1-5].img*')]
                result['disks'].append({'hdd': str(folder), 'files': details})
            except (OSError, ValueError, EOFError) as exc:
                result['errors'].append({'hdd': str(folder), 'error': str(exc)})
            if i % 20 == 0:
                print('%d/%d disques vérifiés' % (i, len(folders)), flush=True)
    if args.report:
        args.report.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'disks': len(result['disks']), 'errors': result['errors'], 'applied': args.apply}))
    if result['errors']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
