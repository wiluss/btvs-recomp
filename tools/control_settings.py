"""Validated local input profile shared by the launcher and native adapter."""
import json
from pathlib import Path

DEFAULT_KEYS = [87, 88, 67, 86, 65, 69, 49, 51, 13, 8, 16, 17,
                38, 40, 37, 39, 90, 83, 81, 68, 73, 75, 74, 76]
SUPPORTED_KEYS = ({0, 8, 9, 13, 16, 17, 18, 27, 45, 46}
                  | set(range(32, 41)) | set(range(48, 58)) | set(range(65, 91))
                  | set(range(96, 108)) | set(range(109, 124))) - {122}


def validate_controls(value):
    if not isinstance(value, dict) or set(value) != {'version', 'keyboard', 'pad', 'sticks'}:
        raise ValueError('Invalid input profile fields')
    if type(value['version']) is not int or value['version'] != 1:
        raise ValueError('Unsupported input profile version')
    for name, count, allowed in [('keyboard', 24, SUPPORTED_KEYS), ('pad', 16, set(range(-1, 16))),
                                  ('sticks', 2, {0, 1, 2})]:
        array = value[name]
        if (not isinstance(array, list) or len(array) != count
                or any(type(n) is not int or n not in allowed for n in array)):
            raise ValueError('Invalid input profile: ' + name)
    for name, unassigned in [('keyboard', 0), ('pad', -1)]:
        assigned = [n for n in value[name] if n != unassigned]
        if len(set(assigned)) != len(assigned):
            raise ValueError('Duplicate input assignment: ' + name)
    if any(not value['keyboard'][n] and value['pad'][n] == -1 for n in (0, 1, 8)):
        raise ValueError('A, B and Start must remain accessible')
    return {k: list(v) if isinstance(v, list) else v for k, v in value.items()}


def _unique_fields(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError('Duplicate input profile field')
        result[k] = v
    return result


def control_environment(root):
    path = Path(root) / 'private/config/controls.json'
    if not path.exists():
        return {}
    raw = path.read_bytes()
    if len(raw) > 8192:
        raise ValueError('Input profile is too large')
    profile = validate_controls(json.loads(raw, object_pairs_hook=_unique_fields))
    numbers = [1] + profile['keyboard'] + profile['pad'] + profile['sticks']
    return {'BUFFY_INPUT_PROFILE': ','.join(map(str, numbers))}
