# Optional HD add-on

The source kit works with the original game graphics. The separate **btvs-recomp-HD-v1.zip** adds our prepared campaign textures, HUD, reconstructed text and launcher artwork, including manual refinements. No AI software or asset reconstruction is required on the player's Mac.

## Install

1. Install and build the supported game from your own ISO first, following [SETUP.md](SETUP.md).
2. Download `btvs-recomp-HD-v1.zip` and `HD-SHA256SUMS` from the same project's GitHub alpha release. Keep the ZIP intact.
3. Open **Packs & skins** in the launcher. **Download the HD pack…** opens the release page; **Install the HD pack…** lets you select the downloaded ZIP.
4. Wait for **HD Pack installed**. The launcher enables the texture and text switches and loads the prepared artwork. You can switch **Textures HD** and **Text HD** off independently in Options.

The ZIP is about **676 MB** (644 MiB); its contents need about **1.32 GB** (1.23 GiB). Keep at least **2 GiB free** for installation, in addition to the game. This is the prepared campaign pack with a 2× environment texture selection, the improved HUD and 8× text assets; it does not replace every texture in every level.

The installer checks the ZIP against the checksum pinned in the source kit, checks every member and the installed game's XBE, and refuses incompatible source recipes. It uses the local file you select; there is no background HD download. Until a release is published, its files are accessible only to the private repository's authorized users.

## Files and existing installations

The add-on is installed into `private/hd/1/` as one complete directory. Saves, disk images and preference files are not modified. Existing local assets under `private/textures/`, `private/launcher/` or `private/fonts/` retain precedence. An identical installed add-on is accepted; a modified or conflicting add-on is refused rather than overwritten. Custom XRTP selection remains separate.

For command-line installation, from the source folder:

```sh
python3 tools/hd_pack.py install /path/to/btvs-recomp-HD-v1.zip
```

If installation fails, open the session log. Confirm that the source kit and HD add-on come from the matching release and that your game setup has finished. No complete installation is published if verification fails or extraction is interrupted. Close the game and installer before manually moving any add-on files.

## Scope and notices

This add-on contains game-derived graphics and manually reconstructed font outputs. The project's MIT license covers original project code and does **not** license the original game's artwork, trademarks or other third-party rights. This is an unofficial add-on, without an assertion of endorsement or authorization from the rights holders.

No disc image, XBE, MAP, game binary, generated game code, save, Xbox disk image, model weight, upscaler executable or editable development master is included. See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). Do not attach the add-on or other game data to bug reports.

The v1 add-on payload did not change when the project was renamed to btvs-recomp. An earlier `Buffy-macOS-HD-v1.zip` with the same pinned checksum remains compatible; the installer verifies bytes, not the selected file's name. You do not need to reinstall existing working HD content for this rename.
