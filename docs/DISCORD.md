# Discord Rich Presence

This optional feature in 0.2 displays **Buffy the Vampire Slayer** as the
activity title, the **current level/area** as its description, the game's official
logo and elapsed session time. It is off by default. Level names come from the
supported user's original mission list, for example **Spanish Mission, Canyon**.
It does not read save contents or claim combat state or completion percentage.

## Enable it

1. Open Discord on the same Mac and sign in normally.
2. In the launcher, enable **Options → Discord Rich Presence**.
3. Launch the game. Changes apply to the next session; no developer setup is needed.

One project Application ID serves all players. Once it is included in the shipped
`config/discord.json`, end users only need their own running desktop Discord
client and the opt-in toggle; they do not create their own developer application
or use the maintainer's Discord account. Developer overrides can still be supplied manually in
`private/config/discord.json`; the launcher exposes only the on/off toggle.
The public ID is already included in this revision’s shared configuration.

The shared public Application ID is **1571266642783117462**. Its Discord
application should be named **Buffy the Vampire Slayer**. A manual local override is
available for development; players do not need to create a Discord application.
No bot, bot token, client secret or OAuth login is needed by the game.

The shared image key is **btvs_logo**. The maintainer uploads the official game
logo under that key in the application's **Rich Presence → Art Assets** page.
The private, upscaled 1024 × 1024 upload file is
`artifacts/discord-levels/btvs_logo-1024.png`. It was derived from the user's game
logo, not the separate btvs-recomp project wordmark. The original game image and
its upscale are not included in Git, the source kit or the launcher bundle.
Only the public image key is distributed; Discord serves the uploaded asset.
The same PNG can be used as the application's general icon if desired.

Make sure Discord permits sharing your activity in its activity privacy settings.
An invalid application, closed Discord, disabled activity sharing or a different
Discord account/client can prevent the card from appearing. The game continues
normally. This integration does not start Discord or change its settings.

## Behavior and privacy

The game supervisor talks only to Discord's local Unix IPC socket using the
[documented RPC protocol](https://docs.discord.com/developers/topics/rpc).
Discord handles displaying the activity to others under your Discord settings.
The game contains no Discord HTTP client, account credential or third-party SDK.

A background worker handles framing, bounded reads/timeouts, heartbeat replies,
disconnects and reconnection. Updates are coalesced and limited to one per
15 seconds after the initial update. Session elapsed time spans internal Xbox
relaunches; level updates can take up to that update interval.
The supervisor clears its activity on normal exit. It does not keep a presence
alive just because the launcher is still open. Turning the toggle off affects
the next launch; close the current session to remove its activity immediately.

Preferences live in `private/config/discord.json`, separately from graphics and
save data. The bundled `config/discord.json` holds public application metadata
only. Broken preferences disable presence and do not block gameplay.

## Validation limits

Tests use a fake local Discord server: fragmented frames, public-ID handshake,
heartbeat echo, activity updates, reconnect, cleanup, missing/unresponsive clients
and Swift/Python preference compatibility. Game-supervisor tests verify lifetime
across relaunches. No real Discord account or external presence is used by tests.
A real desktop Discord client acknowledged Main menu, In game and Spanish
Mission, Canyon during an isolated native Load Game/relaunch test with the shared
Application ID. The public application metadata confirms the exact name and btvs_logo asset;
its CDN thumbnail was visually checked as the official game logo. The requested
1024 upload PNG was produced and size-verified locally. A full Discord profile
card was not inspected through the UI; the CDN thumbnail check does not establish
which resolution the client displays or whether the latest replacement is cached.

## How the level is observed

The existing pinned runtime flushes a host log entry when a disc resource pack is
successfully opened. The presence worker incrementally reads at most 256 KiB per
poll and accepts only that exact successful-open format for level packs. Failed
opens, save paths and unrelated files never become a Discord description. Names
are read from the verified user's `gameinfo/missionlist.txt` inside res_null.pak:
55 campaign/hub entries and 9 special entries, without bundling a game text table.

The cursor is reset to the current log end before each game process starts, so a
previous level cannot leak across an internal relaunch. Normal menu loading resets
the description; unknown level packs use **In game**. Labels identify the level
being opened/loaded, and do not imply that loading has finished or the player has
control. The original English game labels are used regardless of launcher language.
If the log format or mission list is unavailable, presence stays generic and the
game continues. No guest-memory hook, address or vendor runtime patch is added.
