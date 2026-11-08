#!/usr/bin/env python3
"""Instantiate the pinned generic boot template; no guest overrides."""
import json
from pathlib import Path
import subprocess
from loadvars_fix import verify_xbe

ROOT = Path(__file__).resolve().parents[1]


def graphics_defaults(source):
    """Keep the port's timing before the optional layer caches environment."""
    anchor = '    recomp_env_init();'
    if source.count(anchor) != 2:
        raise ValueError('Pinned environment initialization differs')
    return source.replace(anchor,
        '#ifndef _WIN32\n'
        '    setenv("RECOMP_PRESENT_PACING", "spin", 0); /* port default */\n'
        '#endif\n' + anchor)


def main():
    lock = json.loads((ROOT / 'dependencies.lock.json').read_text())['xboxrecomp']
    vendor = ROOT / lock['path']
    revision = subprocess.check_output(['git', '-C', str(vendor), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != lock['revision']:
        raise SystemExit('Toolkit pin mismatch')
    title = json.loads((ROOT / 'config/title.json').read_text())
    if title['identification_status'] != 'identified_from_user_xbe':
        raise SystemExit('Identify the XBE first')
    verify_xbe(ROOT / 'private/game/Default.xbe', title)
    target = ROOT / 'generated/host'
    target.mkdir(parents=True, exist_ok=True)
    source = (vendor / 'templates/new-game/src/main.c').read_text()
    changes = {
        '#define YOUR_GAME_ENTRY_POINT   0x00000000  /* XBE entry point VA */':
        '#define YOUR_GAME_ENTRY_POINT   ' + title['entry_point'],
        '#define YOUR_GAME_XBE_PATH      "game\\\\Your Game Title\\\\default.xbe"':
        '#define YOUR_GAME_XBE_PATH      "private/game/Default.xbe"',
        '#define YOUR_GAME_DIR            "game\\\\Your Game Title"':
        '#define YOUR_GAME_DIR            "private/game"',
    }
    for original, replacement in changes.items():
        if source.count(original) != 1:
            raise SystemExit('Pinned template differs at ' + original)
        source = source.replace(original, replacement)
    source = source.replace('YOUR_GAME_NAME', 'Buffy macOS (experimental)')
    # The optional graphics layer defaults to sleep. Keep this port's timing
    # even with RECOMP_CONFIG=none, before recomp_env_init caches environment.
    # An explicitly supplied environment value remains available to diagnostics.
    source = graphics_defaults(source)
    # Apply the port's keyboard layout before the guest and input threads start.
    anchor = '    host_enhance_init();'
    if source.count(anchor) != 2:  # WinMain and POSIX main in the pinned template
        raise SystemExit('Pinned host initialization differs')
    source = '#include "controls.h"\n#include "widescreen.h"\n' + source.replace(
        anchor, anchor + '\n    buffy_ConfigureKeyboard();\n    buffy_ConfigureWidescreen();')

    (target / 'main.c').write_text(source)
    (target / 'recomp_manual.c').write_bytes((vendor / 'templates/new-game/src/recomp_manual.c').read_bytes())
    (target / 'provenance.json').write_text(json.dumps({
        'source':'vendor/xboxrecomp/templates/new-game/src', 'revision':revision,
        'license':'vendor/xboxrecomp/LICENSE', 'changes':'title, developer paths, inspected entry point, project AZERTY and opt-in HUD initialization, spin default before environment cache',
        'xbe_sha256':title['xbe_sha256'], 'game_overrides':[]}, indent=2) + '\n')


if __name__ == '__main__':
    main()
