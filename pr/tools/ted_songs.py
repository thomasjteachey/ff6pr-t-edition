"""T-Edition's songs -> the Pixel Remaster's tracks: data/ted_songs.json.

T-Edition has two copies of FF6's sound driver, each with its own 255-song table:
  * C5 (vanilla's driver): the map songs (map properties; ted-maps' data/ted_maps.json maps.<m>.song)
    and the event commands F0 (song & 7F), EF, F1;
  * bank 43 (a second copy, pointers at 43/0539, 43/3C5E like C5's): T-Edition's own commands 76, 9E
    (song & 7F) and 9F, which its event list calls "different from normal song ID": its victory
    fanfares and inn jingles (HTML/bgm.html, "Music Not Included in the Music Player") and a copy of
    vanilla's songs.
A slot is one of vanilla's songs when its bytes are the JP ROM's song in the same slot (or the same
length with at most 5% of bytes changed: T-Edition fixed a few notes of 2B and 37); its PR track is the
kit's song table (snes_songs.FF6_SONG_PR_BGM). Slots 55-FE are T-Edition's new songs (For
Producers/FF6-T BGM.txt); in the C5 table it also put new music in vanilla's slots 25 (FF Xmas
arrange), 38 (XB Agnilatha -Night-), 3F (FF3 The Crystal Tower), 49 (XB You Will Know Our Names) and
51 (FF0 Zero), and slot 2F (vanilla's Victory Fanfare) holds no song (a run of 37 bytes: T-Edition
plays fanfares through the second driver). New songs have no PR track: they wait for the kit's SNES
music player.

    .venv/Scripts/python tools/ted_songs.py        (writes data/ted_songs.json, prints a summary)

data/ted_songs.json: {"songs": {"<C5 song>": PR bgm id}, "second": {"<bank-43 song>": PR bgm id},
"no_track": {"<C5 song>": vanilla song with no PR track (silence, sounds)}, "second_no_track": {...},
"new": [C5 songs that are T-Edition's own], "second_new": [...]}; song numbers in decimal (as
ted_maps.json has them).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitpath  # noqa: E402,F401  (T-Edition's repository: the kit's tools on the path)
import snes_events as E  # noqa: E402
import snes_songs as SS  # noqa: E402

OUT = os.path.join(E.P.ROOT, "data", "ted_songs.json")
MAIN, SECOND = 0x50000, 0x430000        # the two drivers' banks (file offsets of C5/0000, 43/0000)
VANILLA_SONGS = 0x55                     # vanilla's 85 songs; 55-FE are T-Edition's


def table(rom, base):
    """{slot: song bytes} of the driver whose bank starts at `base` (song count at +3C5E, the
    pointer to its 3-byte song pointer table at +0539, as in vanilla's C5)."""
    count = rom[base + 0x3C5E]
    tbl = SS._ptr(rom, base + 0x0539)
    out = {}
    for slot in range(count):
        a = SS._ptr(rom, tbl + 3 * slot)
        if a == 0 or a + 2 > len(rom):
            continue
        size = int.from_bytes(rom[a:a + 2], "little")
        if size and a + 2 + size <= len(rom):
            out[slot] = rom[a + 2:a + 2 + size]
    return out


def same_song(a, b):
    """The same piece: equal bytes, or equal length with at most 5% of the bytes changed."""
    return a == b or (len(a) == len(b) and sum(x != y for x, y in zip(a, b)) <= len(a) // 20)


def build(write=True):
    import ted_events as TE
    jp = SS.unheader(open(E.JP_ROM, "rb").read())
    ted = SS.unheader(open(TE.MATO, "rb").read())
    van = table(jp, MAIN)
    out = {"about": "T-Edition song -> PR bgm id (tools/ted_songs.py). songs: the C5 driver's (map songs, "
                    "F0 & 7F, EF, F1); second: the bank-43 driver's (T-Edition's 76, 9E & 7F, 9F). Vanilla's "
                    "songs only (snes_songs.FF6_SONG_PR_BGM); no_track: vanilla songs the PR has no track for; "
                    "new: T-Edition's own songs (no PR track; the kit's SNES music player)."}
    for key, base in (("songs", MAIN), ("second", SECOND)):
        songs, no_track, new = {}, {}, []
        for slot, data in sorted(table(ted, base).items()):
            if slot < VANILLA_SONGS and slot in van and same_song(van[slot], data):
                bgm = SS.FF6_SONG_PR_BGM.get(slot)
                if bgm is None:
                    no_track[str(slot)] = "silence" if slot == 0 else "vanilla song %02X (no PR track)" % slot
                else:
                    songs[str(slot)] = bgm
            else:
                new.append(slot)
        prefix = "" if key == "songs" else "second_"
        out[key] = songs
        out[prefix + "no_track"] = no_track
        out[prefix + "new"] = new
    if write:
        import event_translate as T
        T.write_json(OUT, out, indent=1)
    return out


_loaded = None


def load():
    """data/ted_songs.json (built once if missing)."""
    global _loaded
    if _loaded is None:
        if os.path.exists(OUT):
            import event_translate as T
            _loaded = T.read_json(OUT)
        else:
            _loaded = build()
    return _loaded


def pr_bgm(song, second=False):
    """A T-Edition song number (C5 driver, or the bank-43 one) -> the PR's bgm id, or None."""
    return load()["second" if second else "songs"].get(str(song))


if __name__ == "__main__":
    o = build()
    for key in ("songs", "second"):
        p = "" if key == "songs" else "second_"
        print(f"{key}: {len(o[key])} vanilla songs with a PR track, {len(o[p + 'no_track'])} without, "
              f"{len(o[p + 'new'])} T-Edition songs; new in vanilla's slots: "
              f"{' '.join('%02X' % s for s in o[p + 'new'] if s < VANILLA_SONGS)}")
    print("->", OUT)
