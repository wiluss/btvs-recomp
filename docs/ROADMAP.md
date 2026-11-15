# Roadmap

## Available in 0.2.0-beta.1

- Independent original-Xbox Buffy (2002) port for macOS Apple Silicon, using native
  ARM64 and Metal. Supported USA ISO import and verified local generation/build.
- Five-language launcher with system-language selection, resolution scaling, 4K,
  experimental widescreen, fullscreen, VSync and FPS display.
- Keyboard/controller support and remapping, AZERTY/QWERTY presets, optional arenas.
- Persistent saves, whole-profile backups/restore and a previewable problem report.
- Separate optional HD texture/HUD/text pack; custom XRTP texture/skin library.
- Native Main and Pause outfit selector with animated 3D previews, five stock
  costumes, immediate application on Resume and remembered choice. A launcher
  switch enables/disables the selector for the next session (on by default).
- Opt-in Discord Rich Presence with shared public application metadata, original
  level names, official logo and elapsed session time.
- Automatic launcher/game updates with isolated local builds, journaled
  replacement and rollback. Existing alphas use the small 0.1.1 updater bridge
  first, or the new kit’s update command. Existing imports, save profiles and HD
  packs are reused without ISO reimport.

## Before 1.0

- Validate the complete campaign and level transitions, including cutscenes and
  the outfit selector across different player/scene lifetimes.
- Investigate the intermittent audio crash when reproducible; improve audio
  stability and assess long sessions. The latest work claims no audio fix.
- Collect testing from other Macs and macOS versions.
- Physically test new outfit-menu navigation and custom keyboard/controller maps.
- Profile reproducible effects/enemy-heavy slowdowns before optimizing.
- Refine setup/update usability, recovery and error messages from real reports.

Partial campaign completion cannot establish compatibility of the remaining
missions. Quicksave and arbitrary model/script mods are not implemented. Windows,
Linux and Android game ports are not supported by this release.

## Validation

246 automated tests, ARM64 host probe and signed launcher build passed for the beta
candidate. Prior native checks exercised Main/Pause previews, selection/cancel,
immediate resume, preference persistence and explicit owned-resource teardown.
The project owner also confirmed the new selector works in a real session.
These checks do not establish complete campaign or long-session compatibility.
See [BRINGUP.md](BRINGUP.md) and [known issues](TROUBLESHOOTING.md).


### Outfit movement correction

Corrected the cosmetic’s use of simulation position instead of the original
interpolated render position. Native scripted movement matched source/cosmetic
root positions across 4,000 samples; the normal binary was rebuilt. This does not
establish full campaign, animation or long-session validation.


### Cutscenes and charged attacks

Cutscenes use the original level outfit to preserve native facial expressions and
lip sync; the chosen costume returns automatically in gameplay. Native evidence
confirms both render paths and changing phoneme frames; full cosmetic facial
transfer remains future work. Movement jitter was confirmed fixed by the owner.
A real-controller diagnostic repeated mana attacks without reproducing the crash.
The reported charged-attack/audio crash remains open; no audio fix is claimed.
Support reports now recognize beta/rc version numbers.


## README wardrobe and Discord captures — November 15, 2026

The owner supplied and selected three additional unedited documentation PNGs:
outfit-selector.png, outfit-gameplay.png and discord-presence.png under
docs/screenshots/. The narrow source-image allowlist now contains those three
plus the original four captures. No other asset or HD payload is authorized.
README pairs the native Wardrobe preview with alternate-outfit gameplay and
shows the actual Discord level card. A visible note states that outfit changes
apply to gameplay; cutscenes retain the original level outfit for facial animation
and the chosen outfit returns afterward. No gameplay/runtime change.

Validation: all three supplied PNGs are byte-identical after copying; 33 local
README links/images resolve. The full suite passed: 246 tests (20.962 s), including
the exact image allowlist, archive integrity and export reproducibility checks.


Updater bridge 0.1.2 supersedes 0.1.1: it accepts the three approved new beta
README captures. The withdrawn 0.1.1 assets had no downloads. Game/runtime inputs
are unchanged. Beta 0.2.0-beta.1 archives and tags remain unchanged.
