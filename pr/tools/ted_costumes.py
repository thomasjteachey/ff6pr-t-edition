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
    songs = {}
    if os.path.exists(M.OUT):
        with open(M.OUT, encoding="utf-8") as f:
            for s in json.load(f)["songs"]:
                songs.setdefault(s["name"].lower(), s["no"])
    matched = 0
    for c in chars:
        for k in c["costumes"]:
            title = (k["falcon_song"] or "").split(":")[-1].strip().lower()
            k["falcon_song_no"] = songs.get(title)
            matched += k["falcon_song_no"] is not None
    n = sum(len(c["costumes"]) for c in chars)
    data = {"about": "T-Edition's dressing-room costumes (dressroom.html, 3.0.7 / EX 2.0.6) by tools/ted_costumes.py: "
                     "graphics only; unlocks from events/achievements; falcon_song_no = the music player number when the "
                     "guide's song title matches its display name.",
            "characters": chars}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"{OUT}: {len(chars)} characters, {n} costumes ({sum(1 for c in chars for k in c['costumes'] if k['achievement'])} "
          f"by achievement), {matched} Falcon songs matched to the music player list")


if __name__ == "__main__":
    main(sys.argv[1:])
