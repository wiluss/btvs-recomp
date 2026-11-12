"""Translation parity and executable Swift profile/resource checks, no game assets."""
from pathlib import Path
import json
import plistlib
import re
import shutil
import subprocess
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]


class LauncherLocalizationTests(unittest.TestCase):
    def test_complete_catalog_and_localized_call_sites(self):
        catalog=json.loads((ROOT/'src/launcher/Localizations.json').read_text())
        self.assertEqual(set(catalog),{'fr','en','es','de','it'})
        keys=set(catalog['fr'])
        for language,values in catalog.items():
            self.assertEqual(set(values),keys,language)
            self.assertTrue(all(isinstance(v,str) and v and '<think>' not in v and '```' not in v for v in values.values()))
            for name in ['Start','Back','AZERTY','QWERTY']:
                self.assertEqual(values[name],name)
        for source in ['LauncherView.swift','ControlsView.swift','SetupView.swift','UpdatesView.swift','BuffyLauncher.swift']:
            calls=set(re.findall(r'tr\("([^"\\]+)"\)',(ROOT/'src/launcher'/source).read_text()))
            self.assertFalse(calls-keys,(source,calls-keys))

    def test_compiled_swift_profiles_and_bundled_catalog(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);app=root/'Probe.app/Contents';(app/'MacOS').mkdir(parents=True);(app/'Resources').mkdir()
            (app/'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'local.buffy.test.catalog','CFBundleExecutable':'Probe','CFBundlePackageType':'APPL'}))
            shutil.copy(ROOT/'src/launcher/Localizations.json',app/'Resources/Localizations.json')
            harness=root/'Probe.swift'
            harness.write_text('''import Foundation
@main struct Probe {
 static func main() throws {
  for (language,expected) in [(LauncherLanguage.fr,"Jouer"),(.en,"Play"),(.es,"Jugar"),(.de,"Spielen"),(.it,"Gioca")] {
   precondition(LauncherText.text("Jouer",language:language)==expected)
  }
  var profile=ControlProfile();precondition(profile.valid)
  profile.assignKey(88,to:0);precondition(profile.keyboard[0]==88 && profile.keyboard[1]==87)
  profile.assignPad(1,to:0);precondition(profile.pad[0]==1 && profile.pad[1]==0)
  profile.assignStick(1,to:0);precondition(profile.sticks==[1,0])
  profile.useQwerty();precondition(profile.valid && profile.keyboard[16]==87 && profile.keyboard[18]==65)
  profile.assignKey(0,to:0);profile.assignPad(-1,to:0);precondition(!profile.valid)
  profile=ControlProfile()
  let file=URL(fileURLWithPath:CommandLine.arguments[1]);try JSONEncoder().encode(profile).write(to:file)
  let loaded = try ControlProfile.load(file);precondition(loaded==profile)
  try Data("{\\"version\\":1,\\"version\\":1}".utf8).write(to:file)
  do {_ = try ControlProfile.load(file);preconditionFailure("duplicate fields accepted")} catch {}
  print("Five bundled languages; key/button conflict swaps; QWERTY; stick swap; menu recovery; profile round-trip and duplicate rejection passed.")
 }
}
''')
            exe=app/'MacOS/Probe'
            command=['xcrun','swiftc','-module-cache-path',str(root/'cache'),'-parse-as-library',str(ROOT/'src/launcher/Localization.swift'),str(ROOT/'src/launcher/ControlProfile.swift'),str(harness),'-o',str(exe)]
            result=subprocess.run(command,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run([str(exe),str(root/'profile.json')],capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_uhd_launcher_arguments_reach_widescreen_gameplay(self):
        # Compile the real settings type, then feed its output to the Python
        # launch path. No game, user preferences or save files are accessed.
        import sys
        sys.path.insert(0, str(ROOT/'tools'))
        import play
        import graphics_settings as graphics
        source=(ROOT/'src/launcher/BuffyLauncher.swift').read_text()
        settings=source[source.index('struct LaunchSettings {'):source.index('@MainActor')]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            config=root/'private/config/graphics.json';config.parent.mkdir(parents=True)
            harness=root/'Probe.swift'
            harness.write_text('import Foundation\n'+settings+'''
@main struct Probe {
 static func main() throws {
  let root=URL(fileURLWithPath:CommandLine.arguments[1])
  var s=LaunchSettings(root:root)
  var rows=[[String]]()
  rows.append(s.arguments())
  s.uhd=true;rows.append(s.arguments())
  s.uhd=false;rows.append(s.arguments())
  s.widescreen=true;s.uhd=true;rows.append(s.arguments())
  s.uhd=false;rows.append(s.arguments())
  print(String(data:try JSONSerialization.data(withJSONObject:rows),encoding:.utf8)!)
 }
}
''')
            exe=root/'Probe'
            result=subprocess.run(['xcrun','swiftc','-module-cache-path',str(root/'cache'),
                '-parse-as-library',str(harness),'-o',str(exe)],capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stderr)
            for saved_uhd in (False,True):
                config.write_text(json.dumps({'resolution':'4k' if saved_uhd else 'scale','aspect':'4:3'}))
                result=subprocess.run([str(exe),str(root)],capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr)
                rows=json.loads(result.stdout)
                expected=['16:9' if saved_uhd else '4:3','16:9','4:3','16:9','16:9']
                for args,aspect in zip(rows,expected):
                    selected=play.selected_settings(play.parse_args(args),config)
                    self.assertEqual(selected['aspect'],aspect,(saved_uhd,args))
                    mission=play.build_environment(selected,root/'hdd',0,{})
                    menu=play.build_environment(selected,root/'hdd',0,{},mode='menu')
                    self.assertEqual(mission['RECOMP_DISPLAY_ASPECT'],aspect)
                    self.assertEqual(mission['BUFFY_WIDESCREEN'],str(int(aspect=='16:9')))
                    self.assertEqual(menu['RECOMP_DISPLAY_ASPECT'],'4:3')
                    self.assertEqual(menu['BUFFY_WIDESCREEN'],'0')
                    if '--resolution' in args:
                        self.assertEqual(graphics.render_dimensions(selected),(3840,2160))
                        self.assertEqual(mission['RECOMP_PRESENT_SURFACE'],'uhd')
