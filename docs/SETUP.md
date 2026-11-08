# Installation

This alpha builds the game on your Mac from your own compatible ISO. It is a source distribution; the ZIP contains no game executable, disc image, assets, save, generated game code or HD pack.

## 1. Check compatibility

Use an Apple Silicon Mac and a native ARM64 terminal. The launcher is built for macOS 13 or later; testing so far covers one Mac on macOS 27.2. Intel Macs, Windows, Linux and Android game builds are not supported by this alpha.

The supported input is the identified USA build of Buffy the Vampire Slayer (2002, original Xbox), not Chaos Bleeds. Setup requires both files from your image:

| Input | SHA-256 |
| --- | --- |
| Default.xbe | `cd49da614d92b6ec94f3bd66d503eb4e214f8809e9c7b42f465ee25c709ad35f` |
| final.map | `ce6e0d00dd2cff78b9de68c54bd208815a0b0883b9aff73e6c56e1663b80ba5b` |

The tested ISO includes both. Setup locates the game partition and checks the inputs itself; you do not need to extract them manually. A mismatch is a compatibility refusal. Do not edit the hashes to force a different executable through the address-dependent generation steps.

## 2. Install prerequisites

Install Apple's Command Line Tools if missing:

```sh
xcode-select --install
```

Install Homebrew using its [official instructions](https://brew.sh/) if needed, then:

```sh
HOMEBREW_NO_AUTO_UPDATE=1 brew install python@3.12 cmake ninja pkgconf sdl3 libepoxy openssl@3
```

The current recipe expects the Apple Silicon Homebrew prefix `/opt/homebrew`. Reserve at least 35 GiB free before extraction. Setup checks for 30 GiB of working space again before compilation; other applications can consume that space during setup.

## 3. Verify and extract the release

Download the attached source ZIP and `SHA256SUMS` to the same folder. Compare against the checksum from the release you trust:

```sh
shasum -a 256 -c SHA256SUMS
```

Extract the ZIP into its own folder and keep the files together. If you use GitHub's automatic source archive or clone the repository, the bootstrap command below still fetches the pinned toolkit; do not use a floating runtime revision.

## 4. Build the launcher

In a terminal inside the extracted source folder:

```sh
python3 tools/bootstrap_runtime.py
make launcher
open "build/btvs-recomp.app"
```

Bootstrap fetches only the generic public XboxRecomp toolkit at the commit in `dependencies.lock.json`. It does not fetch a game or change a toolkit checkout at an unexpected revision.

## 5. Prepare your game

Choose **Set up from an ISO…**. On an existing installation, the same command is in **Help**. Select the ISO and choose **Set up game**.

Setup performs these steps:

1. Validate the disc tree, XBE and MAP.
2. Extract into a temporary directory and publish the completed import without overwriting an existing installation.
3. Create `.venv/` and install pinned Python dependencies.
4. Verify or apply the six shipped runtime patches to the pinned generic toolkit.
5. Generate the game sources locally and compile an ARM64 executable.

The ISO stays unchanged. No game files are downloaded. Cancel stops preparation and its child build process; a temporary import is discarded. A completed import can be reused on retry. Unknown or partially modified runtime sources are preserved and refused rather than reset.

The detailed build log is `private/setup/setup.log`. Import and build receipts are in `private/setup/`. A successful build means the files were prepared; the launcher does not automatically certify that gameplay works on your Mac.

## 6. Play and save

Choose **Play**. The launcher starts at the main menu with no time limit. A first-time player gets an empty disk/profile generated from generic runtime geometry. The game creates its first save normally. Use **Load Game** on later launches.

Keep the whole source folder: the launcher currently depends on it. Do not move just the `.app` to Applications. Your save profile is `private/profile/`; back up the whole directory while the game is closed.

A fresh installation uses original game textures and text. To add the prepared textures, HUD and manually refined text, download the separate HD ZIP and follow the [HD add-on guide](HD-PACK.md). Editable font masters are not distributed. Read the [user guide](GRAPHICS.md) before changing resolutions, controls or local packs.

## Command-line equivalents

```sh
# Read-only compatibility inspection:
python3 tools/setup_game.py '/path/to/Buffy (USA).iso' --inspect

# Import and build:
python3 tools/setup_game.py '/path/to/Buffy (USA).iso' --build

# Normal unlimited session, persistent profile:
python3 tools/play.py menu
```

The direct `mission` diagnostic is not the installation path. It still needs private diagnostic state that is not distributed.

## What was tested

An isolated source installation without prior private data, generated files, build products, logs or Python environment was built from the user's ISO. Menu, new-save creation and Load Game into the first level's cutscene were confirmed. Setup testing used dummy audio and scripted runtime input. A second Mac, older macOS versions, the full campaign and long-session stability remain unverified.
