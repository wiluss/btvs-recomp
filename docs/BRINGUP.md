# Bring-up and validation summary

Long traces, private research, generated code and diagnostic captures are not
part of the source kit. Player instructions are in [SETUP.md](SETUP.md).

## Supported inputs and setup

The supplied USA Xbox game was identified against the exact XBE/MAP hashes in
`config/title.json`. The tested ISO contains both `Default.xbe` and `final.map`.
No BuffyNX-specific code, symbols, seeds or overrides are used.

An isolated source installation without prior private inputs, generated files,
build products or Python environment imported the ISO, generated the game and
compiled an ARM64 executable. With a blank diagnostic profile it reached the
main menu, created its first save, and loaded that save after restart into the
first level's opening cutscene. Those installation checks used dummy audio and
scripted controller input on the same Mac as development. They predate 0.2 and
do not constitute a fresh full-ISO beta installation or cross-Mac validation.

The project owner has validated real gameplay, original controller mapping and
the new native Pause outfit selector. The full campaign is not yet validated.

## 0.2 outfit checks

The regenerated native build was exercised on a cloned diagnostic HDD: Main and
Pause entries, animated 3D previews, Workout and Dark Slayer selection, immediate
Resume, Back/cancel, restoration of the level outfit and remembered choice after
cold launch. An explicit auxiliary teardown on the guest thread released the
wardrobe models, previews, animation locks and scratch allocation, followed by
movement/attack with the original player. This checks real cleanup calls, not an
automatic campaign level transition.

The gameplay actor mesh, animation state, collision and scripts keep their original
ownership. Cosmetic rendering receives native numeric bone snapshots and light
IDs. Mismatched skeletons or invalid buffers fall back to the original mesh.
Adversarial ASan/UBSan tests cover guest CPU/stack preservation, ownership, repeated
actor lifetimes, cancellation and cleanup. Synthetic resource tests check ordering,
source preservation, cache reuse and rollback.

The beta also removes redundant wardrobe guidance and adds the five-language
launcher switch. Tests check preference migration/defaults, Swift-to-Python launch
arguments, disabling preparation and stale inherited flags. No new physical
controller or full campaign test was performed for these final UI/settings edits.

## Discord

Fake local-server tests cover protocol framing, handshake, heartbeat, reconnect,
cleanup, missing clients and lifetime across game relaunches. A real desktop client
acknowledged Main menu, In game and the observed Spanish Mission, Canyon activity.
The shared public application name and official-logo CDN thumbnail were checked.
A complete live profile card was not inspected through the UI; artwork caching
and the display on other clients still need user feedback.

## Beta candidate checks

245 automated tests passed. ARM64 host probe and signed launcher compilation
passed. The source archive is built from an explicit allowlist and audited against
its internal manifest; only the approved branding and four documentation PNGs are
allowed as image files. No game executable, ISO, XBE/MAP, save, generated game code
or installable HD pack belongs in that archive.

Testing covers one development Mac on macOS 27.2. The launcher targets macOS 13+;
other hardware, earlier OS releases, full combat/campaign/cutscene compatibility,
automatic level transitions, new menu controller navigation and long sessions
remain open. Audio stutter and an intermittent audio crash remain unresolved.


## Automatic update validation

The actual published alpha.9 source ZIP was checksum-verified. Its original updater
installed the 0.1.1 launcher-only bridge, then the new helper upgraded an isolated
installation to 0.2 with real native regeneration, compilation and installation.
The test used the supported imported XBE/MAP and a prior native game build; it did
not reimport an ISO. Save/HD/preferences sentinel files stayed unchanged. The
installed native executable reached its real Metal main menu on a cloned diagnostic
HDD with the outfit selector disabled. Binary and launcher signatures verified
after their final moves. Dummy audio and scripted input were used.

The exact final bridge ZIP was separately accepted by the original alpha.9 helper.
Its extracted source passed 185 tests with 6 skips after installing the pinned
runtime prerequisites. The beta's 245 tests cover staged game build failure,
partial-install rollback, interrupted recovery, private data preservation, session
locks, concurrent binary changes, runtime patch additions/local edits, version
ordering and child-process cleanup. Live GitHub downloads of the unreleased bridge
and beta cannot be exercised before publication; checksum/download logic has
isolated coverage. Only one Mac was tested. No publication is implied by preparation.


