# T-Edition media inventory (music and graphics) for the Pixel Remaster port

Written 2026-11-20 as planning input. T-Edition = Mato's 3.0.7 build (`build/t-edition/T-Edition 3.0.7 (Mato).sfc`) plus EX 2.0.6. The tools that will consume this (the SNES music player in `plugin/PrKit/Snes`, the sprite converter `tools/snes_charsprites.py` / `tools/pr_art.py` / `PrKit/ArtSwap.cs`) are being built elsewhere; this file says what T-Edition needs from them. Nothing here was run in a game or emulator. Numbers I read from the ROMs myself are marked "(ROM read)" and are not yet in any kit tool; everything else cites its file.

Conventions: ROM addresses are file offsets in the 6 MB headerless image, with the SNES bank form in parentheses (ExHiROM: file 0x4xxxxx = bank 4x, 0x3xxxxx = bank Fx; the producer lists use file offsets). Song numbers are decimal unless written 0x. "Main driver" = the C5 sound driver (file 0x50000), "second driver" = the bank-43 copy (file 0x430000), as `tools/ted_songs.py` names them. SNES monster id `e`; PR monster id = `e + 1` for 0-383, `1000 + e` for 384+ (`tools/idmap.py`, per `ted-monsters.md`).

Paths: `NOTES` = the T-Edition sessions' working notes (on the developer's machine, not in the repository); `GUIDE` = `mods/t-edition/3.0.7-lua-translation/FF6 T-Edition English 3.0/HTML (TRANSLATED GUIDES & INFO ...)/`; `PRODUCERS` = the same release's `For Producers/`; `README` = the Mato Notes README under `mods/t-edition/3.0.7-mato-translation/`. Line numbers for the HTML guides are lines of their text with tags stripped.

## Headline counts

| What | Count | From |
|---|---|---|
| Main-driver song slots | 255 = 70 vanilla with a PR track + 9 vanilla-slot without + 176 not vanilla | `data/ted_songs.json` |
| T-Edition's own songs (main driver) | 175 (player entries 74-248); the 176th "not vanilla" slot, 0x2F, holds no song | `data/ted_music_player.json`, `ted_songs.py` |
| Second-driver slots | 254 = 72 + 12 + 170; only 34 differ from the main driver's copy, 30 of them the fanfares/inn jingles (0xC4-0xE1) | `data/ted_songs.json`; slot compare (ROM read) |
| Fanfares and jingles | 21 victory + 9 inn + vanilla "Good Night" (0x38) = 31 (the guide gives 29 own ids) | `bgm.html` |
| Own songs played by map properties | 36 distinct (21 on the 94 new maps = 66 maps; 19 on 55 vanilla maps); the other 139 are for events, battles, the Falcon and the music player | `ted_maps.json`, ROM read |
| BRR samples | at least 157 (about 520 KB) against vanilla's 63 (about 201 KB) | ROM read, song-table walk with `snes_songs` helpers |
| Monsters needing PR art | 130 rows in `monster_ext.json`: 14 same, 18 recolor, 98 new (104 rows from slots 384-511, 26 from EX 512-539) | `mods/TEditionPort/monster_ext.json` |
| Redrawn vanilla-range monsters 0-383 | 76 of 382 match no vanilla sprite | `NOTES/ted-monsters.md` |
| Costumes | 56 = 4 per character x 14 characters (+ the default look each) | `GUIDE/dressroom.html` |
| Portraits | 75 distinct portrait images in 85 table slots (ROM read); 77 PNGs in the release folder | table at 0x380A00; `FF6 T-Edition Used Images/Portraits` |
| NPC sprite numbers used by the new maps | 112 distinct of 256 table slots; 634 vanilla NPCs re-numbered | `ted_maps.json`, `NOTES/ted-maps.md` |
| Map graphics | graphics sets 82-85 are T-Edition's own (82 and 83 used by new maps); tilesets 5, 6, 19-22, 53 edited; the 94 new maps use 21 tilesets and 32 map palettes (ROM read from `ted_maps.json` properties) | `ted_maps.py` line 24, `NOTES/ted-maps.md` |
| Battle backgrounds | guide lists 60; the ROM table has 57 filled entries, 49 equal to vanilla's | `GUIDE/background.html`; ROM read |

---

## 1. Music

### 1.1 Two sound drivers

T-Edition carries two copies of FF6's sound driver, each with its own song table (`tools/ted_songs.py` docstring; `NOTES/ted-events.md` lines 359-369):

| Driver | Tables | Used by | Slots | Vanilla with PR track | Vanilla without PR track | Not vanilla |
|---|---|---|---|---|---|---|
| Main (C5) | file 0x50000: count at +3C5E, pointer table via +0539 | map properties, event commands F0 (song & 7F), EF, F1 | 255 | 70 | 9 | 176 |
| Second (bank 43) | file 0x430000, same layout | T-Edition's own event commands 76, 9E (song & 7F), 9F ("different from normal song ID"): fanfares and inn jingles | 254 (slot 0x69 empty) | 72 | 12 | 170 |

`data/ted_songs.json` was built by comparing each slot's bytes with the JP ROM's (equal, or same length with at most 5% bytes changed: vanilla 0x2B and 0x37 have a few notes fixed), then taking the PR bgm id from `snes_songs.FF6_SONG_PR_BGM` (ids 01-54 only).

By kind:

| Kind | Count | Notes |
|---|---|---|
| Vanilla with a PR track | 70 main-driver slots (72 on the second driver: it also has 0x2F Victory Fanfare = PR bgm 7, and 0x38 = PR bgm 74) | player list: 70 of the 73 "Original BGM" entries |
| Vanilla without a PR track | 9 main (0 silence, 0x1E, 0x2C, 0x39, 0x3A, 0x3C Mystery Train Stopping, 0x40, 0x48, 0x4A); 12 second (the same plus 0x3F, 0x49, 0x51) | only 0x3C is a named song in the guide (#19); 0x2F (#8 Fanfare) is empty on the main driver and tracked on the second; the others are not songs the guide names (probably sound-effect or unused slots: not verified) |
| T-Edition's own, main driver | 175 songs: slots 0x55-0xFE (170; the guide fills them all, 0xD6 included although `PRODUCERS/FF6-T BGM.txt` shows "???") + 5 in vanilla slots: 0x25 FF Xmas Arrange, 0x38 XB Agnilatha -Night-, 0x3F FF3 The Crystal Tower, 0x49 XB You Will Know Our Names, 0x51 FF0 Zero | `ted_songs.json` "new" lists 176 because 0x2F (a 37-byte run, no song) is counted too |
| Second-driver jingles and fanfares | 30 slots 0xC4-0xE1 differ from the main copy (ROM read: slots >= 85 that differ are 0x5B, 0x6B, 0xC0, 0xC1 and 0xC4-0xE1; 135 of the 169 slots from 85 up are byte-identical to the main driver's). The guide names 29 ids: 20 victory fanfares, 9 inn jingles; EST2 Victory has no id (0xD1 by elimination); vanilla "Good Night" (0x38) is the 31st jingle | 0x5B, 0x6B, 0xC0, 0xC1 differ for a reason not found (unknown). The same id means a different song per driver (0xD6 = Crystal World on the main driver, FF10 Victory's Fanfare on the second) |

Sizes (ROM read): the main driver's own songs (slots >= 85) total 265,094 bytes; the 34 differing second-driver songs 25,864 bytes. Song source addresses in the ROM are listed per song in `PRODUCERS/FF6-T BGM.txt` (main-table slots 0x55-0xFE, from 5D0000 Into the Darkness to 5C0CF0 Yuna's Theme; its fanfare list has 18 lines, 5E5DB0 to 5B19A0, with one address listed twice). Waveform tables were relocated: waveform data 5E0480 -> 5F0480, start table 5E0180 -> 5F0000, correction 5E0280 -> 5F0180, ADSR 5E0380 -> 5F0300 (`PRODUCERS/FF6-T Edition address changes.txt`).

### 1.2 Where T-Edition's own songs are used

