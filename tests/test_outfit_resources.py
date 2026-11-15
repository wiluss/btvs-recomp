"""Synthetic native-menu/pak rewrite regressions; no original assets."""
from pathlib import Path
import hashlib
import struct
import tempfile
import unittest
from unittest.mock import patch
from tools import outfit_resources as outfit
from tools.game_resources import directory_size_fields, read_records


def u32(data,p):return struct.unpack_from('<I',data,p)[0]
def words(*xs):return struct.pack('<'+'I'*len(xs),*xs)

def fake_mbf():
    data=bytearray(845685+14*32)
    strings=words(94)
    for i in range(1,95):
        name=b'IDS_STARTGAME' if i==1 else f'IDS_SYNTHETIC_{i}'.encode()
        strings+=name+b'\0'+words(i)+f'Text {i}'.encode()+b'\0'
    data[100:100+len(strings)]=strings
    struct.pack_into('<I',data,843416,15)
    starts=[843540]+[845685+32*i for i in range(14)]
    for i,start in enumerate(starts):
        struct.pack_into('<II',data,843420+i*8,i+1,start-(843420+8*(i+1)))
    head=b'TMenuMain\0IDM_MAIN\0'+words(1,0,14)
    data[843540:843540+len(head)]=head
    template=(b'TTextButton\0'+bytes(5)+b'IDC_EXTRAS\0'+words(0x83,4,8)
              +b'Offset\0'+words(4,69,348)+b'Extent\0'+words(4,100,50)
              +b'Visible\0'+words(2)+b'\1Text\0'+words(3,64)
              +b'Normal Font\0'+words(3,2)+b'Active Font\0'+words(3,1)
              +b'Horizontal Alignment (0L/1C/2R)\0'+words(0,0)
              +b'Vertical Alignment (0T/1C/2B)\0'+words(0,0))
    assert len(template)==222
    data[845111:845333]=template
    logo=b'TStaticImage\0'+bytes(5)+b'IDC_BUFFY_LOGO\0'+words(3,0,2)+b'Offset\0'+words(4,39,28)+b'Extent\0'+words(4,256,128)
    data[844243:844243+len(logo)]=logo
    for i in range(1,15):
        text=f'Original menu {i+1}'.encode()+b'\0'
        data[starts[i]:starts[i]+len(text)]=text
    return bytes(data)


def pak(rows):
    # One dictionary word and one mounted MBF-size metadata entry.
    pool=b'buffy\0'
    prefix=words(0x52014,len(pool),0,len(pool),1,1,0)+pool+words(0,0)
    prefix+=words(1,1,1)+bytes(36)
    prefix+=words(13,3)+b'mbf'+words(0,0,1,1)+struct.pack('<HHI',0,0,1)
    mbf=next(payload for name,_,_,payload in rows if name.endswith('.mbf'))
    prefix+=struct.pack('<HHHHI',0,0,1,0,len(mbf))+words(0xffffffff)
    result=bytearray(prefix)
    for name,res,manual,payload in rows:
        def string(s):b=s.encode();return words(len(b))+b
        header=words(1,len(result),0,len(payload),manual)+string(name)+string(res)+words(0)
        header=header[:8]+words(len(header)+len(payload))+header[12:]
        result+=header+payload
    return bytes(result)+bytes(32)


