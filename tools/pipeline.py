#!/usr/bin/env python3
"""Reproducible local pipeline, pinned toolkit and user XBE/MAP only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from map_symbols import index_map
from xbe_inspect import inspect

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['inspect', 'disasm', 'identify', 'abi', 'recomp', 'all'], default='all')
    args = parser.parse_args()
    lock = json.loads((ROOT / 'dependencies.lock.json').read_text())['xboxrecomp']
    vendor = ROOT / lock['path']
    head = subprocess.check_output(['git', '-C', str(vendor), 'rev-parse', 'HEAD'], text=True).strip()
    if head != lock['revision']:
        raise SystemExit('Toolkit does not match dependencies.lock.json')
    title = json.loads((ROOT / 'config/title.json').read_text())
    xbe_path = ROOT / 'private/game/Default.xbe'
    xbe = inspect(xbe_path.read_bytes())
    if xbe['sha256'] != title['xbe_sha256']:
        raise SystemExit('XBE differs from identified manifest; inspect before generating')
    report, symbols, seeds = index_map((ROOT / 'private/game/final.map').read_bytes(), xbe)
    if report['map_sha256'] != title['symbols']['map_sha256']:
        raise SystemExit('MAP differs from identified manifest')
    output = ROOT / 'generated'
    logs = ROOT / 'logs'
    logs.mkdir(exist_ok=True)
    for folder in ['symbols', 'disasm', 'func_id', 'abi', 'recomp', 'recomp/gen']:
        (output / folder).mkdir(parents=True, exist_ok=True)
    for name, data in [('report', report), ('index', symbols), ('seeds', seeds)]:
        (output / 'symbols' / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')
    (ROOT / 'artifacts/xbe-report.json').write_text(json.dumps(xbe, indent=2) + '\n')
    # No feedback from another title or a previous toolkit checkout is read.
    (output / 'recomp/no-icall-feedback.json').write_text('{}\n')
    commands = {
        'inspect':['tools.xbe_parser', str(xbe_path), '--json', str(output / 'xbe-analysis.json')],
        'disasm':['tools.disasm', str(xbe_path), '--analysis-json', str(output / 'xbe-analysis.json'),
                  '--output', str(output / 'disasm'),
                  '--seed-functions', str(output / 'symbols/seeds.json'), '--force'],
        'identify':['tools.func_id', str(xbe_path), '--functions', str(output / 'disasm/functions.json'),
                    '--strings', str(output / 'disasm/strings.json'), '--xrefs', str(output / 'disasm/xrefs.json'),
                    '--output', str(output / 'func_id')],
        'abi':['tools.abi_analysis', str(xbe_path), '--disasm-dir', str(output / 'disasm'),
               '--func-id-dir', str(output / 'func_id'), '--output-dir', str(output / 'abi')],
        'recomp':['tools.recomp', str(xbe_path), '--all', '--split', '250',
                  '--spin-waits', str(ROOT / 'config/spin-waits.json'),
                  '--game-name', 'Buffy the Vampire Slayer (2002)', '--disasm-dir', str(output / 'disasm'),
                  '--func-id-dir', str(output / 'func_id'), '--abi-dir', str(output / 'abi'),
                  '--icall-sites', str(output / 'recomp/no-icall-feedback.json'),
                  '--output-dir', str(output / 'recomp'), '--gen-dir', str(output / 'recomp/gen')]
    }
    stages = commands if args.stage == 'all' else [args.stage]
    for stage in stages:
        command = ([sys.executable, str(ROOT / 'tools/recomp_driver.py')] + commands[stage][1:]
                   if stage == 'recomp' else [sys.executable, '-u', '-m'] + commands[stage])
        print('Running %s; log: logs/pipeline-%s.log' % (stage, stage), flush=True)
        start = time.monotonic()
        with (logs / ('pipeline-' + stage + '.log')).open('w') as log:
            result = subprocess.run(command, cwd=vendor, stdout=log, stderr=subprocess.STDOUT)
        record = {'stage':stage, 'argv':command, 'returncode':result.returncode,
                  'seconds':round(time.monotonic() - start, 3), 'toolkit':head,
                  'xbe_sha256':xbe['sha256'], 'map_sha256':report['map_sha256']}
        if stage == 'recomp':
            record['generator_driver_sha256'] = hashlib.sha256((ROOT/'tools/recomp_driver.py').read_bytes()).hexdigest()
            record['loadvars_fix_sha256'] = hashlib.sha256((ROOT/'tools/loadvars_fix.py').read_bytes()).hexdigest()
            record['arenas_fix_sha256'] = hashlib.sha256((ROOT/'tools/arenas_fix.py').read_bytes()).hexdigest()
            record['widescreen_fix_sha256'] = hashlib.sha256((ROOT/'tools/widescreen_fix.py').read_bytes()).hexdigest()
            record['letterbox_fix_sha256'] = hashlib.sha256((ROOT/'tools/letterbox_fix.py').read_bytes()).hexdigest()
            record['factory_switch_fix_sha256'] = hashlib.sha256((ROOT/'tools/factory_switch_fix.py').read_bytes()).hexdigest()
            record['spin_waits_sha256'] = hashlib.sha256((ROOT/'config/spin-waits.json').read_bytes()).hexdigest()
        (ROOT / 'artifacts' / ('pipeline-' + stage + '.json')).write_text(json.dumps(record, indent=2) + '\n')
        if result.returncode:
            raise SystemExit('Stage %s failed; inspect its log' % stage)


if __name__ == '__main__':
    main()
