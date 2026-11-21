"""T-Edition's dialogue, from Mato's English build: decode it, and give it PR message keys.

Where it is (found in the build itself; Tsushiy's "address changes" list gives 55/0000 and
55/0002 for the conversation pointers, which is the Japanese build's layout, not Mato's):
  * event command 4B (and 48): C0/7FBF reads 3-byte SNES pointers at 5C/9CE0 (file 0x5C9CE0,
    dialogue n at 3n), text in banks 52+ (dialogue 0 at 52/0000);
  * event command EE (T-Edition's second table): C0/EE33, pointers at 51/E600, text in bank 57+.
Mato's encoding (C0/81B5 draws it): 00 end, 01 new line, 02-0F character names (as the US ROM),
10 pause, 11 xx wait, 12, 13 new page, 14 xx, 15 choice (a line that's an answer), 16 xx, 17-1B
placeholders (19 gil, 1A item name, 1B ...), 1C-1F xx two-byte glyphs, 20-7F one glyph (A-Z 20,
a-z 3A, 0-9 54, punctuation 5E-6E as the US ROM, 7F space), 80-EF words from a dictionary of
112 (pointers 5F/FC00, zero-terminated strings in bank 5F: "Gestahl", "Empire", ... "s ", "I "),
F0-FF character names.

    .venv/Scripts/python tools/ted_dialog.py [n ...]        (prints dialogues; no n: counts + samples)
    .venv/Scripts/python tools/ted_dialog.py --ee n         (EE's table)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import snes_events as E  # noqa: E402

PTRS = 0x5C9CE0        # 4B / 48
PTRS2 = 0x51E600       # EE
MTE_PTRS = 0x5FFC00    # 112 x 2-byte offsets into bank 5F
CHOICE = 0x15
ARG1 = {0x11, 0x14, 0x16, 0x1C, 0x1D, 0x1E, 0x1F}
NAMES = ["Terra", "Locke", "Cyan", "Shadow", "Edgar", "Sabin", "Celes", "Strago", "Relm", "Setzer", "Mog", "Gau",
         "Gogo", "Umaro", "", ""]
# the PR's name tags (story_mes_en: "(TINA)" is the player's name for Terra)
PR_TAGS = ["(TINA)", "(ROCK)", "(KAIEN)", "(SHADOW)", "(EDGAR)", "(MASH)", "(CELES)", "(STRAGUS)", "(RELM)",
           "(SETZER)", "(MOG)", "(GAU)", "(GOGO)", "(UMARO)", "", ""]
PUNCT = {0x5E: "!", 0x5F: "?", 0x60: "/", 0x61: ":", 0x62: '"', 0x63: "'", 0x64: "-", 0x65: ".", 0x66: ",",
         0x67: "...", 0x68: ";", 0x69: "#", 0x6A: "+", 0x6B: "(", 0x6C: ")", 0x6D: "%", 0x6E: "~", 0x7F: " "}


def glyph(b):
    if 0x20 <= b <= 0x39:
        return chr(65 + b - 0x20)
    if 0x3A <= b <= 0x53:
        return chr(97 + b - 0x3A)
    if 0x54 <= b <= 0x5D:
        return chr(48 + b - 0x54)
    return PUNCT.get(b, "")


def file_of(d, ptrs, n):
    a = ptrs + 3 * n
    p = d[a] | d[a + 1] << 8 | d[a + 2] << 16
    return E.file_offset(p >> 16, p & 0xFFFF, len(d))


def count(d, ptrs):
    """How many dialogues a pointer table holds: pointers into ROM banks (40-7D, C0-FF: 4B's run
    from 52/0000 on and go on in EB/EC) until the first zero."""
    n = 0
    while n < 8192:
        a = ptrs + 3 * n
        b = d[a + 2]
        if not (0x40 <= b < 0x7E or b >= 0xC0):
            break
        n += 1
    return n


_mte = {}


def mte(d):
    key = id(d)
    if key not in _mte:
        out = []
        for i in range(112):
            p = d[MTE_PTRS + 2 * i] | d[MTE_PTRS + 2 * i + 1] << 8
            f, s = 0x5F0000 + p, []
            while d[f]:
                s.append(d[f])
                f += 1
            out.append(bytes(s))
        _mte[key] = out
    return _mte[key]


def tokens(d, f, limit=4000):
    """A dialogue's codes, dictionary words expanded: [(code, arg)]."""
    words = mte(d)
    out = []
    for _ in range(limit):
        c = d[f]
        f += 1
        if c == 0:
            break
        if c in ARG1:
            out.append((c, d[f]))
            f += 1
        elif 0x80 <= c <= 0xEF:
            for w in words[c - 0x80]:
                out.append((w, None))
        else:
            out.append((c, None))
    return out


