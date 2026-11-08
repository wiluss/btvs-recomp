"""Supervise a game detached by its bootstrap debugger, without claiming its exit code.

The caller writes a unique PID file from LLDB at its first stop, before detach.
Only that PID, with matching UID/start time/executable, may be terminated.
The game's native watchdog remains a second bound on its lifetime.
"""
import os
from pathlib import Path
import signal
import subprocess
import time


def process_identity(pid, executable):
    """Stable ps identity, or None for an exited/zombie/unexpected process."""
    if pid <= 1 or pid == os.getpid():
        return None
    result = subprocess.run(['ps', '-p', str(pid), '-o', 'stat=,uid=,lstart=,comm='],
                            capture_output=True, text=True, check=False)
    if result.returncode == 1:
        return None  # ps: no matching process
    if result.returncode:
        raise RuntimeError('Cannot inspect detached process: ' + result.stderr.strip())
    fields = result.stdout.strip().split(None, 1)
    if len(fields) != 2 or fields[0].startswith('Z'):
        return None
    identity = fields[1]
    if (identity.split(None, 1)[0] != str(os.getuid())
            or not identity.endswith(' ' + str(executable))):
        return None
    return identity


def terminate_owned(pid, identity, executable):
    """Recheck identity before TERM/KILL; never signal an unrelated process."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        if not identity or process_identity(pid, executable) != identity:
            return
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + 3
        while process_identity(pid, executable) == identity and time.monotonic() < deadline:
            time.sleep(0.05)
    if process_identity(pid, executable) == identity:
        raise RuntimeError('Detached game did not exit after SIGKILL')


def run_detached(command, *, cwd, env, log_path, pid_path, executable,
                 timeout=335, launch_timeout=30):
    """Wait for the debugger's handoff, then supervise the game itself.

    Timeout bounds bootstrap plus gameplay; cleanup has its own short bound.
    Returns debugger status and an observed stop reason. The detached process
    is not our child, so its exit code is deliberately unavailable. Ctrl+C and
    exceptions clean up the launched process before propagating to the caller.
    """
    pid_path = Path(pid_path)
    if pid_path.exists():
        raise ValueError('Use a fresh PID output path')
    start = time.monotonic()
    debugger = None
    pid = identity = None
    try:
        with Path(log_path).open('w') as log:
            debugger = subprocess.Popen(command, cwd=cwd, env=env, stdout=log,
                                        stderr=subprocess.STDOUT, start_new_session=True)
            debugger.wait(timeout=min(timeout, launch_timeout))
        if debugger.returncode:
            raise RuntimeError('Bootstrap debugger failed; inspect ' + str(log_path))
        pid = int(pid_path.read_text().strip())
        identity = process_identity(pid, executable)
        if identity is None:
            raise RuntimeError('Game exited before handoff, or PID identity mismatch')
        while process_identity(pid, executable) == identity:
            if time.monotonic() - start >= timeout:
                reason = 'timeout'
                break
            time.sleep(0.25)
        else:
            reason = 'exited'
        return {'game_pid': pid, 'reason': reason, 'game_exit_code': None,
                'debugger_exit_code': debugger.returncode,
                'seconds': round(time.monotonic() - start, 3)}
    finally:
        try:
            # Recover a PID written at the first stop, even if Ctrl+C interrupted
            # the debugger wait. Its executable/UID must still match before cleanup.
            if pid is None and pid_path.exists():
                try:
                    pid = int(pid_path.read_text().strip())
                except ValueError:
                    pass
            if pid is not None:
                if identity is None:
                    identity = process_identity(pid, executable)
                terminate_owned(pid, identity, executable)
        finally:
            if debugger is not None and debugger.poll() is None:
                try:
                    os.killpg(debugger.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    debugger.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(debugger.pid, signal.SIGKILL)
                    debugger.wait()
