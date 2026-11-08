# Bring-up and validation summary

This is the public summary. Long traces, private research notes, captures and generated snippets are not included. Read [SETUP.md](SETUP.md) for current player instructions.

## Supported input

The identified original Xbox USA build has XBE SHA-256 `cd49da614d92b6ec94f3bd66d503eb4e214f8809e9c7b42f465ee25c709ad35f` and MAP SHA-256 `ce6e0d00dd2cff78b9de68c54bd208815a0b0883b9aff73e6c56e1663b80ba5b`. The MAP matches the preserved PE timestamp, resident section extents and relocated entry point. Xbox addresses use their XBE sections, not a single PE offset.

## Runtime and generation

The generic toolkit is pinned and its six patches are explicit. Title adaptations cover the identified generator instruction, initialization, factory-table handling, arenas and widescreen/letterbox behavior. Generated C is local output, not the permanent fix source.

The isolated ISO setup imported 152 files (2,010,281,870 bytes). Its 173 generated C files match the development output. Runtime source matches after applying the six shipped patches. No previous save, HD pack, generated output or Python environment was copied into that installation.

## Observed stages

- Host probe: ARM64, 64-bit pointers and 16 KiB pages.
- Runtime and title: compiled and rendered real intro/title images on Metal.
- Player interaction: earlier user sessions validated gameplay and the original physical controller mapping.
- Clean ISO setup: menu, new-game name/difficulty, first save and Load Game into the first level's cutscene confirmed.
- Setup-native checks used dummy audio and scripted generic controller input. Bounded watchdog exits are not presented as crashes or successful gameplay sessions.

No complete campaign, new long-session benchmark, physical custom remapping or second-Mac validation is claimed. Audio problems remain open.

## Tests

The asset-free suite compiles selected real generic runtime functions and adapters, with sanitizer coverage where applicable. It covers XBE/MAP validation, generation guards, display/HUD behavior, input semantics, profiles, ISO import, blank disks and lossless storage. Release tests additionally check source selection, forbidden paths/content, symlinks, reproducibility and clean dependency bootstrap.

For `0.1.0-alpha.1`, 145 tests passed in both the development checkout and the exported source installation. The exported kit fetched the pinned toolkit, imported the supported ISO, generated the same 173 C files, compiled the game and built the launcher. The host probe passed on Apple Silicon. Menu/save/load observations above come from the earlier isolated setup checks; the exported-kit build is not a new gameplay session.

A host probe, a passing test suite or a compiled binary alone does not establish menu or gameplay success. Report these separately when changing the code.

## Optional HD add-on candidate

For `0.1.0-alpha.2`, 150 asset-free tests passed, including five synthetic HD-installer tests. The Apple Silicon host probe and launcher build passed. The real ZIP was imported through the native launcher into the isolated supported game setup; it showed HD Pack installed. All installed file hashes and the four original/HD texture/text combinations validated, followed by menu --check. A 25-second native run loaded all 1,973 entries from the installed add-on, using dummy audio and a separate test profile. Watchdog exit 3 was expected (the play CLI reports 1); this is not new menu, gameplay, audio or long-session validation. Subsequent UI automation timed out; a process sample showed the launcher's main thread idle, so the other post-import views were not visually revalidated.
