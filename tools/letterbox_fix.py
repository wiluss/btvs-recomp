"""Cover the outer edges of Buffy's cinematic masks at higher render scales.

Hash-bound by recomp_driver, at the two ILetterBox::PostRender calls only.
The two pointers already on the guest stack name opposite screen-space
corners. Extend the outside edges; keep the inside edges and z unchanged.
"""
FUNCTION = 0x001084A0
SITES = {0x00108575: 'ff5024', 0x001085DC: 'ff5224'}


def prefix(function, instruction):
    if function != FUNCTION or instruction.address not in SITES:
        return []
    if instruction.mnemonic != 'call' or instruction.bytes_hex.lower() != SITES[instruction.address]:
        raise ValueError('Cinematic mask call differs from the reviewed XBE')
    top = instruction.address == 0x00108575
    edge = ('MEMF(a + 4) == 0.0f && MEMF(b + 4) > 0.0f && MEMF(b + 4) <= 480.0f'
            if top else
            'MEMF(b + 4) == 480.0f && MEMF(a + 4) >= 0.0f && MEMF(a + 4) < 480.0f')
    return [
        '{ /* Cinematic masks: expand only the outer screen edges. */',
        '  const uint32_t a = MEM32(esp), b = MEM32(esp + 4);',
        '  if (MEM32(esp + 0x44) == 640 && MEM32(esp + 0x48) == 480',
        '      && MEMF(a) == 0.0f && MEMF(b) == 640.0f',
        '      && MEMF(a + 8) == 10.0f && MEMF(b + 8) == 10.0f',
        '      && ' + edge + ') {',
        '      MEMF(a) = -1.0f;',
        '      MEMF(b) = 641.0f;',
        '      MEMF(a + 4) = -1.0f;' if top else '      MEMF(b + 4) = 481.0f;',
        '  }',
        '}',
    ]
