# Preparing and publishing the alpha

This file is for maintainers. Building the kit does not stage Git changes, create a tag, upload an artifact or publish a release.

## Build and audit

```sh
python3 tools/source_release.py
python3 tools/source_release.py --audit artifacts/release-alpha/dist/Buffy-macOS-v0.1.0-alpha.1-source.zip
```

The output directory contains the source ZIP and `SHA256SUMS`. Inside the ZIP, `RELEASE_MANIFEST.json` lists every member and its digest. The explicit input list is `release/files.json`. It includes selected original source and English public documentation, not the development folder.

Public documentation overlays live under `release/public/`; their exported paths replace local research histories. Export normalizes `release/files.json` to the canonical paths actually in the kit. A kit rebuilt from an extracted kit must produce the same bytes on the tested Python/zlib toolchain.

The private overlay folder is not included in the kit. When working from an exported kit, its canonical documentation files are the source for the next export.

The audit rejects forbidden directories, asset/binary/save extensions, symbolic sources, unknown member types, oversized content, private development-home paths and common credential patterns. It verifies all archive members against the manifest. These checks do not establish authorship, authenticity or universal license compliance; review the selected source and notices too.

## Validate the exact ZIP

Extract into a fresh directory outside the development inputs. Confirm no game/private/generated/build outputs are present. Fetch the dependency with the bootstrap helper, apply the shipped patches, run the asset-free tests, build the launcher and use the supported local ISO setup. Keep all resulting game content and traces local. Verify first save and Load Game without importing a development profile.

Read the known issues and scope in `docs/ALPHA.md`. The archive must contain LICENSE and third-party notices. Never attach a built game, private HD content, a save profile or the isolated test installation.

## Prepare GitHub

The current development checkout has unrelated existing changes and private ignored data. Export and review the source kit as the public tree; do not blindly add or archive the entire checkout. No Git remote is assumed.

Once the intended repository and public source commit/tag are reviewed, create a **draft prerelease** with the source ZIP and checksum only. For example, from a reviewed public checkout with the tag already pushed:

```sh
gh release create v0.1.0-alpha.1 \
  --repo OWNER/REPOSITORY --verify-tag --draft --prerelease \
  --title 'Buffy macOS 0.1.0-alpha.1' \
  --notes-file release/NOTES.md \
  artifacts/release-alpha/dist/Buffy-macOS-v0.1.0-alpha.1-source.zip \
  artifacts/release-alpha/dist/SHA256SUMS
```

Replace the repository explicitly. Do not run this example against an inferred account. Review the draft and its attachments before making it public. This preparation does not itself authorize publishing a release.
