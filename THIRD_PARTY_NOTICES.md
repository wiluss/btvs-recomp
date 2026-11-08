# Third-party notices and license scope

The root MIT license applies to this project's original code. It does not relicense third-party files or grant rights to Buffy game code, assets, fonts, saves, trademarks or artwork.

## Generic XboxRecomp toolkit

The build fetches the [apexJCL fork of XboxRecomp](https://github.com/apexJCL/xboxrecomp) at commit `5d2e6fedfe12e950e2a9285c34257c01647c5bb2`. Its original MIT license credits sp00nz. Some components retain different licenses, including xemu-derived APU/NV2A code under LGPL-2.1-or-later.

Copies of the pin's [MIT license](release/licenses/XboxRecomp-MIT.txt), [complete NOTICE](release/licenses/XboxRecomp-NOTICE.txt) and license texts are included under `release/licenses/`. The fetched runtime retains its headers, LICENSE, NOTICE and LICENSES directory. Treat the upstream NOTICE as the file-level attribution reference. Runtime patches preserve the terms of the files they modify; in particular, changes to LGPL files are not relicensed under the project's MIT license.

The six patches are shipped as source, separately from the pinned upstream source. The [patch guide](patches/xboxrecomp/README.md) describes them. No compiled runtime or recompiled game binary is attached to this source release.

## Build dependencies

The player installs Python, Apple's tools, Homebrew libraries and Python packages separately. This archive does not bundle those executables or libraries. Their licenses remain with their distributions. Dependency references and versions are recorded in `dependencies.lock.json` and the requirements files.

## Optional local content

Private development HD fonts, textures, outline masters and model weights are not included. Their presence on the development machine does not make them release assets. Optional local preparation tools do not grant redistribution rights to their inputs or outputs.

The launcher icon is an original code-drawn monogram, moon and stake. Its source is `tools/launcher_icon.swift`. It contains no extracted logo, game image, reconstructed game font or generated game asset.

## Reference texts

- [MIT license, Open Source Initiative](https://opensource.org/license/mit)
- [LGPL 2.1, Free Software Foundation](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)

The bundled notice and license copies are preserved from the pinned toolkit. Future releases that change dependencies or distribute binaries need their own distribution review.
