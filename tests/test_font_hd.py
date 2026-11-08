"""Glyph geometry and native mixed-scale pack regression, no game/font download."""
import copy
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from PIL import Image,ImageDraw,ImageChops,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import font_hd
import text_pack
import texture_pilot
import texture_profiles
import play
import test_texture_pilot as texture_tests

FONT=ROOT/'vendor/xboxrecomp/third_party/fonts/atkinson-hyperlegible/AtkinsonHyperlegible-Regular.ttf'


class FontTests(unittest.TestCase):
    def fixture(self):
        source=Image.new('RGBA',(40,16));d=ImageDraw.Draw(source)
        d.rectangle((1,2,7,12),fill=(255,255,255,255))
        d.rectangle((25,2,30,12),fill=(255,255,255,255))
        layout={'width':40,'height':16,'glyphs':[
            {'code':65,'box':[0,0,10,16],'ink':[1,2,8,13],'metrics':[0,7,8]},
            {'code':32,'box':[10,0,20,16],'ink':None,'metrics':[0,0,5]},
            {'code':127,'box':[24,0,34,16],'ink':[1,2,7,13],'metrics':[0,6,8]}]}
        return source,layout

    def test_vector_coverage_stays_in_cell_and_keeps_spaces_fallback_metrics(self):
        source,layout=self.fixture();before=source.tobytes();metrics=copy.deepcopy(layout)
        out=font_hd.render_atlas(source,layout,FONT,8,font_size=12,baseline=13)
        self.assertEqual(out.size,(320,128));self.assertEqual(source.tobytes(),before);self.assertEqual(layout,metrics)
        alpha=out.getchannel('A');stock=source.getchannel('A').resize(out.size,Image.Resampling.NEAREST)
        diff=ImageChops.difference(alpha,stock);allowed=Image.new('L',out.size)
        ImageDraw.Draw(allowed).rectangle((0,0,79,127),fill=255)
        self.assertIsNone(ImageChops.multiply(diff,ImageChops.invert(allowed)).getbbox())
        self.assertEqual(alpha.crop((80,0,160,128)).getbbox(),None)
        self.assertEqual(alpha.crop((192,0,272,128)).tobytes(),stock.crop((192,0,272,128)).tobytes())
        self.assertGreater(len(set(alpha.getdata())),2)
        self.assertEqual(out.getchannel('R').tobytes(),alpha.tobytes())

    def text_fixture(self):
        source=Image.new('RGBA',(72,32));glyphs=[];d=ImageDraw.Draw(source)
        for n,c in enumerate('ovg'):
            x=n*24;d.rectangle((x+2,2,x+9,12),fill='white')
            glyphs.append({'code':ord(c),'box':[x,0,x+24,32],'ink':[2,2,10,13],'metrics':[1,8,9]})
        return source,{'width':72,'height':32,'glyphs':glyphs}

    def test_common_baseline_matches_font_and_preserves_overshoot_descender(self):
        source,layout=self.text_fixture()
        alpha=font_hd.render_atlas(source,layout,FONT,8,font_size=12,baseline=15).getchannel('A')
        # Independent font metrics, not the fabricated legacy ink boxes.
        font=ImageFont.truetype(str(FONT),96);bottoms={}
        for n,c in enumerate('ovg'):
            bounds=alpha.crop((n*192,0,(n+1)*192,256)).getbbox()
            expected=font.getbbox(c,anchor='ls')
            self.assertEqual((bounds[1],bounds[3]),(120+expected[1],120+expected[3]))
            bottoms[c]=bounds[3]
        self.assertGreater(bottoms['g'],bottoms['v'])
        self.assertGreater(bottoms['o'],bottoms['v'])

    def test_legacy_v_height_does_not_change_vector_shape_or_baseline(self):
        source,layout=self.text_fixture()
        changed=copy.deepcopy(layout);changed['glyphs'][1]['ink']=[2,6,10,10]
        other=source.copy();other.paste((0,0,0,0),(24,0,48,32))
        ImageDraw.Draw(other).rectangle((26,6,33,9),fill='white')
        a=font_hd.render_atlas(source,layout,FONT,8,font_size=12,baseline=15)
        b=font_hd.render_atlas(other,changed,FONT,8,font_size=12,baseline=15)
        self.assertEqual(a.tobytes(),b.tobytes())

    def test_incompatible_geometry_refused_instead_of_distorting_or_clipping(self):
        source,layout=self.text_fixture();before=source.tobytes()
        for params in ({'baseline':1},{'baseline':31},{'font_size':80},
                       {'width_scale':float('nan')},{'fallback_codes':[ord('v')]},
                       {'fallback_font':FONT,'fallback_codes':[999]}):
            with self.assertRaises(ValueError):font_hd.render_atlas(source,layout,FONT,8,**params)
            self.assertEqual(source.tobytes(),before)

    def test_fallback_uses_same_scale_and_baseline(self):
        source,layout=self.text_fixture()
        options={'font_size':12,'baseline':15}
        a=font_hd.render_atlas(source,layout,FONT,8,**options)
        b=font_hd.render_atlas(source,layout,FONT,8,fallback_font=FONT,fallback_codes=[ord('g')],**options)
        self.assertEqual(a.tobytes(),b.tobytes())

    def test_invalid_or_overlapping_glyphs_refused_without_editing_source(self):
        source,layout=self.fixture();before=source.tobytes()
        variants=[]
        a=copy.deepcopy(layout);a['glyphs'].append(a['glyphs'][0]);variants.append(a)
        a=copy.deepcopy(layout);a['glyphs'][0]['ink']=[0,0,30,4];variants.append(a)
        a=copy.deepcopy(layout);a['glyphs'][2]['box']=[0,0,10,16];variants.append(a)
        a=copy.deepcopy(layout);a['glyphs'][0]['box']=[-1,0,10,16];variants.append(a)
        for item in variants:
            with self.assertRaises(ValueError):font_hd.render_atlas(source,item,FONT,8)
            self.assertEqual(source.tobytes(),before)

    def test_uv_record_schema_uses_w_minus_one_and_signed_metrics(self):
        source=Image.new('RGBA',(128,256));ImageDraw.Draw(source).rectangle((3,3,4,14),fill='white')
        uv=(3/127,0,6/127,20/255);tail=struct.unpack('<2I',struct.pack('<3hH',-1,2,4,0xCDCD))
        entries=[{'code':c,'floats':[0,0,0,0,0,0],'words':[0,0,0,0,0,0]} for c in range(32,128)]
        entries[1]={'code':33,'floats':[*uv,0,0],'words':[0,0,0,0,*tail]}
        objects={'objects':[{'words':[0,0,0,0,128,256,19,32,127,96,0],
                    'entries':entries}]}
        layout=font_hd.layout_from_objects(objects,source);g=layout['glyphs'][1]
        self.assertEqual(g['box'],[3,0,7,21]);self.assertEqual(g['ink'],[0,3,2,15]);self.assertEqual(g['metrics'],[-1,2,4])

    def test_composition_preserves_world_payload_and_native_font_scale(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);image=path/'img.png';Image.new('RGBA',(4,4),(10,20,30,255)).save(image)
            base=path/'base.xrtp';fonts=path/'font.xrtp';combined=path/'combined.xrtp'
            texture_pilot.write_pack([{'hash':1,'width':2,'height':2,'kind':'art','image':image},
                {'hash':2,'width':2,'height':2,'kind':'font','image':image}],base,2)
            Image.new('RGBA',(16,16),(200,200,200,200)).save(image)
            texture_pilot.write_pack([{'hash':2,'width':2,'height':2,'kind':'font','image':image}],fonts,8)
            self.assertEqual(text_pack.compose(base,fonts,combined),2)
            bh,be=text_pack.read_pack(base);ch,ce=text_pack.read_pack(combined)
            self.assertEqual(be[1],ce[1]);self.assertEqual(ch,{'scale':2,'text_scale':8});self.assertEqual(ce[2][0:2],(16,16))
            source=path/'read.c';exe=path/'read'
            source.write_text('''#include "nv2a_tex_pack.h"
#include <assert.h>
int main(int n,char**v){char e[256];(void)n;assert(nv2a_tex_pack_load(v[1],e,sizeof e)==2);
assert(nv2a_tex_pack_scale()==2 && nv2a_tex_pack_text_scale()==8);
struct nv2a_tex_pack_entry *p=nv2a_tex_pack_find(2,2,2);assert(p && p->width==16);
nv2a_tex_pack_unload();return 0;}''')
            texture_tests.TextureTests().compile(exe,[source,ROOT/'vendor/xboxrecomp/src/kernel/nv2a_tex_pack.c',ROOT/'vendor/xboxrecomp/src/kernel/nv2a_backend_common.c'])
            subprocess.run([str(exe),str(combined)],capture_output=True,check=True)

    def test_text_modes_preserve_texture_choice_and_missing_hd_refused(self):
        env=play.build_environment({'textures':'pilot2x','text':'hd'},'/copy',90,{})
        self.assertEqual(env['RECOMP_TEXTURES_PACK'],str(texture_profiles.pack_path('pilot2x',text='hd')))
        env=play.build_environment({'textures':'pilot2x','text':'original'},'/copy',90,{})
        self.assertEqual(env['RECOMP_TEXTURES_FONT'],'off')
        self.assertEqual(env['RECOMP_TEXTURES_PACK'],str(texture_profiles.pack_path('pilot2x')))
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):texture_profiles.verify_profile('original',Path(folder),text='hd')
