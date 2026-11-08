"""Bounded, transactional import of the player's supported Xbox disc.

Reuses the pinned MIT XboxRecomp XDVDFS reader for descriptor discovery;
strict directory validation below deliberately replaces its permissive listing.
No game data is shipped with this tool.
"""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import struct
import tempfile
from safe_publish import publish_directory

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('_buffy_xdvdfs', ROOT/'vendor/xboxrecomp/tools/xiso/xdvdfs.py')
xdvdfs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xdvdfs)
MAX_DIRECTORY = 8 * 1024 * 1024
MAX_TREE_BYTES = 64 * 1024 * 1024
MAX_EXTRACTED = 32 * 1024**3


def identity(s):
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns


def safe_name(name):
    if (not name or name in ('.', '..') or name[-1] in ' .'
            or any(ord(c) < 32 or ord(c) >= 127 or c in '/\\:*?"<>|' for c in name)):
        raise ValueError('Nom de fichier non pris en charge dans l’ISO')
    return name


class Disc(xdvdfs.Xiso):
    def __init__(self, path):
        self.path = str(Path(path).resolve(strict=True))
        self.before = Path(self.path).stat()
        if not stat.S_ISREG(self.before.st_mode):
            raise ValueError('Choisir un fichier ISO local régulier')
        try:
            super().__init__(self.path)
            if identity(os.fstat(self._f.fileno())) != identity(self.before):
                raise ValueError('ISO remplacée pendant l’ouverture')
            desc = self._read_at(32, xdvdfs.SECTOR)
            if desc[-len(xdvdfs.MAGIC):] != xdvdfs.MAGIC:
                raise ValueError('Descripteur ISO incomplet')
        except BaseException as exc:
            if hasattr(self, '_f'):
                self._f.close()
            if isinstance(exc, xdvdfs.XisoError):
                raise ValueError('Image Xbox non reconnue ou format non pris en charge') from exc
            raise

    def unchanged(self):
        if (identity(os.fstat(self._f.fileno())) != identity(self.before)
                or identity(Path(self.path).stat()) != identity(self.before)):
            raise ValueError('L’ISO a changé pendant la préparation')

    def extent(self, sector, size):
        offset = self.base + sector * xdvdfs.SECTOR
        if size < 0 or offset < self.base or offset + size > self.before.st_size:
            raise ValueError('Données hors des limites de l’ISO')
        return offset

    def _read_at(self, sector, size):
        self._f.seek(self.extent(sector, size))
        data = self._f.read(size)
        if len(data) != size:
            raise ValueError('ISO tronquée')
        return data

    def _read_dir(self, sector, size):
        if not 0 < size <= MAX_DIRECTORY:
            raise ValueError('Table de dossier ISO invalide ou trop grande')
        data = self._read_at(sector, size)
        entries = []
        names = set()
        for start in range(0, size, xdvdfs.SECTOR):
            chunk = data[start:start+xdvdfs.SECTOR]
            offset = 0
            while offset < len(chunk):
                tail = chunk[offset:]
                if not tail.strip(b'\0') or not tail.strip(b'\xff'):
                    break
                if len(tail) < 14:
                    raise ValueError('Entrée de dossier tronquée')
                left, right, sec, length, flags, count = struct.unpack_from('<HHIIBB', tail)
                if left == right == 0xffff:
                    if any(b != 0xff for b in tail):
                        raise ValueError('Remplissage de dossier ambigu')
                    break
                if not count or 14+count > len(tail):
                    raise ValueError('Nom de fichier tronqué dans l’ISO')
                name = safe_name(tail[14:14+count].decode('ascii'))
                if name.casefold() in names:
                    raise ValueError('Noms de fichiers en conflit dans l’ISO')
                names.add(name.casefold())
                self.extent(sec, length)
                entries.append(xdvdfs.DirEntry(name, sec, length, flags))
                offset += (14+count+3) & ~3
        return entries

    def inventory(self):
        pending = [(PurePosixPath(), self.root_sector, self.root_size, 0)]
        seen = set()
        files = []
        self.directories = []
        total = tree_bytes = entry_count = 0
        while pending:
            folder, sector, size, depth = pending.pop()
            if depth > 32 or (sector, size) in seen:
                raise ValueError('Arborescence ISO cyclique ou trop profonde')
            seen.add((sector, size))
            tree_bytes += size
            if tree_bytes > MAX_TREE_BYTES:
                raise ValueError('Arborescence ISO trop grande')
            for entry in self._read_dir(sector, size):
                entry_count += 1
                path = folder/entry.name
                if entry_count > 200000 or len(str(path)) > 220:
                    raise ValueError('Arborescence ISO non prise en charge')
                if entry.is_dir:
                    self.directories.append(path)
                    if entry.size:
                        pending.append((path, entry.sector, entry.size, depth+1))
                else:
                    files.append((path, entry))
                    total += entry.size
                    if total > MAX_EXTRACTED:
                        raise ValueError('Contenu extrait trop volumineux')
        return files, total

    def hash_entry(self, entry):
        self._f.seek(self.extent(entry.sector, entry.size))
        remaining = entry.size
        digest = hashlib.sha256()
        while remaining:
            data = self._f.read(min(1024*1024, remaining))
            if not data:
                raise ValueError('ISO tronquée')
            digest.update(data)
            remaining -= len(data)
        return digest.hexdigest()

    def verify_title(self, files, title):
        xbe = [(p,e) for p,e in files if str(p).casefold() == 'default.xbe']
        maps = [(p,e) for p,e in files if p.name.casefold() == 'final.map']
        if len(xbe) != 1:
            raise ValueError('Default.xbe absent de la racine de l’ISO')
        if len(maps) != 1:
            raise ValueError('final.map absent ou ambigu dans l’ISO ; cette édition ne peut pas être préparée')
        if not 0 < xbe[0][1].size <= 32*1024**2 or not 0 < maps[0][1].size <= 64*1024**2:
            raise ValueError('Taille des fichiers de construction non prise en charge')
        if self.hash_entry(xbe[0][1]) != title['xbe_sha256']:
            raise ValueError('Cette édition de Buffy n’est pas encore prise en charge (XBE différent)')
        if self.hash_entry(maps[0][1]) != title['symbols']['map_sha256']:
            raise ValueError('final.map ne correspond pas à l’édition prise en charge')
        self.unchanged()
        return xbe[0][0], maps[0][0]


