# btvs-recomp 0.2.0-beta.1

**A wardrobe for the Slayer, Discord presence and local texture mods.**

## Change Buffy's outfit in game

Open **Outfits** from the original Main or Pause menu. Browse animated **3D
previews** of **Bronze, Workout, Cheerleader, Slayer and Dark Slayer**. Confirm
from Pause and the costume changes immediately when you resume. Back cancels
browsing; **Level outfit** restores the normal appearance. Your choice is
remembered across launches.

**Options → Outfit selector** in the launcher enables or disables the feature
for the next session. It is on by default. Turning it off skips the extra private
resource preparation and model loading. Costumes come from your supported ISO;
no outfit assets or game models are included in this source download.

The wardrobe also fixes a movement jitter: selected outfits now follow the same
interpolated display position as the original model. A scripted native comparison
matched root positions over 4,000 samples. Physics and camera timing are unchanged.

Cutscenes use the level's original outfit so facial expressions and lip sync
remain native. Your selected costume returns automatically during gameplay,
without changing your saved choice. Full facial transfer to cosmetics is not
implemented. Problem reports now recognize beta and rc version numbers.

## Discord Rich Presence

Enable **Options → Discord Rich Presence** to show **Buffy the Vampire Slayer**,
the current level, the official game logo and elapsed session time. It is off by
default. Open the desktop Discord client on the same Mac before playing. The
shared public Application ID is included: no developer account, secret or extra
application setup is needed.

## Local texture mods

The **Packs & skins** library supports importing compatible XRTP packs, enabling
and disabling them, adjusting priority and managing custom texture/skin overlays.
This is separate from the native stock-outfit selector; it does not import arbitrary
3D characters or gameplay scripts. The optional F8 texture overlay is also separate.

## Automatic game-build updates

**The updater can rebuild the game automatically**, using your existing supported
import. It builds in a separate directory and installs only after success. Errors
during installation roll the game, launcher, sources, runtime and generated data
back together. Saves, settings and the HD pack are retained. No ISO reimport or
HD redownload is required. Allow 30 GiB free and several minutes for compilation.

From alpha.8/.9, install **0.1.2 — Updater bridge** with the existing update button,
quit/reopen, then check again for this beta. Old alphas do not recognize betas;
the bridge is a compatible launcher-only update that enables the new process.
Alternatively, extract this beta's source ZIP into a separate folder and run
**Update btvs-recomp.command**, selecting your existing project folder. That
helper upgrades directly, including rebuilding the game, without Terminal commands.
[Update guide](https://github.com/wiluss/btvs-recomp/blob/v0.2.0-beta.1/docs/SETUP.md#upgrade-to-02-from-an-alpha).

New players follow normal ISO setup. The first enabled wardrobe launch builds a
private cache once; later selections reuse it. The unchanged optional
[HD v1 pack](https://github.com/wiluss/btvs-recomp/releases/tag/v0.1.0-alpha.6)
remains compatible and is a separate download. Compatible launcher-only updates
continue to reuse the existing native game.

## Beta scope

246 automated tests, the ARM64 host probe and the signed launcher build passed.
The source ZIP was audited against its manifest and reproduced byte-for-byte
from the extracted kit on the development toolchain.

This version marks a feature milestone, **not 1.0 readiness**. An isolated alpha.9 → 0.1.2 → 0.2 upgrade rebuilt and installed the game,
retained save/HD/preferences sentinels and reached the native main menu. The final
bridge was accepted by the original alpha updater; its own suite ran 185 tests
with 6 skips. No live download of these unreleased versions was possible yet.

The project owner
confirmed that the native Pause selector works in a real session. Short native
checks covered Main/Pause previews, immediate selection, cancellation, remembered
choices, default-outfit restoration and explicit model cleanup. Full campaign,
cutscene doubles, automatic level transitions, physical controller navigation of
the new menu and long sessions still need play testing. An intermittent audio
crash and audio stutter remain unresolved; this release claims no audio fix.

No ISO, XBE, MAP, save, generated game source, game executable or installable HD
content is included in the source kit. The underlying game/HD artwork is outside
the original project's MIT license. Development and artwork preparation used
substantial AI assistance; no AI model or service is required to install or play.
