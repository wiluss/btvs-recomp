"""Optional local Discord RPC. No SDK, account token, HTTP or guest hooks.

Protocol: https://docs.discord.com/developers/topics/rpc
All socket work runs on a bounded background worker, never on the game thread.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import socket
import stat
import struct
import threading
import time
import uuid

MAX_FRAME = 64 * 1024
UPDATE_INTERVAL = 15.0
RETRY_INITIAL = 5.0


def valid_application_id(value):
    return (isinstance(value, str) and re.fullmatch(r'[1-9][0-9]{16,19}', value) is not None
            and int(value) < 2**64)


def load_config(root):
    root=Path(root)
    settings={'application_id':'', 'large_image':'', 'enabled':False}
    for path,keys in [(root/'config/discord.json',{'application_id','large_image'}),
                      (root/'private/config/discord.json',{'application_id','enabled'})]:
        if not path.exists():continue
        if path.is_symlink() or not path.is_file() or path.stat().st_size>4096:
            raise ValueError('Invalid Discord preferences')
        data=json.loads(path.read_text())
        if not isinstance(data,dict) or set(data)-keys:raise ValueError('Invalid Discord preferences')
        # An empty local override keeps the project's public application ID.
        if data.get('application_id')=='':data.pop('application_id')
        settings.update(data)
    if (type(settings['enabled']) is not bool or
        (settings['application_id']!='' and not valid_application_id(settings['application_id'])) or
        not isinstance(settings['large_image'],str) or
        (settings['large_image'] and not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',settings['large_image']))):
        raise ValueError('Invalid Discord preferences')
    return settings


def socket_paths(environ=None):
    env=os.environ if environ is None else environ
    roots=list(dict.fromkeys([env.get(key) for key in ('XDG_RUNTIME_DIR','TMPDIR','TMP','TEMP')
                             if env.get(key)]+['/tmp']))
    return [Path(root)/f'discord-ipc-{n}' for root in roots for n in range(10)]


def frame(opcode,payload):
    data=json.dumps(payload,separators=(',',':')).encode()
    if len(data)>MAX_FRAME:raise ValueError('Discord frame too large')
    return struct.pack('<II',opcode,len(data))+data


class Reader:
    def __init__(self):self.buffer=bytearray()

    def receive(self,sock):
        """Retain fragmented headers/bodies across socket timeouts."""
        while True:
            if len(self.buffer)>=8:
                opcode,size=struct.unpack_from('<II',self.buffer)
                if size>MAX_FRAME:raise ValueError('Discord frame too large')
                if len(self.buffer)>=8+size:
                    payload=bytes(self.buffer[8:8+size]);del self.buffer[:8+size]
                    return opcode,payload
            try:data=sock.recv(4096)
            except socket.timeout:return None
            if not data:raise ConnectionError('Discord closed IPC')
            self.buffer.extend(data)


class SessionPresence:
    def __init__(self,root,*,config=None,paths=None,log=print):
        self.log=log;self.root=Path(root)
        try:self.config=load_config(root) if config is None else config
        except (OSError,ValueError,TypeError):
            self.config={'enabled':False}
            self.log('[DISCORD] Invalid configuration; continuing without presence.')
        self.paths=socket_paths() if paths is None else paths
        self.stop=threading.Event();self.lock=threading.Lock()
        self.activity=None;self.revision=0;self.thread=None
        self.start_time=int(time.time());self.pid=os.getpid()
        self.level_names=None;self.tracker=None

    def __enter__(self):
        if self.config.get('enabled') and valid_application_id(self.config.get('application_id')):
            self.thread=threading.Thread(target=self._run,name='DiscordPresence',daemon=True)
            try:self.thread.start()
            except RuntimeError:
                self.thread=None;self.log('[DISCORD] Worker unavailable; gameplay continues.')
        return self

    def update(self,mode,*,log_path=None):
        with self.lock:
            self.tracker=None
            if log_path is not None and self.thread is not None:
                if self.level_names is None:
                    if __package__:
                        from .discord_levels import load_names
                    else:from discord_levels import load_names
                    try:self.level_names=load_names(self.root)
                    except (OSError,ValueError):self.level_names={}
                if __package__:
                    from .discord_levels import LogLevelTracker
                else:from discord_levels import LogLevelTracker
                try:offset=Path(log_path).stat().st_size
                except OSError:offset=0
                self.tracker=LogLevelTracker(log_path,self.level_names,offset)
            self._set_label('Main menu' if mode=='menu' else 'In game')

    def _set_label(self,label):
        activity={'type':0,'name':'Buffy the Vampire Slayer','details':label,
                  'timestamps':{'start':self.start_time}}
        if self.config.get('large_image'):
            activity['assets']={'large_image':self.config['large_image'],'large_text':'Buffy the Vampire Slayer'}
        if activity!=self.activity:self.activity=activity;self.revision+=1

    def _refresh_level(self):
        with self.lock:
            if self.tracker:
                labels=self.tracker.poll()
                if labels:self._set_label(labels[-1])

    def __exit__(self,*_):
        self.stop.set()
        if self.thread:self.thread.join(timeout=1.5)

    def _connect(self):
        for path in self.paths:
            if self.stop.is_set():return None
            sock=None
            try:
                info=path.lstat()
                if not stat.S_ISSOCK(info.st_mode) or info.st_uid!=os.getuid():continue
                sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);sock.settimeout(.25)
                sock.connect(str(path));return sock
            except (OSError,ValueError):
                if sock:sock.close()
        return None

    def _command(self,sock,activity):
        nonce=str(uuid.uuid4())
        sock.sendall(frame(1,{'cmd':'SET_ACTIVITY','args':{'pid':self.pid,'activity':activity},
                              'nonce':nonce}))
        return nonce

    def _serve(self,sock):
        reader=Reader();ready=False;sent=0;last=None;pending_nonce=None;pending_label=None
        handshake_deadline=time.monotonic()+3
        sock.sendall(frame(0,{'v':1,'client_id':self.config['application_id']}))
        try:
            while not self.stop.is_set():
                self._refresh_level()
                if not ready and time.monotonic()>handshake_deadline:raise TimeoutError('Discord handshake timeout')
                with self.lock:activity,revision=self.activity,self.revision
                if (ready and activity is not None and revision!=sent
                        and (last is None or time.monotonic()-last>=UPDATE_INTERVAL)):
                    pending_nonce=self._command(sock,activity)
                    pending_label=activity['details'];sent=revision;last=time.monotonic()
                incoming=reader.receive(sock)
                if incoming is None:continue
                opcode,payload=incoming
                if opcode==2:raise ConnectionError('Discord requested reconnect')
                if opcode==3:sock.sendall(struct.pack('<II',4,len(payload))+payload);continue
                if opcode==4:continue
                if opcode!=1:raise ValueError('Unsupported Discord opcode')
                message=json.loads(payload)
                if not isinstance(message,dict):raise ValueError('Invalid Discord response')
                if message.get('evt')=='ERROR':raise ConnectionError('Discord rejected presence')
                if message.get('evt')=='READY':
                    ready=True;self.log('[DISCORD] Connected to desktop client.')
                elif (pending_nonce is not None and message.get('cmd')=='SET_ACTIVITY'
                      and message.get('nonce')==pending_nonce):
                    self.log('[DISCORD] Activity confirmed: '+pending_label)
                    pending_nonce=None
        finally:
            if ready and self.stop.is_set():
                try:self._command(sock,None)
                except OSError:pass

    def _run(self):
        delay=RETRY_INITIAL
        while not self.stop.is_set():
            self._refresh_level()
            with self.lock:active=self.activity is not None
            if not active:self.stop.wait(.25);continue
            sock=self._connect()
            if sock is not None:
                try:self._serve(sock)
                except (OSError,ValueError,UnicodeError):pass
                finally:sock.close()
            self.stop.wait(delay);delay=min(30,delay*2)
