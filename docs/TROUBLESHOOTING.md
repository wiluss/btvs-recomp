# Troubleshooting and known issues

## Setup refuses the ISO

Only the identified USA executable and MAP are supported. Compare the hashes in [SETUP.md](SETUP.md). A valid Xbox image from another edition can still be unsupported. A missing or mismatched `final.map` is not fixed by downloading someone else's file or changing the manifest.

If the image is truncated, contains ambiguous paths or exceeds the import limits, setup stops before publishing the import. Keep the source ISO intact and check your own dump. No game download is provided.

## Toolkit or build tools are missing

Run `python3 tools/bootstrap_runtime.py` from the source folder, then follow the prerequisite commands in SETUP. The launcher currently runs from that folder; moving only the `.app` breaks access to its tools.

The recipe expects native ARM64 tools and Homebrew in `/opt/homebrew`. An existing toolkit at a different commit is preserved and refused. Partially modified runtime sources are also preserved; do not reset a development checkout containing work you need. A fresh source folder is the simplest isolated retry.

If setup fails after import, a completed import receipt allows a retry. Details are in `private/setup/setup.log`. Some low-level developer messages are still in French. The launcher translates its own interface into five languages.

## The game stutters or closes

Audio stutter and an intermittent audio crash are known alpha issues. The full campaign and long-session stability are not confirmed. A crash that does not repeat is not evidence that it was fixed.

Try a lower internal resolution before interpreting a heavy scene as a new performance regression. Higher scales, effects and enemy counts can cause substantial frame-rate swings. Keep the exact settings and last checkpoint in your report. No fixed 60/120 FPS promise is made.

## HD options are unavailable

HD content is a separate optional download. Finish game setup, then import the matching HD ZIP through **Packs & skins → Install the HD pack…**. Read the [HD guide](HD-PACK.md). A checksum, game-edition or recipe mismatch is refused; a modified existing add-on is preserved. Existing local assets take precedence over the installed add-on. Compatible custom XRTP packs can still be selected separately.

## Save or disk problems

Close the game before backing up or moving the whole `private/profile/` directory. Do not remove `title.json`, partition images or their gzip archives individually. A profile from a different executable is refused.

Partition images are restored while playing and compacted afterward. A force-quit can leave raw images. If both a raw image and its archive exist, keep both and ask for help rather than overwriting either. See [disk maintenance](GRAPHICS.md#saves-and-disk-storage).

## Controls

Save remapping changes while the game is closed, then relaunch. The same profile applies to all controllers, and in-game prompts keep their Xbox meanings. The stock controller mapping was physically tested; custom mappings need more physical testing. Restore defaults if a custom layout makes navigation difficult.

## Reporting a problem

Include:

- Alpha version and whether you used the attached source kit or a Git checkout.
- Mac chip, RAM, macOS version and free space.
- Resolution/scale, 4:3 or 16:9, fullscreen/VSync and pack settings.
- Last checkpoint, exact actions, reproducibility and expected/actual result.
- A short relevant error excerpt, with personal paths removed.

Do **not** attach the ISO, XBE, MAP, generated game source, recompiled game executable, saves, disk images, game-derived packs, model weights, or the complete project folder. Full runtime logs can contain guest memory and private paths; review them locally before sharing an excerpt. There is no automatic diagnostic uploader.

## Sidebars during 4K gameplay in the first alpha

The initial launcher could display a 16:9 badge in 4K while passing an older 4:3 preference to the game. Until you install a launcher containing the fix, select scaled rendering, enable **16:9 Aspect Ratio**, then select **4K UHD** again before starting the game.

The corrected launcher automatically uses 16:9 gameplay in 4K, including when loading old preferences. The menu intentionally stays 4:3. Bars above/below a 16:9 picture on a taller screen are expected; the picture is not stretched to fill a different aspect ratio.
