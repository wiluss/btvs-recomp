#!/usr/bin/env python3
"""Build local-only texture pilot packs from a verified Metal snapshot.

Requires Pillow. AI inference is offline; original assets are never edited.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import subprocess
import tempfile
import time

from texture_snapshot_lldb import XBE_SHA256, texture_hash, dxt_extent

ROOT = Path(__file__).resolve().parents[1]
KINDS = {'art':0, 'font':1, 'text':2}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def selected(selection, decoded):
    plan = json.loads(Path(selection).read_text())
    source = json.loads((Path(decoded)/'manifest.json').read_text())
    if plan['xbe_sha256'] != XBE_SHA256 or source['xbe_sha256'] != XBE_SHA256:
        raise ValueError('Unreviewed XBE')
    rows, seen = [], set()
    for item in plan['entries']:
        h = int(item['hash'],16)
        if not 0 < h < 1 << 64 or h in seen:
            raise ValueError('Duplicate/invalid texture hash')
        seen.add(h)
        matches = [e for e in source['entries'] if e['hash']==h and
                   (e['width'],e['height'])==(item['width'],item['height'])]
        if len(matches)!=1 or item['kind'] not in KINDS or item['method'] not in ('ai','lanczos'):
            raise ValueError('Unknown texture or processing policy')
        if item['border'] not in ('wrap','clamp'):
            raise ValueError('Unknown border policy')
        row = dict(matches[0], **item)
        # The plan uses printable hashes, while the binary uses unsigned u64.
        row['hash'] = h
        row['path'] = Path(decoded)/matches[0]['image']
        if row['path'].name != matches[0]['image'] or sha(row['path']) != matches[0]['png_sha256']:
            raise ValueError('Decoded texture differs from reviewed capture')
        rows.append(row)
    if not 1 <= len(rows) <= 64:
        raise ValueError('Expected 1..64 explicitly selected textures')
    return rows


def padded_rgb(image, halo, mode):
    from PIL import Image
    image = image.convert('RGB'); w,h=image.size
    if mode == 'wrap':
        tiled=Image.new('RGB',(w*3,h*3))
        for y in range(3):
            for x in range(3):tiled.paste(image,(x*w,y*h))
        return tiled.crop((w-halo,h-halo,2*w+halo,2*h+halo))
    out=Image.new('RGB',(w+2*halo,h+2*halo));out.paste(image,(halo,halo))
    out.paste(image.crop((0,0,w,1)).resize((w,halo)),(halo,0))
    out.paste(image.crop((0,h-1,w,h)).resize((w,halo)),(halo,h+halo))
    out.paste(image.crop((0,0,1,h)).resize((halo,h)),(0,halo))
    out.paste(image.crop((w-1,0,w,h)).resize((halo,h)),(w+halo,halo))
    for x,sx in ((0,0),(w+halo,w-1)):
        for y,sy in ((0,0),(h+halo,h-1)):
            out.paste(image.getpixel((sx,sy)),(x,y,x+halo,y+halo))
    return out


def decode(capture, output):
    from PIL import Image
    capture,output=Path(capture),Path(output)
    manifest=json.loads((capture/'manifest.json').read_text())
    if manifest['xbe_sha256']!=XBE_SHA256:raise ValueError('Unreviewed capture')
    exe=ROOT/'build/texture-decode'
    subprocess.run(['clang','-std=c11','-O2','-ffunction-sections','-fdata-sections',
        '-Wl,-dead_strip','-I',str(ROOT/'vendor/xboxrecomp/src/kernel'),
        '-I',str(ROOT/'vendor/xboxrecomp/src/d3d'),str(ROOT/'tools/texture_decode.c'),
        str(ROOT/'vendor/xboxrecomp/src/kernel/nv2a_backend_common.c'),'-lm','-o',str(exe)],check=True)
    output.mkdir(parents=True,exist_ok=True);rows=[];seen=set()
    for e in manifest['entries']:
        if e['file'] in seen:continue
        seen.add(e['file']);raw=capture/e['file']
        if raw.name!=e['file'] or sha(raw)!=e['sha256'] or texture_hash(raw.read_bytes())!=e['hash']:
            raise ValueError('Capture payload mismatch')
        if len(raw.read_bytes())!=dxt_extent(e['color'],e['width'],e['height'],e['levels']):
            raise ValueError('Invalid source extent')
        pixels=output/(raw.stem+'.bgra')
        run=subprocess.run([str(exe),str(e['color']),str(e['width']),str(e['height']),
            str(e['pitch']),str(e['levels']),str(raw),str(pixels)],check=True,capture_output=True,text=True)
        if int(run.stdout.strip(),16)!=e['hash']:raise ValueError('Native hash disagrees')
        image=output/(raw.stem+'.png')
        Image.frombytes('RGBA',(e['width'],e['height']),pixels.read_bytes(),'raw','BGRA').save(image)
        rows.append(dict(e,image=image.name,png_sha256=sha(image)))
    (output/'manifest.json').write_text(json.dumps({'xbe_sha256':XBE_SHA256,'entries':rows},indent=2)+'\n')
    print(json.dumps({'decoded':len(rows)}))


def upscale(selection, decoded, output, executable, models, lock_path):
    from PIL import Image, __version__ as pillow_version
    lock=json.loads(Path(lock_path).read_text())
    for path,key in [(Path(executable),'executable'),(Path(models)/'realesrgan-x4plus.bin','weights'),
                     (Path(models)/'realesrgan-x4plus.param','network')]:
        if sha(path)!=lock[key]['sha256']:raise ValueError('Unreviewed inference dependency: '+key)
    output=Path(output);output.mkdir(parents=True,exist_ok=True);rows=selected(selection,decoded);started=time.monotonic()
    image_hashes={}
    for row in rows:
        im=Image.open(row['path']).convert('RGBA');w,h=im.size;stem='%016X'%row['hash']
        if row['method']=='ai':
            halo=min(32,w,h);input_path=output/(stem+'-padded.png');ai_path=output/(stem+'-ai.png')
            padded_rgb(im,halo,row['border']).save(input_path)
            with (output/(stem+'-inference.log')).open('w') as log:
                subprocess.run([str(Path(executable).resolve()),'-i',str(input_path.resolve()),
                    '-o',str(ai_path.resolve()),'-n','realesrgan-x4plus','-m',str(Path(models).resolve()),
                    '-s','4','-t','128','-j','1:1:1'],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=180)
            generated=Image.open(ai_path)
            if generated.size!=((w+2*halo)*4,(h+2*halo)*4):raise ValueError('Wrong inference dimensions')
            image4=generated.crop((halo*4,halo*4,(halo+w)*4,(halo+h)*4)).convert('RGBA')
            image4.putalpha(im.getchannel('A').resize((w*4,h*4),Image.Resampling.LANCZOS))
        else:image4=im.resize((w*4,h*4),Image.Resampling.LANCZOS)
        for scale in (2,4):
            image=image4 if scale==4 else image4.resize((w*2,h*2),Image.Resampling.LANCZOS)
            filename=stem+'-'+str(scale)+'x.png'
            image.save(output/filename);image_hashes[filename]=sha(output/filename)
        print(stem+' '+row['label'],flush=True)
    (output/'provenance.json').write_text(json.dumps({'xbe_sha256':XBE_SHA256,
        'selection_sha256':sha(selection),'upscaler_lock_sha256':sha(lock_path),
        'seconds':time.monotonic()-started,'python':sys.version.split()[0],'pillow':pillow_version,'ai_model':'realesrgan-x4plus',
        'scale2':'Lanczos reduction of 4x result','alpha':'source alpha, Lanczos',
        'font_hud':'conservative Lanczos; no generated glyphs','images':image_hashes},indent=2)+'\n')


def write_pack(rows, path, scale):
    """XRTPv2; validate everything before atomically replacing an old pack."""
    from PIL import Image
    if type(scale) is not int or scale not in (2,4,8) or not rows:
        raise ValueError('Expected nonempty 2x/4x/8x pack')
    packed=[];seen=set()
    for row in rows:
        key=row['hash'];kind=row['kind'];w=row['width'];h=row['height']
        if type(key) is not int or not 0<key<1<<64 or key in seen or kind not in KINDS:
            raise ValueError('Duplicate/invalid identity')
        seen.add(key)
        if not all(type(n) is int and 1<=n<=2048 for n in (w,h)):raise ValueError('Invalid guest size')
        image=Image.open(row['image']).convert('RGBA')
        if image.size!=(w*scale,h*scale):raise ValueError('Wrong replacement size/aspect')
        # Full mip chain for surfaces; UI retains one level. Sampler settings
        # remain those requested by the guest, and the source hash covers its mips.
        levels=[image]
        if row.get('mipmaps',kind=='art'):
            while max(levels[-1].size)>1:
                a,b=levels[-1].size
                levels.append(levels[-1].resize((max(1,a//2),max(1,b//2)),Image.Resampling.LANCZOS))
        data=b''.join(level.tobytes('raw','BGRA') for level in levels)
        packed.append((key,image.width,image.height,len(levels),KINDS[kind],data))
    packed.sort();offset=32+32*len(packed);index=[];payload=[]
    for key,w,h,levels,kind,data in packed:
        index.append(struct.pack('<QIIIIQ',key,w,h,levels,kind,offset));payload.append(data);offset+=len(data)
    header=struct.pack('<4sIIIQII',b'XRTP',2,len(packed),scale,32,scale,0)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as stream:
            temp=Path(stream.name);stream.write(header+b''.join(index)+b''.join(payload));stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        if temp is not None and temp.exists():temp.unlink()
    return len(packed)


def pack(selection, decoded, upscaled, output, scale):
    rows=selected(selection,decoded);upscaled=Path(upscaled);output=Path(output)
    proof=json.loads((upscaled/'provenance.json').read_text())
    if proof['xbe_sha256']!=XBE_SHA256 or proof['selection_sha256']!=sha(selection):
        raise ValueError('Upscale provenance mismatch')
    for row in rows:
        row['image']=upscaled/('%016X-%dx.png'%(row['hash'],scale))
        if sha(row['image'])!=proof['images'][row['image'].name]:raise ValueError('Upscale image changed')
    count=write_pack(rows,output,scale)
    output.with_suffix('.json').write_text(json.dumps({'xbe_sha256':XBE_SHA256,'pack_sha256':sha(output),
        'selection_sha256':sha(selection),'scale':scale,'entries':count,'upscale':proof},indent=2)+'\n')
    print(json.dumps({'pack':str(output),'entries':count,'bytes':output.stat().st_size}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('decode');p.add_argument('capture',type=Path);p.add_argument('output',type=Path)
    for cmd in ('upscale','pack'):
        p=sub.add_parser(cmd);p.add_argument('--selection',type=Path,default=ROOT/'config/texture-pilot.json')
        p.add_argument('--decoded',type=Path,default=ROOT/'artifacts/textures/decoded')
        p.add_argument('--output',type=Path,required=True)
        if cmd=='upscale':
            p.add_argument('--executable',type=Path,required=True);p.add_argument('--models',type=Path,required=True)
            p.add_argument('--lock-path',type=Path,default=ROOT/'config/texture-upscaler.json')
        else:p.add_argument('--upscaled',type=Path,required=True);p.add_argument('--scale',type=int,choices=(2,4),required=True)
    args=vars(parser.parse_args());command=args.pop('command')
    globals()[command](**args)


if __name__=='__main__':main()
