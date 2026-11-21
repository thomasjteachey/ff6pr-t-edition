# T-Edition on the Pixel Remaster

Owner: T-Edition lead. Moved verbatim from `pr/PORTING.md` on 2026-11-20 (roadmap item 5); `git log --follow` / the split commit trace any paragraph. Status rows stay in `pr/PORTING.md`.

## Live progress (newest first)

## T-Edition feasibility (2026-11-20)

Mato's English build (3.0.7 A7 r1, `build/t-edition/T-Edition 3.0.7 (Mato).sfc`, 6 MB ExHiROM on
the JP v1.0 ROM). Scoping only; no release planned yet.

**The porter reads it** (`tools/jp_layout.py` + `tools/profile_tedition.py`, `port.py tedition` ->
`mods/TEdition`, `test_mod` green). The JP ROM keeps nearly every data table at the US address
(checked table by table); only the espers (JP E6/F567, where the US ROM put its longer spell names)
and formation AP (D0/FE00) sit elsewhere, and names are kana fields. T-Edition then moved most tables
(found from the long loads in its code): items ED/8F00, monsters 57/3E00 (512 slots), steals/drops
41/EA00 (8 bytes: 2 steals, 4 drop slots at 174/50/20/12 of 256), formations CF/5900 (768), formation flags
CF/2400, sketches CF/1200, rages CF/1600, map properties 4D/0000 (512 maps), chests ED/8584 + 4B/4000,
AP F3/F000, AI FF/F300 + 5F/58F0 (30 KB, twice the US space: read past 3 MB through a hook on
`snes_ai.script`), layouts 41/0000. `jp_layout.build_us_image` writes every record T-Edition changed
into a US-layout image held in memory (nothing written to disk); records it left alone read as the
US ROM's. Mato's text: A-Z 20-39, a-z 3A-53; his build keeps full-length tables between ASCII
`****LABEL****` markers (LONG ITEMS, ENEMY NAMES LONG, LONG MAGIC NAMES, LONG ATTK NAMES = spells
54-255...), so the port gets full names ("Thief's Knife", not "Thief"), not the 8-letter menu ones.

