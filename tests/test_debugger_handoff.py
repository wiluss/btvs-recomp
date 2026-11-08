"""Real detached child lifecycle, bounded cleanup and PID identity guards."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import debugger_handoff as handoff


class DebuggerHandoffTests(unittest.TestCase):
    def launch(self, folder, duration, timeout=3, bootstrap_delay=0):
        folder = Path(folder)
        pid_path = folder / 'pid'
        # This fake bootstrap exits while its independently running child stays.
        # No game, debugger, model or assets required.
        code = ('import subprocess,sys,pathlib,time; '
                'p=subprocess.Popen(["/bin/sleep",sys.argv[2]],'
                'stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True); '
                'pathlib.Path(sys.argv[1]).write_text(str(p.pid)); '
                'time.sleep(float(sys.argv[3]))')
        return handoff.run_detached(
            [sys.executable, '-c', code, str(pid_path), str(duration), str(bootstrap_delay)], cwd=ROOT,
            env=os.environ.copy(), log_path=folder/'log', pid_path=pid_path,
            executable='/bin/sleep', timeout=timeout)

    def test_waits_for_game_after_bootstrap_exits(self):
        with tempfile.TemporaryDirectory() as folder:
            start = time.monotonic()
            result = self.launch(folder, 0.6)
            self.assertGreaterEqual(time.monotonic() - start, 0.5)
            self.assertEqual(result['reason'], 'exited')
            self.assertEqual(result['debugger_exit_code'], 0)
            self.assertIsNone(result['game_exit_code'])
            self.assertIsNone(handoff.process_identity(result['game_pid'], '/bin/sleep'))

    def test_timeout_terminates_detached_game(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.launch(folder, 30, timeout=0.4)
            self.assertEqual(result['reason'], 'timeout')
            self.assertIsNone(handoff.process_identity(result['game_pid'], '/bin/sleep'))

    def test_keyboard_interrupt_cleans_up_game(self):
        actual_identity = handoff.process_identity
        calls = 0

        def interrupt_after_handoff(pid, executable):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise KeyboardInterrupt
            return actual_identity(pid, executable)

        with tempfile.TemporaryDirectory() as folder:
            with patch.object(handoff, 'process_identity', side_effect=interrupt_after_handoff):
                with self.assertRaises(KeyboardInterrupt):
                    self.launch(folder, 30)
            pid = int((Path(folder)/'pid').read_text())
            self.assertIsNone(handoff.process_identity(pid, '/bin/sleep'))

    def test_interrupt_during_bootstrap_recovers_recorded_pid(self):
        actual_wait = subprocess.Popen.wait
        interrupted = False
        with tempfile.TemporaryDirectory() as folder:
            pid_path = Path(folder)/'pid'

            def interrupt_when_recorded(process, *args, **kwargs):
                nonlocal interrupted
                if not interrupted and process.args[0] == sys.executable:
                    deadline = time.monotonic() + 2
                    while time.monotonic() < deadline:
                        if pid_path.exists() and pid_path.read_text().strip().isdigit():
                            break
                        time.sleep(0.01)
                    self.assertTrue(pid_path.exists() and pid_path.read_text().strip().isdigit())
                    interrupted = True
                    raise KeyboardInterrupt
                return actual_wait(process, *args, **kwargs)

            with patch.object(subprocess.Popen, 'wait', new=interrupt_when_recorded):
                with self.assertRaises(KeyboardInterrupt):
                    self.launch(folder, 30, bootstrap_delay=5)
            self.assertIsNone(handoff.process_identity(int(pid_path.read_text()), '/bin/sleep'))

    def test_identity_guards_and_changed_pid_never_signalled(self):
        self.assertIsNone(handoff.process_identity(1, '/bin/sleep'))
        self.assertIsNone(handoff.process_identity(os.getpid(), sys.executable))
        for state, uid, exe in [('Z', os.getuid(), '/bin/sleep'),
                                ('S', os.getuid()+1, '/bin/sleep'),
                                ('S', os.getuid(), '/bin/other')]:
            response = subprocess.CompletedProcess([], 0, f'{state} {uid} Sun Nov 1 12:00:00 2026 {exe}\n', '')
            with patch.object(handoff.subprocess, 'run', return_value=response):
                self.assertIsNone(handoff.process_identity(123456, '/bin/sleep'))
        with patch.object(handoff, 'process_identity', return_value='new identity'):
            with patch.object(handoff.os, 'kill') as kill:
                handoff.terminate_owned(123456, 'original identity', '/bin/sleep')
                kill.assert_not_called()


if __name__ == '__main__':
    unittest.main()
