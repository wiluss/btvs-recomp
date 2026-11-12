# btvs-recomp 0.1.0-alpha.7

Fixes **4K UHD gameplay staying in 4:3** when selected in the launcher. Thanks to Jestifiable for reporting the issue and identifying the workaround.

## Fixed

- Selecting **4K UHD** now enables 16:9 gameplay, including with old saved 4K/4:3 preferences.
- The 16:9 switch and format badge now agree with the actual launch settings. The switch is shown on and locked in 4K.
- Returning to scaled rendering restores the previous scaled-mode aspect choice during the launcher session.

Menus intentionally retain their original 4:3 framing. Gameplay is 16:9; displays with a different aspect ratio can still show bars. This update does not stretch the picture.

## Install or update

Download **btvs-recomp-v0.1.0-alpha.7-source.zip** and **SHA256SUMS** below. Verify the checksum and follow the [installation guide](https://github.com/wiluss/btvs-recomp/blob/v0.1.0-alpha.7/docs/SETUP.md).

For an existing installation, back up the entire `private/profile/` folder, apply the updated source files to your existing project folder without deleting `private/`, and run `make launcher`. Quit the previous launcher and open `build/btvs-recomp.app` again. No ISO reimport or HD reinstallation is needed for this launcher fix.

New players must supply their own supported USA ISO and build locally. No ISO, game executable, generated game source, MAP, save or model is distributed in this source kit.

## HD pack

The **HD v1 pack is unchanged** and remains hosted with the previous release:

- [btvs-recomp-HD-v1.zip](https://github.com/wiluss/btvs-recomp/releases/download/v0.1.0-alpha.6/btvs-recomp-HD-v1.zip)
- [HD-SHA256SUMS](https://github.com/wiluss/btvs-recomp/releases/download/v0.1.0-alpha.6/HD-SHA256SUMS)

If already installed, keep it. Otherwise use **Packs & skins → Install the HD pack…** after game setup. No AI model is required to install or play.

## Validation and limitations

153 tests passed, including a regression compiling the real Swift settings and checking the arguments through the Python launch path. The ARM64 host probe passed and the native launcher rebuilt. The reporting player's Mac has not yet been retested; no new gameplay or performance result is claimed.

On the maintainer's Mac, the default macOS 27.2 SDK lacked the `SwiftUIMacros` plugin. Building succeeded with the already-installed 26.5 SDK, selected for that command only. If you encounter that exact error and have the same SDK installed, use:

```sh
SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk make launcher
```

Audio stutter, an intermittent audio crash, full-campaign coverage and long-session stability remain open. See [known issues](https://github.com/wiluss/btvs-recomp/blob/v0.1.0-alpha.7/docs/TROUBLESHOOTING.md).

This is an experimental, unofficial fan project developed with substantial AI assistance. The MIT license covers original project code, not underlying game artwork or third-party components. Existing notices and license scopes continue to apply.
