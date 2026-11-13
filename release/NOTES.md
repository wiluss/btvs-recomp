# btvs-recomp 0.1.0-alpha.9

**Save backups and easier problem reports.**

## Protect your saved progress

The launcher keeps the three latest automatic copies of your complete save profile before sessions. Unchanged profiles do not create duplicate copies. Open **Saves** to create a manual copy or restore a dated copy while the game is closed. Restoration verifies the archive and keeps your previous profile separately so it remains available.

These are backups of existing saved progress, not in-game quicksaves. Manual copies and displaced profiles are not rotated automatically. Keep external backups too. Low space, an expanded disk, a busy or oversized profile can prevent a new backup; the launcher explains the error and lets you cancel or explicitly continue without a new copy. [Details and limits](https://github.com/wiluss/btvs-recomp/blob/v0.1.0-alpha.9/docs/GRAPHICS.md#saves-and-disk-storage).

## Report a problem

Use the **ladybug button** or **Help → Problem report**. Preview and copy a local summary of the app version, Mac hardware, macOS, graphics settings and last recorded session. Add your checkpoint and reproduction steps before sharing. No automatic upload, raw logs, personal paths, game files, saves or serial numbers.

The new interface is available in English, French, Spanish, German and Italian.

## Update without rebuilding the game

From alpha.8, use **Check for updates → Install update** then quit and reopen the launcher after success. Only the launcher is compiled; your imported ISO data, game binary, saves, settings and HD pack stay in place.

From alpha.6/.7, extract the new source ZIP into a separate folder, close the old launcher/game and double-click **Update btvs-recomp.command**. Select your existing project folder. Official unmodified source kits are required; Git checkouts and edited sources need a manual update. [Update instructions](https://github.com/wiluss/btvs-recomp/blob/v0.1.0-alpha.9/docs/SETUP.md#update-an-existing-installation).

New players still provide their own supported USA ISO and build locally. No ISO, XBE, MAP, save, generated game source or game executable is distributed. The game/runtime and optional HD v1 pack are unchanged:

- [HD v1 download](https://github.com/wiluss/btvs-recomp/releases/download/v0.1.0-alpha.6/btvs-recomp-HD-v1.zip)
- [HD checksums](https://github.com/wiluss/btvs-recomp/releases/download/v0.1.0-alpha.6/HD-SHA256SUMS)

## Validation and limits

175 automated tests passed, including backup integrity, rotation, locks, path traversal, failed-restore rollback, interrupted recovery and report privacy. The ARM64 host probe and launcher build passed. Native backup/restore and report views were tested with a synthetic profile on the development Mac. The personal save profile was not modified; no new gameplay, physical-controller or cross-Mac validation is claimed.

The previously reported intermittent crash has not recurred in the user's latest sessions. It remains unresolved: this release contains no speculative audio or runtime fix. Audio stutter, full-campaign coverage and long-session stability remain open. MIT covers original project code, not underlying game artwork or third-party components.
