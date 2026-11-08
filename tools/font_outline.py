#!/usr/bin/env python3
"""Compile local, reviewed glyph paths into a deterministic TrueType master.

No game contours live here: the source master and layout are private assets.
"""
import argparse
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import re

from font_hd import ROOT, layout_hash
from texture_snapshot_lldb import XBE_SHA256


def build_font(master, layout):
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.pens.cu2quPen import Cu2QuPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.svgLib.path import parse_path
    geometry=(master.get('em_pixels'),master.get('baseline'))
    if (master.get('schema')!=1 or master.get('units_per_pixel')!=64
        or any(type(v) is not int for v in geometry) or geometry not in ((20,15),(32,21))):
        raise ValueError('Unreviewed outline coordinate system')
    em,baseline=geometry;ascent=baseline*64;descent={(20,15):384,(32,21):576}[geometry]
    expected={g['code']:g for g in layout['glyphs'] if g['ink'] is not None and 33<=g['code']<=126}
    paths=master['paths']
    if set(paths)!={str(c) for c in expected}:raise ValueError('Outline coverage differs from layout')
    order=['.notdef','space']+['u%04X'%c for c in sorted(expected)]
    cmap={32:'space',**{c:'u%04X'%c for c in expected}}
    fb=FontBuilder(em*64,isTTF=True);fb.setupGlyphOrder(order);fb.setupCharacterMap(cmap)
    glyphs={};advances={}
    for name in order:
        pen=TTGlyphPen(None)
        if name.startswith('u'):
            code=int(name[1:],16);g=expected[code];path=paths[str(code)]
            if (not isinstance(path,str) or not 1<=len(path)<=131072
                or re.search(r'[^MLCQZHVmlcqzhv0-9.,+\-\sEe]',path)
                or not path.rstrip().endswith(('Z','z'))):
                raise ValueError('Unsupported outline path')
            values=re.findall(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',path)
            if any(not math.isfinite(float(v)) or abs(float(v))>1024 for v in values):
                raise ValueError('Invalid outline coordinate')
            parse_path(path,TransformPen(Cu2QuPen(pen,max_err=.5),(64,0,0,-64,0,ascent)))
            advances[name]=(g['metrics'][2]+2)*64
        else:advances[name]=320
        glyphs[name]=pen.glyph()
        if name.startswith('u'):
            glyph=glyphs[name];glyph.recalcBounds(glyphs)
            if not glyph.numberOfContours:raise ValueError('Empty printable outline')
            # Guard the allocated UV cell, not the legacy ink bbox. Optical
            # corrections (e.g. a wider v) are deliberately possible inside it.
            w=g['box'][2]-g['box'][0]-1;h=g['box'][3]-g['box'][1]-1
            if glyph.xMin<0 or glyph.xMax>w*64 or glyph.yMax>ascent or glyph.yMin<(baseline-h)*64:
                raise ValueError('Outline outside cell: %d'%code)
            # Components can overlap when composing stems and bowls.
            glyph.flags[0]|=0x40  # OVERLAP_SIMPLE, first point only
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({name:(advances[name],getattr(glyphs[name],'xMin',0)) for name in order})
    fb.setupHorizontalHeader(ascent=ascent,descent=-descent)
    family=master.get('family','Local Reconstructed Font')
    if not isinstance(family,str) or not re.fullmatch(r'[A-Za-z0-9 -]{1,64}',family):
        raise ValueError('Invalid font name')
    fb.setupNameTable({'familyName':family,'styleName':'Regular','uniqueFontIdentifier':family+'-1',
        'fullName':family,'psName':family.replace(' ','')+'-Regular'})
    fb.setupOS2(sTypoAscender=ascent,sTypoDescender=-descent,usWinAscent=ascent,usWinDescent=descent)
    fb.setupPost();fb.setupMaxp()
    fb.font['head'].created=fb.font['head'].modified=2082844800
    fb.font.recalcTimestamp=False
    stream=BytesIO();fb.font.save(stream);return stream.getvalue()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--master',type=Path,required=True);p.add_argument('--layout',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--recipe',type=Path,default=ROOT/'config/font-hd.json')
    a=p.parse_args();recipe=json.loads(a.recipe.read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
    if recipe['xbe_sha256']!=XBE_SHA256 or sha((ROOT/'private/game/Default.xbe').read_bytes())!=XBE_SHA256:
        raise ValueError('Unreviewed XBE')
    raw=a.master.read_bytes();layout=json.loads(a.layout.read_text())
    if sha(raw)!=recipe['master_sha256'] or layout_hash(layout)!=recipe['layout_sha256']:
        raise ValueError('Unreviewed master/layout')
    data=build_font(json.loads(raw),layout)
    if sha(data)!=recipe['font_sha256']:raise ValueError('Compiled font differs from reviewed recipe')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(data)
    print(json.dumps({'glyphs':len(json.loads(raw)['paths']),'sha256':sha(data),'bytes':len(data)}))


if __name__=='__main__':main()
