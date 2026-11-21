"""T-Edition's own songs as a song pack for the kit's SNES music player (PrKit/Snes; TedPlugin/TedMusic.cs).

    .venv/Scripts/python tools/ted_music.py [--out DIR] [--all]        (default DIR build/t-edition/music)

T-Edition has two copies of FF6's sound driver, each with its own 255-song table (tools/ted_songs.py):
  * C5 (vanilla's driver): map songs and the event commands F0 / EF / F1: pack slot = the song number;
  * bank 43 (a second copy): T-Edition's commands 76, 9E, 9F (victory fanfares, inn jingles, copies of
    vanilla's songs): pack slot = $100 + the song number.
Both drivers' pointers sit where vanilla's do in their bank (+0539 songs, +01E3 instruments, +0222 BRR, +041C loop,
+049C pitch, +04DE ADSR, +3C5E count). T-Edition (after the Omega patch) moved the per-song instrument tables to
5F/0480 (C5's) and 5F/2480 (43's) and the sample tables to 5F/0000 (loop), 5F/0180 (pitch), 5F/0300 (ADSR); the
BRR pointer table stays at C5/3C5F, shared by both drivers (For Producers/FF6-T Edition address changes.txt).
The pointers already say so, so this reads them the way tools/snes_songs.py does, from each bank's base.

Which songs: T-Edition's own (data/ted_songs.json "new" and "second_new": not vanilla's bytes); vanilla's songs
keep the PR's own tracks (the game plays them). --all puts every song of both tables in the pack (tests).
Names: the music player's display names (data/ted_music_player.json by song id).
Rules (BgmRules, ted_music.json): "tracks" {PR bgm id: slot}: a new song's PR bgm id is 1000 + its pack slot
(1000 + n for C5 song n, 1256 + n for bank-43 song n): map.csv bgm_id, scripts' PlayBGM and monster parties'
battle_bgm_asset_id name it (ted-maps / ted-events / the porter), and the plugin's SnesBgm plays the song;
"songs" {slot: {name, title}}.

player.json: rows for the PR's Extras music player (sound_player_list.csv + etc_text keys) for the new songs, in
T-Edition's music player order, after the PR's own rows (the lead's ted_build writes them into the Magicite data).

samples.json: where each of the pack's samples (BRR bytes) also exists: a byte-identical file in Beyond Chaos's
MIT repo (music/samples/legacy: FF6's own as 01-3F, T-Edition's as ts<index>, ...) or nowhere else ("no_source",
with the songs using each).

Shipping (the user's decision, 11-20; every mod owner's permission): the pack is mod data made from T-Edition's ROM
on the developer's PC and ships in the zip (BepInEx/TEdition/music), every sample included; it is not rebuilt on
the player's machine. FF6's own driver data and instrument samples may ship too: the pack carries FF6's 8 resident
waveforms (snes_songs_at.add_resident: "resident" rows, the player's real programs $00-$07 instead of its
synthesized stand-ins). The SNES ROM itself, other SNES data and the PR's files never ship.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitpath  # noqa: E402,F401
import snes_songs as SS  # noqa: E402

PR = os.path.dirname(HERE)
OUT = os.path.join(PR, "build", "t-edition", "music")
MATO = os.path.join(os.path.dirname(PR), "build", "t-edition", "T-Edition 3.0.7 (Mato).sfc")
TED_SONGS = os.path.join(PR, "data", "ted_songs.json")
PLAYER = os.path.join(PR, "data", "ted_music_player.json")
MAIN, SECOND = 0x50000, 0x430000        # the two drivers' banks (file offsets of C5/0000, 43/0000)
SECOND_SLOT = 0x100                      # bank-43 songs' pack slots: $100 + n
BGM_BASE = 1000                          # a new song's PR bgm id: 1000 + its pack slot


def _off(base, vanilla_off):
    """A driver table pointer's file offset in the driver whose bank starts at base (vanilla's C5 offsets
    relative to C5/0000)."""
    return base + (vanilla_off - MAIN)


def read_driver(rom, base, slots=None):
    """{"songs": {song: {"data", "instruments"}}, "samples": {id: {...}}, "count"} of the driver at `base`
    (tools/snes_songs.read_ff6_songs with the bank's own pointers)."""
    count = rom[_off(base, SS.OFF_COUNT)]
    song_tbl, inst_tbl = SS._ptr(rom, _off(base, SS.OFF_SONG_PTR)), SS._ptr(rom, _off(base, SS.OFF_INST_PTR))
    brr_tbl, loop_tbl = SS._ptr(rom, _off(base, SS.OFF_BRR_PTR)), SS._ptr(rom, _off(base, SS.OFF_LOOP_PTR))
    pitch_tbl, adsr_tbl = SS._ptr(rom, _off(base, SS.OFF_PITCH_PTR)), SS._ptr(rom, _off(base, SS.OFF_ADSR_PTR))
    songs, used = {}, set()
    for slot in range(count):
        if slots is not None and slot not in slots:
            continue
        a = SS._ptr(rom, song_tbl + 3 * slot)
        size = int.from_bytes(rom[a:a + 2], "little")
        if a == 0 or size == 0 or a + 2 + size > len(rom):
            continue
        data = rom[a + 2:a + 2 + size + 1]       # the driver copies one byte past the size (snes_songs)
        inst = [int.from_bytes(rom[inst_tbl + 32 * slot + 2 * i:inst_tbl + 32 * slot + 2 * i + 2], "little")
                for i in range(16)]
        songs[slot] = {"data": data, "instruments": inst}
        used.update(i for i in inst if i)
    samples = {}
    for sid in sorted(used):
        a = SS._ptr(rom, brr_tbl + 3 * (sid - 1))
        size = int.from_bytes(rom[a:a + 2], "little")
        brr = rom[a + 2:a + 2 + size]
        brr = brr[:len(brr) - len(brr) % 9]
        samples[sid] = {"brr": brr, "loop": int.from_bytes(rom[loop_tbl + 2 * (sid - 1):loop_tbl + 2 * (sid - 1) + 2], "little"),
                        "tune": list(rom[pitch_tbl + 2 * (sid - 1):pitch_tbl + 2 * (sid - 1) + 2]),
                        "adsr": list(rom[adsr_tbl + 2 * (sid - 1):adsr_tbl + 2 * (sid - 1) + 2])}
    return {"songs": songs, "samples": samples, "count": count}


def names():
    """song id -> display name: the music player's songs for the C5 table, its fanfares/jingles for bank 43."""
    main, second = {}, {}
    if os.path.exists(PLAYER):
        with open(PLAYER, encoding="utf-8") as f:
            for s in json.load(f)["songs"]:
                (main if s["in_player"] else second).setdefault(s["song"], s)
    return main, second


MAP_PROPS, MAP_SIZE, MAP_SONG = 0x4D0000, 33, 28      # T-Edition's map properties (4D/0000): the song at +28
US_MAP_PROPS = 0x2D8F00                               # the US ROM's (ED/8F00, as tools/bc_music.py MAP_SONGS)
MASTER = os.path.join("master", "Assets", "GameAssets", "Serial", "Data", "Master", "map.csv")


def installed_bgm():
    """PR map id -> the bgm id its map.csv row asks for as installed (T-Edition's merged folder over vanilla's)."""
    import csv
    out = {}
    for root in (os.path.join(PR, "vanilla"), os.path.join(PR, "mods", "TEdition")):
        path = os.path.join(root, MASTER)
        if os.path.exists(path):
            with open(path, encoding="utf-8", newline="") as f:
                for r in csv.DictReader(f):
                    out[int(r["id"])] = int(r["bgm_id"] or 0)
    return out


def map_rules(rom, pack_slots):
    """BgmRules "maps": each PR room of a SNES map whose song is one of T-Edition's own plays it, in place of the
    bgm id the room asks for: its installed map.csv bgm_id, the PR track of the map's vanilla song (the PR's map
    scripts start many rooms' music; a new map: its source room's), or 1000 + song once ted-maps writes that.
    New maps 416+: data/ted_maps.json (song, rooms' pr_id); vanilla maps 0-415: T-Edition's map properties and
    data/snes_pr_maps.json's rooms."""
    bgm = installed_bgm()
    import prdata as P
    us = SS.unheader(open(P.VANILLA_ROM, "rb").read())
    pr_track = SS.FF6_SONG_PR_BGM

    def vanilla_track(snes_map):
        """The PR track of the song this SNES map has in vanilla (the US ROM's map properties): what the PR plays
        there, by map.csv or by its map script (many rooms' map.csv bgm_id is 0)."""
        if snes_map is None or not (0 <= snes_map < 416):
            return None
        return pr_track.get(us[US_MAP_PROPS + MAP_SIZE * snes_map + MAP_SONG])

    rules, clash = {}, []
    counts = {"new": 0, "vanilla": 0}

    def add(pr_id, song, kind, snes_map):
        if song not in pack_slots:
            return
        prev = rules.get(str(pr_id))
        if prev and prev["slot"] != song:
            clash.append(pr_id)
            return
        src = {bgm.get(pr_id, 0), BGM_BASE + song}
        t = vanilla_track(snes_map)
        if t:
            src.add(t)
        rules[str(pr_id)] = {"from": sorted(src), "slot": song}
        counts[kind] += 1

    with open(os.path.join(PR, "data", "ted_maps.json"), encoding="utf-8") as f:
        new = json.load(f)["maps"]
    for m in new.values():
        for room in m.get("rooms", []):
            if room.get("pr_id"):
                add(room["pr_id"], m.get("song", 0), "new", (m.get("source") or {}).get("snes_map"))
    with open(os.path.join(PR, "data", "snes_pr_maps.json"), encoding="utf-8") as f:
        pairs = json.load(f)["maps"]
    for m in range(416):
        song = rom[MAP_PROPS + MAP_SIZE * m + MAP_SONG]
        for room in pairs.get(str(m), []):
            if room.get("pr_id"):
                add(room["pr_id"], song, "vanilla", m)
    note = (f"{counts['new']} rooms of new maps, {counts['vanilla']} rooms of vanilla maps play T-Edition's own songs"
            + (f"; {len(clash)} rooms shared by maps with different songs kept their first ({clash[:6]})" if clash else ""))
    return rules, note


PLAYER_LIST = os.path.join(PR, "vanilla", "master", "Assets", "GameAssets", "Serial", "Data", "Master", "sound_player_list.csv")
PLAYER_SECONDS = 180      # the jukebox's "time" for a new song (its length is the loop's: not measured yet)


def player_rows(pack_slots):
    """Rows for the PR's Extras music player (sound_player_list.csv: id, bgm_asset_id, message_id, time,
    fadeout_flag) for T-Edition's new songs in its own music player's order (data/ted_music_player.json), after the
    PR's own rows; each plays 1000 + slot (the SNES player), named by its etc_text key TED_BGM_<no>_NAME."""
    import csv
    with open(PLAYER_LIST, encoding="utf-8", newline="") as f:
        first = max(int(r["id"]) for r in csv.DictReader(f)) + 1
    with open(PLAYER, encoding="utf-8") as f:
        listed = [x for x in json.load(f)["songs"] if x["in_player"] and x["pr_bgm"] is None and x["song"] in pack_slots]
    rows, texts = [], {}
    for i, x in enumerate(sorted(listed, key=lambda x: x["no"])):
        key = "TED_BGM_%03d_NAME" % x["no"]
        rows.append({"id": first + i, "bgm_asset_id": BGM_BASE + x["song"], "message_id": key,
                     "time": PLAYER_SECONDS, "fadeout_flag": 1})
        texts[key] = x["name"]
    return {"about": "T-Edition's new songs for the PR's Extras music player (tools/ted_music.py): rows to add to "
                     "sound_player_list.csv and keys to add to etc_text_<lang>.txt (English names; other languages: the "
                     "same text). time is a placeholder (180 s): the jukebox's use of it is unchecked.",
            "rows": rows, "etc_text": texts}


# Battle music (T-Edition 3.0.7, read from its code):
#   the battle's song (C2/BD37 at battle start, the C5 driver): none when the formation's flag byte 3 bit 7 is set
#   (the field song goes on) or the event keeps it; else index (byte 3 >> 3) & 7 into vanilla's C2/BEDD
#   (24 14 33 2E 1A 3B FF FF), but index 1 (vanilla's Decisive Battle) reads T-Edition's per-formation table
#   CF/2F70 (C0/DA70; 0: song 14): its many boss and area battle themes;
#   the victory fanfare (C1/0124 -> 45/0000, the bank-43 driver): song 2F (vanilla's fanfare), or with flag byte 1
#   bit 1 the formation's own from CF/B500 (0: none): T-Edition's "Victory Fanfare" songs (bank 43 C4-E1).
FLAGS, BATTLE_SONGS, SONG_INDEX, FANFARES = 0x0F2400, 0x0F2F70, 0x02BEDD, 0x0FB500
DEFAULT_FANFARE = 0x2F
PAUSE_SONGS = 0x0506F9    # C5/06F9: the songs after which the interrupted song resumes (tools/bc_music.py)


def formation_music(rom, f):
    """(battle song: a C5 song or None = the field song goes on, victory fanfare: a bank-43 song or None)."""
    fl = rom[FLAGS + 4 * f:FLAGS + 4 * f + 4]
    battle = None
    if not fl[3] & 0x80:
        idx = (fl[3] >> 3) & 7
        battle = (rom[BATTLE_SONGS + f] or 0x14) if idx == 1 else rom[SONG_INDEX + idx]
        battle = None if battle == 0xFF else battle
    fanfare = (rom[FANFARES + f] or None) if fl[1] & 0x02 else DEFAULT_FANFARE
    return battle, fanfare


def pause_songs(rom):
    out = []
    for b in rom[PAUSE_SONGS:PAUSE_SONGS + 8]:
        if b == 0 or b >= 0x80:
            break
        out.append(b)
    return out


def battle_rules(rom, table, rules, pack_slots, names_=None):
    """BgmRules "battles" {PR monster party: {"slot"}} (each party plays its formation's song: one of the pack's,
    or a slot naming the game's own track; -1 the field song goes on) and "fanfares" (the same for the victory
    fanfare: the player picks it per battle), for every party the game and the port have for T-Edition's 768
    formations (idmap.party, port_encounters.party_ids over the installed monster_party.csv). Parties whose
    battle_bgm_asset_id is 0 (an event keeps its music) and choices equal to what the game plays anyway are left
    out. Adds "songs" entries with pr_bgm for vanilla's songs the choices name."""
    import csv
    import idmap as M
    import port_encounters as E
    import prdata as P
    parties = {int(r["id"]): r for r in P.Table("monster_party")}
    staged = os.path.join(PR, "mods", "TEdition", MASTER.replace("map.csv", "monster_party.csv"))
    if os.path.exists(staged):
        with open(staged, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                parties[int(r["id"])] = r
    main_names, second_names = names_ or names()
    missing = []

    def game_slot(slot, song, track, name):
        rules["songs"].setdefault("%X" % slot, {"name": name, "title": "", "pr_bgm": track})
        return slot

    def battle_slot(song):
        if song is None:
            return -1
        if song in pack_slots:
            return song
        track = table["songs"].get(str(song))
        if track:
            return game_slot(song, song, track, (main_names.get(song) or {}).get("name") or "song %02X" % song)
        missing.append("C5 %02X" % song)
        return None

    def fanfare_slot(song):
        if song is None:
            return -1
        t = rules["tracks"].get(str(BGM_BASE + SECOND_SLOT + song))
        if t is not None:
            return t
        track = table["second"].get(str(song))
        if track:
            return game_slot(SECOND_SLOT + song, song, track, (second_names.get(song) or {}).get("name") or "song 43:%02X" % song)
        missing.append("43 %02X" % song)
        return None

    def plays(slot, party_bgm):
        """What the game would play anyway for this choice (the party's own track: no rule needed)."""
        s = rules["songs"].get("%X" % slot) if slot is not None and slot >= 0 else None
        return s is not None and s.get("pr_bgm") == party_bgm

    battles, fanfares, kept = {}, {}, 0
    for f in range(768):
        ids = list(E.party_ids(f, parties)) + ([M.party(f)] if f < 576 else [])
        battle, fanfare = formation_music(rom, f)
        b, v = battle_slot(battle), fanfare_slot(fanfare)
        for p in ids:
            row = parties.get(p)
            if row is None or str(p) in battles or str(p) in fanfares:
                continue
            bgm = int(row["battle_bgm_asset_id"] or 0)
            if bgm == 0:
                kept += 1
                continue
            if b is not None and not plays(b, bgm):
                battles[str(p)] = {"slot": b}
            if v is not None and not plays(v, 7):          # 7: the PR's victory fanfare, every win's
                fanfares[str(p)] = {"slot": v}
    rules["battles"], rules["fanfares"] = battles, fanfares
    rules["pause_songs"] = pause_songs(rom)
    return (f"battles: {len(battles)} parties play T-Edition's battle song, {len(fanfares)} its own victory fanfare "
            f"({kept} event parties keep their music; no song for {sorted(set(missing)) or 'none'}); "
            f"pause songs {' '.join('%02X' % s for s in rules['pause_songs'])}")


BC_SAMPLES = os.path.join(os.path.dirname(PR), "mods", "beyond-chaos", "src", "BeyondChaos", "music", "samples", "legacy")


def sample_sources(songs, samples, bc_dir=BC_SAMPLES):
    """Which samples also exist, byte for byte, in Beyond Chaos's MIT repo (its .brr files: a 2-byte loop header,
    then the BRR blocks), and which exist nowhere else, with the songs using each (by pack slot and name)."""
    import glob
    files = {}
    for path in sorted(glob.glob(os.path.join(bc_dir, "*.brr"))):
        with open(path, "rb") as f:
            x = f.read()
        files.setdefault(bytes(x[2:] if len(x) % 9 == 2 else x), os.path.basename(path))
    users = {}
    for slot, s in sorted(songs.items()):
        for i in s["instruments"]:
            if i and slot not in users.setdefault(i, []):
                users[i].append(slot)
    bc, none = {}, []
    for sid, s in sorted(samples.items()):
        name = files.get(bytes(s["brr"]))
        if name:
            bc["%02X" % sid] = name
        else:
            none.append({"id": "%02X" % sid, "bytes": len(s["brr"]),
                         "songs": [{"slot": "%X" % n, "name": songs[n]["name"]} for n in users.get(sid, [])]})
    using = sorted({n for x in none for n in users.get(int(x["id"], 16), [])})
    return {"about": "T-Edition's samples (ids as the songs' instrument tables give them, 1-based: BC's ts<index> files "
                     "are named by index, sample - 1) found byte for byte in Beyond Chaos's MIT repo "
                     "(src/BeyondChaos/music/samples/legacy), and those found nowhere else with the songs that use them "
                     "(pack slots: C5 n, bank 43 $100 + n)",
            "bc_mit": bc, "no_source": none,
            "songs_using_no_source": ["%X" % n for n in using]}


def build(out=OUT, every=False, log=print):
    rom = SS.unheader(open(MATO, "rb").read())
    with open(TED_SONGS, encoding="utf-8") as f:
        table = json.load(f)
    new_main = set(table["new"]) if not every else None
    new_second = set(table["second_new"]) if not every else None
    a = read_driver(rom, MAIN, new_main)
    b = read_driver(rom, SECOND, new_second)
    main_names, second_names = names()
    songs, samples, rules = {}, dict(a["samples"]), {"tracks": {}, "songs": {}}
    # a bank-43 song that is one of C5's (bytes and instruments): its track plays that one (C5's own slot when
    # it's in the pack, the game's track when it's one of vanilla's songs with a PR track)
    every_main = read_driver(rom, MAIN)["songs"]
    by_bytes = {}
    for n, s_ in sorted(every_main.items()):
        by_bytes.setdefault((bytes(s_["data"]), tuple(s_["instruments"])), n)
    copies = 0
    for n in list(b["songs"]):
        m = by_bytes.get((bytes(b["songs"][n]["data"]), tuple(b["songs"][n]["instruments"])))
        if m is None:
            continue
        slot = SECOND_SLOT + n
        if m in a["songs"]:
            rules["tracks"][str(BGM_BASE + slot)] = m
        elif str(m) in table["songs"]:
            info = main_names.get(m)
            rules["tracks"][str(BGM_BASE + slot)] = slot
            rules["songs"]["%X" % slot] = {"name": info["name"] if info else "song %02X" % m, "title": "", "pr_bgm": table["songs"][str(m)]}
        else:
            continue
        del b["songs"][n]
        copies += 1
    # no song at all: C5's slot 2F (vanilla's fanfare slot, a 37-byte run: T-Edition plays fanfares through the
    # bank-43 driver) and any song whose every voice runs off its end (bank 43's 5B): rendered silent
    junk = []
    for src, offset in ((a["songs"], 0), (b["songs"], SECOND_SLOT)):
        for n in list(src):
            scan = SS.scan_song(src[n]["data"])
            if (offset == 0 and n == 0x2F) or (scan["voices"] and len(scan["bad"]) >= len(scan["voices"])):
                del src[n]
                junk.append(offset + n)
    used = {i for src in (a["songs"], b["songs"]) for s_ in src.values() for i in s_["instruments"] if i}
    samples = {k: v for k, v in list(a["samples"].items()) + list(b["samples"].items()) if k in used}
    for (src, offset, named) in ((a["songs"], 0, main_names), (b["songs"], SECOND_SLOT, second_names)):
        for n, s in src.items():
            slot = offset + n
            info = named.get(n)
            name = info["name"] if info and info["name"] not in ("", "-") else ("T-Edition song %02X" % n if offset == 0 else "T-Edition song 43:%02X" % n)
            title = (info or {}).get("section") or ""
            songs[slot] = dict(s, name=name, title=title)
            rules["tracks"][str(BGM_BASE + slot)] = slot
            rules["songs"]["%X" % slot] = {"name": name, "title": title}
    rules["maps"], map_notes = map_rules(rom, set(songs))
    battle_notes = battle_rules(rom, table, rules, set(songs), (main_names, second_names))
    meta = {"lookahead_patch": False, "echo_delay": 5, "mod": "T-Edition 3.0.7 (Mato)",
            "about": "T-Edition's own songs (tools/ted_music.py): C5 songs at their number, bank-43 songs at $100 + n; "
                     "PR bgm id 1000 + slot. Made from T-Edition's ROM on the developer's PC; ships in the zip."}
    SS.write_pack(out, songs, samples, meta)
    import snes_songs_at as AT          # FF6's 8 resident waveforms (T-Edition's copies are vanilla's), bc-music's
    AT.add_resident(out, AT.read_resident(rom))
    rules["about"] = ("What plays where (PrKit/Snes BgmRules): a new song's PR bgm id 1000 + its pack slot (map.csv bgm_id, "
                      "PlayBGM, battle_bgm_asset_id name it); vanilla's songs stay the game's own tracks.")
    with open(os.path.join(out, "ted_music.json"), "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=1)
    player = player_rows(set(songs))
    with open(os.path.join(out, "player.json"), "w", encoding="utf-8") as f:
        json.dump(player, f, ensure_ascii=False, indent=1)
    log(f"music player: {len(player['rows'])} rows for the PR's Extras player (ids {player['rows'][0]['id']}-{player['rows'][-1]['id']})"
        if player["rows"] else "music player: no rows")
    sources = sample_sources(songs, samples)
    with open(os.path.join(out, "samples.json"), "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=1)
    log(f"samples: {len(sources['bc_mit'])} of {len(samples)} also in Beyond Chaos's MIT repo, {len(sources['no_source'])} nowhere else "
        f"(used by {len(sources['songs_using_no_source'])} of {len(songs)} songs)")
    size = sum(len(s["data"]) for s in songs.values()) + sum(len(s["brr"]) for s in samples.values())
    log(f"maps: {map_notes}")
    log(battle_notes)
    log(f"{out}: {len(songs)} songs ({len(a['songs'])} C5, {len(b['songs'])} bank-43; {copies} bank-43 copies of C5 songs "
        f"play those; left out as no song: {' '.join('%X' % j for j in junk) or 'none'}), {len(samples)} samples, "
        f"{size / 1024:.0f} KB; {sum(1 for s in songs.values() if not s['name'].startswith('T-Edition song'))} named")
    return songs, samples, rules


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--all", action="store_true", help="every song of both tables (tests)")
    a = ap.parse_args(argv)
    build(a.out, a.all)


if __name__ == "__main__":
    main(sys.argv[1:])
