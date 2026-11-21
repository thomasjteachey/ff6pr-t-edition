"""T-Edition's dressing-room costumes (the Falcon's Dressing Room; the "The Best Model" wardrobes in inns).

    .venv/Scripts/python tools/ted_costumes.py [dressroom.html]      -> data/ted_costumes.json

Source: the costume list T-Edition's English package ships (HTML guides, dressroom.html: "Dressing Room Costume
List", 3.0.7 / EX 2.0.6): per character, each costume's name, Japanese name, how it's unlocked (a treasure, an event,
an achievement such as "Character Master" or "Quest Achiever"), the model it's drawn after, and the song the Falcon
plays while it's worn (matched by display name to data/ted_music_player.json when the names agree).
Costumes are graphics only (pr/ted/BATTLE_SPEC.md: no stats); the art comes with the sprite work, the unlock flags
from the events. Without an argument the file comes from downloads/t-edition/FF6 T-Edition English 3.0.rar (7-Zip).
Written: {"about", "characters": [{name, jp, costumes: [{name, jp, unlock, achievement, model, falcon_song,
falcon_song_no}]}]}.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ted_music_list as M  # noqa: E402  (its HTML reader and the RAR fallback)

PR = os.path.dirname(HERE)
OUT = os.path.join(PR, "data", "ted_costumes.json")
CHARACTERS = ["Terra", "Locke", "Cyan", "Shadow", "Edgar", "Sabin", "Celes", "Strago", "Relm", "Setzer", "Mog",
              "Gau", "Gogo", "Umaro"]


def text_lines(html_text):
    p = _Lines()
    p.feed(html_text)
    return [" ".join(l.split()) for l in "".join(p.out).split("\n") if l.strip(" |")]


class _Lines(M.html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if tag in ("tr", "br", "p", "li", "h1", "h2", "h3", "div"):
            self.out.append("\n")
        if tag in ("td", "th"):
            self.out.append(" | ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data.strip())


def parse(lines):
    chars, cur, cost = [], None, None
    head = re.compile(r"^\|\s*(%s)\s*[(（]([^)）]*)[)）]\s*$" % "|".join(CHARACTERS))
    for line in lines:
        m = head.match(line)
        if m:
            cur = {"name": m.group(1), "jp": m.group(2), "costumes": []}
            if all(c["name"] != cur["name"] for c in chars):
                chars.append(cur)
            else:
                cur = next(c for c in chars if c["name"] == m.group(1))
            cost = None
            continue
        if cur is None or line.startswith("|") or line == "▲":
            continue
        j = re.match(r"^《\s*(.*?)\s*》$", line)
        if j and cost is not None:
            cost["jp"] = j.group(1)
            continue
        if cost is None or (cost.get("jp") and ":" in line and not line.endswith(".") and len(line) < 60):
            if ":" in line and len(line) < 60 and not line.endswith("."):
                cost = {"name": line, "jp": "", "unlock": "", "achievement": None, "model": "", "falcon_song": None}
                cur["costumes"].append(cost)
            continue
        song = re.search(r'Falcon while wearing this costume is "([^"]+)"', line)
        if song:
            cost["falcon_song"] = song.group(1)
        elif re.search(r"model|modeled|based|appearance|designed", line, re.I) and not cost["model"]:
            cost["model"] = line
        else:
            cost["unlock"] = (cost["unlock"] + " " + line).strip()
            a = re.search(r'achievement[s]?\s+"([^"]+)"', line, re.I)
            if a and not cost["achievement"]:
                cost["achievement"] = a.group(1)
    return chars


# the guide's game titles -> the music player's short forms ("Romancing Saga 3: Julian's Theme" -> "RS3 Julian")
GAME_SHORT = [("Final Fantasy Tactics", "FFT"), ("Final Fantasy XIII", "FF13"), ("Final Fantasy XII", "FF12"),
              ("Final Fantasy XI", "FF11"), ("Final Fantasy X", "FF10"), ("Final Fantasy IX", "FF9"),
              ("Final Fantasy VIII", "FF8"), ("Final Fantasy VII", "FF7"), ("Final Fantasy VI", "FF6"),
              ("Final Fantasy V", "FF5"), ("Final Fantasy IV", "FF4"), ("Final Fantasy III", "FF3"),
              ("Final Fantasy II", "FF2"), ("Final Fantasy", "FF1"), ("Romancing Saga 3", "RS3"), ("Romancing SaGa 3", "RS3"),
              ("Romancing Saga 2", "RS2"), ("Romancing SaGa 2", "RS2"), ("Romancing Saga", "RS1"), ("Chrono Trigger", "CT"),
              ("Chrono Cross", "CC"), ("Seiken Densetsu 3", "SD3"), ("Live A Live", "LAL"), ("Catalina", "Katalina")]


def _norm(s):
    import re
    s = s.replace("’", "'")
    for a, b in GAME_SHORT:
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", s.lower())


def match_songs(chars):
    """Each costume's Falcon song as the music player's number and song id (data/ted_music_player.json): the guide's
    title with its game shortened as the player writes it, equal or contained either way (names over 5 letters)."""
    if not os.path.exists(M.OUT):
        return 0
    with open(M.OUT, encoding="utf-8") as f:
        songs = [s for s in json.load(f)["songs"] if s["in_player"]]
    by = {}
    for s in songs:
        by.setdefault(_norm(s["name"]), s)
    matched = 0
    for c in chars:
        for k in c["costumes"]:
            n = _norm(k.get("falcon_song") or "")
            m = by.get(n) or next((x for key, x in by.items() if n and len(key) > 5 and (n in key or key in n)), None)
            k["falcon_song_no"] = m["no"] if m else None
            k["falcon_song"] = k.get("falcon_song")
            k["falcon_song_id"] = m["song"] if m else None
            matched += m is not None
    return matched


def main(argv):
    if argv:
        text = M.read_html(argv[0])
    else:
        import shutil
        import subprocess
        import tempfile
        tmp = tempfile.mkdtemp(prefix="ted_dress_")
        try:
            subprocess.run([M.SEVEN_ZIP, "e", M.RAR, f"-o{tmp}", "-y", "-r", "dressroom.html"], check=True, capture_output=True)
            text = M.read_html(os.path.join(tmp, "dressroom.html"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    chars = parse(text_lines(text))
    matched = match_songs(chars)
    n = sum(len(c["costumes"]) for c in chars)
    data = {"about": "T-Edition's dressing-room costumes (dressroom.html, 3.0.7 / EX 2.0.6) by tools/ted_costumes.py: "
                     "graphics only; unlocks from events/achievements; falcon_song_no / falcon_song = the music player number and "
                     "T-Edition song (C5 driver) whose display name matches the guide's title (match_songs).",
            "characters": chars}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"{OUT}: {len(chars)} characters, {n} costumes ({sum(1 for c in chars for k in c['costumes'] if k['achievement'])} "
          f"by achievement), {matched} Falcon songs matched to the music player list")


if __name__ == "__main__":
    main(sys.argv[1:])
