> **Decided with the user, 2026-11-20 ("Yes, as recommended")**: port the boss room and its 12 fights; Omega Weapon as a 13th choice with Mato's optional reward (steal Megalixir, drop the Omega Weapon item); the Dragon's Den left out.

# ted-ex: T-Edition EX 2.0.6 against 3.0.7, and how EX joins the T-Edition mod (2026-11-20)

Files (mine, new): `pr/tools/ted_ex.py` (read only: the catalog; `python tools/ted_ex.py` -> `pr/build/t-edition/ex/catalog.json` +
`catalog.txt`, ~8 s; `tables`, `content` subcommands), `pr/build/t-edition/ex/`. Nothing else edited, nothing committed or
installed, no game or emulator run (all from the two ROMs, the JP ROM, the README/spoiler docs and the kit's decoders).

## 1. What EX is

EX is a second ROM hack on an OLDER T-Edition (Tsushiy's EX 1.6.3 on T-Ed ~2.9; Mato's English EX 2.0.6), a "bonus disc"
played by loading a 3.0.7 save ("save swap"). EX's own content is small; everything else in the ROM is old T-Edition that
EX deliberately broke or stripped to make room ("not designed as a standalone game", EE 508):

* **The boss room** (SNES map 471, behind a door EX opens in the Mog House, map 467): a Moogle (EE 512-519 menu) starts
  12 super-boss fights; two item shops. Each win sets one event bit that 3.0.7's Collection Room reads for its paintings.
* **The Dragon's Den** (maps 417-432): old T-Edition's GBA-style super dungeon (3.0.7 replaced it with the Labyrinth /
  Eureka / Crystal Tower). Its bosses are 3.0.7 monsters in older versions, except **Omega Weapon** (monster 460), the
  one boss 3.0.7 lacks. Mato's notes call it a found-later secret; the walker finds no way into it in EX
  (map 430's event tile leads to 429; nothing leads into 430; the world-map exits are 3.0.7's minus three).

| menu (EE 513/514/518/519) | event pack | formation (AI phases) | monsters (EX slots) | bit on a win | 3.0.7 reads it on |
|---|---|---|---|---|---|
| The Spectre | 0 | 0 | Cloud of Darkness 256 | 267 | maps 469, 494 |
| The Fiend | 1 | 1 -> 2 | Golbez 257, 258 | 000 | 469, 494 |
| The Darkness | 2 | 3 -> 4 | Zeromus 259, 260 | 268 | 469, 494 |
| The Mighty Tree | 3 | 5 -> 6 | Exdeath 261, Neo Exdeath 269 | 269 | 469, 494 |
| The Hero | 4 | 7 <-> 18 | Sephiroth 264, 277 | 26A | 469, 494 |
| The Witch | 5 | 8 | Ultimecia 265 | 26C (only if battle bit $44 clear) | 469, 494 |
| The Chaotic | 6 | 9 | Chaos 266 | 275 | 469, 494 |
| The Tyrant | 7 | 10 -> 11 | Mateus 267, 268 | 2A1 | 469, 494 |
| The Royalty | 8 | 12 -> 19 (23) | Kam'lanaut 270, Eald'narche 271, Orbitals 278/279 (hidden) | 26D | 491, 494 |
| The Divine Might | 9 | 17 -> 13..16 (rotating) | Ark Angels 272-276 | 2C1 | 491, 494 |
| The Reaper | 11 | 20 | Kuja 280 | 2C2 | 469, 494 |
| The Unsent | 12 | 21 -> 22 | Seymour 281, Anima 282 | 002 | 469, 494 |

(pack 10 = formation 19 alone, unused by events; formation 23 = Eald'narche + Orbital, reached by Eald'narche's battle
event F7 5.) After each battle: CA/5E9F (lost -> CC/E55C, vanilla's game-over scene on map 5; identical in 3.0.7).
Battle backgrounds come from the 4D command (7, 38, 2, 39, 54, 32, 26, 40, 28, 25, 23, 34 in menu order of packs 0-12).
No 3.0.7 event sets those 12 bits; 3.0.7 only reads them (paintings). EX sets nothing else 3.0.7 reads.

## 2. Catalog (details: `pr/build/t-edition/ex/catalog.txt`)

**Tables** (EX's C0/C1/C2 differ from 3.0.7's only in these operands; `ted_ex.TABLES`):
monsters EA/7000 (3.0.7 57/3E00); AI scripts E9/7000 (5F/58F0), pointers FF/F300 (same address, EX's contents);
steals/drops 41/EA00 (EX's roll 41/D300 is older: 178/50/20/8 of 256, no RNG overrun); formations CF/5900, flags CF/2400,
packs CF/4800, event packs CF/5000, map packs CF/5600 (same); formation-id constants $2D7/$2D8 (3.0.7 $2E9/$2EA);
short exits 4B/1BFE (4B/9BFE); map graphics pointers DF/DA00 (the JP ROM's; 3.0.7 40/0B00); all other field tables at
3.0.7's addresses; dialogue 4B: 5C/9CE0 EMPTY (one pointer); EE 51/E600 (1263, EX's own numbering: EX 510 = Mog House
welcome, 3.0.7's 506 is its own); monster battle lines CF/E000 -> bank 55 (lines 1-29 = EX's bosses); Mato's name
tables at 3.0.7's addresses (long monster names 55/D650 x 512); item data ED/8F00 + ED/AD00; songs as 3.0.7.

**Monsters**: of 512 slots EX vs 3.0.7: 89 same, 335 older data, 52 Mato's older names, 8 moved, **28 EX's own**:
256-282 (written over 3.0.7's 256-282: Ymir, Angler Whelk, Mega Armor ... Kefka) and 460 Omega Weapon (over Azrael).
262 (Phantom Train) and 263 (a second Exdeath) are leftovers no EX fight uses. The block's AI (spoiler file
`ff6_t_ex_enemy_script.txt` = exactly 256-282): HP 55,000-65,000, levels 119-128; Kam'lanaut/Eald'narche 4,6xx HP
(phase fights); every block monster steals Reincarnation x2, drops Megalixir (all 4 slots); Omega Weapon steals/drops
Dagger (EX zeroed the table; Mato's optional "Alternative Omega Weapon Steal And Drop EX ONLY.ips" sets 41/F860 to steal
Megalixir x2, drop item 230 Omega Weapon). Battle lines 1-29 (texts in the catalog: "We are the Cloud of Darkness...",
"Come, Shadow Dragon!", ...); Omega Weapon's line 101 is blank in EX.

**Spells**: EX's content AI casts 184 spells; 43 differ from 3.0.7. **~31 are EX's own attacks written over 3.0.7's
enemy attacks 166-237** (Aura Ball over Holy Judgment, Big Bang over 10,000 Volts, Supernova over Tidal Wave, Time
Compress, Meteorite, Almagest, Holy Star, Cross Reaver, Black Hole, Grand Cross, Apocalypse, Omega Javelin, Pale Horse,
Genesis Rock...); the other 12 are 3.0.7's spells retuned/renamed by a byte or two (Death, Comet, Kill...).

**Formations**: EX's own = 0-23 (over 3.0.7's 0-23: vanilla's early random fights). Formation flags e3 02 00 0c for all
(byte 3 bits 4-7 = 0: battle music index 0). The den uses event packs 159-176, 185 (formations 630-641, 667-682, 718)
and random packs 228-238 (formations 318, 447-495, 517-525, 627-629, 657-658).

**Maps**: EX has 466 of 3.0.7's 505 slots (none of its own numbers); 3.0.7's 415 and 472-510 are missing. On shared slots
the tables differ as an older build (NPCs 278 maps, chests 62, exits 38, events 16); layouts/graphics differ only on
417-428 (EX's den, layouts 355-380: same pointers as in 3.0.7, used by no 3.0.7 map), 463/464 (older Developers' Room)
and 471. EX's own maps:
* **471 boss room**: 64x64, layout 298 (blank) drawn whole by its entrance event EA/0000 (two 73 commands, 49x38 on BG1 and
  BG2, then CD/A760 animates object 16); graphics sets [210, 41, 106, 2] (no 3.0.7 map shares them), tile props 5, palette
  53, music 238; NPCs: 0 Moogle (sprite 220) at (24,15) -> CD/A780; 1/2 shopkeepers (sprite 105) at (11,18)/(37,18) ->
  shops 107/108; 3-8 sprite 101 decorations (22-26, 16-18). Exit (24,32) -> 467 (79,28). No chests.
* **467 Mog House** (EX's version): entrance CD/A090 redraws (80,37) [08] (closes the Developers' Room door), (79,26)-(79,27)
  [07 17], (78,28)-(79,28) [67 67] (opens the new door) + three BG2 cells (y 89-99); exit (79,26) -> 471 (24,31) replaces
  3.0.7's (80,37) -> 463. NPC 1 (CD/A600, EE 516): unequip all / absent members; NPC 2 (CD/A050, EE 510/511): "What can I do
  here? / Change party / Change outfits".
* **417-432 Dragon's Den**: 12 maps with random battles (packs 228-238), 21 chests (Elixir, X-Ether, Megalixir, Lambent
  Hat, Power Tab, Rubber Suit, Ribbon, Genji Glove, Maximillian, a monster-in-a-box...), bosses Ahriman, 8 Grimoire
  books, Archfiends, Twinhead Dragon, Echidna, Cerberus, Omega Weapon (428, pack 168), Ultima (428, pack 185 + esper 66).

**Events**: decoded with ted_events' dialect on the EX ROM: 52,406 instructions, 14 unknown: 13 B6 + 1 CE, all on old
content (maps 24, 50, 78, 113, 115, 188, 196, 250, 251, 325, 353, 459, 461): B6 after a 4B/EE dialogue that is blank in
EX (choice counts come from the text). None on EX's own maps. EX's own scenes: 471 (EA/0000, CD/A780 + CD/A520-A750, shops
CD/8100/8103, CA/5E9F), 467 (CD/A090, CD/A600, CD/A050), den (CC/E7D0-CD/18F7). EE dialogues they use: 508-519 (hub) and
130-178 (den: blank in EX).

**Items**: no new items (all 256 names equal 3.0.7's; 32 records differ: prices, a few stats, Smelling Salts' byte 27).
The second item table ED/AD00 (155 records) is T-Edition's own (in both ROMs, 13 records differ). Hub shops: 107 Potion,
Hi-Potion, X-Potion, Ether, Hi-Ether, X-Ether; 108 Antidote, Smelling Salts, Gold Needle, Holy Water, Phoenix Down,
Reincarnation (3.0.7's shops 107/108 are weapon/armor shops: the ids collide).

**Music**: none new: EX's song tables equal 3.0.7's (one song pointer differs, song 47). EX's content plays map music 238
(boss room), 240 (Mog House), 104/107/167/57 (den), song 62 (game over).

**Save swap**: carries the whole SRAM; what matters to 3.0.7 is only the 12 boss bits. In EX the same save runs on EX's
older data (items, spells, monsters) and EX's Mog House (party change, outfits, unequip).

## 3. Merge plan (one mod, no save swap)

**Scope (recommendation)**: phase 1 = the boss room + its 12 fights (28 formations' worth of data: formations 0-23,
monsters 256-282, ~31 attacks, 29 battle lines, EE 508-519 text, 2 shops, the door). Omega Weapon as a 13th menu entry in
the boss room (formation 641 + monster 460; with Mato's optional reward, steal Megalixir / drop Omega Weapon item 230)
rather than porting the den. The den itself: leave out (it is old T-Ed content that 3.0.7 superseded, sits where 3.0.7's
dungeon is, has no entrance in EX, and EX stripped its text, battle lines, drops and part of its monsters' AI); ask the
user if they want it later as a portal from the boss room.

**Ids** (EX gets its own block past T-Edition's in every number space; `ted_ex.EX_*_BASE`):

| kind | T-Edition 3.0.7 | EX (virtual SNES id) | PR id |
|---|---|---|---|
| monsters | 0-511 (PR 1-384, 1000 + e for 384-511) | 256-282 -> 512-538, Omega Weapon 460 -> 539 | 1000 + id = 1512-1539 (idmap.MONSTER_EXT) |
| monster specials | ability 6000 + e | 6000 + id = 6512-6539 | (port_monster_ext.SPECIAL_BASE) |
| formations | 0-767 | 0-23 -> 768-791; Omega 641 -> 792 | first party 30000 + f = 30768-30792 |
| event packs | 0-255 (3.0.7 uses 247) | none: EX events name the virtual formation directly | - |
| spells / attacks | 0-255 | EX's own attacks keep their SNES number in an "EX" space | abilities 7000 + s (7166-7237; PR ends 5917) |
| battle lines (AI F3) | 3.0.7's | EX 1-29 (+ Omega's) | own message keys, e.g. MSG_TEDX_BATTLE_<n> |
| maps | 0-510 (PR 644+ for 416-510, ted-maps) | 471 -> 512 (den 417-432 -> 513-528 if ever) | next block after ted-maps' last id |
| shops | 0-127 | 107/108 -> 128/129 | new merchant rows after the porter's |
| dialogue | TED_D<n>, TED_E<n> | EX's EE numbering | TEDX_E<n> (keys; EE 508-519) |
| event bits | 3.0.7's | the 12 boss bits stay as they are (3.0.7 reads exactly them) | the same PR flags ted-events' FlagAlloc gives 3.0.7 |

Formation records hold 9-bit monster ids, so EX's formations can't sit in the in-memory image as 15-byte records naming
512+: the EX source hands them over decoded (monster lists already remapped), not as SNES records.

**Per workstream**

* **Lead / porter** - a second source for the EX records: `ted_ex` reads EX's tables (all addresses above); a
  profile hook (e.g. `profile_tedition.ex_records()` built on ted_ex) adds EX monsters 512-539 (stats from EA/7000, names
  55/D650, specials, steals/drops from 41/EA00 with the 3.0.7 odds, Omega Weapon's from Mato's optional patch if the user
  wants), their AI (E9/7000 + FF/F300, with F2 formation numbers and attack bytes remapped: formations 0-23 -> 768-791,
  EX's own attacks -> the EX ability space), formations 768-792 (decoded), the 12 battle lines, the ~31 EX attacks as new
  ability rows (spell data C4/6AC0 x14, names 55/7C80, a PR look by name/template as port_spells does), shops 128/129.
  Items: nothing (3.0.7's). Don't take EX's data for anything outside this set (it is old T-Edition).
* **ted-monsters (port_monster_ext)** - accept extra monsters/formations from a second source (ids past the image's 512
  monsters / 768 formations; formation monster lists given directly), so 1512-1539 and parties 30768-30792 come out like
  3.0.7's; boss party settings (script 0, no escape) for all EX formations; battle background from the event's 4D bg byte
  (above), not a map; music: formation flags say index 0 (open: whether T-Edition plays special songs for these).
  Art: 28 new sprites (EX's monster graphics entries, like 3.0.7's CF/1A00 list; the BC monster-art hook).
* **ted-maps** - the boss room 471 as a new PR map (virtual 512): layout 298 + entrance event EA/0000's tiles (the same
  "drawn by its entrance event" path as 3.0.7's layout-298 maps, `ted_maps.entrance_tiles` on the EX ROM with
  `ted_ex.Roms().maps[0]` tables), graphics sets [210, 41, 106, 2]; a PointIn at (24,31), a GotoMap at (24,32) -> 467's
  (79,28). In 3.0.7's 467 (Mog House): keep its door (80,37) -> 463, add EX's door: the cells EX's CD/A090 draws at
  (79,26)-(79,28) and a GotoMap at (79,26) -> 471 (24,31), and an arrival point at (79,28).
* **ted-events** - translate EX's scenes from the EX ROM (`ted_events.load("ted-ex")` + EX's EE table 51/E600 for text):
  the boss Moogle CD/A780 (choices EE 513/514/518/519 -> CD/A520-A750: 4D pack -> the virtual formation, then CA/5E9F,
  then the bit), the shops CD/8100/8103 (-> shops 128/129), the room's entrance animation CD/A760; in 467 replace 3.0.7's
  save-transfer lines (its EE 506) with EX's EE 511 adapted (no save swap: "beat them and the paintings appear"), and
  optionally EX's unequip Moogle (CD/A600, EE 516). Add Omega Weapon as a 13th choice if the user wants it. Mapping
  overrides the translator needs for EX: pack -> formation (`ted_ex.HUB_BOSSES` + EX_FORMATION_BASE), map 471 -> its PR map,
  dialogue keys TEDX_E<n>, shops 107/108 -> 128/129, bits unchanged.
* **TedPlugin** - nothing EX-specific in the rules (same battle engine as 3.0.7). EX's battle-time item switch (C2/271B,
  2A5E -> ED/AD00 when $1440 bit 0) is not replicated (3.0.7 doesn't do it; in EX it reads a field-menu flag left over).
  The plugin's SNES-AI runner must take the EX scripts (ids 512-539) and EX's battle events (F7: 2 Zeromus, 4 Ultimecia,
  5 Eald'narche, 6 Exdeath; EX's battle-event scripts are its own, not looked into yet).
* **Text** - EE 508-519 (hub, Mog House), 29 battle lines, monster names (Mato's EX names), ~31 attack names: all English
  from Mato's EX build; Japanese for the PR's other languages: none (EX's JP is Tsushiy's EX 1.6.3, not in the project).
* **Balance** - EX was tuned against old T-Edition; the bosses will meet 3.0.7's party (stronger equipment and rules).
  Worth one test pass per boss once ported (harness: warp to 512, script the Moogle choice; no save needed).

## 4. EX's own problems: fix, leave out, replicate

| problem (Mato's notes / measured) | cause found | merged mod |
|---|---|---|
| "Most to all random battles are garbage, soft lock/crash" | EX wrote its bosses over formations 0-23 and monsters 256-282; 28 maps' random packs hold those formations, 50 other formations name monsters 256-282, 226 other monsters' AI pointers land inside EX's boss scripts (E9/7000-817B), 78 old monsters' AIs switch (F2) to formations 0-23 and 207 show lines 1-29 | not replicated: EX's content gets its own ids; 3.0.7's random battles are untouched |
| "Don't talk to flame NPCs, you'll crash"; "blank text boxes, incl. flying the airship" | EX's 4B dialogue table (5C/9CE0) has one entry: every 4B text reads a zero pointer (text from 00/0000 = WRAM: blank, or control codes that hang); the 18 den NPCs with sprite 104 (the flames) and one more start with a 4B dialogue; EX also blanked 1164 of 1263 EE dialogues (den 130-178) | den left out; the boss room only uses EE text that exists |
| Battle lines of old monsters blank / other bosses' lines | battle lines 30-255 are empty strings; old AIs that show lines 1-29 now show EX's boss lines | EX lines get their own keys |
| Old monsters drop/steal nothing ("Dagger") | 486 of 512 steal/drop records zeroed; only the boss block has items | EX block keeps Reincarnation/Megalixir; Omega Weapon: offer Mato's optional reward |
| Smelling Salts acts as the old Magicite Shard | EX's item 249 byte 27 = 1 (3.0.7: FF) | 3.0.7's item data: fixed |
| Omega teleport -> black screen, take the airship blind | den's exit event after Omega (map 428) into a world state EX didn't set up | den left out; Omega as a boss-room fight returns to the room |
| Ghost NPCs push you off bridges; the turtle only goes north/south unless goaded | den NPC movement scripts (sprites 111 ghosts, 184 turtle) | den left out (if ported later: replicate, they are puzzles) |
| No way into the Dragon's Den in EX | nothing loads map 430 (its tile event leads to 429); 3.0.7 put its own dungeon there | den left out; a portal from the boss room if wanted |
| 14 undecodable event commands | B6 choice counts read from blank texts; old-content maps only | irrelevant to EX's content |
| Monsters 262 (Phantom Train) / 263 (Exdeath) in the block, unused | leftovers | not ported |
| EX battle item switch ($1440 bit 0 -> ED/AD00) | field-menu flag read in battle | not replicated |
| Ultimecia's bit only set when battle bit $44 clear | her fight's own end condition (CD/A5EB) | replicate (it's the fight's rule) |
| Bits 000 and 002 used as boss bits (Golbez, Seymour) | T-Edition reassigned them (3.0.7 only reads them in 469/494) | keep the numbers; ted-events' bit -> flag map must not tie 000/002 to vanilla's meaning |

## 5. Open (for the lead / the user)

* Omega Weapon as a 13th boss-room fight (recommended), and with Mato's optional reward (steal Megalixir, drop the Omega
  Weapon item) or EX's Dagger?
* The Dragon's Den: leave out (recommended) or a later portal?
* Boss music: EX's formations ask for battle song index 0; whether T-Edition maps super-boss fights to its own songs
  (ted-battle / music) is not established.
* EX's 28 monster sprites: EX keeps 3.0.7's graphics-entry table (CF/1A00, 5 B x 512, read by the same C1/C3 code);
  the entries of 256-282 and 460 are EX's own (76 entries differ in all; the others are old T-Ed's). The art itself is
  where those entries point; checking whether some reuse 3.0.7 sprites (as port_monster_ext.match_art does) is next.
