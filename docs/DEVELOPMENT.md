# Development

This is an independent port of the original 2002 Xbox game. Prior research consulted BuffyNX, but no title-specific code, symbols, seeds or overrides from that project are imported. Read [provenance](PROVENANCE.md), [decisions](DECISIONS.md) and the [bring-up summary](BRINGUP.md).

## Build from source

Follow [SETUP.md](SETUP.md) for the player path. Both extracted source releases and Git checkouts use the exact dependency pin in `dependencies.lock.json`; the bootstrap helper does not require a root Git repository.

The runtime patches are separate source diffs. Bootstrap may apply them explicitly:

```sh
python3 tools/bootstrap_runtime.py --apply-patches
```

It preserves an existing checkout at the correct pin. The patch step refuses unexpected/partial modifications rather than resetting them.

## Tests without game content

With Python 3.12 and the native compiler installed:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-toolkit.txt -r requirements-textures.txt
python3 tools/bootstrap_runtime.py --apply-patches
make test PYTHON=.venv/bin/python
make host-probe
make launcher
```

Tests use synthetic fixtures and selected real generic runtime functions. They do not require a game, an AI model or private HD masters. A host probe or compiled executable does not prove that the menu/gameplay works.

## Permanent fixes

Identify the XBE against `config/title.json` before an address-dependent adaptation. Permanent title fixes belong in the generator adapter or reviewed source override, with the calling convention, evidence and a regression test. Do not edit generated C as the permanent fix.

Preserve guest registers, flags, stack, memory effects and relevant floating-point semantics. Define a reproducible case before optimizing. Keep runtime changes separate, documented and tested. Avoid claiming success beyond the observed stage: host probe, compiled runtime, menu, gameplay and long-session stability are different results.

## Local-only data

`private/`, `generated/`, `build/`, `artifacts/` and `logs/` contain local inputs and outputs. They are not release source. Keep long traces and research snapshots in artifacts; reduce useful regressions to synthetic fixtures. Never stage game files, generated game sources, game binaries, saves, assets, model weights or secrets.

Optional local-AI developer tools are included as source, but are not used by setup or gameplay. Proposals need review and validation. They do not execute their own suggested commands.

## Preparing a release

Use [the release process](../release/PUBLISHING.md). The release file list is explicit; newly added files are not picked up automatically. Public documentation overlays keep private research histories out of the exported kit. The exported list is normalized so the source kit can rebuild itself.

The source-only CI checks packaging and bootstrap with synthetic repositories. It does not build or run the proprietary game and does not establish a Linux game port.

## Inspect original outfit resources

For native wardrobe development, inventory the installed user's supported game:

```sh
/usr/bin/python3 tools/game_resources.py > artifacts/native-outfit-inventory.json
```

This verifies Default.xbe, reads resource metadata and emits JSON only. It neither
exports game assets nor enables an outfit selector. Model payload presence does
not prove animation compatibility or safe switching during play. The native preview and gameplay results are recorded in BRINGUP.md.

## Rebuild for the native outfit selector

The 0.2 outfit selector changes the game generator and native bridge. The new
updater can regenerate/build it automatically; older alphas need the 0.1.1 updater
bridge or the new kit’s update command. For a manual developer rebuild, retain the supported imported ISO
files, existing analysis outputs and save profile; regenerate and rebuild locally:

```sh
.venv/bin/python tools/pipeline.py --stage recomp
make game-build
make launcher
```

Run the normal full setup/generation instead if the prior analysis outputs are
missing. No ISO reimport is required for an intact supported installation.
`tools/play.py` enables the private resource view only when the binary contains
the protocol marker emitted by the reviewed generator binding; merely linking
`outfits.c` into stale generated code keeps the classic menu. Use **Options → Outfit selector** to enable or disable it before launch. Main and
Pause include animated 3D previews, with immediate application on Resume. For diagnostics,
`BUFFY_NATIVE_OUTFITS=0` disables the feature without deleting preferences.

The title/byte guards, original resource hash, native stack/CPU ABI checks and
private resource namespace must remain in place. Never hand-edit generated chunks
as a permanent fix. No additional outfit assets may enter the source kit.


## Discord level observation

`tools/discord_levels.py` reads the verified player's missionlist payload and
incrementally observes successful disc-pack opens in the pinned host log. It uses
no guest memory or new native binding. Its tests use synthetic mission text and
log fragments. This presence update itself needs only supervisor/launcher changes;
the native stock-outfit selector above still has its separate regeneration requirement.
The public application ID/key are source metadata; original mission text and Discord
artwork remain outside the source kit. See DISCORD.md for operation and validation.
