"""T-Edition EX's boss AI for the kit's SNES AI host (PrKit/Ff6/SnesAiHost), as T-Edition's plugin runs
its own monsters' (TedPlugin/TedEnemyAi.cs: BepInEx/TEdition/ted_ai.json {"snes_ai": ...}).

    .venv/Scripts/python tools/ted_ex_ai.py      -> build/t-edition/ex/ted_ex_ai.json (+ a summary)

The scripts are EX's own (AI scripts E9/7000 + pointers FF/F300 of the EX ROM) for its 28 monsters, ids
512-539 (tools/ted_ex.py EX_IDS: PR 1512-1539), in port_ai.snes_ai_data's schema, rewritten where the
merged mod differs from EX's ROM:

  * F2 (formation change: Golbez's second form, Sephiroth's two, the Ark Angels' rotation...): the host has
    none, so each fight is one formation listing every form (ted_ex.fight_layout; the later ones hidden at
    the start) and each F2 becomes F5 0B <0|2> <the new formation's slots> (show; 0 = refill HP when the
    F2 asked for it, its bit 0x80, else 2 = as they are) then F5 0B 04 <the old one's other slots> (hide).
    Not the same as the SNES when the F2 keeps HP (no 0x80: Sephiroth, the Ark Angels): there the next
    form takes over the HP left; here each form keeps its own.
  * slot references of a monster moved to another slot by the merge (F5 / FC 11 / FC 12 masks, target
    codes $30-$35 of F1 and the target conditions): renumbered.
  * F3 (battle lines): EX's lines 1-29 are T-Edition's numbers too; the host keys lines by that byte, so
    EX's get numbers T-Edition's scripts never show (LINE_SLOTS), their text under TEDX_BTL_<n>_<k> keys.
  * attacks: EX wrote its bosses' own attacks over T-Edition's enemy attacks 166-237 (Big Bang over
    10,000 Volts...): "attack_overrides" {SNES attack: PR ability 7000 + attack} for the plugin's
    AbilityFor of monsters 512+; other attacks are T-Edition's (the porter's "attacks" table).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitpath  # noqa: E402,F401
import prdata as P  # noqa: E402
import snes_ai as A  # noqa: E402
import ted_ex as X  # noqa: E402

OUT = os.path.join(X.OUT, "ted_ex_ai.json")
SPECIAL_BASE = 6000     # port_monster_ext.SPECIAL_BASE: a new monster's special is ability 6000 + id
SHOW_REFILL, SHOW_KEEP, HIDE_KEEP = 0, 2, 4     # F5 actions (the host: 0/2 show, 4 hide)
TARGET_CONDITIONS = {0x06, 0x07, 0x08, 0x09, 0x0E, 0x0F, 0x17}   # FC sub-commands whose first byte is a target
MASK_CONDITIONS = {0x11, 0x12}                                  # FC 11/12: monsters <mask> alive / dead


def script_bytes(d, e):
    """EX monster e's script: (main, counter) raw bytes, each ending with its FF."""
    i = X.AI_DATA + X.word(d, X.AI_PTRS + 2 * e)
    parts = []
    for _ in range(2):
        start = i
        while True:
            op = d[i]
            i += A.SIZES.get(op, 1) if op >= 0xF0 else 1
            if op == 0xFF:
                break
        parts.append(bytes(d[start:i]))
    return parts


def ops(raw):
    i = 0
    while i < len(raw):
        op = raw[i]
        n = A.SIZES.get(op, 1) if op >= 0xF0 else 1
        yield raw[i:i + n]
        i += n


def line_slots(R):
    """Battle-line numbers T-Edition 3.0.7's scripts never show (its 512 monsters' F3), from 100 up: EX's
    lines go there."""
    used = set()
    for e in range(512):
        main, ctr = X.ai(R.ted, e, data=X.TED_AI_DATA)
        used |= {a[0] for n, a in main + ctr if n == "message"}
    return [i for i in range(100, 256) if i not in used]


class Fight:
    """One merged fight: per EX formation its slot map, its shown slots (merged numbers)."""

    def __init__(self, layout):
        self.maps = {int(k): v for k, v in layout["maps"].items()}
        self.shown = {}
        for g, m in self.maps.items():
            self.shown[g] = sorted(m.values())

    def mask(self, g, slots_of_g):
        return sum(1 << self.maps[g][s] for s in slots_of_g if s in self.maps[g])


def _remap_mask(mask, smap):
    if mask in (0, 0xFF) or not smap or all(k == v for k, v in smap.items()):
        return mask
    out = 0
    for s in range(6):
        if mask >> s & 1:
            out |= 1 << smap.get(s, s)
    return out


