# Generic runtime patches

Per-patch validation notes below are historical. See `docs/BRINGUP.md` for the current menu, save/load and gameplay validation scope.

Immutable base: XboxRecomp `5d2e6fedfe12e950e2a9285c34257c01647c5bb2`. Local submodule changes are intentional and described by the patches below; its gitlink does not change. Do not mix additional modifications into these diffs.

## 0001 — Infinite w in CPU/Metal epilogue

Reviewed local Qwen proposal: `artifacts/qwen-screen-w-proposal.json`. RCP/RCC and guest data remain unchanged. The CPU and MSL emitter bound only signed infinities to ±2^64 before host clipping/conversion. Zeros continue to become 1; finite values and NaNs are preserved. This is a targeted compatibility fix, not a full xemu clamp implementation nor NV2A hardware validation. Windows HLSL remains outside this macOS patch.

**Explicit application**, once after installing the pinned submodule:

```sh
git -C vendor/xboxrecomp apply --check ../../patches/xboxrecomp/0001-screen-w-infinity.patch
git -C vendor/xboxrecomp apply ../../patches/xboxrecomp/0001-screen-w-infinity.patch
make test
make host-probe
make runtime
make game-build
```

`make runtime-patch-check` verifies that the patch is already applied before relevant tests and compilations, without modifying any file. To remove it, use `git -C vendor/xboxrecomp apply --reverse ../../patches/xboxrecomp/0001-screen-w-infinity.patch` after preserving any other work.

Synthetic regression of the helper and clip coordinates: `tests/screen_w.c`, launched by `tests/test_screen_w.py`. Source references and actual validation are logged in `docs/BRINGUP.md` and `docs/PROVENANCE.md`. Ordinary tests require neither the game nor Qwen.

Actual validation: 27 project tests (59 C assertions), ARM64 probe, and 1,200 successful Metal shader compilations. CPU/Metal captures of the title and visible intro videos, extended trial up to the attract video; interactive menu and engine gameplay remain unvalidated. The 400 MSL SCREEN_SPACE goldens are renewed in this patch; the other 800 cases remain identical.

## 0002 — Audio DMA from an XBE image buffer

Unchanged base, separate patch: `0002-apu-image-sample-dma.patch`. Calls
`MmGetPhysicalAddress` on an image page are recorded in a map
reserved for VP sample reads. Voice, SGE, and notification tables retain their resolver; existing heap rules remain identical.
PCM, ADPCM paths, and ring probe use the sample resolver.
No Buffy-specific addresses appear in the runtime patch.

The Buffy capture shows a null DSOUND buffer in the image, but replaced during
DMA by bytes from a contiguous allocation of the same physical number.
This is a local adaptation of the pinned runtime, not a global sync with a fork. It does not resolve the general ambiguity of two live **sample** buffers having the same physical number: an explicitly named image page then takes priority for samples.

Apply explicitly after 0001:

```sh
git -C vendor/xboxrecomp apply --check ../../patches/xboxrecomp/0002-apu-image-sample-dma.patch
git -C vendor/xboxrecomp apply ../../patches/xboxrecomp/0002-apu-image-sample-dma.patch
make test
make host-probe
make game-build
```

Regressions: `tests/test_apu_image.py` compiles the extracted real functions
with two distinct storages; `tests/apu_image.c` verifies image/window, page
unnamed, heap, limits, and high RAM. The patch also extends the integrated test
`vendor/xboxrecomp/tests/apu_phys` linked to the full runtime, with synthetic XBE:

```sh
cmake -S vendor/xboxrecomp/tests/apu_phys -B build/audio-phys -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_PREFIX_PATH=/opt/homebrew -DOPENSSL_ROOT_DIR=/opt/homebrew/opt/openssl@3
cmake --build build/audio-phys --target apu_phys_test --parallel 4
ctest --test-dir build/audio-phys --output-on-failure
```

Provenance and licenses: existing pin resolution, local adaptation after
Buffy proofs and rejected Qwen proposals. Comparison with takedawn translation tracking is documented in `docs/PROVENANCE.md`; its global owner code is not reused. File modification notices remain preserved: notably LGPL-2.0-or-later for the APU extracted from xemu, MIT for parts of the toolkit covered by its general license. See `vendor/xboxrecomp/LICENSE`
and `vendor/xboxrecomp/LICENSES/`.

## 0003 — convert only referenced vertices for Metal

Separate patch `0003-metal-compact-vertices.patch`, same toolkit pin.
After expanding primitives into lists, a draw-local table remaps
indices and lists used vertices. If at least 25% of the range is unused, only referenced vertices are converted to float4. Guest buffers are re-read each draw: no inter-draw content cache.

