# Buffy macOS

An independent Apple Silicon port of **Buffy the Vampire Slayer (2002, original Xbox)**, built with a pinned generic XboxRecomp runtime and Metal rendering.

**Source alpha — `0.1.0-alpha.1`.** Build the game locally from your own compatible Xbox disc image. This project does not provide or download the game.

## What you need

- An Apple Silicon Mac. The launcher targets macOS 13 or later; the current build has been tested on one Mac running macOS 27.2. Earlier supported OS versions and other Mac models still need testing.
- Apple's Command Line Tools, Homebrew in `/opt/homebrew`, and the packages below.
- Your own compatible USA ISO, including `Default.xbe` and `final.map`. Setup checks their exact hashes before importing anything. Other editions and modified executables are not currently supported.
- At least 35 GiB free before setup. Keep free space available for compilation and the Xbox disk images used while playing.

No AI model, LM Studio installation, private save, or previously generated game code is required.

## Install

Download and extract the **source ZIP attached to the alpha release**. Keep its folder intact: the launcher runs from that source folder.

From a terminal in the extracted folder:

```sh
# Install Apple's Command Line Tools if they are missing:
xcode-select --install

# With Homebrew already installed:
HOMEBREW_NO_AUTO_UPDATE=1 brew install python@3.12 cmake ninja pkgconf sdl3 libepoxy openssl@3

# Fetch the exact public generic toolkit, then build our launcher:
python3 tools/bootstrap_runtime.py
make launcher
open "build/Buffy Launcher.app"
```

Skip `xcode-select --install` if the tools are already installed. The full [installation guide](docs/SETUP.md) covers prerequisites, verification and troubleshooting.

In the launcher, choose **Set up from an ISO…**, select your image, then **Set up game**. Setup imports the files, creates a local Python environment, applies the shipped runtime patches, and builds the game. It may download development dependencies; it never downloads game content.

When setup finishes, choose **Play**. A new player starts at the main menu with an empty save profile. After saving, use **Load Game** to continue.

## Features

- Native ARM64 runtime and Metal rendering.
- Resolution scaling, 4K output, experimental 16:9, fullscreen, VSync and an FPS overlay.
- Keyboard and controller support, with remapping and AZERTY/QWERTY keyboard presets.
- A launcher in English, French, Spanish, German and Italian. It follows a supported system language until you choose a language yourself.
- Persistent saves and lossless compression of dormant Xbox partition images.
- Local XRTP texture packs and optional arena access.

**A clean source installation uses original game textures and text.** The development machine's reconstructed fonts, HD packs, logo and background images are not distributed. Their private masters are not yet reproducible through the public setup; the corresponding options remain disabled when packs are absent. The launcher has an original, code-drawn fallback design and icon.

## Alpha limitations

Audio can stutter, an intermittent audio crash remains unresolved, and performance varies considerably with resolution and effects. The full campaign and long sessions have not been validated. The original controller mapping was tested physically; custom controller mappings still need physical testing.

The setup was tested from the user's USA ISO in an isolated source installation on the same Mac: extraction, generation, ARM64 compilation, a blank-disk menu, creation of the first save, and loading that save into the first level's opening cutscene. Those setup checks used dummy audio and the runtime's scripted controller API. They do not replace gameplay, audio or cross-machine testing.

See the [user guide](docs/GRAPHICS.md), [known issues](docs/TROUBLESHOOTING.md) and [release notes](release/NOTES.md).

## Saves and updates

Your save profile lives in `private/profile/`. Keep a backup of the **whole profile**, including its title metadata and disk files. Do not delete it when updating. Setup does not overwrite an existing installation, and this first alpha has no automatic upgrade or uninstall flow.

Never upload your ISO, extracted game files, saves, disk images or complete development folder in a bug report. The [reporting guide](docs/TROUBLESHOOTING.md#reporting-a-problem) lists the useful details.

## Development and provenance

Start with [development instructions](docs/DEVELOPMENT.md) and [provenance](docs/PROVENANCE.md). The pinned dependency is the [apexJCL macOS/Metal fork of XboxRecomp](https://github.com/apexJCL/xboxrecomp), based on work by sp00nz and contributors.

Prior research consulted BuffyNX. This project does not import its title-specific code, symbols, seeds or overrides. Game-specific adaptations come from the user's identified XBE and concordant MAP.

## License

Original project code is [MIT licensed](LICENSE). Third-party files retain their own licenses, including the runtime's xemu-derived LGPL components. See [third-party notices](THIRD_PARTY_NOTICES.md). The game's code, data, trademarks and artwork are not licensed by this project. This is an unofficial project and is not affiliated with the original rights holders.
