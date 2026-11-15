"""Read original level labels and observe successful pack opens in the host log.

No guest addresses, runtime edits, save contents or external level catalog.
"""
from pathlib import Path
import json
import os
import re
import shlex

MAP_ID=re.compile(r'[a-z0-9_-]{1,80}')
PACK_OPEN=re.compile(
    rb'^\s*\[FILE\] d:\\pak\\res_([a-z0-9_-]{1,80})\.pak '
    rb'\(disp [0-9]+ opts 0x[0-9a-f]+ from 0x[0-9a-f]+\) -> 0x00000000\s*$',re.I)


def mission_names(data):
    if len(data)>64*1024:raise ValueError('Mission list exceeds supported size')
    names={}
    for line in data.decode('ascii').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):continue
        if len(line)>2048:raise ValueError('Mission entry exceeds supported size')
        fields=shlex.split(line)
        if len(fields)<6 or fields[0] not in ('EXEC','SPECIAL'):raise ValueError('Unsupported mission list entry')
        key,label=fields[5].lower(),fields[3]
        if (not MAP_ID.fullmatch(key) or not 2<=len(label)<=128
                or any(ord(c)<32 or ord(c)>126 for c in label)):
            raise ValueError('Invalid mission label')
        if key in names and names[key]!=label:raise ValueError('Conflicting mission label')
        names[key]=label
    if not names or len(names)>256:raise ValueError('Missing or excessive mission entries')
    return names


def load_names(root):
    if __package__:
        from .loadvars_fix import verify_xbe
        from .game_resources import read_records
    else:
        from loadvars_fix import verify_xbe
        from game_resources import read_records
    root=Path(root);game=root/'private/game'
    verify_xbe(game/'Default.xbe',json.loads((root/'config/title.json').read_text()))
    pack=game/'pak/res_null.pak'
    rows=[row for row in read_records(pack) if row.name=='gameinfo\\missionlist.txt']
    if len(rows)!=1 or rows[0].data_size>64*1024:raise ValueError('Unsupported mission list resource')
    with pack.open('rb') as stream:
        stream.seek(rows[0].data_offset);names=mission_names(stream.read(rows[0].data_size))
    return names


def level_label(key,names):
    if key=='null':return 'Main menu'
    if key in names:return names[key]
    if key=='g00_buffyhistory':return 'Buffy History'
    arena=re.fullmatch(r'arena0([1-4])d?',key)
    if arena:return 'Arena '+arena[1]
    return None


class LogLevelTracker:
    """Bounded incremental tail; only successful disc-pack opens affect state."""
    def __init__(self,path,names,offset=0):
        self.path=Path(path);self.names=names;self.offset=offset
        self.pending=b'';self.dropping=False
        self.identity=None

    def poll(self):
        try:
            with self.path.open('rb') as stream:
                info=os.fstat(stream.fileno());identity=(info.st_dev,info.st_ino)
                if (self.identity is not None and identity!=self.identity) or info.st_size<self.offset:
                    self.offset=0;self.pending=b'';self.dropping=False
                self.identity=identity
                stream.seek(self.offset);block=stream.read(256*1024);self.offset+=len(block)
        except OSError:return []
        lines=(self.pending+block).split(b'\n');self.pending=lines.pop()
        labels=[]
        for line in lines:
            if self.dropping:self.dropping=False;continue
            if len(line)>512:continue
            match=PACK_OPEN.fullmatch(line)
            if not match:continue
            key=match[1].decode('ascii').lower();label=level_label(key,self.names)
            if label is not None:labels.append(label)
            elif re.fullmatch(r'(m[0-9]{2}_.+|hub[0-9]{2}|arena[0-9]+d?)',key):
                labels.append('In game')  # unknown level never inherits a stale name
        if len(self.pending)>512:
            self.pending=b'';self.dropping=True
        return labels
