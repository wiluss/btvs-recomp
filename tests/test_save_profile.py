from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from save_profile import persistent_hdd
from fresh_hdd import partition_table
import play

TITLE = {'title_id': '45410012', 'xbe_sha256': 'identified-edition'}


class SaveProfileTests(unittest.TestCase):
    def test_fresh_profile_needs_no_private_seed_and_preserves_new_saves(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            self.assertIsNone(play.hdd_source('menu',None,0x45410012))
            with persistent_hdd(root/'profile',None,TITLE) as hdd:
                self.assertEqual((hdd/'Partition0.img').read_bytes(),bytes(0x800)+partition_table())
                self.assertEqual(partition_table()[:16],b'****PARTINFO****')
                save=hdd/'UDATA/45410012/first.ses';self.assertTrue(save.parent.is_dir())
                self.assertEqual(list(save.parent.iterdir()),[])
                save.write_bytes(b'new player progress')
            with persistent_hdd(root/'profile',None,TITLE) as hdd:
                self.assertEqual(save.read_bytes(),b'new player progress')
                self.assertEqual(play.hdd_source('menu',hdd,0x45410012),hdd)

    def test_menu_uses_the_profile_and_diagnostics_can_request_a_copy(self):
        self.assertEqual(play.parse_args(['menu']).profile, play.ROOT/'private/profile')
        self.assertIsNone(play.parse_args(['menu', '--temporary-hdd']).profile)
        self.assertIsNone(play.parse_args(['menu', '--hdd', 'previous-session']).profile)
        self.assertIsNone(play.parse_args(['mission']).profile)

    def test_saved_progress_survives_two_launches_without_changing_seed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            seed = root/'seed'
            seed.mkdir()
            (seed/'checkpoint').write_text('canyon')
            profile = root/'private/profile'
            with persistent_hdd(profile, seed, TITLE) as hdd:
                self.assertEqual((hdd/'checkpoint').read_text(), 'canyon')
                (hdd/'checkpoint').write_text('courtyard')
            with persistent_hdd(profile, seed, TITLE) as hdd:
                self.assertEqual((hdd/'checkpoint').read_text(), 'courtyard')
            self.assertEqual((seed/'checkpoint').read_text(), 'canyon')

    def test_check_does_not_create_a_lock_or_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with persistent_hdd(root/'private/profile', root/'seed', TITLE, check=True) as hdd:
                self.assertEqual(hdd, root.resolve()/'private/profile/hdd')
            self.assertEqual(list(root.iterdir()), [])

    def test_another_session_is_refused_until_the_first_releases_the_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            seed = root/'seed'
            seed.mkdir()
            with persistent_hdd(root/'profile', seed, TITLE):
                with self.assertRaisesRegex(ValueError, 'déjà ouverte'):
                    with persistent_hdd(root/'profile', seed, TITLE):
                        self.fail('Concurrent writer accepted')
            with persistent_hdd(root/'profile', seed, TITLE):
                pass

    def test_copy_failure_can_be_retried_without_publishing_a_partial_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            seed = root/'seed'
            seed.mkdir()
            with patch('save_profile.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'cp')):
                with self.assertRaises(subprocess.CalledProcessError):
                    with persistent_hdd(root/'profile', seed, TITLE):
                        pass
            self.assertFalse((root/'profile').exists())
            self.assertEqual(sorted(p.name for p in root.iterdir()), ['profile.lock', 'seed'])
            with persistent_hdd(root/'profile', seed, TITLE) as hdd:
                self.assertTrue(hdd.is_dir())

    def test_another_edition_cannot_open_an_existing_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            seed = root/'seed'
            seed.mkdir()
            with persistent_hdd(root/'profile', seed, TITLE):
                pass
            other = dict(TITLE, xbe_sha256='another-edition')
            for check in (False, True):
                with self.assertRaisesRegex(ValueError, 'incompatible'):
                    with persistent_hdd(root/'profile', seed, other, check=check):
                        pass
