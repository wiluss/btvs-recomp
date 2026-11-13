# User guide

## Main screen

**Play** starts the main menu with a persistent save profile and no time limit. **Options** contains display and HD settings. **Packs & skins** selects a local XRTP pack and controls arena access. **Controls** and **Saves** are in the footer; **Help** contains setup and the session log.

The launcher follows a supported system language on first use: English, French, Spanish, German or Italian. Otherwise it uses English. A choice made with the globe is saved and takes priority. This translates the launcher, not the game's dialogue or button prompts.

## Display

Start with the default 2× internal resolution, then adjust for your Mac. Higher scales and effects can substantially reduce frame rate. The original 4:3 base is 640×480. Experimental 16:9 expands the horizontal view in gameplay; the menu keeps its original framing. The dedicated 4K option renders at 3840×2160 and automatically enables 16:9 gameplay. Its 16:9 switch is shown on and locked while 4K is selected. Switching back to scaled rendering restores the previous scaled-mode aspect choice. Menus retain 4:3 framing; screens wider or taller than 16:9 can still have bars around gameplay. A high internal resolution does not by itself replace low-resolution textures or HUD images.

Fullscreen, VSync and the FPS overlay are optional. The overlay reports engine/presentation timing; it is not a guarantee of your display's physical refresh rate. Display preferences are saved in `private/config/graphics.json`.

## Textures, text and skins

A clean alpha installation uses original game assets. The separate [HD add-on](HD-PACK.md) contains prepared textures, HUD, text and launcher artwork. Download its ZIP from the release page and import it with **Packs & skins → Install the HD pack…**. The launcher enables the HD switches after a successful installation. Editable reconstruction masters are not included.

Select a local `.xrtp` file through Packs & skins, or drop one onto its panel. A pack must match this game/build and pass validation at launch. Selecting a file is not a claim that its contents have been verified. Do not upload game-derived packs to this project's issue tracker.

The four arenas can be enabled in Extras. This does not replace campaign progression. Skins use compatible local texture packs; no general mod browser or automatic mod installer is included.

## Keyboard and controller remapping

Open Controls while the game is closed. Changes take effect on the next launch.

- **Keyboard:** click a binding and press a key, or use its menu. Escape cancels capture. One key per action; Command combinations are not supported and F11 is reserved for fullscreen. AZERTY and QWERTY reset keyboard bindings without changing the controller profile.
- **Controller:** choose the physical source for each Xbox button. The labels show position and Xbox/PlayStation equivalents. The sticks can be exchanged or disabled. One profile applies to all connected controllers.
- An input already assigned elsewhere swaps the two bindings. A, B and Start must remain available through at least one device.
- **Restore defaults** resets keyboard and controller bindings. **Save** writes the profile; **Cancel** discards edits. Settings cannot be changed during gameplay.

Default AZERTY movement is ZQSD; the camera uses IJKL. Xbox A is W, B is X, X is C, Y is V, White is A, Black is E, the triggers are 1/3, Start is Return and Back is Backspace. Arrow keys operate the D-pad. Numeric keypad 8/2/4/6 remain movement alternatives unless explicitly reassigned or that direction is disabled.

Bindings are saved in `private/config/controls.json`. The game continues to display its original logical Xbox button labels. Physical testing confirmed the original controller mapping; custom mappings have automated coverage and still need physical validation.

## Saves and disk storage

The persistent profile is `private/profile/`. Use Load Game after restarting. The first profile is generated empty; no developer save is imported.

The launcher creates a verified copy of the whole profile before starting a session. It keeps the three latest automatic copies and skips duplicate copies when nothing has changed. This applies to launches through the app, not direct CLI runs. A first launch without a profile continues normally. Copies contain existing saved progress, not the current in-memory game state: this is not quicksave.

Open **Saves** to create a manual copy, select a dated copy to restore, or open the current profile folder. Close the game first. Manual copies are not rotated. Archives live in `private/backups/`. A restore verifies the game identity and every file checksum before replacing the profile; the previous profile is kept verbatim in `private/backups/replaced-*`. Keep those folders until you are satisfied with the restored progress. Interrupted restores are checked before the next launcher backup/launch.

A backup can fail if space is low, the profile is in use, partitions are still expanded, or the profile exceeds the 768 MiB safety limit. The launcher shows the error and lets you cancel or explicitly continue without a new backup. Existing copies are preserved. An interrupted restore must be recovered before launch. Complete a normal game session or use the maintenance procedure below to compact expanded partitions. Keep external backups as well: these local copies do not protect against disk failure.

Back up the whole profile while the game is closed. Keep `title.json`, `hdd/`, saves and partition files together. The title metadata binds the profile to the supported XBE. An incompatible profile is refused.

Partition images 1–5 are compressed into standard `.img.gz` files while idle, restored before play, and compacted after the game stops. Their contents and Xbox geometry stay unchanged. Partition0, UDATA, TDATA, caches and ordinary files remain in place. Space for the restored images is still required while playing. A force-quit can leave raw images, which are preserved for a later normal close or maintenance.

APFS clones share blocks. Adding their logical file sizes or allocated-block counts does not measure unique physical disk use. Old development diagnostics once inflated the folder's reported size above 1 TB; those diagnostics are not part of the alpha.

Advanced maintenance, with the game closed:

```sh
# Inventory only:
python3 tools/hdd_storage.py pack --all-local

# Lossless compaction, with a local report:
python3 tools/hdd_storage.py pack --all-local --apply --report artifacts/hdd-compaction.json

# Restore before running a raw diagnostic executable outside the launch tools:
python3 tools/hdd_storage.py restore /path/to/hdd --apply
```

If both an image and its archive exist, the tool refuses to overwrite either. Keep both and request help. See [troubleshooting](TROUBLESHOOTING.md) for useful reporting details.
