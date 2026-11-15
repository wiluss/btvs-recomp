"""Hash-gated native wardrobe call sites; never edits the guest executable."""
SITES = {
    (0x64550, 0x64550): ('mov', '8b0d14bb7700', 'extern void buffy_OutfitsDiagnosticAbort(uint32_t);', 'buffy_OutfitsDiagnosticAbort(MEM32(esp+4));'),
    (0x218210, 0x2183C1): ('pop', '5f', 'extern void buffy_OutfitsConstruct(uint32_t); extern const char *buffy_OutfitsBindingProtocol;', 'buffy_OutfitsBindingProtocol = \"BTVS_NATIVE_OUTFITS_PROTOCOL_2\"; buffy_OutfitsConstruct(ebx);'),
    (0x217F40, 0x217F40): ('push', '53', 'extern void buffy_OutfitsDestroy(uint32_t);', 'buffy_OutfitsDestroy(ecx);'),
    (0x222470, 0x222470): ('sub', '83ec1c', 'extern int buffy_OutfitsLoad(uint32_t);', 'if (buffy_OutfitsLoad(ecx)) { esp += 4; return; }'),
    (0x221C90, 0x221C90): ('mov', 'a11c047f00', 'extern int buffy_OutfitsCommand(uint32_t,uint32_t);', 'if (buffy_OutfitsCommand(ecx,MEM32(esp+4))) { esp += 8; return; }'),
    (0x2226B0, 0x2226B0): ('sub', '83ec1c', 'extern int buffy_OutfitsMessage(uint32_t,uint32_t,uint32_t);', 'if (buffy_OutfitsMessage(ecx,MEM32(esp+4),MEM32(esp+8))) { esp += 20; return; }'),
    (0x221E60, 0x221E60): ('push', '55', 'extern void buffy_OutfitsUpdate(uint32_t);', 'buffy_OutfitsUpdate(ecx);'),
    (0x405D0, 0x405D0): ('push', '55', 'extern void buffy_OutfitsResourcesReady(void);', 'buffy_OutfitsResourcesReady();'),
    (0x286B10, 0x286B10): ('sub', '83ec14', 'extern uint32_t buffy_OutfitsRender(uint32_t);', 'ecx = buffy_OutfitsRender(ecx);'),
    (0x131E40, 0x131E40): ('push', '53', 'extern void buffy_OutfitsActorDestroy(uint32_t);', 'buffy_OutfitsActorDestroy(ecx);'),
    (0x223A60, 0x223A60): ('push', '57', 'extern int buffy_OutfitsPauseMessage(uint32_t,uint32_t,uint32_t);', 'if (buffy_OutfitsPauseMessage(ecx,MEM32(esp+4),MEM32(esp+8))) { esp += 20; return; }'),
    (0x223760, 0x223760): ('sub', '83ec18', 'extern int buffy_OutfitsPauseLoad(uint32_t);', 'if (buffy_OutfitsPauseLoad(ecx)) { esp += 4; return; }'),
    (0x1EAE80, 0x1EAECD): ('mov', '8b0db46b7e00', 'extern int buffy_OutfitsKeepImage(uint32_t);', 'if (buffy_OutfitsKeepImage(MEM32(edi+4))) goto loc_001EAEEE;'),
}


def prefix(function, instruction):
    site = SITES.get((function, instruction.address))
    if site is None:
        return []
    mnemonic, encoded, declaration, body = site
    if instruction.mnemonic != mnemonic or instruction.bytes_hex.lower() != encoded:
        raise ValueError('Native wardrobe call site differs from reviewed XBE')
    return [declaration, body]
