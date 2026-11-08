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

The launcher icon is an original code-drawn B monogram, moon and stake. It is not an extracted or traced game logo. The release bundles no game-derived launcher art or reconstructed game font.

Development experiments used local game textures, privately reconstructed font outlines and separately downloaded general-purpose upscaling tools/models. Their assets, masters, weights and resulting packs are not in this source release. Optional metadata and preparation tools do not make those private results distributable or reproducible through the public alpha setup.

## AI assistance and validation

Local Qwen was used for bounded proposals, translation and review, with human/hosted review and independent tests. Incomplete or incorrect proposals were not treated as authority. No AI model is part of the runtime or installation requirements.

Detailed private development histories, captures, generated snippets and long traces remain local. This public summary records the provenance of included source and adaptations; it does not distribute those inputs or assert full campaign validation.
