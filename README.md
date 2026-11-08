<div align="center">

<img src="docs/branding/logo-display.svg" alt="btvs-recomp" width="520">

**Buffy the Vampire Slayer · Original Xbox, 2002 · Apple Silicon**

An independent recompilation that brings Buffy to macOS with native ARM64 and Metal rendering.
Bring your own supported USA ISO. The game is built locally on your Mac.

<img src="docs/branding/status.svg" alt="Source alpha · ARM64 + Metal · Optional HD" width="596">

<p>
<a href="https://github.com/wiluss/btvs-recomp/releases"><img src="docs/branding/download.svg" alt="Download alpha" width="190"></a>
<a href="docs/SETUP.md"><img src="docs/branding/setup.svg" alt="Installation" width="190"></a>
<a href="docs/HD-PACK.md"><img src="docs/branding/hd.svg" alt="HD add-on" width="190"></a>
<a href="https://github.com/wiluss/btvs-recomp/issues/new/choose"><img src="docs/branding/issues.svg" alt="Report a bug" width="190"></a>
</p>

**Source alpha `0.1.0-alpha.4`** · Unofficial fan project · No game download

</div>

## Sunnydale, on your Mac

| Native rendering | Optional HD | Your controls |
| :--- | :--- | :--- |
| ARM64 + Metal, resolution scaling, 4K output and experimental 16:9. | Prepared campaign textures, HUD and reconstructed text, including manual refinements. | Keyboard and controller support, remapping, AZERTY/QWERTY presets. |

A five-language launcher follows a supported system language until you choose one. Persistent saves, fullscreen, VSync, an FPS overlay and optional arena access are included.

## Start playing

**1. Get the source kit.** Download the attached `btvs-recomp-v0.1.0-alpha.4-source.zip` and `SHA256SUMS` from [Releases](https://github.com/wiluss/btvs-recomp/releases). Verify the checksum and extract the folder.

**2. Build the launcher.** You need an Apple Silicon Mac, Apple's Command Line Tools and the listed Homebrew packages. Follow the [installation guide](docs/SETUP.md), or expand the commands below.

<details>
<summary><strong>Build commands</strong></summary>

From a terminal in the extracted source folder:

```sh
# Skip this if Apple's Command Line Tools are already installed:
xcode-select --install

# With Homebrew already installed in /opt/homebrew:
HOMEBREW_NO_AUTO_UPDATE=1 brew install python@3.12 cmake ninja pkgconf sdl3 libepoxy openssl@3

python3 tools/bootstrap_runtime.py
make launcher
open "build/btvs-recomp.app"
```

Keep the source folder intact: this alpha's launcher runs from it. No AI model or LM Studio installation is required.

</details>

**3. Supply your ISO.** Choose **Set up from an ISO…** in the launcher and select your own compatible USA image. Setup verifies `Default.xbe` and `final.map`, imports the files and compiles the game locally. It downloads development dependencies when needed, never the original game.

**4. Play.** Start from the main menu. After saving, choose **Load Game** to continue your adventure.

### Add the HD treatment

Download the optional **`btvs-recomp-HD-v1.zip`** (about 676 MB), then choose **Packs & skins → Install the HD pack…**. The prepared add-on preserves our manual refinements; it needs no AI tools on your Mac. Textures and text can be switched off independently. [HD installation and scope →](docs/HD-PACK.md)

The source kit contains the project logo and README graphics, with gameplay graphics supplied separately by your ISO and the optional HD add-on.

## Before you enter the Hellmouth

- **Mac:** Apple Silicon, macOS 13 or later targeted. Tested on one Mac running macOS 27.2; other models and earlier OS versions still need validation.
- **Game:** your own supported USA ISO with the exact XBE/MAP hashes checked by setup. Other editions and modified executables are unsupported.
- **Space:** at least **35 GiB free** before game setup; keep space available for builds and Xbox disk images. The optional HD add-on needs additional space.

**This is an alpha.** Audio can stutter, an intermittent audio crash remains unresolved, and performance varies with effects and resolution. The full campaign and long sessions have not been validated. Stock controller mapping was tested physically; custom mappings still need physical testing. See [known issues](docs/TROUBLESHOOTING.md).

The isolated ISO setup reached the menu, created the first save and loaded it into the first level's opening cutscene. Those checks used dummy audio and scripted controller input on the same Mac; they do not establish audio or cross-machine stability. Read the [validation summary](docs/BRINGUP.md).

## Keep your progress

Back up the **whole `private/profile/` folder**, including title metadata and disk files. Do not delete it when updating. Setup preserves an existing installation; this alpha has no automatic upgrade or uninstall flow.

For help, read the [user guide](docs/GRAPHICS.md) and [reporting instructions](docs/TROUBLESHOOTING.md#reporting-a-problem). Never upload your ISO, game files, saves, disk images or complete development folder.

## Built independently

Based on the pinned generic [XboxRecomp macOS/Metal fork](https://github.com/apexJCL/xboxrecomp), with work by sp00nz and contributors. Prior research consulted BuffyNX; this project imports none of its title-specific code, symbols, seeds or overrides. Game-specific adaptations come from the identified user-supplied XBE and concordant MAP.

[Development](docs/DEVELOPMENT.md) · [Provenance](docs/PROVENANCE.md) · [Roadmap](docs/ROADMAP.md) · [Release notes](release/NOTES.md)

Original project code is [MIT licensed](LICENSE); third-party components keep their own licenses. The game-derived HD add-on and title-inspired branding are not relicensed under MIT. Read the [notices](THIRD_PARTY_NOTICES.md). This project is not affiliated with the original rights holders.
