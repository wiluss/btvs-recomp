"""Keep a title-bound HDD between launcher sessions."""
from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from fresh_hdd import create_hdd


@contextmanager
def persistent_hdd(profile, seed, title, *, check=False):
    profile = Path(profile).resolve()
    identity = {key: title[key] for key in ('title_id', 'xbe_sha256')}

    def validate():
        if profile.exists():
            stored = json.loads((profile/'title.json').read_text())
            if stored != identity or not (profile/'hdd').is_dir():
                raise ValueError('Profil de sauvegarde incompatible avec ce jeu')

    if check:
        validate()
        yield profile/'hdd'
        return

    profile.parent.mkdir(parents=True, exist_ok=True)
    with profile.with_name(profile.name+'.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Cette partie est déjà ouverte dans une autre session') from None
        validate()
        if not profile.exists():
            staging = Path(tempfile.mkdtemp(prefix=profile.name+'-', dir=profile.parent))
            try:
                if seed is None:
                    create_hdd(staging/'hdd', int(title['title_id'], 16))
                else:
                    subprocess.run(['cp', '-cR', str(seed), str(staging/'hdd')], check=True)
                (staging/'title.json').write_text(json.dumps(identity, indent=2)+'\n')
                staging.rename(profile)
            finally:
                if staging.exists():
                    shutil.rmtree(staging)
        yield profile/'hdd'
