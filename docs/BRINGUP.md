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

## btvs-recomp identity candidate

For `0.1.0-alpha.3`, 151 asset-free tests and the Apple Silicon host probe passed. The renamed launcher compiled and its name/logo were inspected natively. The game rebuilt incrementally in the isolated supported ISO installation with the new generated host title; no new gameplay, audio or performance validation is claimed. GitHub-rendered README markup was inspected in a local browser. A dedicated regression checks the narrowly allowed branding PNG/SVG assets while keeping other game data excluded. The HD v1 bytes are unchanged after renaming the attachment.

## Moon branding layer

For `0.1.0-alpha.4`, 151 tests, the ARM64 host probe and launcher build passed. The moon composition was inspected in a local browser and the native launcher. The wordmark PNG is byte-identical to alpha.3; the original game-logo moon was isolated with its obscured portions reconstructed, then layered separately. No new game launch, gameplay, audio or runtime validation is claimed for this visual change.

## Silver lettering presentation

The alpha.5 logo uses matching neutral-grey gradients, light bevel edges and darker offset shadows in SVG and SwiftUI. Both approved PNGs remain byte-identical. Browser and native visual checks confirmed the final effect after fixing a native mask-transparency defect. This presentation-only change does not establish new gameplay, audio or runtime validation.

The final alpha.5 palette was lightened following user feedback while retaining bevel highlights and shadows. The final native/browser render, 151 tests and ARM64 host probe passed. No new game launch or gameplay validation is claimed.

## README screenshots and AI disclosure

For alpha.6, 152 tests passed with the existing macOS Python environment, including a new source-kit regression for the exact approved screenshot paths and size limits. The Homebrew Python and .venv lacked Pillow; those initial runs are not counted as successful. The GitHub-rendered README was inspected locally in a browser. All four captures are byte-identical to the supplied originals. No native code changed, so no new host probe or launcher build was required. This documentation update does not establish new gameplay, audio or performance validation.
