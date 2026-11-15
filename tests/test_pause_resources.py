"""Synthetic Pause layout and sequential resource/lifetime boundary fixtures."""
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from tools import outfit_resources as res
from tools.game_resources import read_records, directory_layout, directory_size_fields
from tests.test_outfit_resources import fake_mbf, words, u32


def pause_fixture():
    raw=fake_mbf();template=raw[845111:845333]
    def button(name,ident,tab,y):
        block=bytearray(template.replace(b'IDC_EXTRAS\0',name.encode()+b'\0'))
        at=block.index(name.encode()+b'\0')+len(name)+1
        struct.pack_into('<II',block,at,ident,tab)
        struct.pack_into('<ii',block,block.index(b'Offset\0')+11,273,y)
        return bytes(block)
    pause=b'TMenuPause\0IDM_PAUSE\0'+words(9,0,16)
    pause+=button('IDC_PAUSE_RESUME',85,1,76)+button('IDC_PAUSE_OPTIONS',86,2,128)+button('IDC_PAUSE_QUIT',87,3,180)
    pause+=b'IDC_PAUSE_OBJECTIVE\0'+words(133,0,0)+b'untouched objective'
    pause=pause.ljust(3091,b'\0')
    table=843420;starts=[table+8*(i+1)+u32(raw,table+i*8+4) for i in range(15)]
    menus=[raw[starts[i]:starts[i+1] if i<14 else len(raw)] for i in range(15)];menus[8]=pause
    out=bytearray(raw[:table]);at=15*8
    for i,menu in enumerate(menus):out+=words(i+1,at-8*(i+1));at+=len(menu)
    return bytes(out)+b''.join(menus)


def menus(data):
    count=16;table=data.index(b'TMenuMain\0IDM_MAIN\0')-count*8
    starts=[table+8*(i+1)+u32(data,table+i*8+4) for i in range(count)]
    return [data[starts[i]:starts[i+1] if i<count-1 else len(data)] for i in range(count)]


def prefix():
    groups={0:['buffybronze','buffysport','buffycheer','buffyslayer','darkslayer'],
            4:['buffybronze','buffyworkout','buffycheer','buffyslayer','darkslayer'],5:['default'],13:['buffy']}
    names=list(dict.fromkeys(n for rows in groups.values() for n in rows));pool=b'';offsets=[]
    for name in names:offsets.append(len(pool));pool+=name.encode()+b'\0'
    data=words(0x52014,len(pool),0,len(pool),len(names),len(names),*offsets)+pool+words(0,0)
    data+=words(12,12,4)
    for name,parent in [('meshes',65535),('chars',0),('slayer',1),('interfc',65535)]:data+=name.encode().ljust(34,b'\0')+struct.pack('<H',parent)
    for kind,items in groups.items():
        ext={0:b'mtx',4:b'msh',5:b'gin',13:b'mbf'}[kind]
        data+=words(kind,len(ext))+ext+words(0,0,len(items),len(items))
        for name in items:
            ident=names.index(name);directory=3 if kind==13 else 2
            data+=struct.pack('<HHIHHHHI',ident,ident,1,directory,ident,1,0,12345)
    return data+words(0xffffffff)


def pack(pre,rows):
    out=bytearray(pre)
    for name,resource,manual,data in rows:
        def string(s):b=s.encode();return words(len(b))+b
        head=words(1,len(out),0,len(data),int(manual))+string(name)+string(resource)+words(0)
        out+=head[:8]+words(len(head)+len(data))+head[12:]+data
    return bytes(out)+bytes(32)


