# T-Edition music and graphics: the plan (the lead, 2026-11-20)

From `MEDIA_INVENTORY.md` (what T-Edition has and where) and the kit's tools (`pr/MODDING.md`: "SNES music
player", "SNES sprites → PR art", "Monster images"). Every piece is built from the developer's T-Edition ROM
by a tool; whether the zip carries the results (T-Edition's songs and art are Tsushiy's, many from other
Square games) is the user's decision. Players need no ROM, so without that the mod plays the PR's music
and look-alike art.

## Music (owner: the TedPlugin session; `tools/ted_music.py`, `TedPlugin/TedMusic.cs`)

1. **Song pack** (`tools/snes_songs.py read_ff6_songs` on the US-layout image or the ROM's own tables): the
   175 own songs of the main driver at their slot numbers, the 34 second-driver songs that differ (the 30
   fanfares and inn jingles, 0x5B/0x6B/0xC0/0xC1) at $100 + slot, every BRR sample they use. `snes_songs.py
   check` lists resident-waveform and sound-effect uses. Written to `BepInEx/TEdition/music`
   (ted_build / ted_testinstall install it, like `ted_ai.json`).
2. **What plays where** (`bgm.json` for `BgmRules`):
   - `"tracks"`: PR bgm 1000 + slot for each own song, 1256 + slot for the second driver's.
   - `"maps"`: the 66 new maps and 55 vanilla maps with an own song (new maps by `ted_maps.json`; vanilla
     maps from the map properties at 4D/0000 against the JP ROM's).
   - `"battles"`: per party once T-Edition's battle-song rule is found (formation flags' byte 3 >> 4 plus
     its own table; EX's 13 fights).
   - The 70 vanilla songs keep the PR's tracks (`"songs"` pr_bgm).
3. **Events**: the translator (`event_translate.song_bgm`, the ted-events session) gives T-Edition's own
   songs PlayBGM 1000 + n (F0/EF/F1) and its fanfare/inn commands 76/9E/9F 1256 + n with the
   PauseBGM / jingle / ReplayBgm pattern. One line to ted-events when `ted_music.py` fixes the numbers.
4. **Later, with the menus**: the Falcon's song by worn costume (53 songs; the table isn't found yet) and
   the music player (277 entries, `data/ted_music_player.json`).
5. **Checks**: `plugin/Snes.Tests check | renderall`; `tools/snes_song_ref.py` against Snes9x for a
   handful of songs; one QA batch playing a new map, an event song and a fanfare.

## Graphics

| Piece | Owner | Tools | Count |
|---|---|---|---|
| Monsters: new, recolors, EX | ted-monsters, after its data items and the second item bank | `port_sprites.py` / `pr_art.py` `ArtWriter.monster` → `MonsterImages` (static, keyed by PR id 1000 + e) | 98 new + 18 recolors + 26 EX |
| Monsters redrawn in the vanilla range (0-383) | ted-monsters, after the above | the same | 76 |
| NPC sprites on the new maps | ted-maps | a PR look per SNES sprite number (look-alikes first) | 112 numbers |
| Costumes (56 + Gogo's 10 forms), portraits (75), the dressing room | a costumes session when the RAM budget allows (until then, after the monsters in ted-monsters) | `snes_charsprites.py group_frames`, `ArtSwap.Load` (swappable frame sets), TedPlugin's dressing-room menu | 56 + 10 + 75 |
| Tilesets 82-85 and edited ones, new battle backgrounds, the Collection Room paintings | later, only where a look-alike looks wrong in a QA run | `snes_rooms` look matching | — |

The inventory's open questions go to whoever owns the piece. Questions for the user (asked by the lead):
whether the songs and art ship in the zip, and whether to ask Tsushiy and Mato before a release.
