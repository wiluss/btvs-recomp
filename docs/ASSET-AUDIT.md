# Original asset audit

Read-only audit of the supported imported USA game on November 14, 2026. The XBE
is verified against `config/title.json` before inspecting actual pack payloads.
No BuffyNX resource list, symbols or title-specific code was used for this audit.
No assets are exported by the inventory or included in the source kit.

## Findings

| Content | Evidence | Possible use / limits |
| --- | --- | --- |
| Five Buffy outfits | Bronze, Workout, Cheerleader, Slayer and Dark Slayer have actual model/material payloads. Each gameplay model has one byte-identical geometry variant across its source packs. | These are already in the native selector. No sixth Buffy outfit model was found in the installed packs. |
| Main-menu Buffy | `guislayer/buffybronze.msh` has the same payload hash as gameplay Bronze. The menu also includes material entries ending in `_phan`. | The model is not another outfit. The material entries are candidates for visual experiments, not a confirmed hidden costume. |
| Buffy History Slayer materials | The face, body and leg textures have an original 512 × 512 top mip, versus 256 × 256 in gameplay. All seven shared mip payloads are byte-identical for each material; geometry is identical too. | Higher-resolution originals of the same outfit, not another costume. Useful source material for future HD work; no change to the current outfit selector or HD pack. |
| Scooby Gang | Cordelia, Willow, Giles and Xander have model payloads. | Candidates for a future model gallery. Skeleton, animation and gameplay compatibility with Buffy have not been established. |
| Vampires / bosses | Angel human/vampire, Spike, Drusilla, Master and other forms have actual payloads. | Possible gallery/preview content. They are not safely interchangeable Buffy outfits without rig/animation work. |
| Texture named `test` | `textures/all-purpose/skybox/test.mtx` appears in multiple campaign packs, including several cubemap material entries. | Its name does not establish that it is unused. Do not expose it as cut content on that basis. |

The 65 inspected packs contain **326 distinct base-model paths**, including
**76 character-model paths** (NPCs and posed variants included). Payload record
counts include duplicates across levels: 8,623 mesh records, 23,297 material
records and 49,114 bone-animation records. These are not unique asset counts.

Loose dialogue archives, WMV videos, music, XPR resources and `install.dat` also
exist. They were listed, but their contents were not exhaustively classified by
this pack audit. No unused map, audio clip or additional costume is confirmed.

## Reproduce

```sh
mkdir -p artifacts
/usr/bin/python3 tools/game_resources.py --audit > artifacts/asset-audit.json
```

The report lists actual model sources, Buffy mesh/material hashes and pack
locations, and names that merit investigation. It deliberately leaves
`confirmed_unused` empty. Resource presence, a suggestive name or absence from
a static reference search cannot prove that content is unused: the engine loads
resources dynamically and campaign coverage is incomplete.

Detailed local results are kept in `artifacts/presence-outfit-polish/`. Assets
remain private. A future gallery could reuse these resources from each player's
ISO; this audit does not implement such a gallery or unlock new playable actors.

## Buffy History material follow-up

The three actual Slayer material payloads were extracted and decoded locally
using the pinned generic Xbox texture decoder. Each History material contains
eight image levels, 512 down to 4 pixels; each campaign material contains seven,
256 down to 4. For face, body and legs, **every shared compressed image payload
matches exactly** (21 matching levels in total). The face decodes as BC3/DXT5;
body and legs as BC1/DXT1. Native pixel dimensions and decoded images confirm an
additional high-resolution top image, not a different outfit or palette.

The original 512-pixel textures have four times the top-level pixel count. They
may offer a better original source for later texture work, but their appearance
has not been tested as a replacement in gameplay and the existing HD pack has
not been regenerated. A 512-pixel original is not automatically preferable to
the current manually refined HD results. No new outfit entry was added.

Reproducible local evidence: `artifacts/history-materials/inspect_history.py`,
`verified-comparison.json`, source metadata and six decoded PNGs. All asset
payloads/images remain private and are excluded from Git and source exports.
