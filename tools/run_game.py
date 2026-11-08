#!/usr/bin/env python3
"""Bounded diagnostic boot, with verified local XBE and isolated writable HDD.

A timeout, crash or even a clean return never establishes menu/gameplay success.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

if __package__:
    from .hdd_storage import storage_lock, prepared_hdd
else:
    from hdd_storage import storage_lock, prepared_hdd

ROOT = Path(__file__).resolve().parents[1]
LABEL_RE = re.compile(r'^[a-zA-Z0-9_-]{1,48}$')


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=int, default=30)
    parser.add_argument('--backend', choices=['metal', 'cpu'], default='metal')
    parser.add_argument('--debug', type=str, default='unimpl_trap,kick_event=1')
    parser.add_argument('--label', type=str, default='boot')
    args = parser.parse_args(argv)

    if not 1 <= args.seconds <= 300:
        raise SystemExit('Choose 1..300 seconds for a diagnostic run')
    if not LABEL_RE.fullmatch(args.label):
        raise SystemExit('Label must match [a-zA-Z0-9_-]{1,48}')
    return args


def _build_env(args):
    env = os.environ.copy()
    env.pop('RECOMP_GAME_FILES', None)  # template uses our exact Default.xbe path
    env['RECOMP_HDD_DIR'] = str(ROOT / 'build/hdd')
    env['RECOMP_PB_BACKEND'] = args.backend
    env['RECOMP_WATCHDOG_SECS'] = str(max(1, args.seconds - 5))
    env['RECOMP_DEBUG'] = args.debug
    env['RECOMP_STUB_LOG'] = '1'
    return env


def main():
    args = parse_args()
    title = json.loads((ROOT / 'config/title.json').read_text())
    sha = hashlib.sha256((ROOT / 'private/game/Default.xbe').read_bytes()).hexdigest()
    generation = json.loads((ROOT / 'artifacts/pipeline-recomp.json').read_text())
    if sha != title['xbe_sha256'] or sha != generation['xbe_sha256'] or generation['returncode']:
        raise SystemExit('Executable input/generation does not match manifest')

    env = _build_env(args)
    (ROOT / 'build/hdd').mkdir(parents=True, exist_ok=True)
    log_path = ROOT / 'logs' / f'{args.label}.log'
    artifact_path = ROOT / 'artifacts' / f'{args.label}.json'

    start = time.monotonic()
    timed_out = False
    with storage_lock(ROOT), prepared_hdd(ROOT/'build/hdd'), log_path.open('w') as log:
        child = subprocess.Popen([str(ROOT / 'build/game/buffy-macos')], cwd=ROOT, env=env,
                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            child.wait(timeout=args.seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()

    report = {
        'scope': 'diagnostic boot only',
        'seconds': round(time.monotonic() - start, 3),
        'returncode': child.returncode,
        'timed_out': timed_out,
        'xbe_sha256': sha,
        'backend': args.backend,
        'debug_mode': args.debug,
        'menu_verified': False,
        'gameplay_verified': False,
        'log': str(log_path.relative_to(ROOT))
    }
    artifact_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
