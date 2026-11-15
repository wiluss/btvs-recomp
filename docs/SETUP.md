# Installation

This beta builds the game on your Mac from your own compatible ISO. It is a source distribution; the ZIP contains no game executable, disc image, assets, save, generated game code or HD pack.

## 1. Check compatibility

Use an Apple Silicon Mac and a native ARM64 terminal. The launcher is built for macOS 13 or later; testing so far covers one Mac on macOS 27.2. Intel Macs, Windows, Linux and Android game builds are not supported by this beta.

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

## Update an existing installation

Close the game before updating. In the launcher choose the circular-arrow button
or **Help → Check for updates**, review the release notes and choose **Install
update**. Quit and reopen the launcher after success. The updater downloads the
official source ZIP, verifies its GitHub SHA-256 digest and manifest, and builds
separately before replacing anything. Compatible launcher-only updates build only
the launcher. Game/runtime changes automatically regenerate and compile the game
from the already imported supported files.

No ISO reimport, HD redownload or save copying is needed. Native build prerequisites,
Python 3.12 and internet access for any missing build dependencies are still needed.
Allow at least **30 GiB free** and several minutes for a game rebuild. Updates do
not run while a game session or disk-maintenance operation holds the session lock.
Locally edited source or runtime files are preserved and refused for manual review.
Official attached kits include `RELEASE_MANIFEST.json`; Git checkouts and GitHub's
automatic source archives still need a manual developer update.

### Upgrade to 0.2 from an alpha

Older alphas cannot recognize beta versions or build game updates themselves.
Choose either route:

- **Existing update button (alpha.8/.9):** install **0.1.2 — Updater bridge**,
  quit and reopen the launcher, then check again and install **0.2.0-beta.1**.
  Both installations are automatic. The bridge is a launcher-only compatibility
  update; the game gains the new features in the beta update.
- **Direct upgrade from the beta ZIP:** download the attached
  `btvs-recomp-v0.2.0-beta.1-source.zip` and `SHA256SUMS`, verify them, extract into
  a **separate folder**, close the old game/launcher and double-click
  **Update btvs-recomp.command** in the new folder. Choose your existing project
  folder (containing `private`, `build` and `tools`). The new helper handles the
  game rebuild and launcher update automatically. Use this route for earlier
  alphas without an update button too.

Your existing installation stays in its current folder. Keep an external backup
of the whole `private/profile/` with the game closed. Neither route reimports the
ISO or downloads a game. On the next Play, an enabled outfit selector prepares
its own private resource cache once; this needs additional space/time. Disable
**Options → Outfit selector** before playing to skip that preparation.

### Failure and recovery

Builds use an isolated directory and their own runtime checkout/tool environment.
The installed game, launcher and private data remain available if compilation
fails. During installation, source, native game, generated output, runtime and
generation records are replaced as one journaled transaction. Errors restore the
previous versions. The updater retains previous files and logs under
`artifacts/launcher-update-*/`; game build details are in `game-build.log`.

If macOS or the updater is forcibly stopped during installation, keep the lock
and backups. Once the updater has stopped, recover from the project folder:

```sh
/usr/bin/python3 tools/update_launcher.py --target "$PWD" --recover
```

If that helper is unavailable, run the helper in the downloaded kit with
`--target` pointing to the existing project folder. Keep backups until the new
version has been tested. Updates never copy, compact or replace your save disks.

### Optional Discord presence

Discord Rich Presence is off by default. Enable it in Options; the shared project Application ID is already included. see [Discord setup and validation limits](DISCORD.md).
No Discord account or client is needed to play without this feature.
