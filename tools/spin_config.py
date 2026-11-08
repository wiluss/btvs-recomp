"""Bind project-owned spin-wait selections to their identified input XBE."""
import json


def verify(path, xbe_sha256):
    doc = json.loads(path.read_text())
    about = doc.get('about') if isinstance(doc, dict) else None
    if not isinstance(about, dict) or about.get('xbe_sha256') != xbe_sha256:
        raise ValueError('Spin-wait selection does not match the identified XBE')


def verify_arguments(arguments, xbe_sha256):
    from pathlib import Path
    for i, arg in enumerate(arguments):
        if arg == '--spin-waits':
            if i + 1 >= len(arguments):
                raise ValueError('--spin-waits requires a path')
            verify(Path(arguments[i + 1]), xbe_sha256)
        elif arg.startswith('--spin-waits='):
            verify(Path(arg.split('=', 1)[1]), xbe_sha256)