class PauseResourceTests(unittest.TestCase):
    def test_pause_button_keeps_other_menus_and_shifts_native_focus_tabs(self):
        raw=pause_fixture()
        with patch.object(res,'MBF_SHA256',hashlib.sha256(raw).hexdigest()):
            legacy=menus(res.menu_mbf(raw));result=menus(res.menu_mbf(raw,pause=True))
        for i in range(16):
            if i!=8:self.assertEqual(result[i],legacy[i])
        pause=result[8];self.assertEqual(u32(pause,29),17)
        for name,ident,tab,y in [('IDC_PAUSE_RESUME',85,1,76),('IDC_PAUSE_OUTFITS',512,2,115),('IDC_PAUSE_OPTIONS',86,3,154),('IDC_PAUSE_QUIT',87,4,193)]:
            at=pause.index(name.encode()+b'\0')+len(name)+1
            self.assertEqual(struct.unpack_from('<II',pause,at),(ident,tab))
            self.assertEqual(struct.unpack_from('<ii',pause,pause.index(b'Offset\0',at)+11),(273,y))
        self.assertIn(b'untouched objective',pause)
        with self.assertRaises(ValueError):res._pause_menu(legacy[8][:-1])

    def test_live_pack_preserves_original_sequence_and_appends_only_missing_idle(self):
        mbf=pause_fixture();pre=prefix();dictionary=pre[:directory_layout(pre)['string_table_end']]
        stems=['buffybronze','buffyworkout','buffycheer','buffyslayer','darkslayer'];stock=[]
        for i,stem in enumerate(stems):
            mesh=res.Payload(f'meshes\\chars\\slayer\\{stem}.msh','base',30+i,False,False,bytes([i])* (30+i))
            material=res.Payload(f'meshes\\chars\\slayer\\{stem}.mtx','face',1,False,False,b'M')
            stock.append({'mesh':mesh,'materials':tuple(res.replace(material,resource=str(j)) for j in range(3)),'dictionary':dictionary})
        idle=['buffy_idle_standing_menu','buffy_idle_standingll','buffy_idle_standinglr','buffy_idle_standing_brushoff']
        bones=[(f'animation\\buffyfinal_move\\{n}.boneanim','',False,n.encode()) for n in idle]
        rows=[('interfc\\buffy.mbf','',False,mbf),('meshes\\chars\\slayer\\buffyslayer.msh','base',False,b'ORIGINAL GEOMETRY'),('meshes\\chars\\slayer\\default.gin','',False,b'ORIGINAL GIN')]+bones[1:]
        menu_rows=[('meshes\\chars\\guislayer\\buffybronze.ban','',True,b'MENU ANIMATION TABLE')]+bones
        with tempfile.TemporaryDirectory() as folder,patch.object(res,'MBF_SHA256',hashlib.sha256(mbf).hexdigest()):
            folder=Path(folder);source=folder/'level.pak';menu=folder/'menu.pak';source.write_bytes(pack(pre,rows));menu.write_bytes(pack(pre,menu_rows));original=source.read_bytes()
            result=res.compile_live_pack(source,stock,menu);out=folder/'out.pak';out.write_bytes(result);records=read_records(out)
            self.assertEqual(source.read_bytes(),original)
            self.assertEqual(len(records),len(rows)+27)
            for i,row in enumerate(rows):
                parsed=records[i];self.assertEqual((parsed.name,parsed.resource,parsed.manual),row[:3])
                if i:self.assertEqual(result[parsed.data_offset:parsed.data_offset+parsed.data_size],row[3])
            extra=records[len(rows):]
            self.assertEqual(sum(r.name.endswith('.msh') for r in extra),5)
            self.assertEqual(sum(r.name.endswith('.boneanim') for r in extra),1)
            self.assertTrue(all(r.manual for r in extra[-5:]))
            self.assertTrue(all(r.name.endswith('.ban') for r in extra[-5:]))
            layout=directory_layout(result);self.assertEqual(layout['directory_count'],6)
            fields=directory_size_fields(result)
            for i,stem in enumerate(stems):self.assertEqual([f['size'] for f in fields if f['directory']==5 and f['kind']==4 and f['name']==stem],[30+i])
            self.assertEqual([f['size'] for f in fields if f['directory']==2 and f['kind']==4 and f['name']=='buffyslayer'],[12345])
            bad=list(stock);bad[0]=dict(stock[0],dictionary=b'foreign')
            with self.assertRaisesRegex(ValueError,'dictionaries differ'):res.compile_live_pack(source,bad,menu)
            menu.write_bytes(pack(pre,menu_rows[:-1]))
            with self.assertRaisesRegex(ValueError,'idle animations'):res.compile_live_pack(source,stock,menu)
