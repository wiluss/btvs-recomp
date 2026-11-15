"""Real local IPC fixtures only: never connect to the user's Discord client."""
from pathlib import Path
import json
import socket
import struct
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from tools import discord_presence as rpc

ID='123456789012345678'
ROOT=Path(__file__).resolve().parents[1]


class DiscordPresenceTests(unittest.TestCase):
    def test_preferences_are_opt_in_bounded_and_have_no_account_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            self.assertFalse(rpc.load_config(root)['enabled'])
            (root/'config').mkdir();(root/'private/config').mkdir(parents=True)
            common=root/'config/discord.json';local=root/'private/config/discord.json'
            common.write_text(json.dumps({'application_id':ID,'large_image':'logo'}))
            local.write_text(json.dumps({'enabled':True,'application_id':''}))
            self.assertEqual(rpc.load_config(root),{'application_id':ID,'large_image':'logo','enabled':True})
            for data in [{'enabled':1},{'token':'not accepted'},{'application_id':'-123'},[]]:
                local.write_text(json.dumps(data))
                with self.assertRaises(ValueError):rpc.load_config(root)
            with rpc.SessionPresence(root,log=lambda _:None) as presence:
                presence.update('menu');self.assertIsNone(presence.thread)
        for value in [True,123,'','0'*18,'2'*21,'1;evil','18446744073709551616']:
            self.assertFalse(rpc.valid_application_id(value))

    def test_ipc_paths_follow_discord_order_and_fragmented_frames_are_retained(self):
        paths=rpc.socket_paths({'TMPDIR':'/one','TEMP':'/two','TMP':'/one'})
        self.assertEqual(paths[0],Path('/one/discord-ipc-0'))
        self.assertEqual(paths[10],Path('/two/discord-ipc-0'))
        self.assertEqual(len(paths),30)
        class Fragments:
            def __init__(self,chunks):self.chunks=iter(chunks)
            def recv(self,_):
                part=next(self.chunks)
                if isinstance(part,Exception):raise part
                return part
        data=rpc.frame(1,{'evt':'READY'})
        sock=Fragments([data[:3],socket.timeout(),data[3:10],socket.timeout(),data[10:]])
        reader=rpc.Reader()
        self.assertIsNone(reader.receive(sock));self.assertIsNone(reader.receive(sock))
        self.assertEqual(json.loads(reader.receive(sock)[1]),{'evt':'READY'})
        with self.assertRaises(ValueError):
            rpc.Reader().receive(Fragments([struct.pack('<II',1,rpc.MAX_FRAME+1)]))

    def test_real_ipc_handshake_ping_campaign_update_and_clear_on_exit(self):
        with tempfile.TemporaryDirectory(prefix='rpc-',dir='/tmp') as folder:
            path=Path(folder)/'discord-ipc-0'
            server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            server.bind(str(path));server.listen();server.settimeout(3)
            self.addCleanup(server.close)
            menu=threading.Event();campaign=threading.Event();cleared=threading.Event()
            messages=[];errors=[]
            def serve():
                try:
                    conn,_=server.accept()
                    with conn:
                        conn.settimeout(2);reader=rpc.Reader()
                        op,data=reader.receive(conn)
                        self.assertEqual((op,json.loads(data)),(0,{'v':1,'client_id':ID}))
                        ready=rpc.frame(1,{'cmd':'DISPATCH','evt':'READY','data':{}})
                        conn.sendall(ready[:5]);conn.sendall(ready[5:])
                        ping=b'opaque heartbeat';conn.sendall(struct.pack('<II',3,len(ping))+ping)
                        pong=False
                        while not cleared.is_set():
                            incoming=reader.receive(conn)
                            if incoming is None:continue
                            op,data=incoming
                            if op==4:self.assertEqual(data,ping);pong=True;continue
                            payload=json.loads(data);self.assertEqual(payload['cmd'],'SET_ACTIVITY')
                            messages.append(payload)
                            activity=payload['args']['activity']
                            if activity is None:cleared.set();break
                            conn.sendall(rpc.frame(1,{'cmd':'SET_ACTIVITY','nonce':payload['nonce'],'evt':None}))
                            if activity['details']=='Main menu':menu.set()
                            else:campaign.set()
                        self.assertTrue(pong)
                except BaseException as error:errors.append(error);menu.set();campaign.set()
            worker=threading.Thread(target=serve,daemon=True);worker.start()
            config={'enabled':True,'application_id':ID,'large_image':'logo'}
            with patch.object(rpc,'UPDATE_INTERVAL',.02):
                with rpc.SessionPresence(folder,config=config,paths=[path]) as presence:
                    presence.update('menu');self.assertTrue(menu.wait(3))
                    presence.update('mission');self.assertTrue(campaign.wait(3))
            worker.join(3)
            self.assertFalse(worker.is_alive());self.assertEqual(errors,[]);self.assertTrue(cleared.is_set())
            activities=[m['args']['activity'] for m in messages if m['args']['activity']]
            self.assertEqual([a['details'] for a in activities],['Main menu','In game'])
            self.assertTrue(all(a['name']=='Buffy the Vampire Slayer' for a in activities))
            self.assertTrue(all(a['assets']['large_image']=='logo' for a in activities))
            self.assertEqual(activities[0]['timestamps'],activities[1]['timestamps'])
            self.assertTrue(all(m['args']['pid']==presence.pid for m in messages))

    def test_missing_client_and_unresponsive_handshake_never_block_the_caller(self):
        with tempfile.TemporaryDirectory(prefix='rpc-',dir='/tmp') as folder:
            path=Path(folder)/'not-a-socket';path.write_text('regular file must be ignored')
            start=time.monotonic()
            with rpc.SessionPresence(folder,config={'enabled':True,'application_id':ID},paths=[path]) as presence:
                presence.update('mission')
            self.assertLess(time.monotonic()-start,1)
            path.unlink()
            server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);server.bind(str(path));server.listen();server.settimeout(3)
            self.addCleanup(server.close)
            with rpc.SessionPresence(folder,config={'enabled':True,'application_id':ID},paths=[path]) as presence:
                presence.update('menu');conn,_=server.accept()
                self.addCleanup(conn.close)
                start=time.monotonic()
            self.assertLess(time.monotonic()-start,1)

    def test_disconnect_reconnects_without_changing_session_start_time(self):
        with tempfile.TemporaryDirectory(prefix='rpc-',dir='/tmp') as folder:
            path=Path(folder)/'discord-ipc-0';server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            server.bind(str(path));server.listen();server.settimeout(3);self.addCleanup(server.close)
            stamps=[]
            with patch.object(rpc,'RETRY_INITIAL',.01):
                with rpc.SessionPresence(folder,config={'enabled':True,'application_id':ID},paths=[path]) as presence:
                    presence.update('mission')
                    for _ in range(2):
                        conn,_=server.accept()
                        with conn:
                            conn.settimeout(2);reader=rpc.Reader();reader.receive(conn)
                            conn.sendall(rpc.frame(1,{'evt':'READY'}))
                            _,payload=reader.receive(conn);stamps.append(json.loads(payload)['args']['activity']['timestamps'])
                            conn.sendall(rpc.frame(2,{'code':0}))
            self.assertEqual(stamps[0],stamps[1])

    def test_swift_preferences_agree_with_python_and_persist(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);harness=root/'main.swift';binary=root/'probe'
            harness.write_text('''import Foundation
let root=URL(fileURLWithPath:CommandLine.arguments[1])
var p=try DiscordPreferences.load(root:root)
precondition(!p.enabled && p.applicationID.isEmpty)
p.applicationID="123456789012345678";p.enabled=true;precondition(p.validID)
try p.save(root:root);precondition(try DiscordPreferences.load(root:root)==p)
p.applicationID="18446744073709551616";precondition(!p.validID)
'''.replace('precondition(try DiscordPreferences.load(root:root)==p)','let saved=try DiscordPreferences.load(root:root);precondition(saved==p)'))
            subprocess.run(['xcrun','swiftc','-module-cache-path',str(ROOT/'build/launcher-module-cache'),
                            str(ROOT/'src/launcher/DiscordPreferences.swift'),str(harness),'-o',str(binary)],check=True,capture_output=True)
            subprocess.run([str(binary),str(root)],check=True)
            self.assertTrue(rpc.load_config(root)['enabled'])
            self.assertEqual(rpc.load_config(root)['application_id'],ID)


if __name__=='__main__':unittest.main()
