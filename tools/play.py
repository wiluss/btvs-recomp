#!/usr/bin/env python3
"""Launch the title with persistent graphics settings and same-title restarts.

Each session copies the reference or selected HDD. A quick reboot reuses that copy.
"""
import argparse
from contextlib import ExitStack
from itertools import count
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import struct
import subprocess
import tempfile
import time

from control_settings import control_environment
from hdd_storage import storage_lock, prepared_hdd
from fresh_hdd import create_hdd
from graphics_settings import load_settings, save_settings, settings_environment, validate_settings, render_dimensions
from loadvars_fix import verify_xbe
from save_profile import persistent_hdd
from texture_profiles import PROFILES, verify_local_pack, verify_profile

ROOT = Path(__file__).resolve().parents[1]
PAGE_SHA256 = '60f731383fa8bc62b6a09acbe03368472e255d1039c5b558ba9604c3bc6352a4'
MAX_RELAUNCHES = 16


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['menu', 'mission'], nargs='?', default='mission')
    resolution = p.add_mutually_exclusive_group()
    resolution.add_argument('--scale', type=int, choices=range(1,5), help='facteur de résolution interne (1..4), appliqué au format choisi')
    resolution.add_argument('--resolution', choices=['scale', '4k'], help='4k : sortie 3840×2160 en 16:9')
    p.add_argument('--filter', choices=['nearest', 'linear'])
    p.add_argument('--aspect', choices=['4:3', '16:9'], help='champ horizontal, sans étirement')
    p.add_argument('--hud', choices=['edges', 'safe'], help='barres de vie aux bords ou zone centrale 4:3')
    texture = p.add_mutually_exclusive_group()
    texture.add_argument('--textures', choices=PROFILES, help='textures originales ou pack HD local')
    texture.add_argument('--texture-pack', type=Path, help='pack XRTP local pour cette session')
    p.add_argument('--text', choices=['auto','original','hd'], help='texte du pack, police originale ou reconstruction HD')
    arena = p.add_mutually_exclusive_group()
    arena.add_argument('--unlock-arenas', dest='arenas', action='store_true', help='afficher les quatre arènes dès l’ouverture d’Extras')
    arena.add_argument('--no-unlock-arenas', dest='arenas', action='store_false', help='garder le déblocage d’origine')
    p.set_defaults(arenas=None)
    for key, opposite in [('fps','no-fps'), ('fullscreen','windowed'), ('vsync','no-vsync')]:
        group = p.add_mutually_exclusive_group()
        group.add_argument('--'+key, dest=key, action='store_true')
        group.add_argument('--'+opposite, dest=key, action='store_false')
        p.set_defaults(**{key:None})
    p.add_argument('--seconds', type=int, default=0, help='durée maximale, 0 = illimitée, sinon 1..3600 s')
    p.add_argument('--hdd', type=Path, help='dossier d’une partie précédente à copier en mode menu')
    p.add_argument('--profile', type=Path, help='profil conservant les sauvegardes entre sessions en mode menu')
    p.add_argument('--temporary-hdd', action='store_true', help='copie HDD de diagnostic pour cette session')
    p.add_argument('--settings-file', type=Path, default=ROOT/'private/config/graphics.json',
                   help='profil graphique JSON, par défaut private/config/graphics.json')
    p.add_argument('--check', action='store_true', help='vérifier sans lancer ni sauvegarder')
    p.add_argument('--show-settings', action='store_true', help='afficher sans modifier de fichier')
    p.add_argument('--save-settings', action='store_true', help='sauvegarder les réglages sans lancer')
    args = p.parse_args(argv)
    if not 0 <= args.seconds <= 3600:
        p.error('--seconds doit être compris entre 0 et 3600 (0 = illimité)')
    if args.texture_pack and args.save_settings:
        p.error('--texture-pack sélectionne un pack pour une session')
    if args.hdd is not None and (args.mode != 'menu' or args.save_settings):
        p.error('--hdd sélectionne un disque pour une session en mode menu')
    if args.profile is not None and (args.mode != 'menu' or args.save_settings):
        p.error('--profile conserve une partie en mode menu')
    if args.temporary_hdd and args.profile:
        p.error('--temporary-hdd et --profile sont incompatibles')
    if args.mode == 'menu' and not (args.profile or args.hdd or args.temporary_hdd or args.save_settings):
        args.profile = ROOT/'private/profile'
    return args


