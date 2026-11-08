"""Synthetic vector masters only; no game glyphs, models or font download."""
import copy
from io import BytesIO
from pathlib import Path
import sys
import unittest

from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTFont

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import font_outline


class OutlineTests(unittest.TestCase):
    def fixture(self):
        paths={
            '65':'M1 6 L5 6 L5 12 L1 12 Z',
            '111':'M0 4 L8 4 L8 12 L0 12 Z M2 6 L2 10 L6 10 L6 6 Z',
            '103':'M0 5 L3 5 L3 18 L0 18 Z'}
        master={'schema':1,'family':'Synthetic Outline Test','units_per_pixel':64,
                'em_pixels':20,'baseline':15,'paths':paths}
        layout={'width':72,'height':24,'glyphs':[
            {'code':c,'box':[n*24,0,(n+1)*24,24],'ink':[1,2,9,13],'metrics':[1,8,9]}
            for n,c in enumerate([65,111,103])]}
        return master,layout

    def test_deterministic_font_and_left_bearing_matches_outline(self):
        master,layout=self.fixture();before=copy.deepcopy((master,layout))
        a=font_outline.build_font(master,layout);b=font_outline.build_font(master,layout)
        self.assertEqual(a,b);self.assertEqual((master,layout),before)
        font=TTFont(BytesIO(a))
        self.assertEqual(font['head'].created,2082844800)
        self.assertEqual(font['head'].modified,2082844800)
        self.assertEqual(font['hmtx']['u0041'][1],64)
        self.assertEqual(font['hmtx']['u0041'][1],font['glyf']['u0041'].xMin)
        self.assertEqual(set(font.getBestCmap()),{32,65,103,111})

    def test_counter_stays_open_and_descender_passes_baseline(self):
        master,layout=self.fixture();font=ImageFont.truetype(BytesIO(font_outline.build_font(master,layout)),160)
        image=Image.new('L',(192,192));d=ImageDraw.Draw(image)
        d.text((0,120),'o',font=font,fill=255,anchor='ls')
        self.assertGreater(image.getpixel((8,64)),200)
        self.assertEqual(image.getpixel((32,64)),0)
        self.assertEqual(image.getbbox(),(0,32,64,96))
        image.paste(0,(0,0,192,192));d.text((0,120),'g',font=font,fill=255,anchor='ls')
        self.assertEqual(image.getbbox(),(0,40,24,144))

    def test_missing_extra_unclosed_invalid_and_overflow_paths_refused(self):
        master,layout=self.fixture();variants=[]
        x=copy.deepcopy(master);del x['paths']['65'];variants.append(x)
        x=copy.deepcopy(master);x['paths']['66']=x['paths']['65'];variants.append(x)
        for path in ['M0 0 L1 0 L1 1','M0 0 Z','M0 0 L1e999 1 L1 2 Z',
                     'M-1 3 L5 3 L5 5 L-1 5 Z','M0 0 L30 0 L30 2 L0 2 Z',
                     '<script>bad</script>']:
            x=copy.deepcopy(master);x['paths']['65']=path;variants.append(x)
        for item in variants:
            with self.assertRaises(ValueError):font_outline.build_font(item,layout)

    def test_larger_master_changes_ink_without_changing_advance(self):
        master,layout=self.fixture();other=copy.deepcopy(master)
        other['paths']['65']='M0 6 L7 6 L7 12 L0 12 Z'
        a=TTFont(BytesIO(font_outline.build_font(master,layout)))
        b=TTFont(BytesIO(font_outline.build_font(other,layout)))
        self.assertEqual(a['hmtx']['u0041'][0],b['hmtx']['u0041'][0])
        self.assertEqual(a['glyf']['u0041'].yMin,b['glyf']['u0041'].yMin)
        self.assertGreater(b['glyf']['u0041'].xMax,a['glyf']['u0041'].xMax)

    def test_second_reviewed_geometry_keeps_source_units_and_descender(self):
        master,layout=self.fixture();master.update(em_pixels=32,baseline=21)
        master['paths']['103']='M0 14 L3 14 L3 24 L0 24 Z'
        layout['height']=30
        for g in layout['glyphs']:g['box'][3]=30
        data=font_outline.build_font(master,layout);tt=TTFont(BytesIO(data))
        self.assertEqual(tt['head'].unitsPerEm,2048)
        self.assertEqual(tt['hhea'].ascent,1344)
        self.assertEqual(tt['hmtx']['u0041'][0],11*64)
        font=ImageFont.truetype(BytesIO(data),256);image=Image.new('L',(240,240))
        ImageDraw.Draw(image).text((0,168),'g',font=font,fill=255,anchor='ls')
        self.assertEqual(image.getbbox(),(0,112,24,192))
        for em,baseline in [(32,20),(32.0,21),(32,True),(20,21)]:
            bad=copy.deepcopy(master);bad.update(em_pixels=em,baseline=baseline)
            with self.assertRaises(ValueError):font_outline.build_font(bad,layout)


if __name__=='__main__':unittest.main()