def inspect_disc(iso, title):
    with Disc(iso) as disc:
        files, total = disc.inventory()
        xbe, mapping = disc.verify_title(files, title)
        return {'compatible': True, 'files': len(files), 'extracted_bytes': total,
                'partition_offset': disc.base, 'xbe': str(xbe), 'map': str(mapping),
                'xbe_sha256': title['xbe_sha256'], 'map_sha256': title['symbols']['map_sha256']}


def import_disc(iso, destination, title, progress=lambda event: None):
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError('Une installation existe déjà ; elle est conservée')
    # Validate compatibility before creating a destination or copying assets.
    with Disc(iso) as disc:
        files, total = disc.inventory()
        xbe_path, map_path = disc.verify_title(files, title)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with (destination.parent/'.iso-import.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('Une préparation est déjà en cours') from None
            if destination.exists() or destination.is_symlink():
                raise ValueError('Une installation existe déjà ; elle est conservée')
            if shutil.disk_usage(destination.parent).free < total + 512*1024**2:
                raise ValueError('Espace disque insuffisant pour extraire le jeu')
            staging = Path(tempfile.mkdtemp(prefix='.buffy-import-', dir=destination.parent))
            try:
                for folder in disc.directories:
                    (staging/folder).mkdir(parents=True, exist_ok=True)
                done = 0
                for path, entry in files:
                    normalized = ('Default.xbe' if path == xbe_path else
                                  'final.map' if path == map_path and len(path.parts) == 1 else path)
                    target = staging/normalized
                    target.parent.mkdir(parents=True, exist_ok=True)
                    # The tree and every component have already been validated.
                    disc.extract(entry, str(target))
                    if target.stat().st_size != entry.size:
                        raise ValueError('Extraction incomplète')
                    done += entry.size
                    progress({'stage': 'extract', 'done': done, 'total': total})
                if len(map_path.parts) > 1:
                    shutil.copyfile(staging/map_path, staging/'final.map')
                # Recheck the two exact build inputs after extraction.
                for name, expected in [('Default.xbe', title['xbe_sha256']), ('final.map', title['symbols']['map_sha256'])]:
                    if hashlib.sha256((staging/name).read_bytes()).hexdigest() != expected:
                        raise ValueError('Vérification après extraction échouée')
                disc.unchanged()
                if destination.exists() or destination.is_symlink():
                    raise ValueError('Destination créée pendant la préparation ; aucune installation remplacée')
                publish_directory(staging, destination)
            finally:
                if staging.exists():
                    shutil.rmtree(staging)
    return {'imported': True, 'files': len(files), 'extracted_bytes': total,
            'xbe_sha256': title['xbe_sha256'], 'map_sha256': title['symbols']['map_sha256'],
            'menu_validated': False, 'gameplay_validated': False}
