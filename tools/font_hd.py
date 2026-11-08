#!/usr/bin/env python3
"""Rebuild the reviewed Latin glyph atlases without editing guest font metrics.

Layout and raster assets stay local; source recipe and code are versioned.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from texture_pilot import write_pack
from texture_snapshot_lldb import XBE_SHA256
from text_pack import build_profiles, digest, additional_recipes, word_recipe

ROOT=Path(__file__).resolve().parents[1]


def layout_from_objects(objects, source):
    candidates=[o for o in objects['objects'] if o['words'][4:6]==list(source.size)
                and o['words'][7:10]==[32,127,96]]
    if len(candidates)!=1:raise ValueError('Expected one reviewed Latin font object')
    record=candidates[0]
    if len(record['entries'])!=96 or {e['code'] for e in record['entries']}!=set(range(32,128)):
        raise ValueError('Incomplete character map')
    w,h=source.size;alpha=source.getchannel('A');glyphs=[]
    for e in candidates[0]['entries']:
        u0,v0,u1,v1=e['floats'][:4]
        if not (0<=u0<=u1<=1 and 0<=v0<=v1<=1):raise ValueError('Invalid glyph UV')
        box=[round(u0*(w-1)),round(v0*(h-1)),round(u1*(w-1))+1,round(v1*(h-1))+1]
        ink=alpha.crop(box).point(lambda p:255 if p>=128 else 0).getbbox()
        metrics=struct.unpack('<3h',struct.pack('<2I',*e['words'][4:])[:6])
        glyphs.append({'code':e['code'],'box':box,'ink':list(ink) if ink else None,'metrics':list(metrics)})
    return {'width':w,'height':h,'glyphs':glyphs}


def layout_hash(layout):
    return hashlib.sha256(json.dumps(layout,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def raster_glyphs(font_path, codes, size, width_scale=1.0, variations=None):
    """One font and affine transform for the whole face; bounds relative to baseline.

    Cropping is only storage: the returned signed bounds retain the original
    baseline, overshoot and descenders. Never fit a glyph to its old ink box.
    """
    from PIL import Image,ImageDraw,ImageFont
    if type(size) is not int or not 1<=size<=1024:raise ValueError('Invalid font size')
    if not isinstance(width_scale,(int,float)) or not math.isfinite(width_scale) or not .25<=width_scale<=2:
        raise ValueError('Invalid common width scale')
    font=ImageFont.truetype(str(font_path),size)
    if variations is not None:
        axes=font.get_variation_axes()
        if len(variations)!=len(axes) or any(not isinstance(v,(int,float)) or not math.isfinite(v)
            or not axis['minimum']<=v<=axis['maximum'] for v,axis in zip(variations,axes)):
            raise ValueError('Invalid font variations')
        font.set_variation_by_axes(variations)
    dimensions=(size*4,size*4);origin=(size,size*2)
    target=(round(dimensions[0]*width_scale),dimensions[1]);pen=(round(origin[0]*target[0]/dimensions[0]),origin[1])
    result={}
    for code in codes:
        canvas=Image.new('L',dimensions)
        ImageDraw.Draw(canvas).text(origin,chr(code),font=font,fill=255,anchor='ls')
        bounds=canvas.getbbox()
        if bounds is None or bounds[0]==0 or bounds[1]==0 or bounds[2]==dimensions[0] or bounds[3]==dimensions[1]:
            raise ValueError('Empty or clipped vector glyph: %d'%code)
        if target!=dimensions:canvas=canvas.resize(target,Image.Resampling.LANCZOS)
        # Ignore only remote ringing below 8/255 when finding storage bounds;
        # retain the original antialias coverage inside those bounds.
        bounds=canvas.point(lambda a:255 if a>=8 else 0).getbbox()
        if bounds is None:raise ValueError('Empty transformed glyph: %d'%code)
        result[code]=(canvas.crop(bounds),tuple(v-pen[i%2] for i,v in enumerate(bounds)))
    return result


def render_atlas(source, layout, font_path, scale, *, font_size=17, baseline=15,
                 width_scale=1.0, variations=None, fallback_font=None, fallback_codes=()):
    from PIL import Image
    if type(scale) is not int or scale not in (2,4,8):raise ValueError('Invalid glyph scale')
    if not all(isinstance(v,(int,float)) and math.isfinite(v) and 0<v<=128 for v in (font_size,baseline)):
        raise ValueError('Invalid common font geometry')
    if source.mode!='RGBA' or source.size!=(layout['width'],layout['height']):raise ValueError('Atlas differs')
    w,h=source.size;seen=set();regions=[]
    for g in layout['glyphs']:
        code=g['code'];box=g['box'];ink=g['ink']
        if type(code) is not int or code in seen or not 0<=code<=65535:raise ValueError('Invalid/duplicate glyph')
        seen.add(code)
        if len(box)!=4 or not all(type(x) is int for x in box) or not (0<=box[0]<box[2]<=w and 0<=box[1]<box[3]<=h):
            raise ValueError('Glyph outside atlas')
        if ink is None:continue
        if len(ink)!=4 or not all(type(x) is int for x in ink) or not (0<=ink[0]<ink[2]<=box[2]-box[0] and 0<=ink[1]<ink[3]<=box[3]-box[1]):
            raise ValueError('Ink outside glyph')
        rect=(box[0]+ink[0],box[1]+ink[1],box[0]+ink[2],box[1]+ink[3])
        if any(max(rect[0],r[0])<min(rect[2],r[2]) and max(rect[1],r[1])<min(rect[3],r[3]) for r in regions):
            raise ValueError('Overlapping glyph ink')
        regions.append(rect)
    alpha=source.getchannel('A').resize((w*scale,h*scale),Image.Resampling.NEAREST)
    replacements=[g for g in layout['glyphs'] if g['ink'] is not None and 33<=g['code']<=126]
    if len(set(fallback_codes))!=len(fallback_codes) or any(type(c) is not int or c not in {g['code'] for g in replacements} for c in fallback_codes):
        raise ValueError('Invalid fallback characters')
    if fallback_codes and fallback_font is None:raise ValueError('Missing fallback font')
    rasters=raster_glyphs(font_path,[g['code'] for g in replacements],round(font_size*scale),width_scale,variations)
    if fallback_codes:
        rasters.update(raster_glyphs(fallback_font,fallback_codes,round(font_size*scale),width_scale))
    placements=[]
    for g in replacements:
        mask,bounds=rasters[g['code']];box,ink=g['box'],g['ink']
        # UV rectangles include the last texel, shared with the next cell.
        # Keep that texel and one output pixel at each edge transparent.
        cw=(box[2]-box[0]-1)*scale;ch=(box[3]-box[1]-1)*scale
        if mask.width>cw-2:raise ValueError('Vector glyph too wide: %d'%g['code'])
        x=max(1,min(cw-1-mask.width,round((ink[0]+ink[2])*scale/2-mask.width/2)))
        y=round(baseline*scale)+bounds[1]
        if y<1 or y+mask.height>ch-1:raise ValueError('Vector glyph outside baseline cell: %d'%g['code'])
        rect=(box[0]*scale+x,box[1]*scale+y,box[0]*scale+x+mask.width,box[1]*scale+y+mask.height)
        # Check actual output, including retained fallback/other glyphs.
        for other in layout['glyphs']:
            if other['code']==g['code'] or other['ink'] is None:continue
            b,k=other['box'],other['ink']
            r=tuple((b[i%2]+k[i])*scale for i in range(4))
            if max(rect[0],r[0])<min(rect[2],r[2]) and max(rect[1],r[1])<min(rect[3],r[3]):
                raise ValueError('Vector glyph overlaps neighbour')
        if any(max(rect[0],r[0])<min(rect[2],r[2]) and max(rect[1],r[1])<min(rect[3],r[3]) for _,r in placements):
            raise ValueError('Vector glyph overlaps replacement')
        placements.append((mask,rect))
    # Clear all old ink before pasting new glyphs, retaining spaces/fallback.
    # This allows coherent glyphs outside their old ink, within their own UVs.
    for g in replacements:
        b,k=g['box'],g['ink']
        alpha.paste(0,tuple((b[i%2]+k[i])*scale for i in range(4)))
    for mask,rect in placements:
        alpha.paste(mask,rect[:2])
    # The original binary atlas has RGB == alpha (black transparent texels).
    # Keep that coverage convention, including under additive font blending.
    return Image.merge('RGBA',(alpha,alpha,alpha,alpha))


def main():
    from PIL import Image
    from menu_words_hd import prepare_words
    from texture_profiles import verify_profile
    installed_pack = ROOT/'private/textures/font-hd.xrtp'
    installed_recipe = ROOT/'config/font-hd.json'
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--objects',type=Path,required=True);p.add_argument('--atlas',type=Path,required=True)
    p.add_argument('--font',type=Path,required=True);p.add_argument('--recipe',type=Path,default=ROOT/'config/font-hd.json')
    p.add_argument('--output', type=Path, default=installed_pack,
                   help='Use a separate path to export a pack without updating the installed profiles')
    args = p.parse_args()
    install = args.output.resolve() == installed_pack.resolve()
    if install and args.recipe.resolve() != installed_recipe.resolve():
        p.error('The installed pack requires config/font-hd.json. Use --output to export separately.')
    recipe = json.loads(args.recipe.read_text())
    if install:
        for profile in ('pilot2x', 'pilot4x'):
            verify_profile(profile, ROOT)
    if digest(ROOT/'private/game/Default.xbe')!=XBE_SHA256:raise ValueError('Unreviewed XBE')
    inputs=[(recipe,args.font,args.atlas,args.objects)]
    for spec,extra in additional_recipes(ROOT,recipe):
        inputs.append((extra,ROOT/spec['font'],ROOT/spec['atlas'],ROOT/spec['objects']))
    rows=[];images=[];counts=[];seen=set()
    for index,(item,font,atlas,objects_path) in enumerate(inputs):
        if item['scale']!=recipe['scale']:raise ValueError('Font collection scales differ')
        source=Image.open(atlas).convert('RGBA');objects=json.loads(objects_path.read_text())
        if item['xbe_sha256']!=XBE_SHA256 or digest(font)!=item['font_sha256']:
            raise ValueError('Unreviewed font source')
        if hashlib.sha256(source.tobytes()).hexdigest()!=item['atlas_rgba_sha256']:
            raise ValueError('Unreviewed source atlas')
        layout=layout_from_objects(objects,source)
        if layout_hash(layout)!=item['layout_sha256']:raise ValueError('Font layout differs')
        fallback=item.get('fallback_font');fallback_path=ROOT/fallback['path'] if fallback else None
        if fallback and digest(fallback_path)!=fallback['sha256']:raise ValueError('Unreviewed fallback font')
        image=render_atlas(source,layout,font,item['scale'],fallback_font=fallback_path,**item['render'])
        key=int(item['texture_hash'],16)
        if key in seen:raise ValueError('Duplicate font texture identity')
        seen.add(key);png=(args.output.with_suffix('.png') if index==0 else
            args.output.with_name(args.output.stem+'-%016X.png'%key))
        rows.append({'hash':key,'width':source.width,'height':source.height,'kind':'font','image':png,'mipmaps':False})
        images.append(image);counts.append(sum(g['ink'] is not None and 33<=g['code']<=126 for g in layout['glyphs']))
    word_images = []
    words = word_recipe(ROOT, recipe)
    if words:
        for entry, image in prepare_words(ROOT, words):
            key = int(entry['texture_hash'], 16)
            if key in seen:
                raise ValueError('Duplicate text texture identity')
            seen.add(key)
            png = args.output.with_name(args.output.stem+'-%016X.png'%key)
            width, height = entry['dimensions']
            rows.append({'hash':key,'width':width,'height':height,'kind':'text','image':png,'mipmaps':False})
            images.append(image)
            word_images.append((entry['label'], png))
    # Finish validation of every source before replacing any installed output.
    args.output.parent.mkdir(parents=True,exist_ok=True)
    for row,image in zip(rows,images):image.save(row['image'])
    count=write_pack(rows,args.output,recipe['scale'])
    args.output.with_suffix('.json').write_text(json.dumps({'xbe_sha256':XBE_SHA256,'entries':count,
        'font_recipe_sha256':digest(args.recipe),'pack_sha256':digest(args.output),'image_sha256':digest(rows[0]['image']),
        'fonts':[{'texture_hash':'%016X'%row['hash'],'image_sha256':digest(row['image']),'glyphs':n}
                 for row,n in zip(rows,counts)],
        'words':[{'label':label,'image_sha256':digest(png)} for label,png in word_images]},indent=2)+'\n')
    if install:
        build_profiles(ROOT,args.output)
    print(json.dumps({'entries':count,'font_entries':len(counts),'word_entries':len(word_images),
        'glyphs':sum(counts),'scale':recipe['scale'],'pack':str(args.output)}))


if __name__=='__main__':main()
