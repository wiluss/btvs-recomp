# Development

This is an independent port of the original 2002 Xbox game. Prior research consulted BuffyNX, but no title-specific code, symbols, seeds or overrides from that project are imported. Read [provenance](PROVENANCE.md), [decisions](DECISIONS.md) and the [bring-up summary](BRINGUP.md).

## Build from source

Follow [SETUP.md](SETUP.md) for the player path. Both extracted source releases and Git checkouts use the exact dependency pin in `dependencies.lock.json`; the bootstrap helper does not require a root Git repository.

The six runtime patches are separate source diffs. Bootstrap may apply them explicitly:

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
