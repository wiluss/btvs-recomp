"""Widen CPU visibility planes for the hash-verified Buffy XBE.

View setup copies projection bounds into four camera-space corner vectors.
Widen only those copies. The original bounds are subsequently passed to
D3DXMatrixPerspectiveOffCenterLH and must retain their original values.
"""
FUNCTION = 0x002A4870
SITE = 0x002A4B7A


def prefix(function, instruction):
    if function != FUNCTION or instruction.address != SITE:
        return []
    if instruction.mnemonic != 'lea' or instruction.bytes_hex.lower() != '8d6c2438':
        raise ValueError('Visibility corner setup differs from the reviewed XBE')
    return [
        '{ extern float buffy_CullAspect(void);',
        '  const float ratio = buffy_CullAspect();',
        '  if (ratio > 1.0f && MEM32(0x7F4254) == 0 && MEM32(0x7F4258) == 0',
        '      && MEM32(0x7F425C) == 640 && MEM32(0x7F4260) == 480) {',
        '      MEMF(esp + 0x38) *= ratio;',
        '      MEMF(esp + 0x44) *= ratio;',
        '      MEMF(esp + 0x50) *= ratio;',
        '      MEMF(esp + 0x5C) *= ratio;',
        '  }',
        '}',
    ]
