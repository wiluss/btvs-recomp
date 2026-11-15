"""Synthetic mission labels/logs only; no game text or personal saves."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools import discord_levels as levels
from tools import discord_presence as rpc


def opened(key,status='00000000'):
    return f'  [FILE] d:\\pak\\res_{key}.pak (disp 1 opts 0x60 from 0x0057807F) -> 0x{status}\n'.encode()


class DiscordLevelTests(unittest.TestCase):
    def test_mission_names_preserve_original_labels_and_reject_untrusted_entries(self):
        data=b'# comment\nEXEC 0 3 "Training, Test Area" "Objective text" M00_Test_1 "params:1"\n'
        self.assertEqual(levels.mission_names(data),{'m00_test_1':'Training, Test Area'})
        special=b'SPECIAL 0 4 "Test arena" "Objective" Arena01d "params"\n'
        self.assertEqual(levels.mission_names(special),{'arena01d':'Test arena'})
        for bad in [b'',b'x'*(65536+1),b'not an entry',b'EXEC 0 3 "Bad" "obj" ../escape',
                    data+b'EXEC 0 3 "Conflicting label" "obj" M00_Test_1',
                    b'EXEC 0 3 "Bad\tlabel" "obj" M00_Test_1']:
            with self.subTest(bad=bad[:40]),self.assertRaises(ValueError):levels.mission_names(bad)

    def test_incremental_success_only_tracking_handles_splits_menus_and_unknown_levels(self):
        with tempfile.TemporaryDirectory() as folder:
            log=Path(folder)/'game.log';log.write_bytes(b'')
            tracker=levels.LogLevelTracker(log,{'m00_test_1':'Training, Test Area'})
            line=opened('M00_Test_1')
            log.write_bytes(line[:23]);self.assertEqual(tracker.poll(),[])
            with log.open('ab') as stream:stream.write(line[23:])
            self.assertEqual(tracker.poll(),['Training, Test Area'])
            with log.open('ab') as stream:
                stream.write(opened('m00_test_1','C0000034'))
                stream.write(b'[FILE] d:\\pak\\res_m00_test_1.pak -> 0x00000000\n')
                stream.write(opened('textures'));stream.write(opened('null'))
                stream.write(opened('arena02d'));stream.write(opened('m99_unknown'))
            self.assertEqual(tracker.poll(),['Main menu','Arena 2','In game'])
            self.assertEqual(tracker.poll(),[])

    def test_log_reset_truncation_rotation_and_overlong_lines_do_not_reuse_stale_data(self):
        with tempfile.TemporaryDirectory() as folder:
            log=Path(folder)/'game.log';old=opened('null');log.write_bytes(old)
            tracker=levels.LogLevelTracker(log,{},offset=len(old))
            self.assertEqual(tracker.poll(),[])
            with log.open('ab') as stream:stream.write(b'x'*700)
            self.assertEqual(tracker.poll(),[])
            with log.open('ab') as stream:stream.write(opened('arena01')+opened('arena02'))
            self.assertEqual(tracker.poll(),['Arena 2'])
            log.write_bytes(opened('null'));self.assertEqual(tracker.poll(),['Main menu'])
            replacement=Path(folder)/'new.log';replacement.write_bytes(opened('arena03'));replacement.replace(log)
            self.assertEqual(tracker.poll(),['Arena 3'])

    def test_live_level_changes_update_activity_without_resetting_elapsed_time(self):
        with tempfile.TemporaryDirectory() as folder:
            log=Path(folder)/'game.log';log.write_bytes(opened('arena01'))
            config={'enabled':False,'application_id':'123456789012345678','large_image':'btvs_logo'}
            presence=rpc.SessionPresence(folder,config=config,paths=[])
            # A sentinel lets the synchronous fixture exercise the active tracker
            # without creating any Discord connection or background thread.
            presence.thread=object();presence.level_names={'m00_test_1':'Training, Test Area'}
            presence.update('mission',log_path=log)
            self.assertEqual(presence.activity['details'],'In game')
            start=presence.activity['timestamps']
            with log.open('ab') as stream:stream.write(opened('m00_test_1'))
            presence._refresh_level()
            self.assertEqual(presence.activity['details'],'Training, Test Area')
            self.assertEqual(presence.activity['name'],'Buffy the Vampire Slayer')
            self.assertEqual(presence.activity['assets']['large_image'],'btvs_logo')
            presence.update('menu',log_path=log)
            presence._refresh_level()
            self.assertEqual(presence.activity['details'],'Main menu')
            self.assertEqual(presence.activity['timestamps'],start)


if __name__=='__main__':unittest.main()
