#!/usr/bin/env python3
"""Report preparation status; never installs or modifies system software."""
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    lock = json.loads((ROOT / 'dependencies.lock.json').read_text())['xboxrecomp']
    runtime = ROOT / lock['path']
    head = None
    if (runtime / '.git').exists():
        result = subprocess.run(['git','-C',str(runtime),'rev-parse','HEAD'], capture_output=True,text=True)
        if result.returncode == 0:
            head = result.stdout.strip()
    report = {
        'platform':platform.platform(), 'architecture':platform.machine(),
        'python':platform.python_version(),
        'tools':{name:shutil.which(name) for name in ['git','clang','make','cmake','ninja','pkg-config','uv','codex','lms']},
        'lm_studio_app_in_standard_locations':any(p.exists() for p in [Path('/Applications/LM Studio.app'),Path.home()/'Applications/LM Studio.app']),
        'toolkit_revision':head, 'toolkit_matches_lock':head == lock['revision'],
        'game_xbe_candidates':[p.name for p in (ROOT/'private/game').glob('*') if p.suffix.lower() == '.xbe'],
        'isolated_python_present':(ROOT/'.venv/bin/python').exists(),
        'local_model_probe_report':'artifacts/local-probe.json' if (ROOT/'artifacts/local-probe.json').exists() else None,
        'note':'Read-only dependency inventory. A past probe report does not establish current server/model state.'
    }
    print(json.dumps(report, indent=2))
    return 0 if head == lock['revision'] else 1


if __name__ == '__main__':
    sys.exit(main())
