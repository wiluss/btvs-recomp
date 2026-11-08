"""Enable the four reviewed arena bits before Extras reads RunOptions."""

FUNCTION = 0x0021DBF0
SITE = 0x0021DDF5


def prefix(function, instruction):
    if function != FUNCTION or instruction.address != SITE:
        return []
    if instruction.mnemonic != 'mov' or instruction.bytes_hex.lower() != '8b4038':
        raise ValueError('Extras RunOptions read differs from the reviewed XBE')
    return [
        'extern int buffy_ArenasEnabled(void);',
        'if (buffy_ArenasEnabled() && (MEM32(eax + 0x38) & 15u) != 15u)',
        '    MEM32(eax + 0x38) |= 15u;',
    ]