## Stock-outfit movement jitter — November 15, 2026

The user observed Buffy shaking during movement while scenery stayed stable;
a fresh launch with the outfit selector disabled removed it. Native diagnostics
reproduced a mismatch: the cosmetic used the actor physics transform while the
original animated mesh used its already interpolated render transform. Across
4,000 samples the previous path differed by up to 6.155 world units; the corrected
path has zero source/cosmetic root-position error across 4,000 samples, with an
actual distinct Workout cosmetic confirmed in the native run. An initial base-class
guard that merely restored the default appearance was rejected before integration.

Use the checked TMeshAnimModelInstance first-part render matrix (12 numeric floats),
as stored by native UpdateMesh, rather than querying the actor physics transform.
Retain bone snapshots, light IDs, native ABI preservation and original actor/state
ownership. The synthetic regression deliberately separates physics and rendered
positions and checks full target matrices across frames, malformed data fallback,
CPU state and cleanup. It fails on the previous source and passes with the fix.

Permanent source: src/game/outfits.c and tests/native_outfit_pause.c. No generator,
physics, camera, frame limiter, resource recipe, personal profile or vendor changes.
Native evidence uses dummy audio, scripted movement and the cloned diagnostic HDD;
long sessions and campaign transitions remain unverified. Logs, rejected probes,
comparison JSON and captures are under artifacts/release-beta1/motion-jitter/.
The normal game was rebuilt; the existing outfit cache is retained. Validation: 245 tests passed
(18.005 s), ARM64 host probe and normal game compilation passed. The final
visual movement correction was subsequently confirmed by the player.


## Charged kick investigation and cutscene faces — November 15, 2026

The owner confirmed the movement-jitter correction. A later A, A, held-A mana
attack crashed with the selector enabled; the same attack passed after disabling
it and restarting. The crash report points to DirectSound CRefCount::Release on
the kernel-timer DPC thread, matching the area of a pre-wardrobe intermittent
audio failure. This does not establish that outfit code caused the corruption.
No runtime/audio patch or speculative invalid-callback suppression was applied.

A cloned-save diagnostic with physical controller and normal CoreAudio then
completed repeated actual mana attacks (1000 down to 100) and a normal window
close with exit 0. No crash reproduced. Synthetic earlier A sequences that did
not consume mana are not considered successful reproductions. Private lifecycle
tracing and the crash summary remain in artifacts/release-beta1/special-attack/.
The audio crash remains open, including its possible relationship to the selector.

The owner also observed Buffy's frozen face/lips in a cutscene with a selected
cosmetic. Numeric bone snapshots do not transfer mesh/phoneme animation channels.
Render the original mesh during cutscenes through its unmodified native render
path, then resume the separately owned chosen cosmetic during gameplay. Preserve
the choice and resource ownership. Query TGO::Cine_IsCutsceneRunning at 0x943E0
(cdecl, no arguments) through the full CPU/FP/SIMD-preserving helper. The supplied
XBE hash was rechecked against config/title.json before adapting this path.
Full cosmetic facial-channel transfer remains unimplemented.

Adversarial ASan/UBSan regression covers repeated cutscene/gameplay transitions,
choice retention, absence of cosmetic pose/light updates while bypassed, and CPU
preservation. Native Metal evidence on an isolated baseline HDD clone: 21
cutscene samples drew the original mesh with 10 distinct phoneme-frame values;
5 subsequent gameplay samples drew a distinct Slayer cosmetic, selection 4
unchanged. The configured 55-second watchdog stopped that run with exit 3; this
was not a clean gameplay exit or a new audio validation (dummy audio). No full
campaign, other cinematics, or visual lip-sync review by the owner is claimed.

Also corrected the support report's version parser to recognize beta and rc
versions instead of reporting unknown. Validation: 246 tests passed (18.473 s),
ARM64 host probe and normal native game build passed. The initial restricted run
had eight environment permission errors; the complete authorized local run passed.
No personal profile/save writes, vendor edits, commit, tag or publication.