class OutfitResourceTests(unittest.TestCase):
    def test_native_menu_strings_relative_directory_and_original_submenus(self):
        source=fake_mbf()
        with patch.object(outfit,'MBF_SHA256',hashlib.sha256(source).hexdigest()):
            result=outfit.menu_mbf(source)
        start=result.index(b'IDS_STARTGAME\0')-4
        self.assertEqual(u32(result,start),103)
        for text in [b'Outfits\0',b'Level outfit\0',b'Dark Slayer\0',b'Back\0']:
            self.assertIn(text,result)
        # Locate the native menu table by the retained width/height area.
        delta=result.index(b'TMenuMain\0IDM_MAIN\0')-843540
        index=843420+delta-8
        self.assertEqual(u32(result,index-4),16)
        starts=[index+8*(i+1)+u32(result,index+8*i+4) for i in range(16)]
        self.assertTrue(result[starts[0]:].startswith(b'TMenuMain\0IDM_MAIN\0'))
        self.assertEqual(u32(result,starts[0]+27),15)
        for i in range(1,15):self.assertTrue(result[starts[i]:].startswith(f'Original menu {i+1}'.encode()))
        self.assertTrue(result[starts[15]:].startswith(b'TMenuMain\0IDM_OUTFITS\0'))
        self.assertEqual(result.count(b'IDC_OUTFIT_'),7)
        self.assertEqual(result.count(b'IDC_WARDROBE_TITLE\0'),1)
        self.assertEqual(result.count(b'IDC_WARDROBE_HINT\0'),0)
        with self.assertRaisesRegex(ValueError,'Unreviewed'):
            outfit.menu_mbf(source+b'tampered')

    def test_private_namespace_clones_metadata_without_changing_campaign_entries(self):
        groups={0:['buffybronze','buffysport','buffycheer','buffyslayer','darkslayer'],
                4:['buffybronze','buffyworkout','buffycheer','buffyslayer','darkslayer'],5:['default']}
        names=list(dict.fromkeys(name for rows in groups.values() for name in rows))
        pool=b'';offsets=[]
        for name in names:offsets.append(len(pool));pool+=name.encode()+b'\0'
        data=words(0x52014,len(pool),0,len(pool),len(names),len(names),*offsets)+pool+words(0,0)
        data+=words(11,11,3)
        for name,parent in [('meshes',65535),('chars',0),('slayer',1)]:
            data+=name.encode().ljust(34,b'\0')+struct.pack('<H',parent)
        for kind,items in groups.items():
            ext={0:b'mtx',4:b'msh',5:b'gin'}[kind]
            data+=words(kind,len(ext))+ext+words(0,0,len(items),len(items))
            for name in items:
                ident=names.index(name)
                data+=struct.pack('<HHIHHHHI',ident,ident,1,2,ident,1,0,12345)
        data+=words(0xffffffff)
        before=outfit.directory_layout(data)
        result=outfit.preview_directory(data)
        after=outfit.directory_layout(result)
        self.assertEqual(before['directory_count'],3)
        self.assertEqual(after['directory_count'],4)
        self.assertEqual(len(after['fields']),22)
        for kind,items in groups.items():
            for name in items:
                fields=[f for f in after['fields'] if f['kind']==kind and f['name']==name]
                self.assertEqual({f['directory'] for f in fields},{2,3})
                self.assertTrue(all(f['size']==12345 for f in fields))
        self.assertIn(b'recomp_outfits\0',result)
        with self.assertRaisesRegex(ValueError,'directory tree'):
            outfit.preview_directory(result)

    def test_pack_rewrite_updates_mounted_mbf_size_and_keeps_sources_unchanged(self):
        mbf=fake_mbf()
        with tempfile.TemporaryDirectory() as folder:
            game=Path(folder);(game/'pak').mkdir()
            original=[('meshes\\chars\\guislayer\\buffybronze.msh','base',False,b'GUI'),
                      ('meshes\\chars\\guislayer\\default.gin','',False,b'STATES'),
                      ('animation\\idle.boneanim','',False,b'IDLE'),
                      ('meshes\\chars\\guislayer\\buffybronze.ban','',True,b'ANIMATION TABLE'),
                      ('interfc\\buffy.mbf','',False,mbf)]
            menu=game/'pak/res_null.pak';menu.write_bytes(pak(original))
            names=['buffybronze','buffyworkout','buffycheer','buffyslayer','darkslayer']
            catalog={'outfits':[]}
            for ident,stem in enumerate(names):
                name=f'meshes\\chars\\slayer\\{stem}'
                rows=[(name+'.msh','base',False,f'MODEL {ident}'.encode())]
                texture='meshes\\chars\\slayer\\'+('buffysport' if ident==1 else stem)+'.mtx'
                rows.extend((texture,part,False,part.encode()) for part in ['face','body','leg'])
                # Minimal metadata also includes a .mbf-sized entry for this fixture.
                rows.append(('unused.mbf','',False,b'x'))
                path=game/'pak'/f'outfit{ident}.pak';path.write_bytes(pak(rows))
                records=read_records(path)
                catalog['outfits'].append({'id':stem,'sources':[{'pack':path.name,'model':{'name':name+'.msh'},'materials':[{'name':texture}]*3}]})
            before={p:p.read_bytes() for p in (game/'pak').iterdir()}
            with patch.object(outfit,'MBF_SHA256',hashlib.sha256(mbf).hexdigest()),patch.object(outfit,'stock_inventory',return_value=catalog) as verify,patch.object(outfit,'preview_directory',side_effect=lambda b:b[:read_records(menu)[0].header_offset]):
                result=outfit.compile_menu_pack(game,game/'title.json')
                verify.assert_called_once_with(game,game/'title.json')
            output=game/'result.pak';output.write_bytes(result)
            records=read_records(output)
            menu_record=next(r for r in records if r.name=='interfc\\buffy.mbf')
            mounted=next(f for f in directory_size_fields(result) if f['kind']==13)
            self.assertEqual(mounted['size'],menu_record.data_size)
            self.assertGreater(mounted['size'],len(mbf))
            self.assertEqual(len([r for r in records if r.name.endswith('.msh')]),6)
            self.assertEqual(len([r for r in records if r.name.endswith('.ban')]),6)
            self.assertEqual(len([r for r in records if r.name.endswith('.gin')]),2)
            self.assertEqual(len([r for r in records if r.name.endswith('.boneanim')]),1)
            self.assertTrue(all(p.read_bytes()==data for p,data in before.items()))


