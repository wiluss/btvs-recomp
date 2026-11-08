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
