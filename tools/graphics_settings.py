"""Project graphics preferences; the pinned runtime receives explicit values.

RECOMP_CONFIG=none prevents unrelated configs from altering the guest/input.
Keep spin timing and explicit aspect/HUD choices. FPS counts engine flips.
"""
import json
import os
from pathlib import Path
import tempfile
from texture_profiles import PROFILES, pack_path

DEFAULTS = {'scale': 2, 'fps': True, 'fullscreen': False, 'vsync': True, 'filter': 'linear',
            'aspect': '4:3', 'hud': 'edges', 'textures': 'original', 'text': 'auto',
            'resolution': 'scale', 'arenas': True}


def validate_settings(data):
    # Qwen's reduced proposal, reviewed: exact types reject bool-as-scale.
    if not isinstance(data, dict) or set(data) - set(DEFAULTS):
        raise ValueError('Préférences graphiques invalides ou clé inconnue')
    out = dict(DEFAULTS, **data)
    if type(out['scale']) is not int or not 1 <= out['scale'] <= 4:
        raise ValueError('scale doit être un entier de 1 à 4')
    for key in ('fps', 'fullscreen', 'vsync', 'arenas'):
        if type(out[key]) is not bool:
            raise ValueError(key + ' doit être un booléen')
    if type(out['filter']) is not str or out['filter'] not in ('nearest', 'linear'):
        raise ValueError('filter doit être nearest ou linear')
    for key, choices in [('aspect', ('4:3', '16:9')), ('hud', ('safe', 'edges')),
                         ('textures', tuple(PROFILES)), ('text', ('auto','original','hd')),
                         ('resolution', ('scale', '4k'))]:
        if type(out[key]) is not str or out[key] not in choices:
            raise ValueError(key + ' doit être ' + ' ou '.join(choices))
    return out


def load_settings(path):
    path = Path(path)
    return validate_settings(json.loads(path.read_text()) if path.exists() else {})


def save_settings(path, settings):
    settings = validate_settings(settings)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=path.name+'.', delete=False) as stream:
            temp = Path(stream.name)
            json.dump(settings, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()


def render_dimensions(settings):
    s = validate_settings(settings)
    if s['resolution'] == '4k':
        return 3840, 2160
    # Pinned runtime rounds the 16:9 padding to 107 guest pixels per side.
    return (854 if s['aspect'] == '16:9' else 640) * s['scale'], 480 * s['scale']


def settings_environment(settings):
    s = validate_settings(settings)
    uhd = s['resolution'] == '4k'
    return {
        'RECOMP_CONFIG': 'none',
        'RECOMP_RENDER_SCALE': '5' if uhd else str(s['scale']),
        'RECOMP_OVERLAY_STATS': str(int(s['fps'])),
        'RECOMP_PRESENT_FULLSCREEN': str(int(s['fullscreen'])),
        'RECOMP_PRESENT_VSYNC': str(int(s['vsync'])),
        'RECOMP_PRESENT_FILTER': s['filter'],
        'RECOMP_PRESENT_PACING': 'spin',
        'RECOMP_DISPLAY_ASPECT': s['aspect'],
        'RECOMP_DISPLAY_MOVIE': 'black',
        'BUFFY_HUD': s['hud'],
        'RECOMP_TEXTURES_PACK': str(pack_path(s['textures'],text=s['text'])) if s['textures']!='original' or s['text']=='hd' else 'none',
        'RECOMP_TEXTURES_FONT': 'off' if s['text']=='original' else 'on',
        'RECOMP_TEXTURES_TEXT': 'off' if s['text']=='original' else 'on',
        'RECOMP_MOUSE': '0',
        **({'RECOMP_PRESENT_SURFACE': 'uhd'} if uhd else {}),
    }