The path preserves index order, topology, and the values of each
shader input. The Metal ID is used solely to read the converted buffer; it is not exposed to the Xbox program. Hor+ scans use the full range: compaction is therefore disabled if the target has padding. Small draws (range ≤64), programs without inputs, and dense ranges retain the existing path. Validation failures leave indices unchanged; maximum size 65536 and ID 65535 are supported. Scratch space is per-render-thread, like existing index buffers.

The existing option `RECOMP_TRACE=metal_prof` adds counters per 300 flips:
range, distinct/used vertices, actually converted vertices, formats, conversion time, remapping time, and counting cost. Without this trace, counters and their clocks do not run. Remapping is active.

Explicit application after the two previous patches:

```sh
git -C vendor/xboxrecomp apply --check ../../patches/xboxrecomp/0003-metal-compact-vertices.patch
git -C vendor/xboxrecomp apply ../../patches/xboxrecomp/0003-metal-compact-vertices.patch
make test
make host-probe
make game-build
```

Regressions without games: `tests/test_vertex_metrics.py`,
`tests/test_vertex_compact.py`, `tests/vertex_compact.c`. The test reuses
the actual expansion and decoding of the toolkit for ten topologies, six
formats, and four component sizes. Remapped shader inputs are compared bit-by-bit, including NaN and signed zero. Bounds, atomic fallback, repeated indices, sparse ranges, and 65536 vertex cases are tested.
8,259 C checks also pass under AddressSanitizer and UndefinedBehaviorSanitizer.

Qwen local algorithmic proposal reviewed; bounded implementation after incomplete/expired proposals, details and measurements in BRINGUP and PROVENANCE.
Local generic code, no BuffyNX-specific borrowing. Toolkit notices and licenses remain preserved; no global update.

## 0004 — optional Metal HUD anchoring

Separate patch `0004-metal-hud-anchor.patch`, after 0001–0003, same pin.
The existing Hor+ layer retains the scene and its placement rules. An
optional callback receives the **already calculated** footprint of texels actually uploaded, the program, format, dimensions, and X/Y bounds of the batch. Without callback, without padding, outside 2D or outside CENTRE placement: no offset. The callback can choose a displacement from left/right padding. Only the host constants' X offset and the two X scissor bounds change. Texture coordinates, guest data, and 3D scene remain intact. Scissor is bounded with signed 64-bit integers; drawings that become empty are ignored. Recording is atomic; the callback must remain valid.

The title-specific choice lives in `src/host/widescreen.c`, **outside the runtime**.
It is limited to health quads identified on our XBE, and notably excludes their reuse in tip panels. `BUFFY_HUD=edges` activates this
choice via the launcher; `safe` or an absent value retains native placement.
The existing trace `RECOMP_TRACE=aspect` also displays the texture cache hash, without a second read or second hash calculation.

```sh
git -C vendor/xboxrecomp apply --check ../../patches/xboxrecomp/0004-metal-hud-anchor.patch
git -C vendor/xboxrecomp apply ../../patches/xboxrecomp/0004-metal-hud-anchor.patch
make test
make host-probe
make game-build
```

Regressions: `tests/hud_anchor.c`, `tests/hud_selector.c`,
`tests/test_hud_anchor.py`, and preferences/CLI in `test_graphics_settings.py`.

Real helpers compiled under ASan/UBSan; translation, unchanged width, clipping
1×–4×, absent callback, fake identifiers, shared panel and NaN tested.
Local code on MIT pin generic interfaces; notices preserved.
Qwen proposals reviewed and visual/performance limits in BRINGUP/PROVENANCE.

## 0005 — Metal UHD output

Patch `0005-metal-uhd.patch` follows 0004. It adds
`present.surface=uhd`, a fixed Metal drawable of 3840×2160. The launcher
chooses a 5× rendering, then the presentation pass applies the chosen filter. HUD anchoring also accepts the 5× factor. Previous presentation options retain their sizing rules.

```sh
git -C vendor/xboxrecomp apply --check ../../patches/xboxrecomp/0005-metal-uhd.patch
git -C vendor/xboxrecomp apply ../../patches/xboxrecomp/0005-metal-uhd.patch
make test
make host-probe
make game-build
```

The anchoring test verifies translation and scissor up to 5×.
`make runtime-patch-check` reverses 0005 and verifies 0004 on a copy of the
affected files, since both patches touch HUD factor control.

## 0006 — relaunch page transmission

`0006-launch-page-handoff.patch` adds two optional host-side paths.
The bridge exports 4096 bytes of the guest page on a fast restart request and can import them before XBE entry. It publishes the imported page into the exported LaunchDataPage after allocating it in the contiguous arena. The launcher verifies the title and executable path before using the page.

```sh
git -C vendor/xboxrecomp apply --check ../../patches/xboxrecomp/0006-launch-page-handoff.patch
git -C vendor/xboxrecomp apply ../../patches/xboxrecomp/0006-launch-page-handoff.patch
make game-build
```

Tests verify rejection of invalid pages and HDD reuse between two processes. The native test covers Arena 1 selection.