By map properties (the song byte at +28 of each 33-byte map record; T-Edition's table is at 0x4D0000 (4D/0000), `NOTES/ted-maps.md` line 52):

- 94 new maps (`data/ted_maps.json`, `maps.<m>.song`): 21 maps song 0 (silence); 5 tracked (songs 40, 42, 43, 45, 77 = maps 481, 444, 510, 492, 508); 2 on vanilla 0x39 (maps 429, 434; no PR track); **66 maps use 21 of T-Edition's songs**: 0x38 (509), 0x3F (497-504), 0x58 (433), 0x59 (482-483), 0x61 (437-438), 0x65 (461), 0x68 (421-428), 0x6B (417-420, 431-432), 0xA7 (505), 0xAD (484, 493), 0xBB (440, 442-443), 0xBC (435, 506), 0xBE (441), 0xC0 (445-446), 0xCF (453-458), 0xD0 (447-452), 0xD6 (477-480), 0xEC (463-464), 0xED (466, 468), 0xF0 (467, 491), 0xF2 (473-476). Matches the 28 songs / 5 tracked / 2 no-track / 21 own in `NOTES/ted-events.md` line 365.
- Vanilla maps 0-415 (ROM read, property byte +28 against the JP ROM): 82 maps changed song. 27 became song 0, 55 take 19 of T-Edition's songs: 0x55 (313, 315), 0x56 (243-244, 250, 252), 0x59 (176-181), 0x5B (317), 0x5C (217-219), 0x5E (41-43, 48-51), 0x62 (297-300), 0x65 (32-38), 0x66 (371-375), 0x67 (401-402), 0x6E (353), 0x70 (157, 160-161, 164), 0x73 (344), 0x75 (188), 0x7B (404-405), 0x93 (195), 0x96 (44), 0xAD (406, 408), 0xBC (387). Why 27 vanilla maps went silent is not established (an event may start their song).
- EX content plays map music 238 (boss room), 240 (Mog House), 104/107/167/57 (den), song 62 (game over) (`NOTES/ted-ex.md` lines 96-97); EX's song tables equal 3.0.7's except one pointer (song 47).

By event commands: 76 s v, 9E s and 9F s v play from the second driver; F0, EF and F1 from the main one (F0 76+ is past vanilla's 0x54). Stubbed so far: "T-Edition's own songs ... have no PR track: they stay stubs" (`NOTES/ted-events.md` lines 311-313); 380 "sounds/songs" stubs among T-Edition's 3,682 distinct stubs (line 119; songs are not split from sounds there).

By battles: the guide's "where used" names a battle for 64 of the 175 (bosses, dungeon battles, Soul Shrine groups 2-14: 15 entries mention the Shrine). How a formation picks its song in T-Edition's ROM is **not established** (the formation flag byte 3 bits 4-7 are a music index in vanilla; EX's formations all carry 0: `NOTES/ted-ex.md` lines 66, 187).

By the Falcon (airship): each costume plays its own song; the guide names a "Falcon song" in 53 of the 175 entries, and `dressroom.html` names a song for every costume (some are vanilla songs, e.g. Umaro's Oracle's Bolero plays Returners).

By the Developer's Room and Config: a music player (README lines 540-555); its list is `data/ted_music_player.json` (277 entries: 247 in the player = 73 original + 174 new, plus 30 jingles outside it; made by `tools/ted_music_list.py` from `bgm.html`).

The 175 songs with the guide's stated use are in Appendix B; the 30 jingles in Appendix C.

### 1.3 What the player would hear today

(From the porter's rules; no game run.)

- **New maps**: `tools/ted_maps.py` lines 702-709 and 805-809 set `bgm_id` from `ted_songs.json` "songs" only. Song 0 = silence (bgm 0); 5 maps get a PR track; the 2 no-track maps and the **66 maps with T-Edition's own songs get no bgm of their own** and keep "the source's BGM" (`NOTES/ted-maps.md` line 27), i.e. the music of the vanilla room the new map was cloned or drawn from (59 maps cloned, 35 converted: `ted_maps.json` "how").
- **Vanilla maps**: I found nothing that changes a vanilla map's BGM (`ted_maps.py` writes `bgm_id` only for new maps), so the PR's own music presumably plays on all 82 maps whose song T-Edition changed (inference).
- **Events**: vanilla songs translate to PlayBGM through `event_translate.song_bgm`; T-Edition's own songs and every 76/9E/9F fanfare and jingle stay stubs, so the scene's music does not change (`NOTES/ted-events.md` lines 308-313). F3 maps to ReplayBgm, FA to nothing.
- **Battles**: `tools/port_monster_ext.py` lines 165-182 give each T-Edition party the PR battle music learned for vanilla parties with the same flag nibble, so every battle plays a vanilla PR battle or boss tune; none of the 64 battle-related new songs plays.
- **Victory fanfares and inn jingles**: the PR's own (the T-Edition commands are stubs; not checked in game).
- **Falcon costume songs, dressing room, music player**: not built (`NOTES/t-edition-lead.md` line 119: TedPlugin menus remain).

### 1.4 Source addresses, counts, needed output, unknowns

| Item | Source address (file offset) | Count | Output the PR needs | Unknown |
|---|---|---|---|---|
| Main-driver songs | tables at 0x50000 (C5); song bytes 0x5A0000-0x5EF4B0 per `FF6-T BGM.txt` | 255 slots, 175 own (265,094 bytes) | a song pack (`songs.json` + `songs.bin`, `tools/snes_songs.py`) that the SNES player plays by song number, made on the player's machine from the player's own ROM; no ROM and no SNES-derived audio in the shipped zip (whether the Square-derived songs ship is the user's decision, `NOTES/t-edition-lead.md` line 125) | none for the addresses; instrument and loop tables go with the pack |
| Second-driver jingles | tables at 0x430000 | 34 differing slots (30 jingles, plus 0x5B, 0x6B, 0xC0, 0xC1), plus 0x25 per `ted_songs.json` | the same, chosen by driver (commands 76/9E/9F): a second song-id namespace | what 0x5B, 0x6B, 0xC0, 0xC1 are; the slot of the EST2 fanfare |
| BRR samples | pointer table via +0222 in each driver; waveform tables 0x5F0000-0x5F0480 | at least 157 (520,722 bytes), the same read from both drivers | the sample set inside the pack | exact count (my walk stops at the first malformed entry); the 8 resident waveforms (programs $00-$07) are FF6's and the PR player synthesizes stand-ins (`tools/bc_music.py` docstring) |
| Song-to-use, maps | `ted_maps.json` for new maps; 0x4D0000 for vanilla maps | 36 own songs on maps | per-map override: PR map id -> song (like `bc_music.json` "maps") | the vanilla-map overrides are not made |
| Event songs | commands 76, 9E, 9F, F0, EF, F1 | 380 sound/song stubs on T-Edition's own events | PlayBGM of a pack song by number; fanfares with the PauseBGM / jingle / ReplayBgm pattern | the split of the 380 between sounds and songs |
| Battle songs | formation flags (vanilla table 0x0F5900, 4 bytes per formation, byte 3 >> 4) | 64 own songs named for battles | per-party song (like `bc_music.json` "formations": slot + fanfare flag) | how T-Edition selects a song per formation; EX's 13 fights |
| Falcon songs | the dressing-room costume tables (not located) | 53 songs, 56 costumes | switch the airship song when a costume is worn | where the costume-to-song table is |
| Music player list | `GUIDE/bgm.html` | 277 entries | `data/ted_music_player.json` exists, PR tracks filled in for the 70 vanilla ones | the PR's jukebox hook |

---

## 2. Monster art

### 2.1 Where T-Edition keeps the art

(`NOTES/ted-monsters.md` lines 28-33, `NOTES/t-edition-lead.md` lines 65-67, `PRODUCERS/FF6-T Edition address changes.txt`.)

- Graphics entries: file 0x0F1A00 (CF/1A00), 512 x 5 bytes, vanilla's format; read by C1/2064, C1/24E6, C3/B8CC instead of D2/7000.
- Tiles: T-Edition's hook at C1/2040 stores the monster id in $6400 and C0/D978 picks the bank: **F0/0000 + 8 x pointer** (file 0x300000) for monsters 0-416 and 432-479; **F4/0000** (0x340000) for 417-431; **F5/0000** (0x350000) for 480-511. Vanilla was E9/7000.
- Palettes: **41/6200** (file 0x416200; vanilla D2/7820, "127820 -> 416200" in the address-changes file).
- Stencils as vanilla (D2/A820 pointers; the big ones start at D2/AC44).
- Other monster tables moved: monster data 2A7000 -> 573E00, special attack names 2AAE00 -> 5F4500, behaviour (AI) 297000 -> 5F58F0, special attack animation 2CE6E8 -> 425000.
- Reader: `profile_tedition.MonsterSprites` (snes_sprites.Sprites with the three changes above). EX: the same entry table (EX keeps 3.0.7's CF/1A00); `ted_ex.ExSprites` reads EX's ROM (entries for 256-282 and 460 are EX's own; palettes 41/6200).

### 2.2 Counts

| Range | Monsters | Art | Source |
|---|---|---|---|
| 0-383 (vanilla range) | 384 | 306 of 382 match a vanilla sprite (239 in their own slot); **76 are T-Edition's redrawn art, covered by no work yet** (the porter and `port_sprites` read D2/7000, T-Edition's are at CF/1A00). The lead's other measure: only 26 of the 384 graphics entries are byte-equal to vanilla's | `NOTES/ted-monsters.md` lines 32-34, 136-139; `NOTES/t-edition-lead.md` lines 65-66 |
| 384-511 (new) | 128 slots; 104 have a PR row (`monster_ext.json`), the other 24 are in no formation the port handles | 14 same, 17 recolor, 73 new | `monster_ext.json` (written 18:03 today) |
| EX 512-539 | 28 slots, 26 in fights (518 and 519 are not) | 25 new, 1 recolor (539 Omega Weapon = Ultima Weapon's shape) | `monster_ext.json`; `NOTES/ted-ex.md` lines 202, 253 |
| Total rows | 130 | 14 same / 18 recolor / 98 new | computed from `monster_ext.json` |

The notes still carry earlier figures (64 new / 17 recolor / 13 same; later 89 new and 5 reuse; then 98 / 18); `monster_ext.json` is the current source and is what this table and Appendix A use. The 24 unused slots in 384-511 are not examined (unknown: do they have art?).

"same": vanilla art on a T-Edition id; nothing to convert (the PR row already points at the vanilla PR asset). "recolor": a vanilla shape in T-Edition's colours (a colour table on the PR art, `port_sprites`' recolor). "new": new art; the row shows the stand-in (nearest-size vanilla monster) until the art arrives.

PR ids are `1000 + e` (EX: 1512-1539). Sprite sizes (opaque box) are in Appendix A: from 20x19 (EX Orbital) and 21x30 (Korpokkur, Alraune) up to 128x128 (EX Sephiroth, Zeromus's second form, Omega Weapon); the biggest in 384-511 are 120x104 (Ghost Train), 112x112 (Diabolos), 110x95 (Marilith), 108x93 (Kraken).

### 2.3 EX's bosses (sprites from EX's ROM, ids 512-539)

The boss room has 12 fights plus Omega Weapon as a 13th (`NOTES/ted-ex.md` lines 13-14, 195-202). Monsters: 512 Cloud of Darkness (126x98), 513/514 Golbez (two forms), 515/516 Zeromus (two forms; the second form "has been given a new sprite", cut to fit 128x128, `GUIDE/EX history.html` line 109), 517 Exdeath, 520 and 533 Sephiroth (128x128), 521 Ultimecia, 522 Chaos, 523/524 Mateus, 525 Neo Exdeath, 526 Kam'lanaut, 527 Eald'narche, 528-532 Ark Angels (five different sprites), 534/535 Orbital (20x19), 536 Kuja, 537 Seymour, 538 Anima, 539 Omega Weapon (recolor of 279 Ultima Weapon). EX's sprites come from a different ROM, so the converter must read both the 3.0.7 and the EX 2.0.6 images. Boss-room battle backgrounds come from each event's battle byte (all specific).

### 2.4 Source addresses, counts, needed output, unknowns

| Item | Address | Count | Output | Unknown |
|---|---|---|---|---|
| Sprite entries | 0x0F1A00 (5 B x 512) | 512 | one image per monster id (the sprite's opaque box), pivot bottom-centre, a 226x226 bestiary thumbnail each (`MODDING.md`: "Monsters are images ... `mn_ff6_NNN`") | the PR monster_asset row numbering for T-Edition (`ArtWriter.monster` uses row 2000 + m for BC; the porter's PR ids are 1000 + e) |
| Sprite tiles | 0x300000 (F0), 0x340000 (F4), 0x350000 (F5) | 98 new + 18 recolor, + 76 redrawn vanilla-range (+ the 24 unused slots) | PNGs by SNES id through `ArtWriter.monster`, served by `ArtSwap` or `MonsterImages` | whether the 76 redrawn 0-383 monsters get converted (no one owns it) |
| Palettes | 0x416200 | one per entry | a palette per image; for the 18 recolors the old/new palette pair (`recolor`) | whether each recolor's PR shape really matches (the row says so) |
| EX | EX ROM, same tables | 26-28 | as above, from the EX image | EX's entries for 256-282 and 460 not yet matched against 3.0.7 sprites |

---

## 3. Character graphics: costumes and the dressing room

### 3.1 What exists

- 14 playable characters x 4 alternate costumes = **56 costumes** (`GUIDE/dressroom.html`: Terra, Locke, Cyan, Shadow, Edgar, Sabin, Celes, Strago, Relm, Setzer, Mog, Gau, Gogo, Umaro, four each; `GUIDE/change.html` line 1085: "up to 4 new costumes total for each character"). Costume 1 unlocks before 2 before 3 (README lines 640-650). Unlocks come from quests, achievements and secrets (README: Worrying Priestess, Mother's Warmth, Secret Present in Eureka; Melancholy of a Dancer opens the dressing room on the Falcon).
- A costume changes graphics only (field/map, battle, menu portrait), plus stat tweaks and a Falcon song; the battle spec ports nothing of the costume system's rules (`pr/ted/BATTLE_SPEC.md` lines 135-138: the 22-byte table at file 0x403100 is dead data; "The costume system changes graphics only").
- Per costume: a field sprite, a battle sprite and a portrait (README line 641: "each one comes with a different portrait"; `GUIDE/EX history.html` line 541: changing costumes changes the menu portraits; lines 679-682 name "field/battle/portrait sprites"). Some portraits were still missing in an older version (line 601).
- Mog has a new pose (costumes included, `GUIDE/EX history.html` line 432). Gogo's Chameleon Robe replaces his battle sprite each battle with one of 10: Leo, Banon, Trance Terra, Merchant, Ghost, Kefka, Gestahl, Cid, Daryl, Rachel (`dressroom.html`; EX history line 169) = 10 more battle sheets. Status sprites: a Pig and a Kappa battle sprite ("Special Battle" folder), and the "Toad" status portrait and sprite were changed (EX history line 824).
- Costume art is mostly other games' characters (Lightning, Squall, Vaan, Firion, Auron, Draco, ...): original to T-Edition, not recolors of FF6 sheets.

### 3.2 Where the data is (address-changes file; ROM read for counts)

| Table | Old file offset | T-Edition file offset | Count / size |
|---|---|---|---|
| Field character graphic offset (2 bytes per slot; consecutive sheets 0x16A0 apart) | C0/D0F2 (165 slots; the address-changes file's 0xD024 is wrong, ted-maps 2026-11-20) | 0x380400 (F8/0400) | 256 slots; 250 distinct (offset, bank) pairs; the first sheets run from file 0x150000 in steps of 0x16A0 (ROM read) |
| Field character graphic bank | C0/D23C (165 slots; not 0xD16E) | 0x380600 (F8/0600) | read as 2 bytes per slot (the bank, then a constant 0x20); the second byte's meaning is unverified |
| Battle character graphic offset | 0x2CDE5 | 0x426000 (42/6000) | not decoded (count unknown) |
| Battle character palettes | 0x2D6300 | 0x3EF000 (FE/F000) | not decoded; `PRODUCERS/FF6-T Edition character palettes.pal` and `original ff6 character palettes.pal` are 384 bytes each |
| Portrait data (0x320 bytes = 40x40, 4bpp, each) | 0x2D1D00 | 0x490000 (49/0000) | 75 distinct images (offsets 0, 0x320, ... to index 74) in 85 slots (ROM read; vanilla 18, the rest 56 costumes plus extras) |
| Portrait offsets | 0x376AF | 0x380A00 (F8/0A00) | 2 bytes per slot |
| Portrait palette ids | 0x37694 | 0x380B00 (F8/0B00) | 1 byte per slot; ids reach 74 |
| Portrait palettes | 0x3848C | 0x415200 (41/5200) | 75 palettes by the ids above |
| Character size data | 0x48FC0 | 0x403F00 | not decoded |

Release-folder source images (T-Edition's own working PNGs, `FF6 T-Edition Used Images/`, drawn with FF3usME and FF3se; counts are files, so a field sprite and its battle ("戦闘用") variant count separately): sprites Default 33, Dress 1 45, Dress 2 57, Dress 3 49, Dress 4 30, NPC 1 (Kappa), Special Battle 2 (Pig, Kappa) = 217 files; portraits Default 19, Dress 1 15, Dress 2 15, Dress 3 14, Dress 4 14 = 77 files, 40x40, 16 colours (`Portraits/readme.txt`). They are an alternative to reading the ROM; whether they may be used is the same Square-derived question as for the music (`NOTES/t-edition-lead.md` line 125).

### 3.3 Needed output and what is unknown

- Per costume (56, plus the 14 defaults and Gogo's 10 battle forms): field and battle frame sets in the PR's named-frame format: 32x32 RGBA frames, 50-62 names (`Default_00..02`, `WalkB/L/R_*`, `Idle_00`, `Ready_00`, `Win_00`, `Down_00`, ...) per PR group (`mo_ff6_pNNN` field atlas, `bc_ff6_pNNN` battle), from SNES sheets of 0x16A0 bytes (4bpp, with riding poses) plus a 16-colour palette, through `snes_charsprites.group_frames`. PR groups p001-p014 are the cast, so a costume is a swappable alternate frame set (`ArtSwap.Load`, "a costume put on"). Portraits: `portrait(raw 0x320 B, 16 colours)` -> 40x40 into `fa_ff6_pNNN/Default_00`, 75 distinct. A dressing-room feature in TedPlugin picks which set is live per character with the unlock rules (`NOTES/t-edition-lead.md` line 119: not done).
- Open: how field and battle sheets differ per costume (T-Edition has separate field and battle tables; the kit assumes the same pixels for both, and the "(戦闘用)" PNGs suggest some differ); the layout of the new poses (Mog's) against the kit's pose table at C0/CE3A; whether every T-Edition sheet is 0x16A0 bytes; how many battle sheets there are; Terra's trance and Esper looks for costumes; guest-character looks (Leo, Banon, Kefka, ... in the vanilla slots 0-21); the battle palette count. The pose map in `data/ff6_charsprites.json` covers vanilla slots 0-21 only.

---

## 4. Other graphics

### 4.1 NPC and field sprites

- T-Edition re-numbered the NPC sprites of 634 vanilla NPCs ("its own sprite numbering", `NOTES/ted-maps.md` line 71); the field sprite table is the 256-slot table at 0x380400/0x380600 above. The 94 new maps hold 455 NPC records (`ted_maps.json`; 454 in `NOTES/ted-maps.md` line 72) using **112 distinct sprite numbers**, the highest 255 (ROM read from the `sprite` field).
- Known new ones: EX boss room (map 471) Moogle sprite 220, shopkeepers 105, decorations 101 (`NOTES/ted-ex.md` lines 73-76); 3 new NPC sprites in `GUIDE/EX history.html` line 261; Arvis and Jun in Narshe get sprites 176/171 and a merchant 224 (`NOTES/ted-events.md` lines 305-309); the den's flame NPCs 104, ghosts 111 and turtle 184 (den left out).
- Porter stubs: T-Edition's new event code has 727 NPC graphics/palette/hide/delete stubs (`NOTES/ted-events.md` line 119), and obj_graphics/obj_palette stubs number 2,890 each across the README events, mostly Shadow's dreams (line 345).
- Output needed: a map from T-Edition NPC sprite number (0-255) to a PR entity look. The PR keeps NPCs as per-map entities, so either PR looks are chosen by hand per sprite number (the current approach: the PR shows its own look) or the SNES sheets are converted into new PR sprites. Sheet sizes for NPC slots other than the 0x16A0 character sheets are unknown.

### 4.2 Tilesets and map graphics

- Map graphics pointers 0x400B00 (40/0B00; vanilla DF/DA00): graphics sets **82-85 are T-Edition's own**; tilesets (pointers DF/BA00 + DE/0000 unchanged): T-Edition edited tilesets 5, 6, 19-22, 53; map palettes 0x4B6000 (4B/6000; vanilla 0x2DC480); layouts: T-Edition changed layouts 6 and 7 (vanilla maps 47/74/75 BG1, 182/302/340-344 BG2) (`ted_maps.py` line 24, `NOTES/ted-maps.md` lines 56-70).
- Use by new maps (ROM read from `ted_maps.json` properties bytes 7-12 and 25; set numbers above 127 may be 7-bit encoded in places, EX decodes its room as (82, 83, 40, 19), `NOTES/ted-ex.md` line 269): graphics set 82 on maps 477-480, set 83 on maps 497-505; 84 and 85 on none; 64 distinct graphics-set bytes, 21 tilesets and 32 map palettes across the 94 maps.
- Today: 59 new maps are clones of PR rooms (a vanilla layout and look), 35 are drawn by `snes_rooms` from vanilla rooms that look alike (`ted_maps.json` "how"); neither converts T-Edition's own tile art. Maps 433 and 435 are not built (their looks, tilesets 54 and 65, exist only on vanilla maps 317 and 391; `NOTES/ted-maps.md` line 127). The EX boss room (471) uses sets [210, 41, 106, 2] and palette 53 (`ted-ex.md` line 74).
- Output needed: for each T-Edition graphics set or tileset that no PR room matches, PR tile images (the PR draws maps from its own tilesets, so these are new tile sprites plus a layout that uses them) or, as now, an accepted look-alike. Unknown: which of the 94 maps look wrong with their look-alike; how many tiles in sets 82-85 and the edited tilesets are new art as against edits of vanilla.

### 4.3 Battle backgrounds

- Table 0x26F800 (E6/F800; vanilla 0x270000) and palettes 0x26FC00 (vanilla 0x270150). The guide lists 60 backgrounds (`GUIDE/background.html`, Grasslands through Sky (WoR), including Art Gallery, Crystal Room, Dream Dungeon, Desert (Night)). In the ROM (ROM read, 6-byte entries) 57 entries are filled (0-56): 49 of the first 56 equal vanilla's, 7 differ, entry 56 is new. The 57 against 60 and the order against the guide are not reconciled.
- The porter maps an SNES background b to the PR's `bg_ff6_<b+1>` (ids 1-50 = bg_ff6_01-50; 51-58 = bg_ff6_54-61), checked against vanilla (`NOTES/ted-monsters.md` lines 119-124). A T-Edition background past 58 has no PR asset; EX's 13 fights take their event's background byte.
- Output needed: PR background images for the new or edited backgrounds (which ones: unknown until the table is decoded); the rest reuse the PR's.

### 4.4 Menu art: the Collection Room paintings

- The Beginner's House in Narshe holds the Collection Room, with "a large art gallery room that will fill up with paintings every time you defeat a boss in the bonus EX patch" (README lines 247-257, 556-560). EX's 12 boss wins each set one event bit that 3.0.7's Collection Room reads (`NOTES/ted-ex.md` lines 13-14; the bits are ScenarioFlag4 5-16 in the PR port, Omega 17, line 220). `GUIDE/history.html` mentions a Painting Room with an innermost painting, changed paintings, and an FF9 painting wrongly shown after "A Mother's Hope" (lines 4523, 4740, 4909, 5392).
- The paintings appear to be map tiles in the room's graphics (the room is a field map). I found no separate image table for them: the painting count and the tile addresses are unknown. The PR side needs the room as PR tile art or look-alike frames, plus the boss-win flags (already allocated in the event port).
- The Collection Room's item displays and the 20 achievements (README lines 247-262) are text and flags; no graphics found.
- Other menu graphics not examined: window types (`GUIDE/windowtype.html`, `Extra Patches (Window Menu Edits)`), the dressing-room UI, and the battle short menu ("graphical only", README line 189).

### 4.5 Portraits (non-costume)

Default portraits were redrawn ("Default portraits have been changed for each character", `GUIDE/history.html` line 1937; README line 847): the 18 vanilla portrait slots (indices 0-17 of the 0x380A00 table) plus guest and NPC portraits (slots 18 and 19 reuse portraits 0 and 1, slot 20 = image 18, ROM read). Counts are in section 3's table; the release folder's 19 Default portraits correspond.

### 4.6 Source addresses, counts, needed output, unknowns (summary)

| Item | Address (file) | Count | Output | Unknown |
|---|---|---|---|---|
| NPC sprites | 0x380400 / 0x380600 | 256 slots, 250 distinct pairs, 112 numbers used by new maps | sprite sheets or a PR-look assignment per number | sheet formats; mapping to PR entities |
| Graphics sets, tilesets | 0x400B00; DF/BA00 + DE/0000; palettes 0x4B6000 | sets 82-85; tilesets 5, 6, 19-22, 53 edited; 21 tilesets, 32 palettes on new maps | tile images only where look-alikes are not accepted | tile counts; maps that look wrong |
| Battle backgrounds | 0x26F800 / 0x26FC00 | 57 entries filled (guide: 60) | PNGs for the new or edited ones | which are new |
| Collection Room paintings | map graphics (not located) | 12 EX bits; painting count unknown | tile art or look-alike | everything but the flags |
| Portraits | 0x490000 / 0x380A00 / 0x380B00 / 0x415200 | 75 images, 75 palettes | 40x40 PNG per portrait into `fa_ff6_*` | the slot-to-character mapping beyond 0-17 |

---

## Summary: what T-Edition will need

From a music player: T-Edition needs a player that takes a song number and a driver (the main table for maps and F0/EF/F1, the second table for the 76/9E/9F fanfares and inn jingles) and plays it from a pack built on the player's machine from their own ROM (175 own songs, 29-31 jingles and fanfares, at least 157 BRR samples, and a second song-id namespace in which one id means another song). It must override the BGM of a PR map (66 new and 55 vanilla maps use own songs), of a battle party (64 battle songs, selection rule unknown) and of the Falcon by worn costume (53 songs). The 70 vanilla songs with PR tracks need no player; the vanilla-slot songs without PR tracks (only Mystery Train Stopping is a named song) are minor; whether the Square-derived songs ship is the user's decision. From a sprite converter: T-Edition needs SNES-to-PR conversion for 98 new and 18 recolored monsters (plus 76 redrawn vanilla-range ones nobody covers, and 26 EX monsters read from EX's ROM; images keyed by SNES id with PR id 1000 + e, thumbnails 226x226), the 56 costumes as swappable per-character frame sets with 75 portraits and 10 Gogo battle forms (field and battle tables are separate, and some sheets may differ between field and battle), an NPC sprite-number to PR-look map for 112 numbers on the new maps, and a decision on tile art for graphics sets 82-85, the edited tilesets, the new battle backgrounds and the Collection Room paintings, whose addresses are not yet found.

---

## Appendix A. Monsters needing PR art (130 rows, `monster_ext.json`)

| SNES id | PR id | Name | Range | Art | Vanilla PR asset (same / recolor) or stand-in (new) | Sprite size |
|---|---|---|---|---|---|---|
| 384 | 1384 | Ramuh Clone | T-Ed | new | new art; stand-in PR 3 Ninja | 47x63 |
| 386 | 1386 | Shiva Clone | T-Ed | same | = vanilla art of PR 264 Shiva | 40x48 |
| 387 | 1387 | Siren Clone | T-Ed | new | new art; stand-in PR 17 Commander | 31x54 |
| 389 | 1389 | Catoblepas | T-Ed | new | new art; stand-in PR 113 Vector Hound | 48x40 |
| 400 | 1400 | Ifrit Clone | T-Ed | same | = vanilla art of PR 265 Ifrit | 47x44 |
| 401 | 1401 | Kirin Clone | T-Ed | new | new art; stand-in PR 29 Briareus | 64x55 |
| 405 | 1405 | Seraph Clone | T-Ed | new | new art; stand-in PR 3 Ninja | 45x64 |
| 407 | 1407 | Unicorn Clone | T-Ed | new | new art; stand-in PR 35 Fossil Dragon | 64x64 |
| 409 | 1409 | Asura | T-Ed | new | new art; stand-in PR 37 Fiend Dragon | 62x88 |
| 415 | 1415 | Snoll | T-Ed | recolor | recolor of PR 170 Grenade | 32x32 |
| 416 | 1416 | Omega | T-Ed | new | new art; stand-in PR 185 Oceanus | 67x56 |
| 417 | 1417 | Desert Trap | T-Ed | new | new art; stand-in PR 13 Dark Force | 54x64 |
| 418 | 1418 | Magna Roader | T-Ed | same | = vanilla art of PR 6 Magna Roader | 64x60 |
| 419 | 1419 | Mini Magna | T-Ed | same | = vanilla art of PR 175 Magna Roader | 32x32 |
| 420 | 1420 | Ghost Train | T-Ed | new | new art; stand-in PR 131 Dragon | 120x104 |
| 421 | 1421 | Hidon | T-Ed | same | = vanilla art of PR 291 Hidon | 80x88 |
| 422 | 1422 | Still Life | T-Ed | same | = vanilla art of PR 80 Still Life | 56x63 |
| 423 | 1423 | Vargas | T-Ed | same | = vanilla art of PR 259 Vargas | 56x79 |
| 424 | 1424 | Vargas | T-Ed | same | = vanilla art of PR 259 Vargas | 56x79 |
| 425 | 1425 | Life Trap | T-Ed | new | new art; stand-in PR 13 Dark Force | 54x64 |
| 426 | 1426 | Gilgamesh | T-Ed | new | new art; stand-in PR 35 Fossil Dragon | 64x74 |
| 427 | 1427 | Gilgamesh | T-Ed | new | new art; stand-in PR 16 Skeletal Horror | 80x96 |
| 428 | 1428 | Mom Bomb | T-Ed | new | new art; stand-in PR 16 Skeletal Horror | 80x98 |
| 429 | 1429 | Dadaluma | T-Ed | same | = vanilla art of PR 263 Dadaluma | 88x56 |
| 430 | 1430 | Number 024 | T-Ed | same | = vanilla art of PR 266 Number 024 | 65x80 |
| 431 | 1431 | Yeti | T-Ed | same | = vanilla art of PR 271 Yeti | 56x64 |
| 433 | 1433 | FreezeDrgn | T-Ed | same | = vanilla art of PR 329 Ice Dragon | 32x32 |
| 434 | 1434 | Draculady | T-Ed | new | new art; stand-in PR 3 Ninja | 48x64 |
| 435 | 1435 | Alv | T-Ed | new | new art; stand-in PR 250 Baalzephon | 40x64 |
| 436 | 1436 | Crystal Dragon | T-Ed | recolor | recolor of PR 37 Fiend Dragon | 64x95 |
| 437 | 1437 | Colossus | T-Ed | recolor | recolor of PR 157 Pluto Armor | 64x64 |
| 438 | 1438 | Helldiver | T-Ed | recolor | recolor of PR 252 Death Machine | 56x63 |
| 439 | 1439 | Vanguard | T-Ed | recolor | recolor of PR 234 Fortis | 61x62 |
| 440 | 1440 | Ochiudo | T-Ed | recolor | recolor of PR 4 Samurai | 56x63 |
| 441 | 1441 | Ninja Master | T-Ed | recolor | recolor of PR 189 Outsider | 47x64 |
| 442 | 1442 | Holy Dragon | T-Ed | same | = vanilla art of PR 36 Holy Dragon | 96x95 |
| 443 | 1443 | Silenus | T-Ed | new | new art; stand-in PR 21 Belmodar | 48x48 |
| 444 | 1444 | Li'l Murderer | T-Ed | new | new art; stand-in PR 73 Humpty | 31x32 |
| 445 | 1445 | Valefor | T-Ed | new | new art; stand-in PR 72 Outcast | 46x48 |
| 446 | 1446 | Aeronite | T-Ed | recolor | recolor of PR 331 Storm Dragon | 64x48 |
| 447 | 1447 | Carrot | T-Ed | recolor | recolor of PR 97 Malboro | 64x64 |
| 448 | 1448 | Apanda | T-Ed | recolor | recolor of PR 281 Behemoth King | 64x96 |
| 449 | 1449 | Astos | T-Ed | new | new art; stand-in PR 21 Belmodar | 48x48 |
| 450 | 1450 | Myrmecoleon | T-Ed | recolor | recolor of PR 31 Chimera | 88x64 |
| 451 | 1451 | Proserpine | T-Ed | new | new art; stand-in PR 4 Samurai | 58x78 |
| 452 | 1452 | Donberry | T-Ed | recolor | recolor of PR 84 Tonberry | 32x30 |
| 453 | 1453 | Queen Behemoth | T-Ed | same | = vanilla art of PR 127 Behemoth King | 64x96 |
| 454 | 1454 | Shield Dragon | T-Ed | recolor | recolor of PR 132 Primeval Dragon | 86x60 |
| 455 | 1455 | Hecto | T-Ed | recolor | recolor of PR 59 Leap Frog | 32x32 |
| 456 | 1456 | Korpokkur | T-Ed | new | new art; stand-in PR 77 Bandit | 21x30 |
| 457 | 1457 | Emeralditan | T-Ed | new | new art; stand-in PR 131 Dragon | 94x96 |
| 458 | 1458 | Moon Goddess | T-Ed | new | new art; stand-in PR 21 Belmodar | 50x50 |
| 459 | 1459 | Skulnant | T-Ed | new | new art; stand-in PR 186 Living Dead | 32x48 |
| 460 | 1460 | Azrael | T-Ed | new | new art; stand-in PR 21 Belmodar | 50x50 |
| 461 | 1461 | Cerberus | T-Ed | new | new art; stand-in PR 35 Fossil Dragon | 68x66 |
| 462 | 1462 | Alraune | T-Ed | new | new art; stand-in PR 77 Bandit | 21x30 |
| 463 | 1463 | Wolframiter | T-Ed | new | new art; stand-in PR 37 Fiend Dragon | 64x80 |
| 464 | 1464 | Kefka | T-Ed | recolor | recolor of PR 330 Kefka | 64x64 |
| 465 | 1465 | Audience | T-Ed | new | new art; stand-in PR 86 Mover | 3x3 |
| 466 | 1466 | Reflect Bit | T-Ed | new | new art; stand-in PR 8 Cloud | 32x32 |
| 467 | 1467 | Leo Reborn | T-Ed | new | new art; stand-in PR 3 Ninja | 46x74 |
| 468 | 1468 | Undead Cherub | T-Ed | new | new art; stand-in PR 3 Ninja | 48x64 |
| 469 | 1469 | Leviathan | T-Ed | new | new art; stand-in PR 37 Fiend Dragon | 64x82 |
| 470 | 1470 | Death Rider | T-Ed | recolor | recolor of PR 156 Test Rider | 92x80 |
| 471 | 1471 | Earth Eater | T-Ed | recolor | recolor of PR 22 Muud Suud | 80x80 |
| 472 | 1472 | Seraph | T-Ed | new | new art; stand-in PR 3 Ninja | 45x64 |
| 473 | 1473 | Ultima | T-Ed | new | new art; stand-in PR 131 Dragon | 92x100 |
| 474 | 1474 | Carbuncle | T-Ed | new | new art; stand-in PR 44 Zokka | 32x38 |
| 475 | 1475 | Valigarmanda | T-Ed | new | new art; stand-in PR 32 Behemoth | 75x96 |
| 476 | 1476 | Wisp | T-Ed | new | new art; stand-in PR 77 Bandit | 21x32 |
| 477 | 1477 | Adamantoise | T-Ed | new | new art; stand-in PR 131 Dragon | 94x96 |
| 478 | 1478 | Tantarian | T-Ed | new | new art; stand-in PR 38 Brachiosaur | 88x51 |
| 479 | 1479 | Grimoire | T-Ed | new | new art; stand-in PR 38 Brachiosaur | 88x51 |
| 480 | 1480 | Last Wyrm | T-Ed | new | new art; stand-in PR 37 Fiend Dragon | 78x94 |
| 481 | 1481 | Mist Dragon | T-Ed | new | new art; stand-in PR 69 Armored Weapon | 79x63 |
| 482 | 1482 | Mist Dragon | T-Ed | new | new art; stand-in PR 60 Lizard | 79x23 |
| 483 | 1483 | Marilith | T-Ed | new | new art; stand-in PR 131 Dragon | 110x95 |
| 484 | 1484 | Lich | T-Ed | new | new art; stand-in PR 131 Dragon | 86x97 |
| 485 | 1485 | Kraken | T-Ed | new | new art; stand-in PR 131 Dragon | 108x93 |
| 486 | 1486 | Tiamat | T-Ed | new | new art; stand-in PR 131 Dragon | 103x93 |
| 487 | 1487 | Bahamut | T-Ed | new | new art; stand-in PR 131 Dragon | 96x128 |
| 488 | 1488 | Leviathan | T-Ed | new | new art; stand-in PR 37 Fiend Dragon | 64x82 |
| 489 | 1489 | Odin | T-Ed | new | new art; stand-in PR 5 Borghese | 61x80 |
| 490 | 1490 | Ahriman | T-Ed | new | new art; stand-in PR 131 Dragon | 85x91 |
| 491 | 1491 | 2-Head Dragon | T-Ed | new | new art; stand-in PR 43 Vasegiatta | 104x61 |
| 492 | 1492 | Echidna | T-Ed | new | new art; stand-in PR 83 Hill Gigas | 50x101 |
| 493 | 1493 | Nightmare | T-Ed | new | new art; stand-in PR 35 Fossil Dragon | 64x64 |
| 494 | 1494 | Alexander | T-Ed | new | new art; stand-in PR 131 Dragon | 88x124 |
| 495 | 1495 | Asura | T-Ed | new | new art; stand-in PR 37 Fiend Dragon | 62x88 |
| 496 | 1496 | Diabolos | T-Ed | new | new art; stand-in PR 131 Dragon | 112x112 |
| 497 | 1497 | Titan | T-Ed | new | new art; stand-in PR 13 Dark Force | 54x72 |
| 498 | 1498 | Barbariccia | T-Ed | new | new art; stand-in PR 42 Vulture | 63x73 |
| 499 | 1499 | Rubicante | T-Ed | new | new art; stand-in PR 32 Behemoth | 48x96 |
| 500 | 1500 | Scarmiglione | T-Ed | new | new art; stand-in PR 12 Apocrypha | 64x62 |
| 501 | 1501 | Cagnazzo | T-Ed | new | new art; stand-in PR 129 Wyvern | 79x48 |
| 502 | 1502 | Bahamut | T-Ed | new | new art; stand-in PR 131 Dragon | 96x128 |
| 503 | 1503 | Enkidu | T-Ed | new | new art; stand-in PR 83 Hill Gigas | 64x103 |
| 504 | 1504 | Barbariccia | T-Ed | new | new art; stand-in PR 37 Fiend Dragon | 64x80 |
| 505 | 1505 | Rubicante | T-Ed | new | new art; stand-in PR 32 Behemoth | 47x96 |
| 506 | 1506 | Scarmiglione | T-Ed | new | new art; stand-in PR 53 Vampire Thorn | 40x40 |
| 507 | 1507 | Cagnazzo | T-Ed | new | new art; stand-in PR 38 Brachiosaur | 87x52 |
| 508 | 1508 | Odin | T-Ed | new | new art; stand-in PR 5 Borghese | 61x77 |
| 509 | 1509 | Burn Tyrant | T-Ed | new | new art; stand-in PR 131 Dragon | 88x111 |
| 510 | 1510 | Asura | T-Ed | new | new art; stand-in PR 37 Fiend Dragon | 62x88 |
| 512 | 1512 | Cloud of Darkness | EX | new | new art; stand-in PR 131 Dragon | 126x98 |
| 513 | 1513 | Golbez | EX | new | new art; stand-in PR 131 Dragon | 123x124 |
| 514 | 1514 | Golbez | EX | new | new art; stand-in PR 131 Dragon | 125x126 |
| 515 | 1515 | Zeromus | EX | new | new art; stand-in PR 43 Vasegiatta | 96x64 |
| 516 | 1516 | Zeromus | EX | new | new art; stand-in PR 131 Dragon | 128x128 |
| 517 | 1517 | Exdeath | EX | new | new art; stand-in PR 131 Dragon | 107x125 |
| 520 | 1520 | Sephiroth | EX | new | new art; stand-in PR 131 Dragon | 128x128 |
| 521 | 1521 | Ultimecia | EX | new | new art; stand-in PR 83 Hill Gigas | 80x123 |
| 522 | 1522 | Chaos | EX | new | new art; stand-in PR 131 Dragon | 111x96 |
| 523 | 1523 | Mateus | EX | new | new art; stand-in PR 131 Dragon | 128x98 |
| 524 | 1524 | Mateus | EX | new | new art; stand-in PR 131 Dragon | 120x115 |
| 525 | 1525 | Neo Exdeath | EX | new | new art; stand-in PR 131 Dragon | 128x123 |
| 526 | 1526 | Kam'lanaut | EX | new | new art; stand-in PR 83 Hill Gigas | 64x100 |
| 527 | 1527 | Eald'narche | EX | new | new art; stand-in PR 3 Ninja | 48x64 |
| 528 | 1528 | Ark Angel | EX | new | new art; stand-in PR 83 Hill Gigas | 63x111 |
| 529 | 1529 | Ark Angel | EX | new | new art; stand-in PR 4 Samurai | 55x63 |
| 530 | 1530 | Ark Angel | EX | new | new art; stand-in PR 156 Test Rider | 90x83 |
| 531 | 1531 | Ark Angel | EX | new | new art; stand-in PR 4 Samurai | 56x61 |
| 532 | 1532 | Ark Angel | EX | new | new art; stand-in PR 131 Dragon | 109x104 |
| 533 | 1533 | Sephiroth | EX | new | new art; stand-in PR 131 Dragon | 128x128 |
| 534 | 1534 | Orbital | EX | new | new art; stand-in PR 76 Cactuar | 20x19 |
| 535 | 1535 | Orbital | EX | new | new art; stand-in PR 76 Cactuar | 20x19 |
| 536 | 1536 | Kuja | EX | new | new art; stand-in PR 37 Fiend Dragon | 50x90 |
| 537 | 1537 | Seymour | EX | new | new art; stand-in PR 83 Hill Gigas | 84x110 |
| 538 | 1538 | Anima | EX | new | new art; stand-in PR 83 Hill Gigas | 70x119 |
| 539 | 1539 | Omega Weapon | EX | recolor | recolor of PR 279 Ultima Weapon | 128x128 |

## Appendix B. T-Edition's own songs on the main driver (175)

From `bgm.html` (player number, song id, display name, where T-Edition uses it) and the map lists above. "Guide: where used" is the guide's wording ("-" = not named). The map column comes from `ted_maps.json` (new maps) and my ROM read (vanilla maps).

| Player no. | Song id | Name | Guide: where used | Map-property use |
|---|---|---|---|---|
| 74 | 37 (0x25) | Final Fantasy Xmas Arr | Plays in the Achievement Room upon 100% completion. | - |
| 75 | 207 (0xCF) | FF1 Matoya's Cave | Matoya's Cave. | new maps 453-458 |
| 76 | 209 (0xD1) | FF1 Battle Scene | Matoya's Cave Battle. | - |
| 77 | 169 (0xA9) | FF1 Inside a Boss Battle | Battle VS. Astos and Chaos. | - |
| 78 | 128 (0x80) | FF1 Boss Battle A | Battle VS. Lich and Kraken. | - |
| 79 | 129 (0x81) | FF1 Boss Battle B | Battle VS. Marilith and Tiamat. | - |
| 80 | 245 (0xF5) | FF2 Town | Locke's "Wild Rose Bandana" Falcon song. | - |
| 81 | 186 (0xBA) | FF2 Rebel Army Theme | World of Ruin Narshe Elder's House after meeting Banon. Gogo's "Mysidian Priest's Robe" Falcon song. | - |
| 82 | 123 (0x7B) | FF2 Dungeon | Ebot's Rock. | vanilla maps 404-405 |
| 83 | 95 (0x5F) | FF2 Battle Scene 1 | Ebot's Rock Battle. | - |
| 84 | 172 (0xAC) | FF2 Battle Scene 2 | Battle VS. Skull Dragon. | - |
| 85 | 130 (0x82) | FF2 Battle Scene A | Battle VS. Hidon and Emperor Mateus. | - |
| 86 | 200 (0xC8) | FF3 Cute Little Tozas | Relm's "Sky-Blue Dirndl" Falcon song. | - |
| 87 | 199 (0xC7) | FF3 Elia the Maiden of Water | Relm's "White Robe" Falcon song. | - |
| 88 | 122 (0x7A) | FF3 Town of Water | Town of Maranda. | - |
| 89 | 251 (0xFB) | FF3 Let Me Know the Truth | Strago's "Black Robe" Falcon song. | - |
| 90 | 107 (0x6B) | FF3 Cave Crystal | Labyrinth of the Ancients. | new maps 417-420, 431-432 |
| 91 | 104 (0x68) | FF3 Forbidden Land Eureka | Forbidden Land Eureka. | new maps 421-428 |
| 92 | 63 (0x3F) | FF3 The Crystal Tower | Crystal Tower. | new maps 497-504 |
| 93 | 90 (0x5A) | FF3 Battle 1 | Labyrinth of the Ancients/Forbidden Land Eureka Battle. | - |
| 94 | 154 (0x9A) | FF3 Battle 2 | Battle VS. Cerberus, Ahriman, Echidna, and Two-Headed Dragon. | - |
| 95 | 231 (0xE7) | FF3 Final Battle | Soul Shrine Group 10. Battle VS. Cloud of Darkness. | - |
| 96 | 249 (0xF9) | FF4 Red Wings | Edgar's "Dragon Mail" Falcon song. | - |
| 97 | 222 (0xDE) | FF4 Theme of Love | Celes's "Opera Dress" Falcon song. | - |
| 98 | 223 (0xDF) | FF4 Rydia | Terra's "Feymarch Bustier" Falcon song. | - |
| 99 | 206 (0xCE) | FF4 Hey Cid! | Strago's "Engineer's Goggles" Falcon song. | - |
| 100 | 225 (0xE1) | FF4 Hello! Big Chocobo! | Gogo's "Chameleon Robe" Falcon song. | - |
| 101 | 86 (0x56) | FF4 Kingdom Baron | Imperial Castle at Vector. Setzer's "Knight's Armor" Falcon song. | vanilla maps 243-244, 250, 252 |
| 102 | 87 (0x57) | FF4 Mystic Mysidia | WoB Thamasa. Strago's "Guru's Glasses" Falcon song. | - |
| 103 | 250 (0xFA) | FF4 Fabul | Sabin's "Fabul Martial Wear" Falcon song. | - |
| 104 | 88 (0x58) | FF4 The Lunarians | Soul Shrine. Strago's "Lunar Cloak" Falcon song. | new maps 433 |
| 105 | 178 (0xB2) | FF4 Mt. Ordeals | Shadow's "Shinobi Clothing" Falcon song. | - |
| 106 | 92 (0x5C) | FF4 Illusionary World | WoB Eidolon Village. | vanilla maps 217-219 |
| 107 | 85 (0x55) | FF4 Into the Darkness | Phoenix's Cave. | vanilla maps 313, 315 |
| 108 | 168 (0xA8) | FF4 Dancing Calcobrena | Cyan's Dream event. | - |
| 109 | 217 (0xD9) | FF4 Lunar Whale | Shadow's "Lunar Mail" Falcon song. | - |
| 110 | 106 (0x6A) | FF4 Battle 1 | Phoenix's Cave Battle. | - |
| 111 | 139 (0x8B) | FF4 Battle 2 | Battle VS. Mom Bomb, Mist Dragon, and Ashura. | - |
| 112 | 135 (0x87) | FF4 The Dreadful Fight | Battle VS. 4 Elements and Golbez. | - |
| 113 | 233 (0xE9) | FF4 The Final Battle | Soul Shrine Group 11. Zeromus Battle. | - |
| 114 | 117 (0x75) | FF5 My Home Sweet Home | Kohlingen. Gau's "Traveler's Clothes" Falcon song. | vanilla maps 188 |
| 115 | 114 (0x72) | FF5 Music Box -Arranged- | Kohlingen Bar after the sidequest "Requiem". | - |
| 116 | 158 (0x9E) | FF5 Lenna | Battle VS. Last Wyrm. | - |
| 117 | 246 (0xF6) | FF5 Spreading Grand Wings | Relm's "Bal Kingdom Princess Clothing" Falcon song. | - |
| 118 | 226 (0xE2) | FF5 Dear Friends | Shadow's "Wanderer's Cloak" Falcon song. | - |
| 119 | 159 (0x9F) | FF5 The Dawn Warriors | Fanatic's Tower after Omniscient's defeat. Gogo's "Great Tree's Heavy Armor" Falcon song. | - |
| 120 | 108 (0x6C) | FF5 Battle 1 | Fanatic's Tower Battle. | - |
| 121 | 146 (0x92) | FF5 Battle 2 | Battle VS. Carbuncle, Catoblepas, and Gil Turtle. | - |
| 122 | 140 (0x8C) | FF5 Battle on the Big Bridge | Gilgamesh Battles. | - |
| 123 | 142 (0x8E) | FF5 The Decisive Battle | Battle VS. Omniscient and Exdeath. | - |
| 124 | 141 (0x8D) | FF5 The Last Battle | Soul Shrine Group 12. Battle VS. Neo Exdeath. | - |
| 125 | 105 (0x69) | FF6 Town2/Unreleased | Gogo's "Aegishjalmr" Falcon song. | - |
| 126 | 112 (0x70) | FF6 Town3/Unreleased | WoB Mobliz. | vanilla maps 157, 160-161, 164 |
| 127 | 118 (0x76) | FF7 Ahead On Our Way | Tzen. | - |
| 128 | 247 (0xF7) | FF7 Holding My Thoughts in My Heart | Setzer's "Jet-Black Coat" Falcon song. | - |
| 129 | 193 (0xC1) | FF7 Interrupted By Fireworks | "Thoughts and Wishes" sidequest. Shadow's "SOLDIER Uniform" Falcon song. | - |
| 130 | 252 (0xFC) | FF7 Aerith's Theme | Terra's "Flower Seller's Dress" Falcon song. | - |
| 131 | 253 (0xFD) | FF7 Cosmo Canyon | Umaro's "Full-Moon Hairpins" Falcon song. | - |
| 132 | 215 (0xD7) | FF7 Gold Saucer | Mog's "Shiny-Gold Crown" Falcon song. | - |
| 133 | 208 (0xD0) | FF7 Forested Temple | WoR Phantom Forest. | new maps 447-452 |
| 134 | 198 (0xC6) | FF7 Cid's Theme | Edgar's "Pilot's Suit" Falcon song. | - |
| 135 | 211 (0xD3) | FF7 Fighting | WoR Phantom Forest Battle. | - |
| 136 | 145 (0x91) | FF7 Those Who Fight Further | Battle VS. Number 128 and Inferno. | - |
| 137 | 164 (0xA4) | FF7 J-E-N-O-V-A | Battle VS. Omega. | - |
| 138 | 234 (0xEA) | FF7 One Winged Angel | Soul Shrine Group 14. Battle VS. Sephiroth. | - |
| 139 | 166 (0xA6) | FF8 Fisherman's Horizon | Solitary Island (Cid's alive). Edgar's "Cross-Sword Coat" Falcon song. | - |
| 140 | 195 (0xC3) | FF8 Roses and Wine | WoR South Figaro Bar after "A Girl's Wish" sidequest. | - |
| 141 | 185 (0xB9) | FF8 Fragments of Memories | Locke's "SeeD Jacket" Falon song. | - |
| 142 | 120 (0x78) | FF8 The Man with the Machine Gun | Cyan's Dream Dungeon Battle. | - |
| 143 | 148 (0x94) | FF8 Force Your Way | Battle VS. IAF and Ironclad. | - |
| 144 | 230 (0xE6) | FF8 The Extreme | Soul Shrine Group 15. Battle VS. Ultimecia. | - |
| 145 | 238 (0xEE) | FF9 A Place to Call Home | Crystal Room (EX). Gau's "Honorable Thief's Vest" Falcon song. | - |
| 146 | 212 (0xD4) | FF9 Quina's Theme | Umaro's "Pure-White Apron" Falcon song. | - |
| 147 | 248 (0xF8) | FF9 South Gate | Mog's "Mog Bag" Falcon song. | - |
| 148 | 116 (0x74) | FF9 Unforgettable Sorrow | Cyan's Dream - Doma Castle after event. Cyan's "Exotic Foreign Armor" Falcon song. | - |
| 149 | 243 (0xF3) | FF9 Rose of May | Celes's "Alexandrian General Armor" Falcon song. | - |
| 150 | 137 (0x89) | FF9 You're Not Alone | Cyan's Dream event. | - |
| 151 | 188 (0xBC) | FF9 Terra | Lost Road to the Sealed Gate. | vanilla maps 387; new maps 435, 506 |
| 152 | 214 (0xD6) | FF9 Crystal World | Crystal Room. | new maps 477-480 |
| 153 | 113 (0x71) | FF9 Battle 1 | Lost Road to the Sealed Gate Battle. | - |
| 154 | 161 (0xA1) | FF9 Battle 2 | Battle VS. Earth Dragon. | - |
| 155 | 196 (0xC4) | FF10 To Zanarkand | Cyan's "Spira Monk Clothes" Falcon song. | - |
| 156 | 202 (0xCA) | FF10 Men Staked on Blitz | Sabin's "Auroch Bandana" Falcon song. | - |
| 157 | 111 (0x6F) | FF10 Movement in Green | WoR Mobliz after Humbaba's defeat. | - |
| 158 | 254 (0xFE) | FF10 Yuna's Theme | Celes's "Summoner's Kimono" Falcon song. | - |
| 159 | 98 (0x62) | FF10 Path of Repentance | Daryl's Tomb. | vanilla maps 297-300 |
| 160 | 197 (0xC5) | FF10 Yuna's Decision | Celes's "Witch's Robe" Falcon song. | - |
| 161 | 102 (0x66) | FF10 Servants of the Mountain | Eidolon Mountain. Umaro's "Ronso Waist Cloth" Falcon song. | vanilla maps 371-375 |
| 162 | 213 (0xD5) | FF10 Normal Battle | Daryl's Tomb Battle. | - |
| 163 | 165 (0xA5) | FF10 Seymour Battle | Battle VS. Shinryu. | - |
| 164 | 205 (0xCD) | FF10-2 Eternity -Band ver- | Gau's "Ace Uniform" Falcon song. | - |
| 165 | 240 (0xF0) | FF11 Mog House | Mog House (Collector's Room small area). | new maps 467, 491 |
| 166 | 177 (0xB1) | FF11 Windurst | Relm's "Wizard's Attire" Falcon song. | - |
| 167 | 236 (0xEC) | FF11 The Grand Duchy of Jeuno | Developer's Room. | new maps 463-464 |
| 168 | 237 (0xED) | FF11 Kazham | Developer's Room - Eidolon Village. | new maps 466, 468 |
| 169 | 189 (0xBD) | FF11 Recollection | Cyan's Dream event. | - |
| 170 | 162 (0xA2) | FF11 Fighters of the Crystal | Ark Angels battle. | - |
| 171 | 239 (0xEF) | FF11 Belief | Battle VS. Kam'lanaut and Eald'narche. | - |
| 172 | 204 (0xCC) | FF11 Currents of Time | Mog's "Tonberry Coat" Falcon song. | - |
| 173 | 216 (0xD8) | FF11 A New Horizon | Cyan's "Gold-Trim Armor" Falcon song. | - |
| 174 | 115 (0x73) | FF11 The Cosmic Wheel | WoR Thamasa. | vanilla maps 344 |
| 175 | 176 (0xB0) | FF11 Luck of the Mog | Soul Shrine Group 4. | - |
| 176 | 210 (0xD2) | FF12 Clan Headquarters | Locke's "Sky Pirate's Clothing" Falcon song. | - |
| 177 | 201 (0xC9) | FF12 Time For a Rest | Setzer's "Emperor's Redingote" Falcon song. | - |
| 178 | 97 (0x61) | FF12 Eruyt Village | WoR Eidolon Village. | new maps 437-438 |
| 179 | 203 (0xCB) | FF12 Destiny | Cyan's "Judge's Mail" Falcon song. | - |
| 180 | 242 (0xF2) | FF13 The Sunleth Waterscape | Narshe during the sidequest "Night Patrol". Sabin's "Nora's Coat" Falcon song. | new maps 473-476 |
| 181 | 244 (0xF4) | FF13 March of the Dreadnoughts | Terra's "Bodhum Military Uniform" Falcon song. | - |
| 182 | 100 (0x64) | FF13 Blinded By Light | Ancient Castle Cave and Ancient Castle Battle. | - |
| 183 | 124 (0x7C) | FF13-2 Noel -Final Journey- | WoR World Map after obtaining the Falcon. | - |
| 184 | 81 (0x51) | FF0 Zero | "A Mother's Hope" sidequest. | - |
| 185 | 93 (0x5D) | FFT Tutorial | Narshe's Beginner's Hall - Advanced course selection. | - |
| 186 | 170 (0xAA) | FFT Antipyretic | Narshe Defense Battle. | - |
| 187 | 190 (0xBE) | FFTA Amber Valley | "Protect Mt. Koltz!" sidequest. | new maps 441 |
| 188 | 125 (0x7D) | FFT4HL Vulpes -Daytime- | Albrook. | - |
| 189 | 138 (0x8A) | FFT4HL Vulpes -Night- | Albrook (during new story event). | - |
| 190 | 241 (0xF1) | BDFF That Person's Name is | Soul Shrine Group 9. | - |
| 191 | 156 (0x9C) | SD1 Battle 2 | Battle VS. Freeze Dragon. | - |
| 192 | 160 (0xA0) | SD2 Meridian Dance | Battle VS. Valigarmanda. | - |
| 193 | 181 (0xB5) | SD3 Nuclear Fusion | Battle VS. Diabolos. | - |
| 194 | 153 (0x99) | MQ Battle 2 | Battle VS. Yellow Dragon. | - |
| 195 | 183 (0xB7) | SG2 Decisive Battle | Battle VS. Blue Dragon. | - |
| 196 | 180 (0xB4) | SG3SOL Pileup Stack | Battle VS. Storm Dragon. | - |
| 197 | 218 (0xDA) | RS1 Grey | Edgar's "Disguise Set" Falcon song. | - |
| 198 | 94 (0x5E) | RS1 Dungeon 1 | Narshe Mines. | vanilla maps 41-43, 48-51 |
| 199 | 192 (0xC0) | RS1 Horrible Shadow | WoR South Figaro Basement during the quest "A Girl's Wish". | new maps 445-446 |
| 200 | 96 (0x60) | RS1 Battle 1 | WoR South Figaro Basement Battle. | - |
| 201 | 157 (0x9D) | RS1 Battle 2 | Battle VS. Triceratops and Burn Tyrant. | - |
| 202 | 228 (0xE4) | RS1 Coup De Grace | Soul Shrine Group 6. | - |
| 203 | 187 (0xBB) | RS2 The Sinking Ship | South Figaro Cave during the sidequest "Destroy the Cave Demons". | new maps 440, 442-443 |
| 204 | 99 (0x63) | RS2 Normal Battle | South Figaro Cave Battle during the sidequest "Destroy the Cave Demons". | - |
| 205 | 194 (0xC2) | RS2 Battle with Kujinshi | South Figaro Cave Boss Battle during the sidequest "Destroy the Cave Demons". | - |
| 206 | 229 (0xE5) | RS2 Last Battle | Soul Shrine Group 7. | - |
| 207 | 219 (0xDB) | RS3 Julian | Locke's "Ancient Armor" Falcon song. | - |
| 208 | 220 (0xDC) | RS3 Tomas | Gau's "Tuxedo" Falcon song. | - |
| 209 | 221 (0xDD) | RS3 Katalina | Terra's "Silk Dress" Falcon song. | - |
| 210 | 91 (0x5B) | RS3 Nightmare | Cyan's Dream Dungeon. | vanilla maps 317 |
| 211 | 101 (0x65) | RS3 Boundaries | WoR Narshe. | vanilla maps 32-38; new maps 461 |
| 212 | 150 (0x96) | RS3 Fairy Town | WoR Mobliz Houses. | vanilla maps 44 |
| 213 | 224 (0xE0) | RS3 Snowman's Town | Mog's "Geomancer's Hat" Falcon song. | - |
| 214 | 103 (0x67) | RS3 Bottom Sea Palace | Ancient Castle Cave. | vanilla maps 401-402 |
| 215 | 167 (0xA7) | RS3 Holy King Temple | Holy Angel Ultima's Floor. | new maps 505 |
| 216 | 126 (0x7E) | RS3 Battle 1 | WoR Narshe Battle. | - |
| 217 | 144 (0x90) | RS3 Battle 2 | Battles VS. Seraphim and Necronomicon. | - |
| 218 | 149 (0x95) | RS3 Four Noble Devils 1 | Battle VS. Bahamut. | - |
| 219 | 151 (0x97) | RS3 Four Noble Devils 2 | Battle VS. Leviathan. | - |
| 220 | 174 (0xAE) | RS3 Gen's Castle Battle | Soul Shrine Group 2. | - |
| 221 | 136 (0x88) | RS3 Last Battle | Soul Shrine Group 8. | - |
| 222 | 109 (0x6D) | SF1 Trick | Owzer's Mansion. | - |
| 223 | 110 (0x6E) | SF1 Alone | Sealed Cave. | vanilla maps 353 |
| 224 | 119 (0x77) | SF1 Battle #1 | Sealed Cave Battle. | - |
| 225 | 191 (0xBF) | SF1 Battle #2 | Battle VS. Chadarnook. | - |
| 226 | 131 (0x83) | SF1 Battle #3 | Battle VS. Fiend. | - |
| 227 | 132 (0x84) | SF1 Battle #4 | Battle VS. Demon. | - |
| 228 | 134 (0x86) | SF1 Battle #5 | Battle VS. Reverse Leo. | - |
| 229 | 133 (0x85) | SF1 Last Battle Asellus | Battle VS. Goddess. | - |
| 230 | 184 (0xB8) | SF2 Besessenheit | Battle VS. Holy Dragon. | - |
| 231 | 143 (0x8F) | MS Believing My Justice | Battle VS. Odin. | - |
| 232 | 227 (0xE3) | US Battle Theme I | Soul Shrine Group 5. | - |
| 233 | 171 (0xAB) | XE Distant Promise | "Father and Daughter" sidequest. | - |
| 234 | 147 (0x93) | XE Ship of Regret and Sleep | Rachel's Room. | vanilla maps 195 |
| 235 | 173 (0xAD) | XE Shevat | Ancient Castle. | vanilla maps 406, 408; new maps 484, 493 |
| 236 | 175 (0xAF) | XE Flight | Soul Shrine Group 3. | - |
| 237 | 232 (0xE8) | XE Awaken | Battle VS. Ultima. | - |
| 238 | 73 (0x49) | XB You Will Know Our Names | Battles VS. Ultima Buster. | - |
| 239 | 56 (0x38) | XB Agnilatha -Night- | WoR Floating Continent. | new maps 509 |
| 240 | 121 (0x79) | LOM Hometown Domina | Nikeah. | - |
| 241 | 163 (0xA3) | LAL MEGALOMANIA | Battle VS. Guardian. | - |
| 242 | 155 (0x9B) | LAL PURE ODIO | Battle VS. Wrexsoul. | - |
| 243 | 89 (0x59) | CT Corridors of Time | Mt. Zozo. | vanilla maps 176-181; new maps 482-483 |
| 244 | 127 (0x7F) | CT Battle 1 | Mt. Zozo Battle. | - |
| 245 | 179 (0xB3) | CT Battle 2 | Coliseum Battle. | - |
| 246 | 235 (0xEB) | CT Battle with Magus | Soul Shrine Group 13. | - |
| 247 | 182 (0xB6) | RUD The Flame and the Arrow | Battle VS. Red Dragon. | - |
| 248 | 152 (0x98) | EST2 Battle 2 | Battle VS. Humbaba (4). | - |

## Appendix C. Fanfares and jingles outside the player (second driver, `bgm.html`)

Song ids are the second driver's. The EST2 "Victory" fanfare (battle vs Humbaba (4)) has no id in the guide (0xD1 by elimination). `data/ted_music_player.json` shows these 30 with `pr_bgm` null; the vanilla "Good Night" (id 0x38) is tracked on the second driver (PR bgm 74, `ted_songs.json` "second").

| Guide entry | Second-driver id | Name | Where used |
|---|---|---|---|
| Victory Fanfare 1 | 210 (0xD2) | FF1 Victory | Matoya's Cave. Ebot's Rock Battle. Battle VS. Astos, Chaos, Skull Dragon, Hidon, and Mateus. |
| Victory Fanfare 2 | 203 (0xCB) | FF3 Victory's Fanfare | Labyrinth of the Ancients. Forbidden Land Eureka. Battle VS. Cerberus, Ahriman, Echidna, Two-Headed Dragon, and Cloud of Darkness. |
| Victory Fanfare 3 | 201 (0xC9) | FF4 Victory's Fanfare | Phoenix's Cave Battle. Battle VS. Mom Bomb, Mist Dragon, Ashura, Golbez, 4 Fiends, and Zeromus. |
| Victory Fanfare 4 | 200 (0xC8) | FF5 Victory's Fanfare | Fanatic's Tower Battle. Battle VS. Carbuncle, Catoblepas, Titan, Omniscient, Gilgamesh, Gil Turtle, and Exdeath. |
| Victory Fanfare 5 | 212 (0xD4) | FF7 Fanfare | WoR Phantom Forest Battle. Battle VS. Number 128, Inferno, and Sephiroth. |
| Victory Fanfare 6 | 204 (0xCC) | FF8 The Winner | Cyan's Dream Dungeon Battle. Battle VS. IAF, Iron Clad, and Ultimecia. |
| Victory Fanfare 7 | 206 (0xCE) | FF9 Victory's Fanfare | Lost Path Battle. Battle VS. Earth Dragon and Kuja. |
| Victory Fanfare 8 | 214 (0xD6) | FF10 Victory's Fanfare | Daryl's Tomb Battle. Battle VS. Shinryu and Seymour. |
| Victory Fanfare 9 | 205 (0xCD) | FF13 Glory's Fanfare | Ancient Castle Cave and Ancient Castle Battle. |
| Victory Fanfare 10 | 207 (0xCF) | MQ Victory's Fanfare | Battle VS. Yellow Dragon. |
| Victory Fanfare 11 | 224 (0xE0) | SD2 Victory | Battle VS. Valigarmanda. |
| Victory Fanfare 12 | 225 (0xE1) | SD3 Victory | Battle VS. Diabolos. |
| Victory Fanfare 13 | 208 (0xD0) | SaGa 2 Eat the Meat! | Battle VS. Storm Dragon. |
| Victory Fanfare 14 | 196 (0xC4) | RS1 Victory! | WoR South Figaro Basement Battle. Battle VS. Burn Tyrant. |
| Victory Fanfare 15 | 197 (0xC5) | RS2 Victory! | South Figaro Cave Battle (Bar sidequest event). |
| Victory Fanfare 16 | 198 (0xC6) | RS3 Victory! | WoR Narshe. Battle VS. Seraphim, Necronomicon, Leviathan, Bahamut, and Ultima. |
| Victory Fanfare 17 | 199 (0xC7) | SF1 Victory! | Sealed Cave Battle. Battle VS. Chadarnook. |
| Victory Fanfare 18 | 213 (0xD5) | SF2 Freudenbezeigung IV | Battle VS. Holy Dragon. |
| Victory Fanfare 19 | 202 (0xCA) | CT Fanfare 1 | Mt. Zozo Battle. Coliseum. |
| Victory Fanfare 20 | 211 (0xD3) | RUD Winners Take All | Battle VS. Red Dragon. |
| Inn 22 | 222 (0xDE) | FF2 Inn | Jidoor Inn |
| Inn 23 | 219 (0xDB) | FF3 Inn | Maranda Inn |
| Inn 24 | 217 (0xD9) | FF4 Inn | Thamasa Inn |
| Inn 25 | 215 (0xD7) | FF5 Inn | Kohlingen Inn |
| Inn 73 | 56 (0x38) | FF6 Good Night | Various locations. |
| Inn 26 | 220 (0xDC) | FF7 Good Night, See You Tomorrow | Tzen Inn |
| Inn 27 | 221 (0xDD) | FF9 Good Night | Doma Castle Beds |
| Inn 28 | 218 (0xDA) | FF10 Good Night | Mobliz Beds |
| Inn 29 | 223 (0xDF) | FF: T4HL Now for a Good Night | Albrook Inn |
| Inn 30 | 216 (0xD8) | RS3 Overnight at the Inn | Narshe Inn |
