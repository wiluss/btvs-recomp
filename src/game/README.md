# Buffy integration

The user's XBE C is generated under `generated/recomp/gen/` and linked to the generic runtime by the root CMake. The WBINVD instruction extension lives in `tools/recomp_driver.py`, with proof and test in `docs/BRINGUP.md`.

Add here future wrappers and patches from our analysis, with the address linked to the XBE hash, the calling convention, and a test. Regenerated files remain in `generated/`.

Defensive initialization at site `LoadVariables` is carried by the generator
in `tools/loadvars_fix.py`, enabled by `tools/recomp_driver.py` after control
of the XBE SHA-256. This is not a function replacement in this folder.
Contract, regression and limits: `docs/BRINGUP.md` and `docs/PORT-COMPARISON.md`.

The factory `sub_0027C200` has a table of 535 internal arms. The adapter
`tools/factory_switch_fix.py`, enabled under the same XBE hash control,
relieves for this single table the limit of the two generator readers.
The arms remain in their function; no function seed is added.

The outer edges of the bands from `ILetterBox::PostRender` are adapted
by `tools/letterbox_fix.py`, under the same XBE hash control. The test
`tests/test_letterbox_fix.py` compiles the real preparation blocks of the
arguments and verifies the only allowed stores. No global change
of projection or permanent patch in the generated C.

The native stock-outfit selector uses `outfits.c` and byte-checked generator
prefixes from `tools/native_outfits_fix.py`, bound to the supported XBE. Protocol
2 includes Main/Pause navigation, previews, resource-completion preloading,
render-only cosmetic substitution and actor cleanup. Guest calls preserve all TLS
CPU/FP/SIMD state and check their stack contract. Gameplay actor, CharState,
collision and script pointers are retained; native numeric bone snapshots and
current light IDs drive the cosmetic mesh at draw time. Use the original animated
model’s render-interpolated first-part world matrix, not its actor physics
transform; those positions differ between simulation ticks. Skeleton names, parents,
counts, snapshot owners and buffers are checked before drawing.

Bone snapshots do not carry facial mesh/phoneme channels. During cutscenes return
the original mesh from the render hook, letting its full native render/face path
run. Query the verified retail `TGO::Cine_IsCutsceneRunning` (0x943E0, cdecl,
no arguments) through the CPU-preserving helper; do not modify or clear the saved
choice. The separately owned cosmetic resumes on the next gameplay draw.

`tools/outfit_resources.py` derives private menus and all-five-outfit level packs;
`tools/outfit_install.py` publishes them transactionally. Keep private namespaces
in the same directory order across menu and level packs. Append cosmetic loads
at the end of original level payloads; preload them at native resource completion.
Short menu animation tables follow the cosmetic loads and any missing menu idle
animations. The menu callback persists only the selection, using exact trusted
worker argv with the existing guest CPU gate released while waiting. Packs remain
unchanged during play and are reused across choices. The generator-emitted marker
prevents older binaries from exposing an unsupported Pause screen.

No vendor runtime change is needed for original outfits. Adversarial ASan/UBSan
fixtures cover ABI preservation, malformed bones/buffers, native navigation,
cancel/resume, ownership and repeated actor lifetimes. Synthetic pack/cache tests
cover order, source preservation, reuse and rollback. Native evidence and limits:
BRINGUP.md; player behavior: MODS.md. The launcher’s Outfit selector switch
gates preparation and loading; disabling it keeps the stock menus. Custom XRTP/F8 overlays remain separate.
