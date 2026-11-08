"""Read-only font metadata snapshot for the reviewed Buffy XBE.

GUI::TFontData vtable 0x006634D8 is proven by our MAP and constructor
0x001EB7B0 (mov [eax],0x6634d8), XBE cd49da61… . No target calls/writes.
The table schema is 4 UV floats + 3 signed metrics + 2 padding bytes.
"""
import lldb,json,struct,hashlib,shlex
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def scan(debugger,command,result,internal_dict):
 try:
  if hashlib.sha256((ROOT/'private/game/Default.xbe').read_bytes()).hexdigest()!='cd49da614d92b6ec94f3bd66d503eb4e214f8809e9c7b42f465ee25c709ad35f':raise ValueError('Unreviewed XBE')
  target=debugger.GetSelectedTarget();proc=target.GetProcess();base=target.FindFirstGlobalVariable('g_memory_offset').GetValueAsUnsigned();top=target.FindFirstGlobalVariable('g_heap_next').GetValueAsUnsigned()
  if target.GetExecutable().GetFilename()!='buffy-macos' or proc.GetState()!=lldb.eStateStopped:raise ValueError('Expected stopped Buffy process')
  alias=target.FindFirstGlobalVariable('g_xbox_mem_offset').GetValueAsUnsigned()
  if not base or base!=alias or not 0x1000000<top<0x10000000:raise ValueError('Guest heap mapping differs')
  def read(va,n):
   e=lldb.SBError();raw=proc.ReadMemory(base+va,n,e)
   return raw if e.Success() and len(raw)==n else None
  found=[];needle=struct.pack('<I',0x6634D8)
  for va in range(0x1000000,top,16384):
   data=read(va,min(16384,top-va))
   if data is None:continue
   at=data.find(needle)
   while at>=0:
    obj=va+at;raw=read(obj,44)
    if raw and not obj%4:
     words=struct.unpack('<11I',raw);first,last,count,table=words[7:11]
     if first<=last<=65535 and 1<=count==last-first+1<=512 and 0x1000000<=table<top:
      blob=read(table,count*24)
      if blob:
       entries=[]
       for i in range(count):
        entry=blob[i*24:(i+1)*24];entries.append({'code':first+i,'words':struct.unpack('<6I',entry),'floats':struct.unpack('<6f',entry)})
       extra=read(words[3],96) if words[3] else None
       found.append({'object':hex(obj),'words':words,'entries':entries,'texture_object':extra.hex() if extra else None})
    at=data.find(needle,at+4)
  args=shlex.split(command)
  if len(args)!=1:raise ValueError('Expected one output path')
  out=Path(args[0]).resolve();out.write_text(json.dumps({'heap_top':hex(top),'objects':found},indent=2));result.AppendMessage('font objects: '+str(len(found)))
 except Exception as e:result.SetError(str(e))
def __lldb_init_module(debugger,internal_dict):debugger.HandleCommand('command script add -f font_snapshot_lldb.scan font-scan')
