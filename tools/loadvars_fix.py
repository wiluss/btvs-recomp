"""Hash-bound caller repair; see docs/BRINGUP.md (LoadVariables).

No host pointer casts: MEM32 translates guest addresses. The two stores
initialize pointees, not argument slots, before the original CALL pushes RA.
"""
import hashlib

XBE_SHA256 = 'cd49da614d92b6ec94f3bd66d503eb4e214f8809e9c7b42f465ee25c709ad35f'
FUNCTION = 0x00014030
SITE = 0x000140AE
TARGET = 0x002B46D0
CALL_BYTES = 'e81d062a00'


def verify_xbe(path, manifest):
    if manifest['xbe_sha256'] != XBE_SHA256:
        raise ValueError('LoadVariables fix requires its reviewed XBE manifest')
    if hashlib.sha256(path.read_bytes()).hexdigest() != XBE_SHA256:
        raise ValueError('LoadVariables fix requires the reviewed XBE bytes')


def prefix(function, instruction):
    if function != FUNCTION or instruction.address != SITE:
        return []
    if (instruction.mnemonic != 'call' or instruction.call_target != TARGET
            or instruction.bytes_hex.lower() != CALL_BYTES):
        raise ValueError('LoadVariables call site differs from reviewed x86')
    return [
        '/* LoadVariables: initialize File_Read pointees before pushing return address. */',
        'MEM32(MEM32(esp + 4)) = 0;',
        'MEM32(MEM32(esp + 8)) = 0;',
    ]