def _remap_target(t, smap):
    if 0x30 <= t <= 0x35 and smap:
        return 0x30 + smap.get(t - 0x30, t - 0x30)
    return t


def rewrite(raw, e, home, fight, present, lines, log):
    """One section of EX monster e's script for the merged fight: home = its own EX formation, present =
    {EX formation: its slots shown at the start (EX's numbers)}. After an F2 the slots the block names are
    the new formation's (Golbez's "unhide monster 0" right after his F2 is his second form) until its FE."""
    cur = home
    smap = fight.maps.get(home, {})
    out = bytearray()
    for o in ops(raw):
        op = o[0]
        if op == 0xFE and cur != home:
            cur, smap = home, fight.maps.get(home, {})
        if op == 0xF2:
            g = (o[2] | o[3] << 8) & 0x3FF
            if g not in fight.maps:
                log(f"  monster {e}: F2 to formation {g} outside its fight: dropped")
                continue
            show = fight.mask(g, present[g])
            hide = fight.mask(cur, present[cur]) & ~show
            out += bytes((0xF5, 0x0B, SHOW_REFILL if o[3] & 0x80 else SHOW_KEEP, show))
            if hide:
                out += bytes((0xF5, 0x0B, HIDE_KEEP, hide))
            cur, smap = g, fight.maps.get(g, {})
        elif op == 0xF5:
            out += bytes((0xF5, o[1], o[2], _remap_mask(o[3], smap)))
        elif op == 0xFC and o[1] in MASK_CONDITIONS:
            out += bytes((0xFC, o[1], _remap_mask(o[2], smap), o[3]))
        elif op == 0xFC and o[1] in TARGET_CONDITIONS:
            out += bytes((0xFC, o[1], _remap_target(o[2], smap), o[3]))
        elif op == 0xF1:
            out += bytes((0xF1, _remap_target(o[1], smap)))
        elif op == 0xF3:
            n = o[1] | o[2] << 8
            if n not in lines:
                log(f"  monster {e}: line {n} has no text: dropped")
                continue
            out += bytes((0xF3, lines[n], 0))
        else:
            out += o
    return bytes(out)


def split_line(text, width=36):
    """A battle line (Mato's, lines joined) into boxes of two SNES lines at most."""
    parts = [p.strip() for p in text.split("\n") if p.strip()]
    boxes, cur = [], []
    for p in parts:
        cur.append(p)
        if len(cur) == 2:
            boxes.append(" ".join(cur))
            cur = []
    if cur:
        boxes.append(" ".join(cur))
    return boxes or [""]


PORT = os.path.join(P.ROOT, "mods", "TEditionPort")   # the porter's output: EX's rows and parties are made there


def port_data(port=PORT):
    """From the porter's output (port_monster_ext with ted_ex.ex_records): ({PR party: monster_party row} of the
    fights, {SNES id: its special ability or None} from monster_ext.json); ({}, {}) before a port with EX."""
    import csv
    rows, specials = {}, {}
    path = os.path.join(port, "master", "Assets", "GameAssets", "Serial", "Data", "Master", "monster_party.csv")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            rows = {int(r["id"]): r for r in csv.DictReader(fh) if int(r["id"]) >= 30768}
    ext = os.path.join(port, "monster_ext.json")
    if os.path.exists(ext):
        with open(ext, encoding="utf-8") as fh:
            for e, m in json.load(fh)["monsters"].items():
                if int(e) >= X.EX_MONSTER_BASE:
                    specials[int(e)] = (m.get("special") or {}).get("ability")
    return rows, specials


