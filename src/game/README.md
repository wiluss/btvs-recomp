# Buffy Integration to be developed

The user's XBE C is generated under `generated/recomp/gen/` and linked to the generic runtime by the root CMake. No Buffy function override is added here yet. The WBINVD instruction extension lives in `tools/recomp_driver.py`, with proof and test in `docs/BRINGUP.md`.

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
