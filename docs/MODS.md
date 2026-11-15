# Local texture and skin mods

Available in the 0.2.0-beta.1 source kit. Upgrading from an alpha requires game regeneration and rebuild; see SETUP.md.

## Original game outfits

Open **Outfits** in the game's original **main menu** or **Pause menu**.
Browse **Bronze, Workout, Cheerleader, Slayer and Dark Slayer** with an animated
3D preview, then confirm with the normal Select control. From Pause, selection
returns to **Resume**; the new outfit appears immediately when you resume play.
Back cancels browsing and keeps the selected outfit. **Level outfit** restores
the game's normal level-dependent appearance. Your choice is remembered across
launches. The native selector currently uses English labels.

The wardrobe has a compact original logo, a dedicated heading and a regular
outfit list. Enable or disable **Options → Outfit selector** before launching
(on by default). Disabling skips its resource preparation and extra model loading;
your saved outfit preference is retained. It uses the original models from your supported ISO; no outfit
download is required. The display uses Buffy's current pose and lighting while
retaining the original actor mesh, animation state, collision and scripts for
gameplay. This is a cosmetic change, not a change to abilities or progression.

During cutscenes Buffy uses the level's original outfit, preserving the game's
facial expressions and lip sync. Your selected outfit returns automatically when
gameplay resumes; your saved choice is unchanged. Full facial-animation transfer
to the cosmetic outfits is not implemented.

`private/native-outfits/` holds the derived menus and cosmetic resources. Initial
preparation builds the private packs once, and level loading prepares the models
and previews. Choosing another outfit does not rebuild or replace the running
packs. Imported game files and saves are not edited. Preparation needs temporary
space for private pack copies; a damaged cache is checked/repaired before launch.
Custom texture mods are separate and can also affect the chosen model.

This remains a development feature. Native Pause selection, cancellation,
resumption and saved-choice behavior have been exercised on an isolated test
profile. Full campaign, cutscene doubles, long sessions and physical controller
validation of this new menu remain to be confirmed. The F8 overlay below handles
custom texture packs; it is separate from the native original-outfit selector.