**What ports for free** (no T-Edition code but the layout profile): ~75% of the data records
T-Edition changed (~3,300 of ~4,360): characters (50), items' data (251), spells/lores (234, each with
the PR look of the same-named spell: the spell porter's templates follow T-Edition's re-slotting),
espers (27, 181 learning rows), monsters (381), steals/drops (291, the 4 drop slots folded to 2),
formations (293), the Veldt, AP, shops (82 matched, 524 rows), sketches (384), rages (158), dances,
natural magic, 190 chests in 117 PR maps, encounters (306 new parties), monster AI (263 compiled + 42
bosses). Not: 94 new monsters (slots 384-511) and the 221 formations using them or numbered 576-767
(the porter's tables stop at 384/576; the PR needs new monster rows and art); 125 event packs on
those; 93 new maps and their 70 chests; T-Edition re-slotted items: 97 of its 256 item slots hold
another vanilla item (Mythril Sword in Valiant Knife's slot), so the data lands on a PR row with the
wrong look (the porter needs an item step like the spells' templates); per-character HP/MP growth;
16 redrawn monster sprites; ~25 relic bits and everything else in assembly. Names: items 110 and
spells 87 new or renamed, monsters 121.

**New maps**: kit infrastructure built for it (MODDING.md "SNES maps and places"): `tools/snes_maps.py`
(SNES map -> PR map(s) with tile offsets; 242 of 416 SNES maps placed from chests, exits and tile
agreement) and `tools/snes_rooms.py` (SNES tile -> PR tile stack + collision, learned from vanilla
rooms with the same graphics; a new map's files, package entry and master rows). T-Edition's 93 new
map slots are mostly copies of vanilla layouts with new events (layout 298 alone is used by ~25), plus
about ten new layouts (381-390). Test room: map 431 ($1AF, 16x16, new layouts 383/384, the Veldt
cave's graphics) -> Map_30761_6 (PR map 806, script 629): every cell has a PR tile, collision gives a
cave chamber with its doorway; on held-out Veldt cave rooms the learned collision is 88% right, the
exact tile stack 20% (the PR varies its decoration). In game: see the next paragraph.

**In game** (PC test runner, 2026-11-20 14:03, BNW active + the test folder; shots in
build/t-edition/shots): a new map id works through Magicite alone: `warp 806 1` loaded Map_30761_6
within a second and it renders (new_room.png: the cave chamber in the PR's own Veldt cave art, the
character at its doorway, the minimap drawn from the new map; a few cells along the lower walls black
or patchy where the learned stack is off). One step down onto its door fired the `GotoMap` and moved to
map 488 (Map_30761_1). Nothing beyond text assets was needed: tilemap/collision/entity JSON in an
existing group (its atlas), that group's `package.json` with the new map listed, `map.csv` and
`map_script.csv` rows, an empty map script. Right after arriving in 488 the game was back at the title;
the runner then found the harness's `load` had not loaded the save (the field was the title's idle
demo, which a map change ends), so that drop is probably the demo's, not the door's. **Confirmed
2026-11-20 15:19** (ted-newmap-diag, the runner's boot now a New Game warped to a free field, since no
save loads headless): 488 loads at its own entrance and at the arrival point added for the new room; the
party walked from 806 through its door into 488 and stayed there (8 s, no title), then walked back into
806 (shots diag_*.png). A new map id, its door and the way back all work through Magicite alone.

**Effort, revised**: still about 2-3x the WC port, now ~2.5x with the bulk clearer. Data is mostly
there (left: item identity, new monsters/formations with art via BC's monster-art hook, drops, growth,
costumes). Maps are a known per-room cost with the tools above, plus T-Edition's NPC/exit/event tables
(relocated like the rest). The bulk is events (~45 new events, 20 pub quests, changed vanilla scenes,
Cyan's dream battles: SNES event scripts rewritten as PR scripts by hand, as WC's 62 checks were) and
the battle overhaul (~40 listed rule changes with no asm source: reverse-engineered from T-Edition's
C2 changes and expansion code, then plugin code). Music (~200 songs) and costumes/portraits ride on
the Beyond Chaos SNES music player and sprite conversion. A generic SNES event script -> PR script
translator would cut the event work most, for T-Edition, BC's light events and BNW alike.

## T-Edition port (2026-11-20, lead session "FF6 T-Edition Pixel Remaster port")

Decided with the user: **one mod** for T-Edition and EX (EX's super-bosses, reached through the Mog
House door after Ultima, in the same game: no save swap); **players need no ROM** (the user: "why do the
players need their own ROM? (they don't for WC now)"): like BNW, the mod ships T-Edition's ported data,
and copies of the game's own files are made on the player's machine. **T-Edition's own songs and art
ship in the zip** (the user, 2026-11-20: permission from every mod's owner, "go ahead and bundle any
art/assets/music"): song pack (its own songs and samples), monster art, costumes and portraits are built
from T-Edition's ROM on the developer's PC and carried as the mod's data. FF6's SNES sound driver and built-in
instrument samples may ship too (the user has that permission); the SNES ROM, other SNES data and the PR's
files never do. The public repository still holds back data with PR colour values. Names: Magicite and data folder `TEdition`, plugin `plugin/TedPlugin`,
saves `ModSaves "TEdition"`, public repo github.com/thomasjteachey/ff6pr-t-edition (`tools/ted_publish.py`:
T-Edition's tools listed one by one, so a workstream's files join once reviewed; the kit as `kit/`).

Workstreams (child sessions, notes in the lead's side-session folder): **ted-events** (`snes_events.py`,
`event_translate.py`: SNES field event code decoded for the US, JP and T-Edition ROMs and translated into
PR scripts, validated on vanilla scenes the PR has; Mato's dialogue), **ted-maps** (`snes_maps.py`,
`snes_rooms.py`, `ted_maps.py`: T-Edition's relocated NPC/exit/event tables, coverage, tile accuracy, the
93 new maps into `mods/TEditionMaps` + `data/ted_maps.json`), **ted-battle** (`snes_disasm.py`, a 65816
disassembler for the kit; `ted_battle.py`: T-Edition's battle code against the JP ROM's; the spec of each
rule change). The lead: the porter, `plugin/TedPlugin`, the build that merges the workstreams' folders.

**Item identity** (`tools/item_identity.py`, kit; a profile's `item_identity = True`): T-Edition's item
list is rebuilt, not renamed: 97 of its slots hold another vanilla item, and many changed kind (Marvelous
Cheer, a weapon, in Aegis Shield's slot; White Robe, body armor, in Goggles'). Each slot gets an identity
(the vanilla item of the same kind and name: the PR's name, the SNES name, or one clearly closest
spelling), a row (the identity's; a new item its own slot's row when free and of its table, else the
freed row whose vanilla item looks most like it, else a new row) and a template (the identity, or the
vanilla item of the same kind and icon with the closest power; the mod's icon bytes are mapped to the
US ROM's from the identities). The row takes the template's look (`LOOK`: weapon category, battle sprite
and effect, guard icon; an armor row the equip slot of the mod's kind). `idmap.ITEM_OVERRIDES` holds the
rows that aren't idmap's default, and port.py hands the porters a vanilla baseline in the mod's item
numbering (in memory): each slot's record and name are those of the vanilla item its row held (a new row:
its template's), and vanilla's item references (shops, chests, steals and drops, starting equipment,
metamorph) name the slot that has that item's row, so every slot-by-slot diff writes exactly what differs.
New rows (copies of their template's row) get content rows and `MSG_PORT_<TABLE>_NAME/INF_<id>` keys and
are registered in `prdata.ADDED_ROWS`, so porters reading a fresh table find them. T-Edition: 255 items,
150 + 14 + 1 identities, 24 new weapon rows (92-115), 42 freed rows reused. Left: Mato's descriptions for
new items (a new row shows its template's), the PR's handling of weapon ids past 91 in game (not run yet),
what the stat tabs and T-Edition's other new consumables do (plugin).

**Build** (`tools/ted_build.py [--no-port] [--test]`, 2026-11-20): T-Edition ships one Magicite folder, because the game reads one copy of each map package and entity file: in the first in-game event test BNW's copy of map_20071's package.json hid the translated scripts, and T-Edition's own workstreams touch the same files (the porter's chests and the new maps' objects in six entity files, three packages). The porter writes `mods/TEditionPort` (profile `out`); the build makes `mods/TEdition` from it and merges `mods/TEditionMaps` and `mods/TEditionEvents` in with the kit's three-way merge (`tools/magicite_merge.py`), then runs the kit's Magicite check; `--test` runs test_mod on the porter's output. First build: 445 files copied, 59 merged, 0 conflicts, 0 problems. `mods/TEdition` is what is installed (StreamingAssets/Magicite/TEdition) and packaged; the workstreams' folders never are.

**EX** (study by the child session ted-ex, 2026-11-20; `pr/ted/EX_PLAN.md`, catalog `tools/ted_ex.py` -> build/t-edition/ex/): EX's own content is small: one boss room (SNES map 471) behind a door in the Mog House (467), where a Moogle starts 12 super-boss fights (Cloud of Darkness, Golbez, Zeromus, Exdeath, Sephiroth, Ultimecia, Chaos, Mateus, Kam'lanaut and Eald'narche, the Ark Angels, Kuja, Seymour), each win setting one event bit that 3.0.7's Collection Room reads; no new items, no new music, ~31 attacks of its own. EX wrote its bosses over T-Edition's formations 0-23 and monsters 256-282 and stripped its dialogue and drop tables, which is where its garbage random battles, flame-NPC crashes and blank text boxes come from; the merged mod gives EX's content its own ids instead (proposed: monsters 512-539 -> PR 1512-1539, formations 768-792, parties 30768+, abilities 7000+, boss room map 512, shops 128/129), so none of that is replicated. The Dragon's Den (old T-Edition's dungeon, maps 417-432) has no way in from EX; its only boss 3.0.7 lacks is Omega Weapon. **Decided with the user (2026-11-20, "Yes, as recommended")**: port the boss room and its 12 fights, add Omega Weapon as a 13th choice with Mato's optional reward (steal Megalixir, drop the Omega Weapon item), leave the Dragon's Den out. ted-ex implements it as its own workstream folder, mods/TEditionEX, merged by ted_build (built the same day: see the Live progress row "EX's boss room built").

**Drop slots**: a profile's `monster_drop_slots(e)` (SNES item ids in odds order) -> `drop_content_id1..8`;
the PR picks a drop slot by the game-wide `MONSTER_DROP_RATE_1..8` (game_constant_int 200-207; vanilla
88/12), which T-Edition's `game_constants` set to its 68/19/8/5 (T-Edition: one roll 0-255 per monster that
ends the battle dead, 174/50/20/12; a picked empty slot drops nothing; for monsters 32+ the roll reads past
its RNG table, a bug that skews their odds: the intended odds are ported). Not yet checked in the PR's code:
what it does when the slot it picks is empty. The PR's own monster rows
(385-611) keep two slots, so their odds become 68/20.