def selected_settings(args, path):
    settings = load_settings(path)
    settings.update({k:getattr(args,k) for k in settings if getattr(args,k,None) is not None})
    if args.scale is not None:
        settings['resolution'] = 'scale'
    if args.resolution == '4k' and args.aspect is None:
        settings['aspect'] = '16:9'
    return validate_settings(settings)


def presentation_settings(settings, mode):
    return dict(settings, aspect='4:3') if mode == 'menu' else settings


def hdd_source(mode, selected, title_id):
    if selected is None:
        if mode == 'menu':
            return None  # New players start from a generated blank disk.
        baseline = ROOT/'build/relaunch-capture-hdd'
        if not baseline.is_dir():
            raise ValueError('État HDD de test absent : '+str(baseline))
        return baseline

    baseline = selected.resolve(strict=True)
    saves = baseline/'UDATA'/f'{title_id:08X}'
    if not ((baseline/'Partition0.img').is_file() and (baseline/'Cache').is_dir()
            and saves.is_dir()):
        raise ValueError('Dossier de partie Buffy non reconnu : '+str(baseline))
    return baseline


def build_environment(settings, hdd, seconds, inherited=None, *, mode='mission'):
    inherited = os.environ if inherited is None else inherited
    env = {k:v for k,v in inherited.items() if not k.startswith('RECOMP_') and k != 'BUFFY_INPUT_PROFILE'}
    env.update(settings_environment(presentation_settings(settings, mode)))
    env.update(control_environment(ROOT))
    env.update(RECOMP_HDD_DIR=str(hdd), RECOMP_KEYBOARD='1', RECOMP_GUEST_LOCK='1',
               RECOMP_DISPATCH_GATE='0', RECOMP_PB_BACKEND='metal',
               RECOMP_WATCHDOG_SECS=str(seconds), RECOMP_DEBUG='unimpl_trap,kick_event=1')
    env['BUFFY_UNLOCK_ARENAS'] = '1' if mode == 'menu' and settings.get('arenas', True) else '0'
    env['BUFFY_WIDESCREEN'] = '1' if env.get('RECOMP_DISPLAY_ASPECT') == '16:9' else '0'
    return env


def mission_script(page, pid_path, stdout, stderr):
    # Same project-derived bootstrap as the earlier verified capture protocol.
    return f'''settings set auto-confirm true
settings set target.disable-aslr false
settings set platform.plugin.darwin.ignored-exceptions EXC_BAD_ACCESS
breakpoint set -n xbox_kernel_bridge_init
process launch --stop-at-entry --stdout "{stdout}" --stderr "{stderr}"
script from pathlib import Path; Path({str(pid_path)!r}).write_text(str(lldb.debugger.GetSelectedTarget().GetProcess().GetProcessID()))
process handle --pass true --stop false --notify false SIGSEGV SIGBUS
continue
breakpoint disable 1
thread step-out
expression -- unsigned int $import_page = (unsigned int)xbox_ContiguousAlloc(4096,4096)
expression -- unsigned long long $import_host = g_xbox_mem_offset + $import_page
script from pathlib import Path; import hashlib; data=Path({str(page)!r}).read_bytes(); assert len(data)==4096 and hashlib.sha256(data).hexdigest()=={PAGE_SHA256!r}; err=lldb.SBError(); proc=lldb.debugger.GetSelectedTarget().GetProcess(); allocated=lldb.frame.EvaluateExpression('$import_page').GetValueAsUnsigned(); addr=lldb.frame.EvaluateExpression('$import_host').GetValueAsUnsigned(); assert allocated and addr and proc.WriteMemory(addr,data,err)==4096 and err.Success()
expression -- *(unsigned int*)(g_xbox_mem_offset+g_xbox_region_base+0x40030) = $import_page
process detach --keep-stopped false
quit
'''