Existing alpha.9 installations need regenerated game code and a rebuilt game for
this feature; the launcher-only updater deliberately refuses that upgrade.
The new protocol disables native wardrobe activation on older game binaries.
See [Development](DEVELOPMENT.md#rebuild-for-the-native-outfit-selector).

## Import a custom skin and choose an outfit

1. Obtain a compatible `.xrtp` skin and its matching `.json` from a creator you trust. Keep both files together, with the same basename.
2. Optionally put a screenshot beside them with the same basename and a `.png` extension. The launcher copies it into its private library when importing a new skin.
3. Close the game. Open **Packs & skins → Buffy’s wardrobe → Import a skin…** and select the `.xrtp`, or drop it onto the wardrobe section.
4. Review the outfit cards, then choose **Wear this outfit**. Importing alone does not enable it. One selection is kept across launcher restarts.
5. To add or replace a card's screenshot later, click its photo button and choose a PNG. A card without an image explicitly asks for a screenshot; the launcher does not fabricate an outfit preview.
6. Choose **Original outfit** to let the game use its normal level-dependent appearance again.

## Change outfit during gameplay

Development builds include an in-game host wardrobe overlay:

1. Import your skins before starting a session; the session catalog holds up to 32 skins.
2. **Pause the game first**, using its normal pause control. The wardrobe does not pause simulation automatically.
3. Press **F8** to open the wardrobe over the game. A compatible controller can also use **Guide + Y**; this chord still needs physical validation.
4. Use **Left/Right** or **D-pad Left/Right** to browse the outfit names and screenshots.
5. Press **Enter / A** to apply the highlighted skin immediately. Choose **Original level outfit** to remove the skin overlay while retaining your selected HD base.
6. Press **F8 / Escape / B** to close the wardrobe, then resume the game normally.

The selected skin is saved for the next launch when preferences can be written. If saving fails, the overlay says that the change applies only to the current session. A bad replacement keeps the currently applied outfit and displays an error. Screenshots are static previews, not a rendered 3D character viewer. The current in-game overlay labels are English; the launcher wardrobe remains available in five languages.

This feature changes the runtime and requires a local **game rebuild**, as well as the updated launcher. It cannot be installed by alpha.8/.9's launcher-only updater. It is not published yet. Imported skins/previews and the session catalog stay under `private/mods/`; no game assets are added to the source kit. Restart the game to include newly imported skins in its catalog.

Skin packs replace supplied textures. They do not unlock original level costumes, change meshes, or automatically identify every Buffy texture across every level. A creator must cover the relevant texture variants; verify the result in gameplay. Existing generic XRTP cosmetic packs remain importable. Scripts, executables, levels and arbitrary mod ZIPs are not accepted. The official HD ZIP still uses **Install the HD pack…**.

## Names, credits and screenshots

Creators can add an optional `skin` object to the existing pack proof JSON:

```json
"skin": {
  "name": "Crimson jacket",
  "author": "Creator name",
  "description": "Describe the outfit and supported levels."
}
```

Keep the existing `xbe_sha256`, `entries` and `pack_sha256` fields. Names and authors have a 100-character limit; descriptions have a 400-character limit. Without skin metadata the filename becomes the card name. No paths, URLs or commands from the JSON are executed.

Screenshots must be non-interlaced 8-bit RGB/RGBA PNGs, at most 8 MiB, 4096 pixels per side and 8 megapixels. The importer checks their chunk checksums, dimensions and bounded decompressed size. Capture the actual outfit in-game before publishing a preview. Screenshot files, skin payloads and generated previews stay local; they are not added to Git or the source kit. Duplicate pack imports reuse the existing card; use its photo button to update the screenshot.

## Combining with HD

The active skin overlays the texture/text profile selected in Options. With HD enabled, unmodified HD entries are retained. A replacement wins over the same texture hash in the base pack. A collision with a different texture kind or aspect ratio is refused before launch. The runtime still applies the original/HD text switches.

The live path keeps the base and skin layers separate; it does not duplicate the whole HD pack for each outfit. The older offline composition cache remains available to development tooling. Missing, damaged or incompatible active mods stop launch with an error; they are not silently disabled. Select **Original outfit** to play without one. Changing the base graphics profile takes effect on the next launch. The source ISO, imported game files, official HD pack and saves are never edited by the manager.

## Files and recovery

- `private/mods/library/<content-sha256>/`: managed copies (`pack.xrtp`, `pack.json`, `mod.json`, and optional managed preview PNGs). Duplicate payloads are imported once. Original source files can be moved after a successful import.
- `private/config/mods.json`: the active selection; separate from graphics preferences.
- `private/mods/sessions/`: immutable per-session outfit catalogs; old catalogs can be moved to Trash while both apps are closed.
- `private/mods/cache/`: disposable offline derived compositions. A newly prepared composition retires old derived caches. Imported mods remain intact.

Keep the whole library when moving your installation. To remove a mod manually, disable it, close the game and launcher, then move its library folder to the macOS Trash. To reclaim derived disk space, close both apps and move `private/mods/cache` to Trash; it will be regenerated. Replaced previews are retained locally; they are not auto-uploaded. Do not edit managed sidecars or payloads in place: import a revised pack instead. Imports are limited to 2 GiB per pack; derived packs have the same limit and temporary free space is required. No executable instructions in JSON are used.

## Creating a pack

Existing developer tooling can build packs from local PNG replacements for known guest texture hashes. This requires your own verified game, a texture inventory from your local capture workflow, and Pillow in your project environment. See [texture development](TEXTURES.md); texture inventories and images are not distributed with the source kit.

A local recipe names PNG files inside its own folder:

```json
{
  "scale": 2,
  "entries": [
    {"hash": "YOUR_CAPTURED_TEXTURE_HASH", "png": "replacement.png"}
  ]
}
```

Replace the placeholder with a real unambiguous hash from your inventory. Images must have the expected dimensions at the requested scale. From the project folder:

```sh
.venv/bin/python tools/texture_mod.py /path/to/recipe.json /path/to/my-skin.xrtp \
  --inventory /path/to/local-inventory.json
```

Share the generated `.xrtp` and matching `.json` together. Build only your intended replacements; the manager overlays them on the player's selected HD profile, so a skin does not need to redistribute the whole HD pack. Do not package your ISO, XBE, MAP, generated game code or saves. The project MIT license does not grant rights to game-derived artwork.

## Validation scope

Synthetic pack tests cover import integrity, duplicate imports, persistent activation, disabling, composition and preservation of unrelated base entries, cache reuse, incompatible collisions, failed copies, busy locks, low space, symlinks and tampering. Native launcher compilation and UI checks are recorded in the roadmap. Synthetic packs are not evidence that a particular community skin looks correct in gameplay; that requires a compatible real mod and a player test.
