import os
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_game


class TestParseArgs(unittest.TestCase):
    def test_defaults(self):
        args = run_game.parse_args([])
        self.assertEqual(args.seconds, 30)
        self.assertEqual(args.backend, 'metal')
        self.assertEqual(args.debug, 'unimpl_trap,kick_event=1')
        self.assertEqual(args.label, 'boot')

    def test_backend_cpu(self):
        args = run_game.parse_args(['--backend', 'cpu'])
        self.assertEqual(args.backend, 'cpu')

    def test_debug_override(self):
        args = run_game.parse_args(['--debug', 'verbose'])
        self.assertEqual(args.debug, 'verbose')

    def test_seconds_bounds(self):
        with self.assertRaises(SystemExit):
            run_game.parse_args(['--seconds', '0'])
        with self.assertRaises(SystemExit):
            run_game.parse_args(['--seconds', '301'])
        # Valid bounds must not raise
        run_game.parse_args(['--seconds', '1'])
        run_game.parse_args(['--seconds', '300'])

    def test_label_validation(self):
        # Valid labels pass silently
        run_game.parse_args(['--label', 'valid_label-1'])
        run_game.parse_args(['--label', 'A' * 48])

        for invalid in ('A' * 49, 'boot\n'):
            with self.subTest(label=invalid), self.assertRaises(SystemExit):
                run_game.parse_args(['--label', invalid])

        # Invalid: traversal, absolute path, empty string
        with self.assertRaises(SystemExit):
            run_game.parse_args(['--label', '../etc'])
        with self.assertRaises(SystemExit):
            run_game.parse_args(['--label', '/absolute'])
        with self.assertRaises(SystemExit):
            run_game.parse_args(['--label', ''])


class TestBuildEnv(unittest.TestCase):
    @patch.object(run_game, 'ROOT', Path('/fake/root'))
    def test_env_backend_debug_injection(self):
        args = run_game.parse_args(['--backend', 'cpu', '--debug', 'verbose'])
        env = run_game._build_env(args)
        self.assertEqual(env['RECOMP_PB_BACKEND'], 'cpu')
        self.assertEqual(env['RECOMP_DEBUG'], 'verbose')

    @patch.dict(os.environ, {'RECOMP_GAME_FILES': '/wrong/game',
                             'RECOMP_TEX_DUMP': '/tmp/texture-',
                             'RECOMP_PB_BACKEND': 'metal', 'RECOMP_DEBUG': 'old'}, clear=True)
    def test_env_preserves_inherited_and_removes_game_files(self):
        args = run_game.parse_args(['--backend', 'cpu', '--debug', 'unimpl_trap,metal_trace'])
        env = run_game._build_env(args)
        self.assertNotIn('RECOMP_GAME_FILES', env)
        self.assertEqual(env['RECOMP_TEX_DUMP'], '/tmp/texture-')
        self.assertEqual(env['RECOMP_PB_BACKEND'], 'cpu')
        self.assertEqual(env['RECOMP_DEBUG'], 'unimpl_trap,metal_trace')
        self.assertEqual(os.environ['RECOMP_GAME_FILES'], '/wrong/game')
        self.assertEqual(os.environ['RECOMP_PB_BACKEND'], 'metal')

    @patch.object(run_game, 'ROOT', Path('/fake/root'))
    def test_env_watchdog_calculation(self):
        args = run_game.parse_args(['--seconds', '10'])
        env = run_game._build_env(args)
        self.assertEqual(env['RECOMP_WATCHDOG_SECS'], '5')


if __name__ == '__main__':
    unittest.main()
