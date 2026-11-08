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
        for source in ['LauncherView.swift','ControlsView.swift','SetupView.swift','BuffyLauncher.swift']:
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
