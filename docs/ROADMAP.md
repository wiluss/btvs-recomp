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
- A standalone installation location, automatic game/runtime upgrades and uninstall flow.

Windows, Linux and Android game ports, quicksave, presence integration and a mod browser are not features of this alpha. Source-only CI on Linux does not establish a Linux game port.

## Project identity

The project and repository are named btvs-recomp. The English README uses a user-requested monochrome Buffy-style lettering adaptation and violet/red navigation graphics. The launcher displays the new name and wordmark. The optional HD v1 payload retains its original bytes under the new filename.

## README presentation

The alpha.6 candidate adds an English AI-assistance disclosure and four unedited owner-supplied launcher/gameplay captures. The exact screenshot paths are audited as a narrow documentation exception; other game assets remain excluded from source. The source packaging regression and the full 152-test suite passed using the existing macOS Python environment, and the GitHub-rendered markup was inspected in a browser. No runtime, HD payload, gameplay or audio change is claimed. Publication remains a separate user action.

## 4K widescreen launcher fix — November 12, 2026

A user report identified a mismatch: the 4K badge showed 16:9 while launcher arguments explicitly selected the saved 4:3 aspect. A compiled Swift regression reproduced that failure before the fix. The launcher now derives its effective aspect from UHD or the scaled-mode preference; the disabled UHD toggle displays the same effective state. Old UHD/4:3 profiles are handled on load, and switching back to scaled rendering preserves the previous choice during the launcher session. The Python CLI still accepts an explicit 4:3 override. Menus keep 4:3 framing. No runtime, projection, XBE address or save handling changed.

Validation: 153 tests passed (39.970 seconds), including the compiled Swift-to-Python launch regression; the ARM64 host probe passed. The native launcher rebuilt successfully with the installed macOS 26.5 SDK selected for that command only. The default 27.2 SDK failed because its SwiftUIMacros plugin was missing; no global toolchain setting was changed. No new gameplay or visual validation on the reporting player's Mac is claimed. The published release has not been replaced.

Alpha.7 packages the 4K launcher fix. HD v1 remains byte-identical and is linked from its existing alpha.6 release; no previous tag or attachment is replaced.

## Launcher-only updates — November 12, 2026

Alpha.8 adds a double-click source-kit updater for existing alpha.6/.7 installations and a five-language update view in the launcher. Official GitHub source downloads are checked against the API SHA-256 digest and archive manifest. Existing tracked sources must match their installed manifest. Changed game/runtime inputs, local edits, symlink destinations and downgrades are refused. The new launcher is built in isolation before replacing allowed source files and the launcher bundle; prior versions and a recovery journal are retained. Saves, game files, HD packs, generated code and runtime are not installed or rebuilt by this helper. Interrupted transactions can be recovered after the updater process stops. Git checkouts without the official kit manifest need manual updating.

Validation: 163 tests passed in 37.946 seconds. Ten updater regressions cover successful installation, failed builds, mid-install rollback, interrupted-transaction recovery, concurrent local edits, symlinks, protected game changes, downgrade refusal and HTTPS/checksum checks. Real compilation and alpha.6-to-alpha.8 migration passed in an isolated kit; private/game/HD/configuration/runtime/generated sentinels stayed byte-identical. The native five-language launcher built, its update screen and current-version check were inspected, and the ARM64 host probe passed. No new gameplay or audio validation.


## Player support and save backups — November 13, 2026

Alpha.9 is a local candidate. The launcher now creates verified full-profile backups before sessions, retaining three distinct automatic copies. The five-language Saves panel creates manual copies and restores a selected copy while retaining the previous profile. Backup/restore uses the existing storage/profile locks, title identity and per-file hashes; interrupted restore recovery runs before the next launcher backup. Raw expanded partitions and oversized profiles are refused rather than copied blindly. This is saved-progress protection, not an in-game quicksave.

A local problem report previews allowlisted system/settings/session metadata and never uploads anything. Raw logs, personal paths, game files, save contents and serial numbers are excluded. No new audio failure has been reported or reproduced by the user; no speculative audio/runtime correction was made.

Validation: 175 tests passed in 40.160 seconds, including 12 backup/report regressions covering restoration, retention, locks, corrupted archives, traversal, rollback, interrupted recovery and privacy exclusions. The ARM64 host probe passed and the launcher compiled. The native French backup creation/restore confirmation/success and report preview were exercised on a synthetic isolated profile. The personal save profile was not restored or modified; no new gameplay or physical controller test is claimed. Evidence remains in artifacts/player-support/. Publication is separate.

Next priorities: reproducible audio/stability reports and cross-Mac testing, then a clearer compatible texture/skin pack manager. A general scripting mod API and full runtime quicksave remain separate, larger projects.