def relaunch_mode(path, title_id):
    with path.open('rb') as stream:
        page = stream.read(4097)
    if len(page) != 4096:
        raise ValueError('Page de relance incomplète ou trop grande')
    kind, target = struct.unpack_from('<II', page)
    destination, terminator, _ = page[8:528].partition(b'\0')
    if (kind != 0 or target != title_id or not terminator
            or destination.lower() != b'\\device\\cdrom0;default.xbe'):
        raise ValueError('La page de relance ne cible pas le même jeu')
    payload = page[1024:].split(b'\0', 1)[0]
    tokens = payload.split()
    # QuitToMain emits title:0 with an explicitly empty map on this XBE.
    return 'menu' if b'title:1' in tokens or b'map:' in tokens else 'mission'


def run_session(binary, hdd, settings, seconds, mode, page, title_id, log, pack=None):
    deadline = time.monotonic() + seconds if seconds else None
    with tempfile.TemporaryDirectory(prefix='buffy-launch-', dir=ROOT/'artifacts') as work, log.open('w') as stream:
        incoming = Path(work)/'incoming.bin'
        outgoing = Path(work)/'outgoing.bin'
        for restart in count():
            remaining = deadline - time.monotonic() if deadline is not None else None
            if remaining is not None and remaining <= 0:
                raise TimeoutError('Limite de durée atteinte avant la relance')
            env = build_environment(settings, hdd, math.ceil(remaining) if remaining is not None else 0, mode=mode)
            env['RECOMP_LAUNCH_PAGE_OUT'] = str(outgoing)
            if page is not None:
                env['RECOMP_LAUNCH_PAGE_IN'] = str(page)
            if pack is not None:
                env['RECOMP_TEXTURES_PACK'] = str(pack)
            child = subprocess.Popen([str(binary)], cwd=ROOT, env=env, stdout=stream,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            try:
                child.wait(timeout=remaining + 5 if remaining is not None else None)
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait()
            if child.returncode or not outgoing.exists():
                return child.returncode, restart
            mode = relaunch_mode(outgoing, title_id)
            if deadline is not None and restart == MAX_RELAUNCHES:
                raise ValueError('Limite de relances atteinte')
            outgoing.replace(incoming)
            page = incoming
            print('Relance du jeu sur le même disque.', flush=True)


def main(argv=None):
    args = parse_args(argv)
    prefs = args.settings_file
    try:
        settings = selected_settings(args, prefs)
    except (ValueError, OSError) as exc:
        raise SystemExit('Réglages inchangés : '+str(exc))
    if args.show_settings:
        print(json.dumps({'path':str(prefs), **settings}, indent=2)); return
    pack = args.texture_pack.resolve() if args.texture_pack else None
    try:
        if pack is None:
            verify_profile(settings['textures'],ROOT,text=settings['text'])
        else:
            title = json.loads((ROOT/'config/title.json').read_text())
            verify_local_pack(pack, title['xbe_sha256'])
    except (OSError,ValueError,KeyError,TypeError) as exc:
        raise SystemExit('Pack de textures refusé, réglages inchangés : '+str(exc))
    if args.save_settings and not args.check:
        save_settings(prefs, settings)
        print('Réglages enregistrés : '+str(prefs)); return
    binary = ROOT/'build/game/buffy-macos'
    if pack is None:
        title = json.loads((ROOT/'config/title.json').read_text())
    verify_xbe(ROOT/'private/game/Default.xbe', title)
    generation = json.loads((ROOT/'artifacts/pipeline-recomp.json').read_text())
    if generation['returncode'] or generation['xbe_sha256'] != title['xbe_sha256']:
        raise SystemExit('Génération incompatible avec le XBE identifié')
    recipe = Path(__file__).with_name('letterbox_fix.py')
    if generation.get('letterbox_fix_sha256') != hashlib.sha256(recipe.read_bytes()).hexdigest():
        raise SystemExit('Regénérer et recompiler le jeu pour les bandes de cinématique')
    if settings['aspect'] == '16:9':
        recipe = Path(__file__).with_name('widescreen_fix.py')
        if generation.get('widescreen_fix_sha256') != hashlib.sha256(recipe.read_bytes()).hexdigest():
            raise SystemExit('Regénérer le jeu avec make generate puis make game-build pour le champ de vision')
    if args.mode == 'menu' and settings['arenas']:
        recipe = Path(__file__).with_name('arenas_fix.py')
        if generation.get('arenas_fix_sha256') != hashlib.sha256(recipe.read_bytes()).hexdigest():
            raise SystemExit('Regénérer le jeu avec make generate puis make game-build pour les arènes')
    if not binary.is_file():
        raise SystemExit('Exécuter make game-build')
    if 'XBOXRECOMP_ENHANCE:BOOL=ON' not in (ROOT/'build/game/CMakeCache.txt').read_text():
        raise SystemExit('Recompiler avec make game-build pour les options graphiques')
    title_id = int(title['title_id'], 16)
    try:
        selected_hdd = args.hdd
        if args.profile and args.profile.exists() and selected_hdd is None:
            selected_hdd = args.profile/'hdd'
        baseline = hdd_source(args.mode, selected_hdd, title_id)
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc))
    page = ROOT/'artifacts/relaunch/launch-page.bin'
    if args.mode=='mission' and hashlib.sha256(page.read_bytes()).hexdigest()!=PAGE_SHA256:
        raise SystemExit('Capture de lancement différente de celle validée')
    if args.profile and args.hdd and args.profile.exists():
        raise SystemExit('Le profil contient déjà une partie. Choisir un nouveau profil pour importer un autre disque')
    if args.check:
        if args.profile:
            with persistent_hdd(args.profile, baseline, title, check=True):
                pass
        print(json.dumps({'mode':args.mode,'settings':settings,
                          'display_aspect':presentation_settings(settings, args.mode)['aspect'],
                          'hdd_source':str(baseline) if baseline is not None else None,
                          'profile':str(args.profile.resolve()) if args.profile else None,
                          'texture_pack':str(pack) if pack else None,
                          'seconds_limit':args.seconds,
                          'launched':False,'saved':False},indent=2)); return
    with ExitStack() as resources:
        resources.enter_context(storage_lock(ROOT))
        name='play-'+args.mode+'-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid())
        hdd=ROOT/'build'/name
        if args.profile:
            try:
                hdd = resources.enter_context(persistent_hdd(args.profile, baseline, title))
            except (OSError, ValueError, subprocess.CalledProcessError) as exc:
                raise SystemExit(str(exc))
        else:
            if baseline is None:
                create_hdd(hdd, title_id)
            else:
                subprocess.run(['cp','-cR',str(baseline),str(hdd)],check=True)
        resources.enter_context(prepared_hdd(hdd))
        save_settings(prefs,settings)
        log=ROOT/'logs'/(name+'.log');log.parent.mkdir(exist_ok=True)
        display = presentation_settings(settings, args.mode)
        width, height = render_dimensions(display)
        print(f"Rendu : {width}x{height} ({display['aspect']}), FPS {'affichés' if settings['fps'] else 'masqués'}.",flush=True)
        print('Textures : '+(str(pack) if pack else settings['textures']),flush=True)
        print('Texte : '+settings['text'],flush=True)
        print('Clavier et manette : profil local si présent, sinon AZERTY et mapping manette d’origine. Ctrl+C : arrêter.',flush=True)
        duration = 'durée illimitée' if args.seconds == 0 else 'limite '+str(args.seconds)+' s'
        print('HDD de test : '+str(hdd)+' ; '+duration+'.',flush=True)
        print('Journal : '+str(log),flush=True)
        record={'mode':args.mode,'settings':settings,'xbe_sha256':title['xbe_sha256'],
                'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'hdd':str(hdd),
                'hdd_source':str(baseline) if baseline is not None else None,'profile':str(args.profile.resolve()) if args.profile else None,
                'seconds_limit':args.seconds,
                'texture_pack':str(pack) if pack else None}
        try:
            code, restarts = run_session(binary, hdd, settings, args.seconds, args.mode,
                                        page if args.mode == 'mission' else None,
                                        title_id, log, pack)
            record.update(game_exit_code=code, restarts=restarts)
            if code:
                raise SystemExit(f'Le jeu s’est arrêté ({code}). Journal : {log}')
        except KeyboardInterrupt:
            record['interrupted']=True
        except (OSError, ValueError, TimeoutError, subprocess.TimeoutExpired) as exc:
            record['error'] = str(exc)
            raise SystemExit(f'{exc}. Journal : {log}')
        finally:
            (ROOT/'artifacts'/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n')
        print('Essai terminé : '+name)


if __name__=='__main__':
    main()
