"""Golden bytes, native decoding/reading, provenance and rejected launches."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from PIL import Image
import texture_pilot as pilot
import texture_snapshot_lldb as snapshot
import texture_profiles as profiles
import graphics_settings
import play


class TextureTests(unittest.TestCase):
    def row(self, folder, key=0x9000000000000001, kind='font', scale=2):
        image=Path(folder)/('source-'+str(key)+'.png')
        Image.new('RGBA',(2*scale,2*scale),(10,20,30,40)).save(image)
        return {'hash':key,'width':2,'height':2,'kind':kind,'image':image}

    def test_hash_vectors_and_mip_extent(self):
        self.assertEqual(snapshot.texture_hash(b''),0x40500CA3D9E617F3)
        self.assertEqual(snapshot.texture_hash(bytes(64)),0x69597731194007AB)
        self.assertEqual(snapshot.texture_hash(bytes(range(256))*4+b'xboxrecomp'),0x0B060D91FB09F186)
        self.assertEqual(snapshot.dxt_extent(12,8,4,4),40)
        for args in [(12,7,4,1),(15,8,4,5),(11,8,4,1),(15,0,4,1)]:
            with self.assertRaises(ValueError):snapshot.dxt_extent(*args)

    def test_pack_golden_alpha_unsigned_sort_and_native_reader(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);pack=path/'pack.xrtp'
            a=self.row(path,key=1);b=self.row(path)
            pilot.write_pack([b,a],pack,2);data=pack.read_bytes()
            self.assertEqual(data[:32],b'XRTP'+struct.pack('<IIIQII',2,2,2,32,2,0))
            self.assertEqual(struct.unpack_from('<QIIIIQ',data,32),(1,4,4,1,1,96))
            self.assertEqual(struct.unpack_from('<QIIIIQ',data,64),(b['hash'],4,4,1,1,160))
            self.assertEqual(data[96:],bytes([30,20,10,40])*32)
            # Parse our bytes with the actual toolkit, independently of Python.
            source=path/'read.c';exe=path/'read'
            source.write_text('''#include "nv2a_tex_pack.h"
#include <assert.h>
int main(int n,char **v){char err[256];(void)n;
 assert(nv2a_tex_pack_load(v[1],err,sizeof err)==2);
 struct nv2a_tex_pack_entry *e=nv2a_tex_pack_find(1,2,2);
 assert(e && e->width==4 && e->levels==1);
 const unsigned *p=nv2a_tex_pack_texels(e);assert(p && p[0]==0x280A141Eu);
 nv2a_tex_pack_set_kind_enabled(XRTP_KIND_FONT,0);assert(!nv2a_tex_pack_find(1,2,2));
 nv2a_tex_pack_unload();return 0;}
''')
            self.compile(exe,[source,ROOT/'vendor/xboxrecomp/src/kernel/nv2a_tex_pack.c',
                              ROOT/'vendor/xboxrecomp/src/kernel/nv2a_backend_common.c'])
            subprocess.run([str(exe),str(pack)],check=True,capture_output=True)

    def compile(self, exe, sources):
        result=subprocess.run(['clang','-std=c11','-O2','-ffunction-sections','-fdata-sections',
            '-Wl,-dead_strip','-I',str(ROOT/'vendor/xboxrecomp/src/kernel'),'-I',str(ROOT/'vendor/xboxrecomp/src/d3d'),
            *map(str,sources),'-lm','-o',str(exe)],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_native_decoder_matches_solid_dxt1_and_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);exe=path/'decode';raw=struct.pack('<HHI',0xF800,0x07E0,0)
            (path/'raw').write_bytes(raw)
            self.compile(exe,[ROOT/'tools/texture_decode.c',ROOT/'vendor/xboxrecomp/src/kernel/nv2a_backend_common.c'])
            args=[str(exe),'12','4','4','0','1',str(path/'raw'),str(path/'pixels')]
            run=subprocess.run(args,capture_output=True,text=True,check=True)
            self.assertEqual(int(run.stdout.strip(),16),snapshot.texture_hash(raw))
            self.assertEqual((path/'pixels').read_bytes(),bytes([0,0,255,255])*16)
            (path/'raw').write_bytes(raw+b'EXTRA')
            self.assertNotEqual(subprocess.run(args,capture_output=True).returncode,0)

    def test_mips_and_invalid_write_preserve_previous_pack(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);pack=path/'pack';row=self.row(path,kind='art',scale=4)
            pilot.write_pack([row],pack,4);original=pack.read_bytes()
            self.assertEqual(struct.unpack_from('<QIIIIQ',original,32)[1:4],(8,8,4))
            self.assertEqual(len(original),64+(64+16+4+1)*4)
            for rows,scale in [([row,row],4),([dict(row,width=3)],4),([dict(row,hash=True)],4),([row],True)]:
                with self.assertRaises(ValueError):pilot.write_pack(rows,pack,scale)
                self.assertEqual(pack.read_bytes(),original)
            with patch.object(pilot.os,'replace',side_effect=OSError('replace failed')):
                with self.assertRaises(OSError):pilot.write_pack([row],pack,4)
            self.assertEqual(pack.read_bytes(),original)
            self.assertEqual(sorted(p.name for p in path.iterdir()),['pack',row['image'].name])

    def test_wrap_and_clamp_borders(self):
        image=Image.new('RGB',(2,2));image.putdata([(1,2,3),(4,5,6),(7,8,9),(10,11,12)])
        wrap=pilot.padded_rgb(image,1,'wrap');clamp=pilot.padded_rgb(image,1,'clamp')
        self.assertEqual(wrap.getpixel((0,0)),(10,11,12))
        self.assertEqual(clamp.getpixel((0,0)),(1,2,3))
        self.assertEqual(list(wrap.crop((1,1,3,3)).getdata()),list(image.getdata()))

    def test_profile_hash_guard_and_missing_pack_before_preference_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'config').mkdir();(root/'config/texture-pilot.json').write_text('{"entries":[{}]}')
            (root/'config/texture-upscaler.json').write_text('{}')
            settings=root/'settings.json';graphics_settings.save_settings(settings,{'scale':4})
            original=settings.read_bytes()
            with patch.object(play,'ROOT',root):
                with self.assertRaisesRegex(SystemExit,'Pack de textures refusé'):
                    play.main(['--settings-file',str(settings),'--textures','pilot2x','--save-settings'])
            self.assertEqual(settings.read_bytes(),original)
            self.assertFalse((root/'build').exists())
            pack=profiles.pack_path('pilot2x',root);pilot.write_pack([self.row(root)],pack,2)
            proof={'xbe_sha256':snapshot.XBE_SHA256,'scale':2,'entries':1,'pack_sha256':pilot.sha(pack),
                'selection_sha256':pilot.sha(root/'config/texture-pilot.json'),
                'upscale':{'upscaler_lock_sha256':pilot.sha(root/'config/texture-upscaler.json')}}
            pack.with_suffix('.json').write_text(json.dumps(proof));profiles.verify_profile('pilot2x',root)
            pack.write_bytes(pack.read_bytes()[:-1]+b'!')
            with self.assertRaises(ValueError):profiles.verify_profile('pilot2x',root)
            env=play.build_environment({'textures':'pilot4x'},'/copy/hdd',90,{'RECOMP_TEXTURES_PACK':'bad'})
            self.assertEqual(env['RECOMP_TEXTURES_PACK'],str(profiles.pack_path('pilot4x')))
            self.assertEqual(play.build_environment({},'/copy/hdd',90,{})['RECOMP_TEXTURES_PACK'],'none')
