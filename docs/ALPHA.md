# Alpha release status

Version: `0.1.0-alpha.7`, source-build prerelease candidate with an optional HD add-on.

Players build locally from their own supported ISO. The source kit contains original project source, public build recipes, metadata, English documentation, runtime patches, license notices and the selected project-branding graphics and four documentation screenshots. A separate optional HD ZIP contains prepared game-derived textures, HUD, text and launcher artwork; see [HD-PACK.md](HD-PACK.md). No ISO, XBE, MAP, save, editable HD master, model, generated game source or recompiled game executable is included in either attachment.

## Verified on the development Mac

- The user's USA ISO contains the exact XBE and `final.map` required by the manifest.
- An isolated source installation without prior private data, generated files, build products, logs or venv completed extraction, dependency preparation, generation and ARM64 compilation.
- Its 173 generated C files match the development installation; the runtime sources match after the six shipped patches.
- A blank profile reached the title and main menu, created the first save, then loaded that save after restart into the first level's opening cutscene.
- Those setup checks used dummy audio and the runtime's scripted input API. They do not establish audio quality, a new gameplay session or long-term stability.
- The development user previously validated real gameplay and the original controller mapping. Physical remapping validation and the complete campaign remain open.

Only one Mac is available for testing. Other hardware and macOS versions need external testing. The launcher targets macOS 13 or later; the tested Mac runs macOS 27.2.

## Public setup scope

The current installer runs inside the extracted source folder and requires native build prerequisites. It is not an independently installed app in Applications. A clean install uses original game graphics until the optional HD add-on is imported. Editable development masters are not shipped. The direct mission diagnostic and its captured bootstrap page are outside the player setup path.

Known issues include audio stutter, an intermittent audio crash, resolution/effect-dependent frame-rate swings and unconfirmed long sessions. See [troubleshooting](TROUBLESHOOTING.md).

## Packaging

The root MIT license covers original project code. Third-party file licenses take precedence for their components. Notices and full license copies are included.

The source archive is built from `release/files.json`, audited and accompanied by `SHA256SUMS` and an internal `RELEASE_MANIFEST.json`. Generated archives and all validation data remain under artifacts. Long private development histories are excluded; the public kit contains English summaries and user instructions.

A prepared local archive or GitHub draft is not a published release. Follow the [release process](../release/PUBLISHING.md) and verify the exact package before publishing.
