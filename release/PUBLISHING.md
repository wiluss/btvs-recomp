# Preparing and publishing a prerelease

This file is for maintainers. Building the kit does not stage Git changes, create a tag, upload an artifact or publish a release.

## Build and audit

```sh
python3 tools/source_release.py --output artifacts/release-beta1/dist
python3 tools/source_release.py --audit artifacts/release-beta1/dist/btvs-recomp-v0.2.0-beta.1-source.zip
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
gh release create v0.2.0-beta.1 \
  --repo OWNER/REPOSITORY --verify-tag --draft --prerelease \
  --title 'btvs-recomp 0.2.0-beta.1' \
  --notes-file release/NOTES.md \
  artifacts/release-beta1/dist/btvs-recomp-v0.2.0-beta.1-source.zip \
  artifacts/release-beta1/dist/SHA256SUMS
```

Replace the repository explicitly. Do not run this example against an inferred account. Review the draft and its attachments before making it public. This preparation does not itself authorize publishing a release.

## Compatibility bridge for existing alphas

Prepare and publish **0.1.1 — Updater bridge** as a separate source prerelease
before 0.2.0-beta.1. Old alpha updaters only recognize alpha/plain version numbers;
they will select 0.1.1, then the updated helper can select the beta on the next
check. The beta also supports direct upgrading through its update command.

The bridge must start from the **actual verified published alpha.9 source kit**,
not a renamed beta tree. Keep all game/runtime build inputs byte-identical to
alpha.9. Replace only the launcher-compatible files: `tools/update_launcher.py`,
`tools/source_release.py`, `src/launcher/UpdatesView.swift`,
`src/launcher/Localizations.json`, `tests/test_launcher_update.py` and
`Update btvs-recomp.command`. Update VERSION/release file-list version to 0.1.1,
and give the bridge its own README and release notes explaining the second step.
Build/audit its ZIP with its own manifest. Validate it using the original alpha
helper, then verify game/saves/HD were retained before the beta upgrade.

Prepared maintainer outputs are in `artifacts/release-beta1/bridge-dist/` and
`artifacts/release-beta1/dist/`, with separate SHA256SUMS. The bridge's reviewed
public tree is the extracted bridge kit, with its own matching source commit/tag.
The beta has a separate reviewed tree/commit/tag. Never point both tags at one
tree or attach the beta kit as the bridge. For example, after reviewing and
pushing the matching bridge tag, create its draft:

```sh
gh release create v0.1.1 --repo OWNER/REPOSITORY --verify-tag --draft --prerelease \
  --title 'btvs-recomp 0.1.1 — Updater bridge' \
  --notes-file artifacts/release-beta1/bridge-kit-final/release/NOTES.md \
  artifacts/release-beta1/bridge-dist/btvs-recomp-v0.1.1-source.zip \
  artifacts/release-beta1/bridge-dist/SHA256SUMS
```

Review/publish the bridge first, then the beta. The existing HD v1 download remains
compatible and need not be uploaded again. Preparing either ZIP does not authorize
creating tags or publishing releases.

## Optional prebuilt HD attachment

The user explicitly selected this separate add-on. Keep all game-derived bytes out of Git and the source ZIP. `tools/hd_pack.py build` reads only the nine approved prebuilt outputs, validates the campaign/text profiles and writes the HD ZIP plus `HD-SHA256SUMS` under artifacts/hd-release/dist. It also writes the source-controlled `config/hd-pack.json` with archive/member hashes and recipe identities. Build the HD attachment before the source ZIP so the catalog is included.

```sh
python3 tools/hd_pack.py build
python3 tools/hd_pack.py audit artifacts/hd-release/dist/btvs-recomp-HD-v1.zip
python3 tools/source_release.py --output artifacts/release-beta1/dist
```

Any change to the approved outputs requires a new add-on ID and matching source catalog; do not silently replace a released archive. The ZIP includes notices and no game executable, disc image, editable master, model, save or third-party font file. Its game-derived graphics are not relicensed under MIT. Test installation into an isolated supported game setup, verify every installed file and launch with the installed profiles. Keep the repository/release private and in draft until publication is explicitly requested.

## Project-branding exception

The source kit now contains the user-requested monochrome project wordmark, an embedded-image SVG presentation and original navigation/status SVGs under docs/branding. `tools/source_release.py` permits only those exact image paths, checks PNG structure/CRC and rejects active or external SVG content. All other game/HD images and fonts remain forbidden. Keep the source kit's logo, its README presentation and the launcher bundle in sync. The user-provided reference and rejected drafts are local working inputs, not release files.

## Documentation-screenshot exception

Only the seven exact PNG paths listed in docs/screenshots/README.md may ship as documentation captures. Each is limited to 8 MiB and checked for valid PNG structure/CRC; the full archive remains capped at 64 MiB uncompressed. Keep them unchanged from the user-supplied originals. No other screenshot, texture or game image is implicitly authorized. Game imagery in these captures is outside the MIT code license.