def export(R=None, party_rows=None, specials=None, log=print):
    """The snes_ai object for EX's monsters (and the texts its keys need): -> (snes_ai, {key: text}).
    party_rows: {PR party: monster_party row} of the fights' parties (30000 + formation) to place each
    SNES slot in its PR cell; without them party_slots/party_members are left out."""
    R = R or X.Roms()
    d = R.ex
    rec = X.ex_records(R)
    inv = {v: k for k, v in X.EX_IDS.items()}
    # each EX monster's fight and home formation; each formation's shown slots
    home, fight_of, present = {}, {}, {}
    for f, lay in rec["layouts"].items():
        fight = Fight(lay)
        for g in fight.maps:
            present[g] = [s for s, (_, _, shown) in X._slots(d, g).items() if shown]
            for s, (ex, _, _) in X._slots(d, g).items():
                if ex in X.EX_IDS and X.EX_IDS[ex] not in home:
                    home[X.EX_IDS[ex]] = g
                    fight_of[X.EX_IDS[ex]] = fight
    # battle lines
    shown_lines = set()
    for i, e in inv.items():
        for raw in script_bytes(d, e):
            shown_lines |= {o[1] | o[2] << 8 for o in ops(raw) if o[0] == 0xF3}
    free = line_slots(R)
    texts, keys, lines = {}, {}, {}
    for n in sorted(shown_lines):
        t = X.battle_text(d, X.LINES_BANK + X.word(d, X.MONSTER_LINES + 2 * n))
        if not t.strip():
            continue
        slot = free.pop(0)
        lines[n] = slot
        ks = []
        for k, box in enumerate(split_line(t)):
            key = f"TEDX_BTL_{n:02d}_{k}"
            texts[key] = box
            ks.append(key)
        keys[slot] = ks
    # attacks EX made its own
    sp = X.spells(R, {"monsters": sorted(inv.values())})
    overrides = {r["spell"]: r["proposed_ability"] for r in sp["differing"] if r["proposed_ability"]}
    import idmap as M
    out = {"version": 5, "scripts": {}, "battle": {}, "special": {}, "message_keys": keys,
           "attacks": [M.spell(i) or 0 for i in range(256)],   # the base table (TedPlugin keeps T-Ed's own)
           "attack_overrides": overrides, "copies": {}, "plugin": sorted(inv), "formations": {},
           "boss_death": []}
    for i, e in sorted(inv.items()):
        fight = fight_of.get(i)
        if fight is None:
            log(f"  monster {i} ({R.name(d, e)}): in no fight: not exported")
            continue
        main, ctr = script_bytes(d, e)
        out["scripts"][i] = (rewrite(main, i, home[i], fight, present, lines, log) +
                             rewrite(ctr, i, home[i], fight, present, lines, log)).hex()
        out["battle"][i] = 1                 # the PR's plain "Battle" (port_ai.battle_ability's default)
        # the special row port_monster_ext made (none where its template monster has none: then "Battle")
        sp = (specials or {}).get(i, SPECIAL_BASE + i) if specials else SPECIAL_BASE + i
        out["special"][i] = sp or out["battle"][i]
        out["copies"][1000 + i] = i
        if d[X.MONSTERS + 32 * e + 0x12] & 0x40:
            out["boss_death"].append(i)
    for f in rec["formations"]:
        out["formations"][30000 + f] = f
    if party_rows:
        out["party_members"], out["party_slots"] = party_cells(rec, party_rows)
    return out, texts


def party_cells(rec, party_rows):
    """{party: [[SNES id, cell, shown, listed] | None per slot]}, {party: [-1, slot of cell 1..9]}: each
    merged formation's slot to the cell of the party row holding the same PR monster nearest its SNES
    position (as port_ai.party_slots)."""
    import port_encounters as E
    members, slots = {}, {}
    for f, mons in rec["formation_monsters"].items():
        p = 30000 + f
        row = party_rows.get(p)
        if not row:
            continue
        free = {k: int(row[f"monster{k}"]) for k in range(1, 10) if row.get(f"monster{k}", "0") not in ("0", "")}
        mem, m = [None] * 6, [-1] * 10
        for s, (i, x, y, shown) in sorted(enumerate(mons), key=lambda t: (not t[1][3], -t[1][1], t[1][2])):
            cand = [k for k, v in free.items() if v == 1000 + i]
            if not cand:
                continue
            k = min(cand, key=lambda c: (E.CELL_XY[c][0] - x) ** 2 + (E.CELL_XY[c][1] - y) ** 2)
            m[k] = s
            mem[s] = [i, k, 1 if shown else 0, 1]
            del free[k]
        # forms the party doesn't list (the later ones: the host brings them in by F5): the free cell
        # nearest their SNES position
        empty = [c for c in range(1, 10) if m[c] == -1]
        for s, (i, x, y, shown) in enumerate(mons):
            if mem[s] is None and empty:
                k = min(empty, key=lambda c: (E.CELL_XY[c][0] - x) ** 2 + (E.CELL_XY[c][1] - y) ** 2)
                empty.remove(k)
                m[k] = s
                mem[s] = [i, k, 0, 0]
        members[p], slots[p] = mem, m
    return members, slots


def main():
    rows, specials = port_data()
    sai, texts = export(party_rows=rows, specials=specials)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"snes_ai": sai}, fh, indent=1, ensure_ascii=False)
    print(f"{len(sai['scripts'])} scripts, {len(sai['message_keys'])} battle lines ({len(texts)} boxes), "
          f"{len(sai['attack_overrides'])} attack overrides, parties {sorted(sai['formations'])}, "
          f"cells for {len(sai.get('party_slots', {}))} (port: {'yes' if rows else 'none yet'}) -> {OUT}")


if __name__ == "__main__":
    main()
