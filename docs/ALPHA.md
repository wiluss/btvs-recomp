# Prerelease status

Version: `0.2.0-beta.1`, source-build beta candidate with an optional HD add-on.

Players build locally from their own supported ISO. The source kit contains original project source, public build recipes, metadata, English documentation, runtime patches, license notices and the selected project-branding graphics and four documentation screenshots. A separate optional HD ZIP contains prepared game-derived textures, HUD, text and launcher artwork; see [HD-PACK.md](HD-PACK.md). No ISO, XBE, MAP, save, editable HD master, model, generated game source or recompiled game executable is included in either attachment.

## Earlier ISO setup validation on the development Mac

These setup checks predate 0.2; they have not been repeated as a fresh full-ISO beta installation.

- The user's USA ISO contains the exact XBE and `final.map` required by the manifest.
- An isolated source installation without prior private data, generated files, build products, logs or venv completed extraction, dependency preparation, generation and ARM64 compilation.
- Its 173 generated C files match the development installation; the runtime sources match after the six shipped patches.
- A blank profile reached the title and main menu, created the first save, then loaded that save after restart into the first level's opening cutscene.
- Those setup checks used dummy audio and the runtime's scripted input API. They do not establish audio quality, a new gameplay session or long-term stability.
- The development user previously validated real gameplay and the original controller mapping. Physical remapping validation and the complete campaign remain open.

Only one Mac is available for testing. Other hardware and macOS versions need external testing. The launcher targets macOS 13 or later; the tested Mac runs macOS 27.2.

## Public setup scope

The current installer runs inside the extracted source folder and requires native build prerequisites. It is not an independently installed app in Applications. A clean install uses original game graphics until the optional HD add-on is imported. Editable development masters are not shipped. The direct mission diagnostic and its captured bootstrap page are outside the player setup path.

Known issues include audio stutter, an intermittent audio crash, resolution/effect-dependent frame-rate swings and unconfirmed long sessions. See [troubleshooting](TROUBLESHOOTING.md).

## Packaging

The root MIT license covers original project code. Third-party file licenses take precedence for their components. Notices and full license copies are included.

The source archive is built from `release/files.json`, audited and accompanied by `SHA256SUMS` and an internal `RELEASE_MANIFEST.json`. Generated archives and all validation data remain under artifacts. Long private development histories are excluded; the public kit contains English summaries and user instructions.

A prepared local archive or GitHub draft is not a published release. Follow the [release process](../release/PUBLISHING.md) and verify the exact package before publishing.

## 0.2 beta additions

246 automated tests, ARM64 host probe and launcher compilation passed. The source ZIP is manifest-audited and reproducible from its extracted kit on the development toolchain.

Native Main/Pause outfit selection with animated 3D previews, immediate cosmetic
application on Resume, remembered selection and a launcher switch (on by default).
Discord Rich Presence is opt-in and includes the shared public application ID,
current level, official logo and session time. Custom XRTP texture mods have a
local import/priority library. Existing profile backups and problem reports remain.

The project owner confirmed the native Pause selector works in a real session.
Short native tests cover previews, selection/cancel/resume, remembered choices and
explicit cleanup. Full campaign transitions, cutscene doubles, long sessions and
physical controller navigation of the new selector remain outside those checks.
This is a version milestone, not proof of 1.0 readiness or an audio crash fix.

The updater now handles game regeneration/rebuild automatically, reusing the
supported import and existing data. Older alphas need the 0.1.1 launcher-only
updater bridge first, or the beta kit’s update command. See
[SETUP.md](SETUP.md#upgrade-to-02-from-an-alpha).


Cutscenes temporarily use the level's original outfit to preserve facial
expressions and lip sync, then restore the chosen cosmetic during gameplay.
A native check confirmed changing phoneme frames and automatic restoration.
The owner confirmed the movement-jitter fix. A subsequent charged-attack crash
remains unresolved; a cloned-save controller/CoreAudio retest did not reproduce
it despite repeated mana-consuming attacks. No new audio fix is claimed.
