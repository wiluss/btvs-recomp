# Current engineering decisions

1. Target Buffy the Vampire Slayer (2002, original Xbox), not Chaos Bleeds. Use
   generic Xbox tooling independently; import no BuffyNX-specific code, symbols,
   seeds or overrides. Prior research consulted BuffyNX and is acknowledged.
2. Pin the generic XboxRecomp fork. Keep runtime changes as separate reviewed,
   tested patches with the original licenses/notices. Do not change vendor code
   implicitly or ship a modified floating dependency.
3. Bind every guest-address adaptation to the identified XBE and concordant MAP.
   Guard injected instruction sites and retain the generator as the source of
   permanent fixes, never hand-edited generated C.
4. Preserve guest registers, stack, flags, memory and relevant floating-point
   behavior. Distinguish compilation, native menu checks, short gameplay and
   complete progression; a host probe is not gameplay validation.
5. Build locally from the player's supported ISO. Exclude game inputs, generated
   game source, game executables, saves, models and private data from source kits.
   The explicitly approved HD add-on remains a separate attachment. Branding and
   the seven exact documentation captures have narrowly scoped allowlist exceptions.
6. Keep player saves in a persistent private profile. Backups capture saved
   progress; do not present them as in-game quicksaves. Preserve existing data
   during setup and updates and retain recovery/rollback checks.
7. Keep the launcher concise, themed and available in five languages. Follow a
   supported system language until explicitly overridden. Keep diagnostic timers
   and forced first-mission startup outside the normal player interface.
8. Keep 4K gameplay widescreen independently of the saved scaled-mode preference.
   Widescreen uses verified visibility-plane adaptations while retaining the
   original projection; menus retain their original framing.
9. Native stock outfits use Main/Pause controls and animated game models from the
   player's files. Preview is separate from the chosen costume; Back cancels.
   Confirming in Pause changes appearance immediately on Resume and focuses Resume.
10. Preserve the original gameplay actor/animation/collision/script ownership.
    Render separately owned cosmetics with native numeric bone snapshots and light
    IDs. Check bone names/parents/counts and buffer bounds; release all owners at
    actor teardown. Protocol 2 gates the reviewed generator bindings and private
    resource recipe. Do not copy campaign animation tables into cosmetic loads.
11. Keep outfit packs immutable during play. Persist only the selected preference;
    reuse prepared resources across choices. The launcher **Outfit selector** switch
    is on by default, applies next session and disables preparation and extra model
    loading when off. Retain the preference when disabled. No arbitrary 3D model or
    gameplay-script import is implied by texture/skin mod support.
12. Discord presence is optional and off by default. Ship only public application
    metadata. Observe successful resource-pack opens off the game thread, resolve
    original level names from the verified user's mission list and fail softly.
    No token, developer account, external SDK or guest-address hook is required.
13. Qwen is optional and targeted. Its proposals require review; no AI service or
    model is required by players. Keep detailed developer traces local.
14. 0.2.0-beta.1 is a feature milestone rather than a 1.0 claim. Existing alphas
    use a launcher-only 0.1.1 bridge to recognize betas and enable game updates.
    Build game changes in isolation, verify inputs/runtime, then install native
    binary, sources, generated output, runtime and receipts together with rollback.
    Retain imported game files, saves, settings and HD packs. Refuse local edits
    rather than overwrite them.


For cosmetic placement, use the source animated model’s checked render matrix
from native UpdateMesh. The actor physics transform can differ between ticks and
causes visible motion jitter. Preserve simulation and camera behavior; regression
coverage must deliberately separate rendered and physics positions.


## Cutscene outfit fallback — November 15, 2026

The cosmetic bone snapshot excludes facial mesh/phoneme channels. Keep the original
mesh's complete render path while the verified retail cutscene query is true;
resume the cosmetic during gameplay without changing the remembered choice.
Do not copy pointer-bearing facial channels or borrow other models' owned parts.
Full cosmetic facial transfer requires separate compatibility and ownership work.
An intermittent charged-attack/audio crash remains unresolved despite a successful
manual retest; do not classify it as fixed or suppress invalid callbacks.


Updater bridge 0.1.2 supersedes 0.1.1: it accepts the three approved new beta
README captures. The withdrawn 0.1.1 assets had no downloads. Game/runtime inputs
are unchanged. Beta 0.2.0-beta.1 archives and tags remain unchanged.
