# Preparing and publishing the alpha

This file is for maintainers. Building the kit does not stage Git changes, create a tag, upload an artifact or publish a release.

## Build and audit

```sh
python3 tools/source_release.py
python3 tools/source_release.py --audit artifacts/release-alpha/dist/btvs-recomp-v0.1.0-alpha.6-source.zip
```

The output directory contains the source ZIP and `SHA256SUMS`. Inside the ZIP, `RELEASE_MANIFEST.json` lists every member and its digest. The explicit input list is `release/files.json`. It includes selected original source and English public documentation, not the development folder.

Public documentation overlays live under `release/public/`; their exported paths replace local research histories. Export normalizes `release/files.json` to the canonical paths actually in the kit. A kit rebuilt from an extracted kit must produce the same bytes on the tested Python/zlib toolchain.

The private overlay folder is not included in the kit. When working from an exported kit, its canonical documentation files are the source for the next export.

The audit rejects forbidden directories, asset/binary/save extensions, symbolic sources, unknown member types, oversized content, private development-home paths and common credential patterns. It verifies all archive members against the manifest. These checks do not establish authorship, authenticity or universal license compliance; review the selected source and notices too.

## Validate the exact ZIP

Extract into a fresh directory outside the development inputs. Confirm no game/private/generated/build outputs are present. Fetch the dependency with the bootstrap helper, apply the shipped patches, run the asset-free tests, build the launcher and use the supported local ISO setup. Keep all resulting game content and traces local. Verify first save and Load Game without importing a development profile.

Read the known issues and scope in `docs/ALPHA.md`. The archive must contain LICENSE and third-party notices. Never attach a built game, editable HD masters, a save profile or the isolated test installation. The approved HD add-on is a separate audited attachment, never part of the source tree or source ZIP.

## Prepare GitHub

The current development checkout has unrelated existing changes and private ignored data. Export and review the source kit as the public tree; do not blindly add or archive the entire checkout. No Git remote is assumed.

Once the intended repository and public source commit/tag are reviewed, create a **draft prerelease** with the source ZIP/checksum and, when selected, the approved HD ZIP/checksum. For example, from a reviewed public checkout with the tag already pushed:

```sh
gh release create v0.1.0-alpha.6 \
  --repo OWNER/REPOSITORY --verify-tag --draft --prerelease \
  --title 'btvs-recomp 0.1.0-alpha.6' \
  --notes-file release/NOTES.md \
  artifacts/release-alpha/dist/btvs-recomp-v0.1.0-alpha.6-source.zip \
  artifacts/release-alpha/dist/SHA256SUMS \
  artifacts/hd-release/dist/btvs-recomp-HD-v1.zip \
  artifacts/hd-release/dist/HD-SHA256SUMS
```

Replace the repository explicitly. Do not run this example against an inferred account. Review the draft and its attachments before making it public. This preparation does not itself authorize publishing a release.

## Optional prebuilt HD attachment

The user explicitly selected this separate add-on. Keep all game-derived bytes out of Git and the source ZIP. `tools/hd_pack.py build` reads only the nine approved prebuilt outputs, validates the campaign/text profiles and writes the HD ZIP plus `HD-SHA256SUMS` under artifacts/hd-release/dist. It also writes the source-controlled `config/hd-pack.json` with archive/member hashes and recipe identities. Build the HD attachment before the source ZIP so the catalog is included.

```sh
python3 tools/hd_pack.py build
python3 tools/hd_pack.py audit artifacts/hd-release/dist/btvs-recomp-HD-v1.zip
python3 tools/source_release.py
```

Any change to the approved outputs requires a new add-on ID and matching source catalog; do not silently replace a released archive. The ZIP includes notices and no game executable, disc image, editable master, model, save or third-party font file. Its game-derived graphics are not relicensed under MIT. Test installation into an isolated supported game setup, verify every installed file and launch with the installed profiles. Keep the repository/release private and in draft until publication is explicitly requested.

## Project-branding exception

The source kit now contains the user-requested monochrome project wordmark, an embedded-image SVG presentation and original navigation/status SVGs under docs/branding. `tools/source_release.py` permits only those exact image paths, checks PNG structure/CRC and rejects active or external SVG content. All other game/HD images and fonts remain forbidden. Keep the source kit's logo, its README presentation and the launcher bundle in sync. The user-provided reference and rejected drafts are local working inputs, not release files.

## Documentation-screenshot exception

Only the four exact PNG paths listed in docs/screenshots/README.md may ship as documentation captures. Each is limited to 8 MiB and checked for valid PNG structure/CRC; the full archive remains capped at 64 MiB uncompressed. Keep them unchanged from the user-supplied originals. No other screenshot, texture or game image is implicitly authorized. Game imagery in these captures is outside the MIT code license.
