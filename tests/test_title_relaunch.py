"""A quick reboot forwards the new page once and keeps the session HDD."""
from pathlib import Path
import signal
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import play

TITLE_ID = 0x45410012


def launch_page(title_id=TITLE_ID, kind=0, path=b'\\Device\\CdRom0;default.xbe', payload=b'title:0'):
    header = struct.pack('<II', kind, title_id) + path + b'\0'
    return header.ljust(1024, b'\0') + payload.ljust(3072, b'\0')


class TitleRelaunchTests(unittest.TestCase):
    def test_duration_defaults_to_unlimited_and_explicit_limits_remain_available(self):
        self.assertEqual(play.parse_args(['menu']).seconds, 0)
        self.assertEqual(play.parse_args(['--seconds', '0']).seconds, 0)
        self.assertEqual(play.parse_args(['--seconds', '3600']).seconds, 3600)
        for value in ('-1', '3601'):
            with self.assertRaises(SystemExit):
                play.parse_args(['--seconds', value])

    def test_unlimited_session_keeps_running_after_elapsed_time_and_many_restarts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'artifacts').mkdir()
            hdd = root/'hdd'
            hdd.mkdir()
            calls = []
            with patch.object(play, 'ROOT', root), patch.object(play.time, 'monotonic', return_value=0) as clock:
                def spawn(*args, **kwargs):
                    env = kwargs['env']
                    child = Mock(returncode=0)
                    child.poll.return_value = 0

                    def wait(timeout):
                        calls.append((timeout, env['RECOMP_WATCHDOG_SECS'], env['RECOMP_HDD_DIR']))
                        clock.return_value += 7200
                        marker = hdd/'checkpoint'
                        self.assertEqual(int(marker.read_text()) if marker.exists() else 0, len(calls)-1)
                        marker.write_text(str(len(calls)))
                        if len(calls) <= play.MAX_RELAUNCHES + 2:
                            Path(env['RECOMP_LAUNCH_PAGE_OUT']).write_bytes(
                                launch_page(payload=b'map:NextChapter title:0'))
                    child.wait.side_effect = wait
                    return child

                with patch.object(play.subprocess, 'Popen', side_effect=spawn):
                    result = play.run_session(root/'title', hdd, {'aspect':'16:9'}, 0,
                                              'menu', None, TITLE_ID, root/'session.log')
            self.assertEqual(result, (0, play.MAX_RELAUNCHES + 2))
            self.assertEqual(len(calls), play.MAX_RELAUNCHES + 3)
            self.assertTrue(all(timeout is None and watchdog == '0' and path == str(hdd)
                                for timeout, watchdog, path in calls))

    def test_explicit_duration_still_terminates_a_child_that_exceeds_the_deadline(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'artifacts').mkdir()
            child = Mock(pid=12345, returncode=0)
            child.poll.return_value = None
            child.wait.side_effect = [subprocess.TimeoutExpired('title', 15), 0]
            with patch.object(play, 'ROOT', root), patch.object(play.time, 'monotonic', return_value=0):
                with patch.object(play.subprocess, 'Popen', return_value=child) as spawn:
                    with patch.object(play.os, 'killpg') as kill:
                        with self.assertRaises(subprocess.TimeoutExpired):
                            play.run_session(root/'title', root/'hdd', {}, 10, 'menu',
                                             None, TITLE_ID, root/'session.log')
                        kill.assert_called_once_with(child.pid, signal.SIGTERM)
                self.assertEqual(child.wait.call_args_list[0].kwargs['timeout'], 15)
                self.assertEqual(spawn.call_args.kwargs['env']['RECOMP_WATCHDOG_SECS'], '10')

    def test_selected_hdd_requires_the_title_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            hdd = Path(folder)/'previous session'
            (hdd/'Cache').mkdir(parents=True)
            (hdd/'Partition0.img').touch()
            (hdd/'UDATA'/'12345678').mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, 'Dossier de partie Buffy'):
                play.hdd_source('menu', hdd, TITLE_ID)
            (hdd/'UDATA'/'45410012').mkdir()
            args = play.parse_args(['menu', '--hdd', str(hdd), '--check'])
            self.assertEqual(play.hdd_source(args.mode, args.hdd, TITLE_ID), hdd.resolve())

    def test_mission_rejects_a_selected_hdd(self):
        with self.assertRaises(SystemExit) as error:
            play.parse_args(['mission', '--hdd', 'previous-session'])
        self.assertEqual(error.exception.code, 2)

    def test_only_complete_same_title_pages_are_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'launch.bin'
            path.write_bytes(launch_page(payload=b'root:Z:\\ title:1'))
            self.assertEqual(play.relaunch_mode(path, TITLE_ID), 'menu')
            path.write_bytes(launch_page(payload=b'root:Z:\\ map: title:0 previousmap:Arena01'))
            self.assertEqual(play.relaunch_mode(path, TITLE_ID), 'menu')
            path.write_bytes(launch_page(payload=b'map:Arena01 title:0'))
            self.assertEqual(play.relaunch_mode(path, TITLE_ID), 'mission')
            for page in (launch_page()[:-1], launch_page() + b'\0',
                         launch_page(title_id=1), launch_page(kind=3),
                         launch_page(path=b'\\Device\\CdRom0;other.xbe')):
                path.write_bytes(page)
                with self.assertRaises(ValueError):
                    play.relaunch_mode(path, TITLE_ID)

    def test_child_receives_page_once_and_keeps_hdd_and_display_setting(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'artifacts').mkdir()
            hdd = root/'hdd'
            hdd.mkdir()
            original = root/'page.bin'
            original.write_bytes(launch_page(payload=b'map:Arena01 title:0'))
            binary = root/'fake-title'
            binary.write_text('''#!/usr/bin/python3
import os
from pathlib import Path

env = os.environ
marker = Path(env["RECOMP_HDD_DIR"]) / "session"
incoming = env.get("RECOMP_LAUNCH_PAGE_IN")
if not incoming:
    assert env["RECOMP_DISPLAY_ASPECT"] == "4:3"
    marker.write_text("kept")
    Path(env["RECOMP_LAUNCH_PAGE_OUT"]).write_bytes(Path("page.bin").read_bytes())
else:
    assert marker.read_text() == "kept"
    assert env["RECOMP_DISPLAY_ASPECT"] == "16:9"
    assert Path(incoming).read_bytes() == Path("page.bin").read_bytes()
    assert not Path(env["RECOMP_LAUNCH_PAGE_OUT"]).exists()
''')
            binary.chmod(0o700)
            with patch.object(play, 'ROOT', root):
                result = play.run_session(binary, hdd, {'aspect':'16:9'}, 15, 'menu',
                                          None, TITLE_ID, root/'session.log')
            self.assertEqual(result, (0, 1))
