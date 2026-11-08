#!/usr/bin/env python3
"""Capture current DXT textures after the first mission HUD, on a cloned HDD.

Diagnostic only: attaching LLDB interrupts audio and invalidates FPS measures.
Uses the existing verified launch page; never edits assets or preferences.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import threading
import time

from debugger_handoff import run_detached, process_identity, terminate_owned
from play import ROOT, PAGE_SHA256, mission_script, build_environment, verify_xbe


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path,help='fresh diagnostic directory')
    parser.add_argument('--font-metrics',action='store_true',help='also read the reviewed font objects')
    parser.add_argument('--seconds',type=int,default=150)
    args=parser.parse_args()
    if not 30<=args.seconds<=300:parser.error('--seconds: 30..300')
    out=args.output.resolve()
    if out.exists():parser.error('Output directory already exists')
    verify_xbe(ROOT/'private/game/Default.xbe',json.loads((ROOT/'config/title.json').read_text()))
    page=ROOT/'artifacts/relaunch/launch-page.bin'
    if hashlib.sha256(page.read_bytes()).hexdigest()!=PAGE_SHA256:raise ValueError('Launch page differs')
    out.mkdir(parents=True)
    binary=ROOT/'build/game/buffy-macos';pid_path=out/'game.pid';stderr=out/'game.stderr.log'
    hdd=ROOT/'build'/('texture-capture-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(out.stat().st_ino))
    subprocess.run(['cp','-cR',str(ROOT/'build/relaunch-capture-hdd'),str(hdd)],check=True)
    script=out/'launch.lldb';script.write_text(mission_script(page,pid_path,out/'game.stdout.log',stderr))
    env=build_environment({'scale':1,'aspect':'16:9','hud':'safe','textures':'original'},hdd,args.seconds)
    env.update(RECOMP_KEYBOARD='0',RECOMP_TRACE='aspect,flip')
    stop=threading.Event();state={}
    def monitor():
        try:
            first=None
            while not stop.wait(.3):
                if not stderr.exists():continue
                log=stderr.read_text(errors='replace')
                if first is None:
                    found=re.search(r'\[aspect.program\] 969115CF flip (\d+):.*hash 1D03BB8D6EC30520',log)
                    if found:first=int(found[1]);state['hud_first_flip']=first
                flips=re.findall(r'\[PB-PERF\] flip (\d+)',log[-20000:])
                if first is None or not flips or int(flips[-1])<first+120:continue
                pid=int(pid_path.read_text());identity=process_identity(pid,binary)
                if identity is None:raise ValueError('Capture target exited')
                commands=['lldb','--batch','-p',str(pid),'-o','command script import '+shlex.quote(str(ROOT/'tools/texture_snapshot_lldb.py')),
                    '-o','texture-snapshot '+shlex.quote(str(out/'snapshot'))]
                if args.font_metrics:
                    commands += ['-o','command script import '+shlex.quote(str(ROOT/'tools/font_snapshot_lldb.py')),'-o','font-scan '+shlex.quote(str(out/'font-objects.json'))]
                commands += ['-o','process detach --keep-stopped false']
                try:
                    with (out/'snapshot.lldb.log').open('w') as log:
                        state['snapshot_returncode']=subprocess.run(commands,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=30).returncode
                finally:terminate_owned(pid,identity,binary)
                return
        except Exception as exc:state['error']=str(exc)
    worker=threading.Thread(target=monitor,daemon=True);worker.start()
    try:
        state.update(run_detached(['lldb','--batch','--source',str(script),str(binary)],cwd=ROOT,env=env,
            log_path=out/'launch.log',pid_path=pid_path,executable=binary,timeout=args.seconds+5))
    finally:stop.set();worker.join(timeout=35)
    state.update(binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),hdd=str(hdd),performance_measurement=False)
    (out/'capture.json').write_text(json.dumps(state,indent=2)+'\n')
    if state.get('error') or state.get('snapshot_returncode')!=0 or not (out/'snapshot/manifest.json').exists():
        raise SystemExit('Capture incomplete; inspect '+str(out))
    print(json.dumps({'captured':len(json.loads((out/'snapshot/manifest.json').read_text())['entries']),'output':str(out)}))


if __name__=='__main__':main()
