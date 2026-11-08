"""Build, audit and install the optional prebuilt HD add-on, separately from source."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import zipfile

from safe_publish import publish_directory

ROOT = Path(__file__).resolve().parents[1]
PACK_ID = '1'
ARCHIVE = 'Buffy-macOS-HD-v1.zip'
MANIFEST = 'manifest.json'
MEMBERS = {
    'textures/campaign-ui-hd.xrtp': 'private/textures/campaign-ui-hd.xrtp',
    'textures/campaign-ui-hd.json': 'private/textures/campaign-ui-hd.json',
    'textures/original-text-hd.xrtp': 'private/textures/original-text-hd.xrtp',
    'textures/original-text-hd.json': 'private/textures/original-text-hd.json',
    'textures/font-hd.xrtp': 'private/textures/font-hd.xrtp',
    'launcher/logo.png': 'private/launcher/logo.png',
    'launcher/mist-1.png': 'private/launcher/mist-1.png',
    'launcher/mist-2.png': 'private/launcher/mist-2.png',
    'fonts/buffy-decorative/BuffyDecorative.ttf': 'private/fonts/buffy-decorative/BuffyDecorative.ttf',
}
RECIPES = ['font-hd.json', 'font-decorative-hd.json', 'menu-words-hd.json',
           'hud-hd.json', 'texture-pilot.json', 'texture-upscaler.json']
README = b'''Buffy macOS optional HD add-on, version 1

Install the supported game from your own ISO first. In the launcher, open
Packs & skins, choose Install HD pack, and select this ZIP without extracting it.
The installer verifies the pinned checksum, game edition and complete contents.
Textures HD and Text HD can be switched off independently in Options.

Includes the prepared campaign textures, HUD, reconstructed text and launcher art.
This is a manually prepared add-on; it is not regenerated from the ISO at setup.
No ISO, game executable, MAP, save, disk image, model or development master is here.

The project's MIT code license does not grant rights to these game-derived
graphics. Original Buffy artwork and trademarks belong to their respective
rights holders. This unofficial add-on is not endorsed by them. Third-party
fonts, model weights and upscaler programs are not bundled.
'''


def digest(stream):
    h = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        h.update(chunk)
    return h.hexdigest()


def file_digest(path):
    with Path(path).open('rb') as stream:
        return digest(stream)


def manifest_bytes(catalog):
    data = {k: catalog[k] for k in ('schema', 'id', 'xbe_sha256', 'recipes', 'files')}
    return (json.dumps(data, sort_keys=True, indent=2) + '\n').encode()


def load_catalog(root):
    catalog = json.loads((Path(root) / 'config/hd-pack.json').read_text())
    expected = set(MEMBERS) | {'README.txt'}
    if (catalog['schema'] != 1 or catalog['id'] != PACK_ID
            or set(catalog['files']) != expected or set(catalog['recipes']) != set(RECIPES)):
        raise ValueError('Unsupported HD catalog')
    for item in [catalog['archive']] + list(catalog['files'].values()):
        if (type(item['bytes']) is not int or not 0 < item['bytes'] <= 2 * 1024**3
                or not isinstance(item['sha256'], str) or len(item['sha256']) != 64
                or any(c not in '0123456789abcdef' for c in item['sha256'])):
            raise ValueError('Invalid HD size or checksum')
    if sum(item['bytes'] for item in catalog['files'].values()) > 2 * 1024**3:
        raise ValueError('HD add-on exceeds the installation budget')
    title = json.loads((Path(root) / 'config/title.json').read_text())
    if title['xbe_sha256'] != catalog['xbe_sha256']:
        raise ValueError('HD add-on targets another game edition')
    for name, expected in catalog['recipes'].items():
        if file_digest(Path(root) / 'config' / name) != expected:
            raise ValueError('HD add-on needs matching source recipes: ' + name)
    return catalog


def checked_archive(stream, catalog):
    """Use the same open file for the checksum and extraction, with bounded sizes."""
    if os.fstat(stream.fileno()).st_size != catalog['archive']['bytes']:
        raise ValueError('HD archive size differs from the release catalog')
    if digest(stream) != catalog['archive']['sha256']:
        raise ValueError('HD archive checksum differs from the release catalog')
    stream.seek(0)
    z = zipfile.ZipFile(stream)
    try:
        names = z.namelist()
        if (len(names) != len(set(n.casefold() for n in names))
                or set(names) != set(catalog['files']) | {MANIFEST}):
            raise ValueError('Unexpected or duplicate HD archive members')
        for info in z.infolist():
            expected = len(manifest_bytes(catalog)) if info.filename == MANIFEST else catalog['files'][info.filename]['bytes']
            if (info.file_size != expected or not stat.S_ISREG(info.external_attr >> 16)
                    or info.flag_bits & 1 or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                raise ValueError('Invalid HD archive member: ' + info.filename)
        if z.read(MANIFEST) != manifest_bytes(catalog):
            raise ValueError('HD manifest differs from the release catalog')
        return z
    except BaseException:
        z.close()
        raise


def stream_member(z, name, expected, destination=None):
    h = hashlib.sha256()
    count = 0
    with z.open(name) as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            count += len(chunk)
            if count > expected['bytes']:
                raise ValueError('HD member exceeds its size: ' + name)
            h.update(chunk)
            if destination is not None:
                destination.write(chunk)
    if count != expected['bytes'] or h.hexdigest() != expected['sha256']:
        raise ValueError('HD member checksum differs: ' + name)


def verify_installed(folder, catalog):
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError('Conflicting HD installation')
    paths = list(folder.rglob('*'))
    if any(p.is_symlink() for p in paths):
        raise ValueError('Symbolic HD installation refused')
    if {p.relative_to(folder).as_posix() for p in paths if p.is_file()} != set(catalog['files']) | {MANIFEST}:
        raise ValueError('Conflicting HD installation contents')
    if (folder / MANIFEST).read_bytes() != manifest_bytes(catalog):
        raise ValueError('Conflicting HD installation manifest')
    for name, expected in catalog['files'].items():
        p = folder / name
        if not p.is_file() or p.stat().st_size != expected['bytes'] or file_digest(p) != expected['sha256']:
            raise ValueError('Existing HD installation was changed: ' + name)


def install(archive, root=ROOT):
    from loadvars_fix import verify_xbe
    from texture_profiles import verify_local_pack
    root = Path(root)
    catalog = load_catalog(root)
    verify_xbe(root / 'private/game/Default.xbe', json.loads((root / 'config/title.json').read_text()))
    archive = Path(archive)
    if archive.is_symlink() or not archive.is_file():
        raise ValueError('Choose a regular HD ZIP file')
    parent = root / 'private/hd'
    for path in (root / 'private', parent):
        if path.is_symlink():
            raise ValueError('Symbolic HD destination refused')
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / PACK_ID
    with archive.open('rb') as source, checked_archive(source, catalog) as z:
        if target.exists() or target.is_symlink():
            verify_installed(target, catalog)
            return {'installed': True, 'already_present': True, 'id': PACK_ID}
        required = sum(item['bytes'] for item in catalog['files'].values()) + 64 * 1024**2
        if shutil.disk_usage(parent).free < required:
            raise ValueError('Not enough free space for the HD add-on')
        with tempfile.TemporaryDirectory(prefix='.install-', dir=parent) as staging:
            incoming = Path(staging) / PACK_ID
            incoming.mkdir()
            for name, expected in catalog['files'].items():
                path = incoming / name
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('xb') as out:
                    stream_member(z, name, expected, out)
                    out.flush()
                    os.fsync(out.fileno())
            (incoming / MANIFEST).write_bytes(manifest_bytes(catalog))
            for name in ('campaign-ui-hd', 'original-text-hd'):
                verify_local_pack(incoming / 'textures' / (name + '.xrtp'), catalog['xbe_sha256'])
            # The source catalog pins all prebuilt outputs. Publish only after
            # the complete add-on is validated, never over existing user files.
            publish_directory(incoming, target)
    return {'installed': True, 'already_present': False, 'id': PACK_ID}


def audit(archive, root=ROOT):
    catalog = load_catalog(root)
    with Path(archive).open('rb') as source, checked_archive(source, catalog) as z:
        for name, expected in catalog['files'].items():
            stream_member(z, name, expected)
    return {'verified': True, 'files': len(catalog['files']) + 1, 'id': PACK_ID}


def build(root, output):
    from texture_profiles import verify_profile
    root, output = Path(root), Path(output)
    verify_profile('campaign2x', root, 'hd')
    verify_profile('original', root, 'hd')
    title = json.loads((root / 'config/title.json').read_text())
    catalog = {'schema': 1, 'id': PACK_ID, 'xbe_sha256': title['xbe_sha256'],
               'recipes': {name: file_digest(root / 'config' / name) for name in RECIPES}, 'files': {}}
    for name, source in MEMBERS.items():
        path = root / source
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing or symbolic HD release input: ' + name)
        catalog['files'][name] = {'bytes': path.stat().st_size, 'sha256': file_digest(path)}
    catalog['files']['README.txt'] = {'bytes': len(README), 'sha256': hashlib.sha256(README).hexdigest()}
    output.mkdir(parents=True, exist_ok=True)
    archive = output / ARCHIVE
    # No directory walk: only these approved prebuilt outputs can enter the ZIP.
    with tempfile.TemporaryDirectory(prefix='.hd-build-', dir=output) as staging:
        temp = Path(staging) / ARCHIVE
        with zipfile.ZipFile(temp, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for name in sorted(set(MEMBERS) | {'README.txt', MANIFEST}):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                with z.open(info, 'w', force_zip64=True) as out:
                    if name in MEMBERS:
                        with (root / MEMBERS[name]).open('rb') as source:
                            shutil.copyfileobj(source, out, 1024 * 1024)
                    else:
                        out.write(README if name == 'README.txt' else manifest_bytes(catalog))
        catalog['archive'] = {'name': ARCHIVE, 'bytes': temp.stat().st_size, 'sha256': file_digest(temp)}
        # Verify sources did not change during compression before emitting a catalog.
        with temp.open('rb') as source, checked_archive(source, catalog) as z:
            for name, expected in catalog['files'].items():
                stream_member(z, name, expected)
        os.replace(temp, archive)
    (root / 'config/hd-pack.json').write_text(json.dumps(catalog, indent=2, sort_keys=True) + '\n')
    (output / 'HD-SHA256SUMS').write_text(catalog['archive']['sha256'] + '  ' + ARCHIVE + '\n')
    return catalog['archive']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('install', 'audit'):
        sub.add_parser(command).add_argument('archive', type=Path)
    sub.add_parser('build').add_argument('--output', type=Path, default=ROOT / 'artifacts/hd-release/dist')
    args = parser.parse_args()
    try:
        result = build(ROOT, args.output) if args.command == 'build' else globals()[args.command](args.archive)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, RuntimeError) as exc:
        raise SystemExit(str(exc))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
