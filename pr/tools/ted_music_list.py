"""T-Edition's music player list (Config -> Sound in T-Edition; the PR's Extras music player for the port).

    .venv/Scripts/python tools/ted_music_list.py [bgm.html]      -> data/ted_music_player.json

Source: the song list T-Edition's English package ships (HTML guides, bgm.html: "Song List", version 3.0.7 /
EX 2.0.6): for each song its number in the music player, its Japanese name, the music player's display name, where
T-Edition uses it, and its song id (hex, the sound driver's). Without an argument the file is taken from
downloads/t-edition/FF6 T-Edition English 3.0.rar (7-Zip), extracted to a temporary folder.
Each song gets the PR track that plays it today (data/ted_songs.json, ted-events: vanilla's songs by song id), or
none: T-Edition's own songs wait for the kit's SNES music player (Beyond Chaos's music work).
Written: {"about", "sections": [names in order], "songs": [{no, section, name, jp, notes, song, pr_bgm, in_player}]}
(in_player false: the guide's "Music Not Included in the Music Player" fanfares and inn jingles, numbered apart).
"""
import html.parser
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PR = os.path.dirname(HERE)
OUT = os.path.join(PR, "data", "ted_music_player.json")
SONGS = os.path.join(PR, "data", "ted_songs.json")
RAR = os.path.join(os.path.dirname(PR), "downloads", "t-edition", "FF6 T-Edition English 3.0.rar")
SEVEN_ZIP = r"C:\Program Files\7-Zip\7z.exe"


class _Table(html.parser.HTMLParser):
    """Rows of every table as lists of cell texts; a row with one cell is a section heading."""

    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell, self.skip = [], None, None, 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1
        elif tag in ("td", "th") and self.row is not None and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if any(self.row):
                self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if not self.skip and self.cell is not None:
            self.cell.append(data)


def read_html(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8", "cp932"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", "replace")


def parse(text):
    t = _Table()
    t.feed(text)
    sections, songs, section, in_player = [], [], "", True
    for row in t.rows:
        cells = [c.strip() for c in row]
        if len(cells) == 1 or (len(cells) >= 1 and not re.fullmatch(r"\d{3}", cells[0]) and len([c for c in cells if c]) == 1):
            name = next(c for c in cells if c)
            if not name.lower().startswith("no."):
                section = name
                if section.lower().startswith("music not included"):
                    in_player = False   # the fanfares and inn jingles the music player doesn't list (their own numbering)
                if section not in sections:
                    sections.append(section)
            continue
        if not re.fullmatch(r"\d{3}", cells[0]) or len(cells) < 5:
            continue
        song = cells[-1]
        if not re.fullmatch(r"[0-9A-Fa-f]{1,2}", song):
            continue
        songs.append({"no": int(cells[0]), "section": section, "jp": cells[1], "name": cells[2],
                      "notes": " ".join(cells[3:-1]).strip(), "song": int(song, 16), "in_player": in_player})
    return sections, songs


def from_rar():
    if not (os.path.exists(RAR) and os.path.exists(SEVEN_ZIP)):
        raise SystemExit(f"no {RAR} or 7-Zip: give bgm.html's path")
    tmp = tempfile.mkdtemp(prefix="ted_bgm_")
    try:
        subprocess.run([SEVEN_ZIP, "e", RAR, f"-o{tmp}", "-y", "-r", "bgm.html"], check=True, capture_output=True)
        return read_html(os.path.join(tmp, "bgm.html"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    text = read_html(argv[0]) if argv else from_rar()
    sections, songs = parse(text)
    with open(SONGS, encoding="utf-8") as f:
        table = json.load(f)
    bgm = {int(k): v for k, v in table.get("songs", {}).items()}
    for s in songs:
        s["pr_bgm"] = bgm.get(s["song"])
    nos = [s["no"] for s in songs if s["in_player"]]
    assert len(nos) == len(set(nos)), "music player numbers repeat"
    data = {"about": "T-Edition's music player (bgm.html, 3.0.7 / EX 2.0.6) by tools/ted_music_list.py: each song's "
                     "number, display name, song id (hex in the guide) and the PR track that plays it (data/ted_songs.json), "
                     "null for T-Edition's own songs (the kit's SNES music player, later).",
            "sections": sections, "songs": songs}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    listed = [s for s in songs if s["in_player"]]
    playable = sum(1 for s in listed if s["pr_bgm"] is not None)
    print(f"{OUT}: {len(listed)} songs in the music player ({len(songs) - len(listed)} fanfares/jingles outside it), "
          f"{len(sections)} sections; {playable} with a PR track today, {len(listed) - playable} waiting for the SNES music player")


if __name__ == "__main__":
    main(sys.argv[1:])
