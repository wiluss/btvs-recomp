# Provenance

## Independent title integration

This project targets Buffy the Vampire Slayer (2002, original Xbox). Prior research consulted BuffyNX; this is not represented as work without prior knowledge. No BuffyNX-specific code, symbol table, seed list, override or title configuration is imported.

The title manifest, MAP conversion and address-dependent generator adapters come from the user's identified XBE and concordant `final.map`, now verified directly in that user's USA ISO. These inputs are not distributed. The project retains build recipes and hashes; extracted data and generated game sources remain local.

## Generic toolkit

The dependency is the [apexJCL macOS/Metal fork of XboxRecomp](https://github.com/apexJCL/xboxrecomp) at `5d2e6fedfe12e950e2a9285c34257c01647c5bb2`, based on sp00nz and contributors' work. The pin, bootstrap and patches are explicit. The dependency's file-level headers, LICENSE, NOTICE and LICENSES directory are preserved.

The generic toolkit includes xemu-derived components under LGPL-2.1-or-later, alongside MIT and other components. See [the bundled notices](../THIRD_PARTY_NOTICES.md) and their full license copies. Root MIT terms cover original project code, not every dependency file.

Our generic screen-w compatibility rule was informed by reading xemu's programmable vertex epilogue at revision `25e1ee2fd59a451f2ab57e825b4f8a5414220c8b`. No xemu function body was copied into the helper. The rule only bounds signed infinite output w; it is not the complete xemu clamp. Other port research informed diagnostics but supplied no title-specific Buffy implementation.

## Local setup and host code

ISO import reuses the pinned generic XDVDFS reader for partition discovery, with strict local directory validation and exclusive publication. The blank partition-table layout comes from the generic runtime's `xbox_build_partition_table`; a test compiles that function and compares its bytes to the local generator.

Controller remapping uses public generic input APIs, preserving keyboard merge, analog pressures and packet numbering. The six runtime patches are separately documented; permanent title fixes are applied by generator adapters with XBE/hash checks. No private launch-page capture is needed for the normal menu setup.

## Artwork and HD content

The launcher icon is an original code-drawn B monogram, moon and stake. It is not an extracted or traced game logo. The separate btvs-recomp wordmark is an explicit user-requested adaptation of the original game's title treatment, generated with the user-supplied monochrome logo as a reference. The selected PNG is included in the README and launcher bundle; the original reference is not in Git. The README's SVG buttons/status strip are original project graphics. This narrow branding exception does not include gameplay textures or reconstructed game fonts in the source kit.

HD preparation used local game textures, manually reconstructed font outlines and separately downloaded general-purpose upscaling tools/models. The optional HD attachment contains selected prebuilt campaign/HUD/text packs, the reconstructed decorative font output and prepared launcher images. It does not contain editable masters, third-party font files, upscaler executables or model weights. This preserves manual refinements rather than claiming they can be regenerated from the ISO alone. Game-derived outputs and title-inspired branding retain their underlying rights; the MIT code license does not grant those rights or establish rights-holder authorization. Gameplay textures and reconstructed fonts remain outside the source ZIP and launcher bundle.

## AI assistance and validation

Local Qwen was used for bounded proposals, translation and review, with human/hosted review and independent tests. Incomplete or incorrect proposals were not treated as authority. No AI model is part of the runtime or installation requirements.

Detailed private development histories, captures, generated snippets and long traces remain local. This public summary records the provenance of included source and adaptations; it does not distribute those inputs or assert full campaign validation.

The user subsequently requested the original game's violet moon behind the selected wordmark. The built-in image editor isolated the moon and reconstructed its obscured portions. The approved moon layer is included under docs/branding, while the wordmark PNG remains unchanged. SVG and SwiftUI compose the two without redrawing the lettering.

The silver-grey raised-letter treatment is an original SVG/SwiftUI presentation effect applied to the existing lettering mask. It does not regenerate either approved PNG or alter the game renderer.

The four README screenshots were supplied by the project owner and explicitly selected on November 9, 2026. They are copied unchanged under docs/screenshots; see that folder's README for scope and rights. They show actual gameplay with optional HD content, not generated scenes or benchmark evidence. Codex and local Qwen assisted development and documentation; AI tools also assisted branding and HD preparation, alongside manual refinements. AI is not required by the player.
