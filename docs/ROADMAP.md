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
