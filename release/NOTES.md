# btvs-recomp 0.1.0-alpha.8

**An easier way to install the 4K widescreen fix and future launcher updates.**

## Already have alpha.6 or alpha.7?

You do **not** need to rebuild the game, reimport your ISO or reinstall the HD pack.

1. Download **btvs-recomp-v0.1.0-alpha.8-source.zip** and **SHA256SUMS** below, verify the checksum, and extract the ZIP into a separate folder.
2. Close the game and the old launcher.
3. Double-click **Update btvs-recomp.command** in the extracted folder.
4. Select your **existing project folder** — the folder containing `private`, `build` and `tools`.
5. Wait for **Update installed**, then reopen `build/btvs-recomp.app` in your existing folder.

A small Terminal window opens automatically to show progress; you do not need to type build commands. Only the launcher is compiled with your existing Apple build tools. The updater preserves your imported game, game binary, saves, settings and HD pack, and retains previous files for rollback.

This path requires the attached official source kits with `RELEASE_MANIFEST.json`. Modified sources and Git checkouts need a manual update. [Full update and recovery instructions](https://github.com/wiluss/btvs-recomp/blob/v0.1.0-alpha.8/docs/SETUP.md#update-an-existing-installation).

## Updates inside the launcher

After installing this version, use the **circular-arrow button** at the bottom of the launcher or **Help → Check for updates**. Review the release notes, choose **Install update**, then quit and reopen the launcher after success.

The first updater supports **launcher-only updates**. It checks official source downloads against their GitHub SHA-256 digest and file manifest, refuses changes requiring a game/runtime rebuild, and preserves locally edited sources rather than overwriting them. Failed installation steps are rolled back; an interrupted update retains recovery information. It checks for releases only when requested and includes newer alpha versions.

## 4K widescreen

Includes the alpha.7 fix: selecting **4K UHD** enables 16:9 gameplay even with old 4K/4:3 preferences. The displayed switch and actual launch settings agree. Menus intentionally keep 4:3 framing; differently shaped displays can still show bars around 16:9 gameplay.

## New players and HD pack

New players still supply their own supported USA ISO and build locally. See the [installation guide](https://github.com/wiluss/btvs-recomp/blob/v0.1.0-alpha.8/docs/SETUP.md). No ISO, game executable, generated game source, MAP, save or AI model is distributed.

HD v1 is unchanged. Keep it if already installed, or download it from its existing location:

- [btvs-recomp-HD-v1.zip](https://github.com/wiluss/btvs-recomp/releases/download/v0.1.0-alpha.6/btvs-recomp-HD-v1.zip)
- [HD-SHA256SUMS](https://github.com/wiluss/btvs-recomp/releases/download/v0.1.0-alpha.6/HD-SHA256SUMS)

## Validation and limits

163 tests passed, including injected build/install failures, rollback, interrupted-update recovery, local-edit preservation and download checks. A real launcher build and alpha.6-to-alpha.8 update succeeded in an isolated installation with preservation sentinels. The ARM64 host probe passed, and the native update screen and release check were inspected. No new game or progression test is claimed.

On the maintainer's Mac, the default macOS 27.2 SDK lacked `SwiftUIMacros`. The updater retries with the installed 26.5 SDK for that build only when this exact error occurs; it does not change system toolchain settings or install another SDK. Other Macs and OS versions still need testing.

Audio stutter, an intermittent audio crash, full-campaign coverage and long-session stability remain open. This is an experimental, unofficial fan project developed with substantial AI assistance. MIT covers original project code, not underlying game artwork or third-party components.
