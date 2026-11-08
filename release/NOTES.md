# btvs-recomp 0.1.0-alpha.4

First source alpha for **Buffy the Vampire Slayer (2002, original Xbox)** on Apple Silicon.

## Installation

Download the attached `btvs-recomp-v0.1.0-alpha.4-source.zip` and `SHA256SUMS`. Verify the checksum, extract the source folder and follow `README.md` or `docs/SETUP.md`.

You need your own supported USA ISO, Apple build tools and the listed Homebrew packages. Run `python3 tools/bootstrap_runtime.py`, build the launcher with `make launcher`, then choose **Set up from an ISO…**. The game is generated and compiled locally. No game download is provided.

## Included

- ARM64/Metal runtime integration and a local ISO setup flow.
- Persistent saves with first-time blank profiles and lossless idle disk compression.
- Resolution scaling, optional 4K/16:9, fullscreen, VSync and FPS overlay.
- Keyboard/controller remapping and a five-language launcher.
- Original project source under MIT, separate runtime patches and third-party notices.

No ISO, game executable, MAP, generated game source, save, disk image, model weight or editable development master is attached. The source ZIP includes only the approved project wordmark and README graphics; gameplay HD data is separate.

## Optional HD add-on

Download `btvs-recomp-HD-v1.zip` (about 676 MB) and `HD-SHA256SUMS` separately if you want the prepared campaign textures, HUD, reconstructed text and launcher artwork. After game setup, open **Packs & skins → Install the HD pack…** and select the ZIP. Installation verifies the pinned checksums and game edition, preserves existing local assets and enables the HD switches. Manual refinements are already included; no AI model is required. Read `docs/HD-PACK.md` for scope and troubleshooting.

The HD add-on contains game-derived graphics. The project's MIT code license does not grant rights over the original artwork or trademarks, and this unofficial add-on is not presented as authorized or endorsed by the original rights holders.

## Known limitations

Audio can stutter and an intermittent audio crash remains open. Performance varies with effects and resolution. The complete campaign, long-session stability, custom physical controller mappings, older macOS versions and other Mac models still need validation. The setup path has been tested on one Mac; scripted setup checks used dummy audio and confirmed menu, first-save creation and loading into the first level's cutscene.

Please read `docs/TROUBLESHOOTING.md` before reporting a problem. Do not upload game files, saves, disk images, full memory-bearing logs or complete project folders.

This is an unofficial project, not affiliated with the original rights holders.
