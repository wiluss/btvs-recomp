"""Read-only LLDB snapshot of the pinned Metal texture cache after the HUD.

Load with `command script import ...`, then `texture-snapshot OUT_DIRECTORY`.
No target expressions, function calls or memory writes. Assets stay local.
"""
import hashlib
import json
from pathlib import Path
import shlex
import struct

ROOT = Path(__file__).resolve().parents[1]
XBE_SHA256 = 'cd49da614d92b6ec94f3bd66d503eb4e214f8809e9c7b42f465ee25c709ad35f'
MASK = (1 << 64) - 1


def texture_hash(raw):
    """Pinned nv2a_tex_hash, over uploaded compressed bytes, not decoded RGB."""
    seed = 0xCBF29CE484222325
    lanes = [seed, seed ^ 1, seed ^ 2, seed ^ 3]
    end = len(raw) // 32 * 32
    for pos in range(0, end, 32):
        for k, word in enumerate(struct.unpack_from('<4Q', raw, pos)):
            lanes[k] = ((lanes[k] ^ word) * 0x100000001B3) & MASK
    for byte in raw[end:]:
        lanes[0] = ((lanes[0] ^ byte) * 0x100000001B3) & MASK
    return ((lanes[0] ^ (lanes[1] << 1) ^ (lanes[2] << 2)
             ^ (lanes[3] << 3)) * 0x100000001B3) & MASK


def dxt_extent(fmt, width, height, levels):
    if fmt not in (12, 14, 15) or not 1 <= levels <= 12:
        raise ValueError('Only bounded DXT textures are captured')
    if not all(type(n) is int and 1 <= n <= 2048 and n & (n-1) == 0
               for n in (width, height)):
        raise ValueError('Unsupported texture dimensions')
    if levels > max(width, height).bit_length():
        raise ValueError('Invalid mip count')
    return sum(((max(1, width >> l)+3)//4) * ((max(1, height >> l)+3)//4)
               * (8 if fmt == 12 else 16) for l in range(levels))


def snapshot(debugger, command, result, internal_dict):
    import lldb
    try:
        args = shlex.split(command)
        if len(args) != 1:
            raise ValueError('Expected one fresh output directory')
        if hashlib.sha256((ROOT/'private/game/Default.xbe').read_bytes()).hexdigest() != XBE_SHA256:
            raise ValueError('Unreviewed XBE')
        target = debugger.GetSelectedTarget()
        process = target.GetProcess()
        if target.GetExecutable().GetFilename() != 'buffy-macos' or process.GetState() != lldb.eStateStopped:
            raise ValueError('Expected stopped Buffy native process')
        cache = target.FindFirstGlobalVariable('s_tc')
        if not cache.IsValid() or cache.GetNumChildren() != 512 or 'TexEntry' not in cache.GetTypeName():
            raise ValueError('Pinned Metal cache layout not found')
        offset = target.FindFirstGlobalVariable('g_memory_offset')
        alias = target.FindFirstGlobalVariable('g_xbox_mem_offset')
        if not offset.IsValid() or not alias.IsValid() or not offset.GetValueAsUnsigned() or offset.GetValueAsUnsigned() != alias.GetValueAsUnsigned():
            raise ValueError('Guest memory mappings disagree')
        base = offset.GetValueAsUnsigned()
        rows = []
        fields = ('offset', 'color', 'width', 'height', 'pitch', 'palette', 'levels', 'bytes', 'gen', 'hash', 'live')
        for i in range(512):
            entry = cache.GetChildAtIndex(i)
            if any(not entry.GetChildMemberWithName(f).IsValid() for f in fields):
                raise ValueError('Pinned cache fields unavailable')
            row = {f:entry.GetChildMemberWithName(f).GetValueAsUnsigned() for f in fields}
            if row['live']:
                rows.append(row)
        newest = max((r['gen'] for r in rows), default=0)
        out = Path(args[0]).resolve()
        out.mkdir(parents=True, exist_ok=False)
        captured, rejected = [], []
        for row in rows:
            try:
                if newest-row['gen'] > 2 or row['pitch'] or row['palette']:
                    raise ValueError('stale/linear/paletted')
                expected = dxt_extent(row['color'], row['width'], row['height'], row['levels'])
                if row['bytes'] != expected or row['offset']+expected > 1 << 32:
                    raise ValueError('extent differs')
                error = lldb.SBError()
                raw = process.ReadMemory(base+row['offset'], expected, error)
                if not error.Success() or len(raw) != expected:
                    raise ValueError('incomplete memory read')
                if texture_hash(raw) != row['hash']:
                    raise ValueError('guest bytes changed since upload')
                name = '%016X-%dx%d.bin' % (row['hash'], row['width'], row['height'])
                path = out/name
                if path.exists() and path.read_bytes() != raw:
                    raise ValueError('identity collision')
                path.write_bytes(raw)
                captured.append(dict(row, file=name, sha256=hashlib.sha256(raw).hexdigest()))
            except ValueError as exc:
                rejected.append(dict(row, reason=str(exc)))
        (out/'manifest.json').write_text(json.dumps({'xbe_sha256':XBE_SHA256, 'newest_gen':newest,
            'entries':captured, 'rejected':rejected}, indent=2)+'\n')
        result.AppendMessage(json.dumps({'captured':len(captured), 'rejected':len(rejected), 'output':str(out)}))
    except Exception as exc:
        result.SetError(str(exc))


def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('command script add -f texture_snapshot_lldb.snapshot texture-snapshot')