def text(d, f, tags=False):
    """Plain text ("\\n" lines, "\\n\\n" pages, choices marked "> "); tags: names as the PR's
    (TINA)-style tags."""
    s = []
    for c, a in tokens(d, f):
        if c == 0x01:
            s.append("\n")
        elif c == 0x13:
            s.append("\n\n")
        elif 0x02 <= c <= 0x0F or 0xF0 <= c <= 0xFF:
            k = c - 2 if c <= 0x0F else c - 0xF0
            s.append((PR_TAGS if tags else NAMES)[k] if k < 16 else "")
        elif c == CHOICE:
            s.append("> ")
        elif c == 0x10:
            s.append(" ")
        elif c in (0x19,):
            s.append("<gil>")
        elif c == 0x1A:
            s.append("<item>")
        elif c < 0x20:
            continue
        else:
            s.append(glyph(c))
    return "".join(s)


def choices(d, f):
    return sum(1 for c, _ in tokens(d, f) if c == CHOICE)


def dialogs(d, ptrs=PTRS):
    return [file_of(d, ptrs, n) for n in range(count(d, ptrs))]


def choice_counts(d):
    """{n: choices} for 4B's dialogues and {("EE", n): choices} for EE's (snes_events' B6)."""
    out = {}
    for n, f in enumerate(dialogs(d)):
        out[n] = choices(d, f)
    for n, f in enumerate(dialogs(d, PTRS2)):
        out[("EE", n)] = choices(d, f)
    return out


def rom_bytes():
    import ted_events
    with open(ted_events.MATO, "rb") as fh:
        return fh.read()


# Monster battle lines (the SNES AI's F3 "message n"; audit T8): Mato moved vanilla's table (US C1/9846 LDA CF/DFE0,X,
# text bank CF) to pointers at CF/E000 with the text in bank 55 (its C1/97F4: LDA #$55, STA $88A9 ... LDA $CFE000,X),
# in this dialogue encoding: 01 new line, 05 pause, 02 nn a character's name, 6F an asterisk (*sploosh*).
BATTLE_PTRS = 0x0FE000
BATTLE_BANK = 0x550000


def battle_lines(d, index, tags=True):
    """Battle message `index` (0-255) -> its lines (pauses dropped, names as PR tags or plain names)."""
    if not 0 <= index < 256:
        return []
    f = BATTLE_BANK | d[BATTLE_PTRS + 2 * index] | d[BATTLE_PTRS + 2 * index + 1] << 8
    out, cur, k = [], [], f
    while k < len(d) and d[k] != 0 and k - f < 600:
        c = d[k]
        if c == 0x01:
            out.append("".join(cur))
            cur = []
        elif c == 0x05:
            cur.append(" ")
        elif c == 0x02:
            k += 1
            n = d[k] if k < len(d) else 0
            cur.append((PR_TAGS if tags else NAMES)[n] if n < 14 else "")
        elif c == 0x6F:
            cur.append("*")
        else:
            cur.append(glyph(c) or "")
        k += 1
    out.append("".join(cur))
    return [" ".join(x.split()) for x in out if x.split()]


class BattleMessages:
    """port_ai's battle line source for T-Edition (profile_tedition.battle_lines): message index -> story_mes keys
    TED_BTL_<index>_<n>, one per line, shown in turn; .texts holds the lines (battle_text.Messages' interface)."""
    def __init__(self, prefix="TED_BTL"):
        self.d, self.prefix = rom_bytes(), prefix
        self.keys, self.texts = {}, {}

    def __call__(self, index):
        if index not in self.keys:
            ks = []
            for n, line in enumerate(battle_lines(self.d, index), 1):
                key = f"{self.prefix}_{index:03d}_{n:02d}"
                self.texts[key] = line
                ks.append(key)
            self.keys[index] = ks
        return self.keys[index]


def pr_text(d, f):
    """A dialogue as a PR story line: names as tags, a speaker's "Name:" prefix split off,
    pages as <P>, lines as \\n (literal, as the message files write it). -> (speaker, text)."""
    t = text(d, f, tags=True)
    speaker = ""
    first, _, rest = t.partition("\n")
    if first.endswith(":") and len(first) <= 24:
        speaker, t = first[:-1], rest
    t = t.replace("\n\n", "<P>").replace("\n", "\\n")
    return speaker, t


if __name__ == "__main__":
    d = rom_bytes()
    args = sys.argv[1:]
    ptrs = PTRS
    if args and args[0] == "--ee":
        ptrs, args = PTRS2, args[1:]
    if args:
        for a in args:
            print(f"--- {a}")
            print(text(d, file_of(d, ptrs, int(a, 0))))
    else:
        n1, n2 = count(d, PTRS), count(d, PTRS2)
        print(f"4B dialogues: {n1}, EE dialogues: {n2}")
        for n in (0, 1, 2, 10, 100, 1000, n1 - 1):
            print(n, repr(text(d, file_of(d, PTRS, n))[:150]))
        for n in (0, 1, n2 - 1):
            print("EE", n, repr(text(d, file_of(d, PTRS2, n))[:150]))