def level_pack(rows):
    names=[name.rsplit('\\',1)[1][:-4] for name,_,_,_ in rows if name.endswith('.msh')]
    pool=b'';offsets=[]
    for name in names:offsets.append(len(pool));pool+=name.encode()+b'\0'
    data=words(0x52014,len(pool),0,len(pool),len(names),len(names),*offsets)+pool+words(0,0)
    data+=words(len(names),len(names),3)
    for name,parent in [('meshes',65535),('chars',0),('slayer',1)]:data+=name.encode().ljust(34,b'\0')+struct.pack('<H',parent)
    data+=words(4,3)+b'msh'+words(0,0,len(names),len(names))
    for i,stem in enumerate(names):
        payload=next(payload for name,_,_,payload in rows if name.endswith('\\'+stem+'.msh'))
        data+=struct.pack('<HHIHHHHI',i,i,1,2,i,1,0,len(payload))
    data+=words(0xffffffff)
    result=bytearray(data)
    for name,res,manual,payload in rows:
        def string(s):b=s.encode();return words(len(b))+b
        header=words(1,len(result),0,len(payload),manual)+string(name)+string(res)+words(0)
        result+=header[:8]+words(len(header)+len(payload))+header[12:]+payload
    return bytes(result)+bytes(32)


class GameplayOutfitResourceTests(unittest.TestCase):
    def test_copied_geometry_changes_preserve_animations_scripts_and_dark_enemy(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'level.pak'
            rows=[('meshes\\chars\\slayer\\buffycheer.msh','base',False,b'ORIGINAL CHEERLEADER MODEL')]
            rows += [('meshes\\chars\\slayer\\buffycheer.mtx',part,False,b'OLD '+part.encode()) for part in ['face','body','leg']]
            preserved=[('meshes\\chars\\slayer\\default.gin','',False,b'STATE DEFINITIONS'),
                       ('animation\\attack.boneanim','',False,bytes(range(255))),
                       ('meshes\\chars\\slayer\\buffycheer.ban','',True,b'FULL CAMPAIGN ANIMATION TABLE'),
                       ('levels\\synthetic.sls','',False,b'ORIGINAL LEVEL SCRIPT'),
                       ('meshes\\chars\\slayer\\darkslayer.msh','base',False,b'UNCHANGED ENEMY')]
            rows+=preserved
            original=level_pack(rows);source.write_bytes(original)
            from tools.game_resources import directory_layout
            assets={'mesh':outfit.Payload('meshes\\chars\\slayer\\buffyworkout.msh','base',7,False,False,b'NEW RIG'),
                    'low':None,'dictionary':original[:directory_layout(original)['string_table_end']],
                    'materials':tuple(outfit.Payload('meshes\\chars\\slayer\\buffysport.mtx',part,len(part),False,False,part.encode()) for part in ['face','body','leg'])}
            result=outfit.compile_play_pack(source,assets)
            output=Path(directory)/'result.pak';output.write_bytes(result)
            records=read_records(output)
            def payload(name):
                row=next(r for r in records if r.name==name)
                return result[row.data_offset:row.data_offset+row.data_size]
            self.assertEqual(payload(rows[0][0]),b'NEW RIG')
            for name,_,_,data in preserved:self.assertEqual(payload(name),data)
            self.assertEqual([r.resource for r in records if r.name.endswith('buffysport.mtx')],['face','body','leg'])
            size=next(f['size'] for f in directory_size_fields(result) if f['name']=='buffycheer')
            self.assertEqual(size,7)
            self.assertEqual(source.read_bytes(),original)
            bad=dict(assets,dictionary=b'wrong')
            with self.assertRaisesRegex(ValueError,'dictionaries differ'):outfit.compile_play_pack(source,bad)

    def test_unrelated_pack_is_retained_and_duplicate_target_materials_are_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'level.pak'
            rows=[('meshes\\chars\\slayer\\buffybronze.msh','base',False,b'OLD')]
            rows += [('meshes\\chars\\slayer\\buffybronze.mtx',part,False,b'OLD') for part in ['face','body','leg']]
            rows += [('meshes\\chars\\slayer\\darkslayer.msh','base',False,b'ENEMY')]
            rows += [('meshes\\chars\\slayer\\darkslayer.mtx',part,False,part.encode()) for part in ['face','body','leg']]
            data=level_pack(rows);path.write_bytes(data)
            from tools.game_resources import directory_layout
            assets={'mesh':outfit.Payload('meshes\\chars\\slayer\\darkslayer.msh','base',3,False,False,b'NEW'),
                    'low':None,'dictionary':data[:directory_layout(data)['string_table_end']],
                    'materials':tuple(outfit.Payload('meshes\\chars\\slayer\\darkslayer.mtx',part,len(part),False,False,part.encode()) for part in ['face','body','leg'])}
            result=outfit.compile_play_pack(path,assets);out=Path(directory)/'result.pak';out.write_bytes(result)
            self.assertEqual(len([r for r in read_records(out) if r.name.endswith('darkslayer.mtx')]),3)
            path.write_bytes(level_pack([('meshes\\chars\\slayer\\darkslayer.msh','base',False,b'ENEMY')]))
            self.assertIsNone(outfit.compile_play_pack(path,assets))


if __name__=='__main__':unittest.main()
