# T-Edition on the Pixel Remaster

Owner: T-Edition lead. Moved verbatim from `pr/PORTING.md` on 2026-11-20 (roadmap item 5); `git log --follow` / the split commit trace any paragraph. Status rows stay in `pr/PORTING.md`.

## Live progress (newest first)

Earlier rows (2026-11-20 and before) are in `docs/progress-2026-11.md`.

| When | Batch | Result |
|---|---|---|
| 2026-11-26 00:30 (coordinator local_e699d13a) | ted-final (73 rooms), ted-gate-act1 (113 requests), ted-art-1/2 (PC) | **0.1.1 pre-release.** ted-final 72/73 (126 = the known test stall on 125's looping vanilla script; the re-enabled rooms 10, 11, 65, 76, 100 pass). ted-gate-act1 38 pass: its failures are the New Game state (26 "no entity runs script": story-layer and hidden NPCs) and **a harness artifact found tonight**: a `tedtalk` whose script never starts (the entity is there but its script doesn't run: 21 such) leaves the game unable to finish its next map load. ted-art-1: map 10 loads straight after New Game, then map 9's failing talk (11003), then map 10 sits at "scene other"; ted-art-2: the same talk, then map 3 (no T-Edition load script) hangs too. So every gate failure after such a talk in the same game (maps 10, 12-17 in run 2, 65 and 100 in run 3, map 42's talks) is the test's, and the 17:27-18:0x deny-listing of the five entrances came from the same artifact. To do: TedHarness `tedtalk` should cancel a request whose script doesn't start (or the gate relaunch after one). Zip TEdition-PR-0.1.1.zip (42 files more than 0.1.0, none less; DLL 583fd19b). |
| 2026-11-25 night (coordinator local_e699d13a) | ted-newgroups-1 (PC) | **Runtime NPC groups (ArtSwap `new_groups`) still stall map loads: `ted_npc_art.NEW_GROUPS_ON` stays False.** With True (mapobject rows 3003-3017 and 3100-3104 naming `mo_ted_s*` groups), the first map after New Game (map 112, Map_20160, which places none of them) sat in "field state ChangeMap" for 3+ minutes, and the log had no ArtSwap "new group atlas" line at all: ArtSwap.NewAtlas was never asked, so the stall comes before any atlas check, from a mapobject row naming a group the game never shipped. Rooms that would show them: 14, 17 and new maps 697, 699, 700, 703, 724, 729, 748, 756. Run stopped by hand and the PC restored (`ted_testinstall.py restore`). The fix is the kit's (what the field loads for mapobject rows). |
| 2026-11-25 night (coordinator local_e699d13a) | ted-deny-1 (PC; build/batches/ted-rooms.py: walk-ins + `talk:` items, each talk followed by leaving the map) | **Deny-list 32 -> 23.** Re-enabled after passing 10/10: the entrances of maps 10 (CD/3290), 11 (CC/3950), 65 (CA/ED73), 100 (CC/6F41, CC/6F5C) and 76 (CB/9797@Map_20101_1), all listed at 17:27-18:0x while the runtime NPC groups were on (the same "room never finishes loading" that turned them off at ~19:00; map 65's T-Edition part is a lone Nop); map 42's three dialogue NPCs (CA/7D21, CA/7D43, CA/7D5B: branches and messages only, the layer edit only swaps their script ids), talked to on map 42 (and CA/7D21 on map 223), then the party leaves to map 43. CD/4DF0 (map 77's merchant, `TED:shop 997`) stays off with a new reason: at 17:27 the shop opened and the game ended right after; the retest ran the talk but the shop never opened (no "[ted] shop 997 opened"). Still off: the cross-place rooms of CD/81A0, CD/4A90, CE/76B0, CD/3BBE (entrance events wired into rooms of other places that share the layout: they don't belong there), CB/A295 (a script that never ends), CA/7D09 (the quest giver), CD/1DC0 (a 600-instruction cutscene). |
| 2026-11-25 evening (coordinator local_78fe7a05: the first release's gates) | ted-gate-1, ted-gate-battles, ted-gate-act1 (+ recheck, ted-final), ted-zip-smoke; PC + laptop | **The 0.1.0 "Act 1 preview" gates.** Battle 72's PreeMptiveMes stall is gone (the kit holds commands in a battle's opening); field gating ok (maps 300/131/297/112). Found and fixed: the **coreclr crashes** after battles (TedEncounters' GetPreeMptiveWeight postfix declared `OwnedCharacterData[]` / `int[]` where the game passes Il2Cpp arrays: every battle's opening read garbage, length 547749760, and corrupted memory; WER showed coreclr.dll 0xc0000005 at 0x1d1fdd, the runner's "started by someone else"); rule 44 never held (TED hooked UpdateGaugeIncrease and read nowState, which FF6 never uses: now the kit's SnesActionFreeze, "time held 1.6-2.4 s for an action"); the battle party id -1 in event/harness battles (InstantiateManager.Create hooked: rages + the result line); the equipment-slot fill ran before the party existed. 12-battle sweep (vanilla, new monsters 30723/30726/2542/30696, bosses 436/447/469/515) ends with no exception. New `tedtalk <script id>` (EventProcedure.RequestEntityAction on the entity: T-Edition's scripts can't start by name, the field loads only what its entities name): 84 NPC scripts on the first act's maps run through it; rooms with T-Edition entrance parts checked by walking in (BNW controls load the same rooms). Turned off for players (data/ted_event_denylist.json, 32 entries; ted_events + ted_quests honour it, "event@room" for one room): entrances whose rooms never finish loading (CD/3290, CA/ED73, CC/6F41, CC/6F5C, CC/3950, CB/9797@76, the cross-place rooms of CD/81A0, CD/4A90, CE/76B0, CD/3BBE), scripts that never end or trap the party (CB/A295, CD/4DF0, CA/7D21/43/5B, CA/7D09's quest giver, CD/1DC0's room). Battle backgrounds (recoloured PR paintings) moved to costumes/backgrounds, left out of the zip. Zip 4.6k files, ~8.7 MB, no game files; installed on the laptop's clean copy it boots, plays the opening battle, walks the field. |
| 2026-11-21 night (after the break: the second item bank, shops, faster builds) | **All 279 of T-Edition's items through the porter, every shop stocked, costume switching on, the build incremental** (ted-monsters, ted-events, TedPlugin, bc-sprites; reviewed by the lead). The kit's held set landed through the kit lead (BNW and WC ports byte-identical): the 24 second-bank relics on rows, 7 of their chests on vanilla maps, 42 boss-reward parties and 278 Coliseum wagers for TedPlugin; ted_build's shop rule gives the 31 shops the porter matched to none their own product group (all 110 stocked shops mapped for `TED:shop`). TedPlugin: rule 57, Lunar Curtain's SOS Reflect, costume layers on the kit's `ArtSwap.SetLayer`. The monster art recipe in palette-slot form (no PR colours) joins the repository. `ted_build`: incremental merge (76.8 s -> 9.0 s, `--verify` identical to a full merge), one build at a time. ted-events: 104 events, a walk-on NPC wiring bug fixed (one match had rewired all five). Checks: ted_build --test --verify 0 conflicts, 0 problems, test_mod 50 OK, tests 62 of 63 (the pub quests' folder test, sent back); pushed 74a0809, 36df92b. ted-monsters archived (its work done; a slot for BNW). Not run in game yet. T-Edition ~54% |
| 2026-11-20 evening (consumables, events at 9% stubs, the kit freeze over) | **T-Edition's consumables work as in T-Edition; its events catalog is down to 9% stubs; the day's work is pushed** (ted-monsters, ted-events, ted-ex, ted-maps; reviewed by the lead). Consumables (`ted_build` consumable rule): item identity copies only a row's look, so re-slotted consumables kept their old row's effect (Power Tab opened the rename screen, Reincarnation was a thrown Super Ball); now the Tabs, Golden Apple and Soma Drop use the PR's stat function, Antidote, Smelling Salts and Gold Needle cure what T-Edition's records say, Reincarnation revives fully. Events: party checks (DE-E3 with case bits) as the PR's BranchByCharacter removed ~11,600 stubs catalog-wide; entrances run after each room's own load script; shops through TedPlugin's `TED:shop <group>` (82 vanilla shops matched); 83 events on vanilla maps (122 wired scripts), 155 scripts on maps 200-415, 262 on the new maps. The second item bank, the 42 boss-reward parties and T-Edition's own shops wait on kit work, which the end of the WC freeze (20:11) now allows. Checks: ted_build --test 0 conflicts, 0 problems, test_mod 50 OK, tests/test_ted* 58 OK; pushed f6aad03, e259ffd. Not run in game yet. T-Edition ~52% |

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
