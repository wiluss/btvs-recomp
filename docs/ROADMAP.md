# Roadmap

## Implemented and validated locally

- ARM64/Metal integration for the identified original Xbox title.
- Player launcher, display settings, original controls and persistent saves.
- Experimental widescreen, high resolutions, arenas and local pack selection.
- Five launcher languages and keyboard/controller remapping.
- ISO import with XBE/MAP checks and generation/compilation in a clean local source installation.
- Blank-disk startup, first-save creation, restart/Load Game and the first level's opening cutscene.
- Lossless idle partition compression and restoration.
- Source-only packaging, English public guides and an original launcher icon.
- A separate prebuilt HD add-on preserving manual refinements, with a pinned catalog and launcher import.

## Before publishing this candidate

- Review the exact source ZIP, notices, checksum and release notes.
- Test the exported kit and its bootstrap without development-state dependencies.
- Select the intended GitHub repository and review its public tree/tag.
- Create and inspect a draft prerelease; publishing is a separate step.

## Still open

- Intermittent audio crash, stutter and broader stability testing.
- Complete campaign/progression validation and long sessions.
- Physical validation of custom controller remapping.
- Other Apple Silicon models and older macOS versions.
- Publicly reproducible optional HD asset/font preparation from the player's files.
- Setup recovery if runtime patch application is interrupted mid-sequence.
- A standalone installation location, updates and uninstall flow.

Windows, Linux and Android game ports, quicksave, presence integration and a mod browser are not features of this alpha. Source-only CI on Linux does not establish a Linux game port.

## Project identity

The project and repository are named btvs-recomp. The English README uses a user-requested monochrome Buffy-style lettering adaptation and violet/red navigation graphics. The launcher displays the new name and wordmark. The optional HD v1 payload retains its original bytes under the new filename.

## README presentation

The alpha.6 candidate adds an English AI-assistance disclosure and four unedited owner-supplied launcher/gameplay captures. The exact screenshot paths are audited as a narrow documentation exception; other game assets remain excluded from source. The source packaging regression and the full 152-test suite passed using the existing macOS Python environment, and the GitHub-rendered markup was inspected in a browser. No runtime, HD payload, gameplay or audio change is claimed. Publication remains a separate user action.

## 4K widescreen launcher fix — November 12, 2026

A user report identified a mismatch: the 4K badge showed 16:9 while launcher arguments explicitly selected the saved 4:3 aspect. A compiled Swift regression reproduced that failure before the fix. The launcher now derives its effective aspect from UHD or the scaled-mode preference; the disabled UHD toggle displays the same effective state. Old UHD/4:3 profiles are handled on load, and switching back to scaled rendering preserves the previous choice during the launcher session. The Python CLI still accepts an explicit 4:3 override. Menus keep 4:3 framing. No runtime, projection, XBE address or save handling changed.

Validation: 153 tests passed (39.970 seconds), including the compiled Swift-to-Python launch regression; the ARM64 host probe passed. The native launcher rebuilt successfully with the installed macOS 26.5 SDK selected for that command only. The default 27.2 SDK failed because its SwiftUIMacros plugin was missing; no global toolchain setting was changed. No new gameplay or visual validation on the reporting player's Mac is claimed. The published release has not been replaced.

Alpha.7 packages the 4K launcher fix. HD v1 remains byte-identical and is linked from its existing alpha.6 release; no previous tag or attachment is replaced.
