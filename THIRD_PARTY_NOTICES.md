# Third-party notices and license scope

The root MIT license applies to this project's original code. It does not relicense third-party files or grant rights to Buffy game code, assets, fonts, saves, trademarks or artwork.

## Generic XboxRecomp toolkit

The build fetches the [apexJCL fork of XboxRecomp](https://github.com/apexJCL/xboxrecomp) at commit `5d2e6fedfe12e950e2a9285c34257c01647c5bb2`. Its original MIT license credits sp00nz. Some components retain different licenses, including xemu-derived APU/NV2A code under LGPL-2.1-or-later.

Copies of the pin's [MIT license](release/licenses/XboxRecomp-MIT.txt), [complete NOTICE](release/licenses/XboxRecomp-NOTICE.txt) and license texts are included under `release/licenses/`. The fetched runtime retains its headers, LICENSE, NOTICE and LICENSES directory. Treat the upstream NOTICE as the file-level attribution reference. Runtime patches preserve the terms of the files they modify; in particular, changes to LGPL files are not relicensed under the project's MIT license.

The six patches are shipped as source, separately from the pinned upstream source. The [patch guide](patches/xboxrecomp/README.md) describes them. No compiled runtime or recompiled game binary is attached to this source release.

## Build dependencies

The player installs Python, Apple's tools, Homebrew libraries and Python packages separately. This archive does not bundle those executables or libraries. Their licenses remain with their distributions. Dependency references and versions are recorded in `dependencies.lock.json` and the requirements files.

## Optional local content

The source kit contains the user-requested title-inspired project logo and original README graphics. Gameplay graphics are separate. The optional HD add-on contains prebuilt campaign textures, HUD, reconstructed font/text outputs and launcher artwork. It preserves manual work from this project and is not automatically recreated from the ISO. Editable outline masters, model weights, third-party font files and upscaler executables are not included. General-purpose Real-ESRGAN tools were used during preparation; no claim is made that their software license grants rights over the game-derived outputs. The original game's artwork and trademarks retain their respective rights; the project's MIT license does not cover those rights or establish permission to distribute them. This unofficial add-on is not represented as endorsed by the rights holders.

The launcher icon is an original code-drawn monogram, moon and stake. Its source is `tools/launcher_icon.swift`. It contains no extracted logo, game image, reconstructed game font or generated game asset.

The separate `docs/branding/logo.png` wordmark is a user-requested lettering adaptation inspired by the game's title artwork, produced with an image-generation tool using the user-supplied monochrome original logo as a reference. It is included in the README and launcher bundle. It is distinct from the code-drawn app icon and is not presented as independently licensed original Buffy artwork. The project's MIT code license does not grant rights to the underlying title artwork or trademarks. The SVG navigation buttons and status strip are original project graphics; see `docs/branding/README.md`.

## Reference texts

- [MIT license, Open Source Initiative](https://opensource.org/license/mit)
- [LGPL 2.1, Free Software Foundation](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)

The bundled notice and license copies are preserved from the pinned toolkit. Future releases that change dependencies or distribute binaries need their own distribution review.

The selected `docs/branding/moon.png` branding layer was prepared from the original game logo's violet moon with lettering removed and occluded areas reconstructed by the built-in image editor. Its use behind the unchanged wordmark was explicitly requested by the user. This layer belongs to the same narrow branding exception; it does not extend MIT to the underlying game artwork.

## Documentation screenshots

The four images listed in [docs/screenshots/README.md](docs/screenshots/README.md) are unedited captures supplied and selected by the project owner for the README. They depict the launcher and actual gameplay with optional HD content. Underlying game artwork and trademarks are not relicensed under MIT. This narrowly selected documentation gallery does not include installable textures or playable game content and does not imply rights-holder endorsement.
