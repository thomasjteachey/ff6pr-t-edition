"""T-Edition's event commands and tables, for tools/snes_events.py (the kit's SNES event decoder).

T-Edition (Tsushiy, on the Japanese v1.0 ROM, 6 MB ExHiROM) added 20 event commands and changed
two. Found from its command table (C0/97F9: the handlers that differ from the JP ROM's), read
from each handler's code (sizes from its LDA #n / JMP advance), and named after Tsushiy's list
("For Producers/FF6-T Edition event commands.txt", which warns of mistakes: its sizes for 5D-5F
and 70-72 are wrong, its 67-6F examples are copies of EB's):

  5B b a    jump to a if bit b of 7E/1E50 is CLEAR (B7's code on another bit array)
  A3 b a    the same on 7E/1860;  A5 b a  the same on 7E/1850
  EC s a    jump to a if the party's lead has status s (byte 1 of 7E/1614: 01 dark ... 80 wound)
  67 n v    compare word n of 7E/1E70 with v -> case bits 1A0 (=) 1A1 (>) 1A2 (<), like EB on 7E/1FC2
  68 1600 (character data words)  69 (a 58/E4CC lookup)  6D 1A00  6E (58/E52A)  6F 1D01
  A4 1863   FC 1300            (all: 4 bytes, word n, value)
  83 n v    set word n of 7E/1DD0;   ED n v  set word n of 7E/1E40;  E5 n  clear 3 bytes at 7E/1860+6n
  66 c d    character c gets character d's properties (40's table at ED/7CA6)
  76 s v    play song s (T-Edition's song numbers) at volume v;  9E s  play;  9F s v  fade in
  EE d      dialogue d from T-Edition's second dialogue table (51/E600, 3-byte pointers)
  CC        (changed) 2 bytes: rebuilds a character's stats (no longer "if any of 5 bits")
  CB        (changed) on map 104 only: 2 bytes, resets the story bits (a new-game-plus); elsewhere
            vanilla's "if any of 4 bits"
The dialogue command 4B reads T-Edition's own pointer table (5C/9CE0, 3 bytes per dialogue).

Its maps (512): event tiles' offsets at C4/0000 with the entries at 4B/0000; NPCs' offsets at
C4/1A10 with the entries at 4D/7CC0; entrance events at D1/FA00 as vanilla (512 x 3 bytes).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import snes_events as E  # noqa: E402

MATO = os.path.join(E.PROJECT, "build", "t-edition", "T-Edition 3.0.7 (Mato).sfc")
EX = os.path.join(E.PROJECT, "build", "t-edition", "T-Edition EX 2.0.6 (Mato).sfc")
MAP_104 = 0x68
DIALOG_PTRS = 0x5C9CE0      # 4B's dialogues: 3-byte pointers (C0/7FBF: LDA $5C9CE0,X; X = 3n)
DIALOG2_PTRS = 0x51E600     # EE's dialogues (C0/EE33)

EXTRA = [
    (0x5B, "if_bit1E50_clear", 5, "bit:b event:a", "cond", "flow"),
    (0xA3, "if_bit1860_clear", 5, "bit:b event:a", "cond", "flow"),
    (0xA5, "if_bit1850_clear", 5, "bit:b event:a", "cond", "flow"),
    (0xEC, "if_lead_status", 5, "status:b event:a", "cond", "flow"),
    (0x67, "cmp_1E70", 4, "word:b value:w", "next", "flag"),
    (0x68, "cmp_1600", 4, "word:b value:w", "next", "flag"),
    (0x69, "cmp_58E4CC", 4, "word:b value:w", "next", "flag"),
    (0x6D, "cmp_1A00", 4, "word:b value:w", "next", "flag"),
    (0x6E, "cmp_58E52A", 4, "word:b value:w", "next", "flag"),
    (0x6F, "cmp_1D01", 4, "word:b value:w", "next", "flag"),
    (0xA4, "cmp_1863", 4, "word:b value:w", "next", "flag"),
    (0xFC, "cmp_1300", 4, "word:b value:w", "next", "flag"),
    (0x83, "word1DD0_set", 4, "word:b value:w", "next", "flag"),
    (0xED, "word1E40_set", 4, "word:b value:w", "next", "flag"),
    (0xE5, "clear_1860", 2, "n:b", "next", "flag"),
    (0x66, "char_copy", 3, "char:b src:b", "next", "party"),
    (0x76, "ted_song_volume", 3, "song:b volume:b", "next", "sound"),
    (0x9E, "ted_song", 2, "song:b", "next", "sound"),
    (0x9F, "ted_song_fade_in", 3, "song:b speed:b", "next", "sound"),
    (0xEE, "dialog2", 3, "dlg:w", "next", "dialog"),
    (0xCC, "char_rebuild", 2, "char:b", "next", "party"),
]
CB_MAP_104 = E.Op(0xCB, "story_reset", 2, "v:b", "next", "flag")


class TedDialect(E.Dialect):
    map_sensitive = frozenset({0xCB})

    def special(self, ins, rom, ctx):
        if ins.op == 0xCB and ctx and ctx.get("map") == MAP_104:
            return CB_MAP_104
        return None


DIALECT = TedDialect("ted", extra=EXTRA)
# event code: CA-CE (the dialogue left CD/CE for 5C/9CE0's banks) and T-Edition's own E9-EC
CODE_RANGES = [(0x000000, 0x050000), (0x1F0000, 0x230000)]
TABLES = E.Tables(maps=511, tile_data=0x4B0000, npc_data=0x4D7CC0, code_end=0x40000, code_ranges=CODE_RANGES)


def dialog_offsets(d, ptrs=DIALOG_PTRS, count=None):
    """File offsets of T-Edition's dialogues (3-byte SNES pointers)."""
    out = []
    i = 0
    while count is None or i < count:
        a = ptrs + 3 * i
        p = d[a] | d[a + 1] << 8 | d[a + 2] << 16
        if count is None and (p >> 16) < 0x40:
            break
        out.append(E.file_offset(p >> 16, p & 0xFFFF, len(d)))
        i += 1
        if count is None and i > 8000:
            break
    return out


def _choices(rom):
    import ted_dialog
    return ted_dialog.choice_counts(rom.data)


def load(name="ted"):
    path = EX if name == "ted-ex" else MATO
    rom = E.Rom(path, DIALECT, TABLES, name=name)
    try:
        rom.dialog_choices = _choices(rom)
    except ImportError:
        rom.dialog_choices = None
    return rom


# --- T-Edition's events as PR scripts (tools/event_translate.py) -----------------------------------
import json  # noqa: E402

OUT = os.path.join(E.P.ROOT, "mods", "TEditionEvents")
ALLOC = os.path.join(E.P.ROOT, "data", "snes_event_alloc_tedition.json")
REPORT = os.path.join(E.P.ROOT, "data", "snes_event_ted_report.json")
KEYS_NAME = "ted_events"

# the events built so far: (event address, SNES map, PR script name, PR map, the entity layer whose
# NPCs the scene moves, bits the test entry sets so T-Edition's branch runs)
EVENTS = [
    # South Figaro, the old man who wants wine (map 86, NPC 1): T-Edition's new scene (his grandson,
    # a Yellow Globe, Hermes Shoes) when bit 161 or 1D5 is set, else vanilla's talk (CA/7B7E)
    dict(event=0x35850, map=86, npc=1, name="sc_ted_cd5850", pr_map="Map_20071_23", layer="ev_e_0038",
         test_bits=(0x161,)),
]
SCRIPTS = os.path.join(E.P.ROOT, "data", "snes_event_scripts_tedition.json")
SCRIPT_IDS = range(9500, 9800)     # script.csv rows for T-Edition's events (9801+: the porter's boxes, 9901+: merchants)


_overrides = None


def item_overrides():
    """{T-Edition item slot: (PR table, row)} where it isn't idmap's default (tools/item_identity.py,
    as the porter sets them)."""
    global _overrides
    if _overrides is None:
        import ff6snes as S
        import item_identity as I
        import profile_tedition as PT
        PT.build()
        rom = S.Rom(PT.MATO)
        n = PT._Image.names
        slots = I.identify(I.mod_items_from(rom, n.items, n.item_icons), log=lambda *a: None)
        _overrides = I.overrides(slots)
    return _overrides


class Texts:
    """T-Edition's dialogue as PR story lines: each SNES dialogue's speaker turns become keys
    TED_D<n>_a_<turn> (EE's table: TED_E<n>_...), its choices TED_D<n>_c_<k>; the speaker goes to
    story_cha as the PR's lines do, the "Name:" prefix dropped; pages joined by <P>."""

    def __init__(self, rom):
        import ted_dialog as D
        self.D, self.d = D, rom.data
        self.mes, self.cha = {}, {}

    def keys(self, key):
        D, d = self.D, self.d
        ee = isinstance(key, tuple)
        n = key[1] if ee else key
        f = D.file_of(d, D.PTRS2 if ee else D.PTRS, n)
        base = "TED_%s%04d" % ("E" if ee else "D", n)
        text = D.text(d, f, tags=True)
        body, choices = [], []
        for line in text.split("\n"):
            if line.startswith("> "):
                choices.append(line[2:].strip())
            else:
                body.append(line)
        pages = "\n".join(body).strip("\n").split("\n\n")
        turns = []                          # [(speaker, [pages])]
        for pg in pages:
            first, _, rest = pg.partition("\n")
            who = first.split(":")[0]
            if ":" in first and 0 < len(who.strip()) <= 16:
                said = first.partition(":")[2].strip()
                turns.append((who.strip(), [(said + ("\n" + rest if rest else "")).strip()]))
            elif turns:
                turns[-1][1].append(pg.strip())
            else:
                turns.append(("", [pg.strip()]))
        out = []
        nl, page = chr(92) + "n", "<P>" + chr(92) + "n"     # the message files' literal \n
        for t, (who, pgs) in enumerate(turns, 1):
            k = "%s_a_%02d" % (base, t)
            self.mes[k] = page.join(p.replace("\n", nl) for p in pgs if p)
            self.cha[k] = who
            out.append(k)
        cks = []
        for c, line in enumerate(choices, 1):
            k = "%s_c_%02d" % (base, c)
            self.mes[k] = line
            cks.append(k)
        return out, cks


def _translator_class():
    import event_translate as T

    class TedTranslator(T.Translator):
        """event_translate.Translator with T-Edition's text and the PR map's entities."""
        texts = None
        layers = None

        def dialog(self, key):
            return self.texts.keys(key)

        def npc_entity(self, n):
            """SNES NPC n of this map -> the PR entity standing on its spot (the map's entity layers,
            the scene's layer first)."""
            if self.snes_map is None or self.pr_map is None:
                return None
            det = _npcs(self.rom).get((self.snes_map, n))
            if det is None:
                return None
            spot = self.local(det["x"], det["y"])
            best = None
            for k, (layer, objs) in enumerate(pr_entities(self.pr_map, self.layers)):
                for name, x, y, eid in objs:
                    if not eid or name in NOT_NPCS:
                        continue
                    d = abs(x - spot[0]) + abs(y - spot[1])
                    if d <= 2 and (best is None or (d, k) < best[0]):   # the PR moved a few by a tile or two
                        best = ((d, k), eid)
            return best[1] if best else None

    return TedTranslator


_npc_cache = {}


def _npcs(rom):
    """{(map, NPC index): its record's details} (entry_points' NPCs, kept per ROM)."""
    if id(rom) not in _npc_cache:
        _npc_cache[id(rom)] = {(e[2], e[3]["npc"]): e[3] for e in E.entry_points(rom) if e[1] in ("npc", "npc_object")}
    return _npc_cache[id(rom)]


NOT_NPCS = {"PointIn", "GotoMap", "OpenTrigger", "TileAnimRegion", "MoveArea", "MapRange", "EffectEntity_fire"}


def pr_entities(pr_map, prefer=None):
    """[(layer, [(object name, x, y, entity id)])] of a PR map: the preferred entity layer first,
    then the others its package lists, then entity_default."""
    import snes_maps
    path = snes_maps.pr_tilemaps().get(pr_map)
    if not path:
        return []
    room = os.path.dirname(path)
    pk = json.load(open(os.path.join(os.path.dirname(room), "package.json"), encoding="utf-8"))
    entry = next((m for m in pk["map"] if m["name"] == pr_map), {})
    names = [x["name"] for x in entry.get("entity", [])]
    if prefer in names:
        names.remove(prefer)
        names.insert(0, prefer)
    out = []
    for nm in names + ["entity_default"]:
        f = os.path.join(room, nm + ".json")
        if not os.path.exists(f):
            continue
        objs = []
        for lay in json.load(open(f, encoding="utf-8")).get("layers", []):
            for o in lay.get("objects") or []:
                props = {q["name"]: q["value"] for q in o.get("properties", [])}
                objs.append((o.get("name", ""), int(o["x"] // 16), int(o["y"] // 16) - (1 if "gid" in o else 0),
                             props.get("entity_id")))
        out.append((nm, objs))
    return out


def build(out=OUT, events=EVENTS, write=True):
    """Translates EVENTS into a Magicite folder: each script (and its after-battle / after-warp
    scripts) in its PR map's folder, a test entry <name>_test (the scene's entity layer, the bits
    that open T-Edition's branch), the map group's package.json listing them, the story text.
    -> (report, MagiciteMod)."""
    import event_translate as T
    from prkit import data as PD, magicite as MG
    import snes_maps
    import idmap as M
    saved = dict(M.ITEM_OVERRIDES)            # T-Edition's item rows while translating, then back
    M.ITEM_OVERRIDES.clear()
    M.ITEM_OVERRIDES.update(item_overrides())
    try:
        return _build(out, events, write, T, MG, PD, snes_maps)
    finally:
        M.ITEM_OVERRIDES.clear()
        M.ITEM_OVERRIDES.update(saved)


def npc_objects(pr_map, spot):
    """[(layer, object, its properties)] for each entity layer of a PR map (and entity_default) with
    an object at `spot` that runs a script (script_id > 0): the NPC in each of its story states."""
    import snes_maps
    room = os.path.dirname(snes_maps.pr_tilemaps()[pr_map])
    pk = json.load(open(os.path.join(os.path.dirname(room), "package.json"), encoding="utf-8"))
    entry = next(m for m in pk["map"] if m["name"] == pr_map)
    out = []
    for nm in [x["name"] for x in entry.get("entity", [])] + ["entity_default"]:
        f = os.path.join(room, nm + ".json")
        if not os.path.exists(f):
            continue
        for lay in json.load(open(f, encoding="utf-8")).get("layers", []):
            for o in lay.get("objects") or []:
                props = {q["name"]: q["value"] for q in o.get("properties", [])}
                at = (int(o["x"] // 16), int(o["y"] // 16) - (1 if "gid" in o else 0))
                if at == tuple(spot) and props.get("script_id"):
                    out.append((nm, o, props))
    return out


class ScriptIds:
    """script.csv ids for new scripts, kept in a JSON file so a script keeps its id."""

    def __init__(self, path, ids=SCRIPT_IDS):
        self.path, self.ids = path, ids
        self.table = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}

    def get(self, name):
        if name not in self.table:
            used = set(self.table.values())
            self.table[name] = next(i for i in self.ids if i not in used)
        return self.table[name]

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.table, f, indent=0, sort_keys=True)


def _vanilla_npc_event(snes_map, npc):
    """The JP ROM's event address for an NPC (what a T-Edition event that wraps it calls)."""
    jp = E.load("jp")
    return next((e[0] for e in E.entry_points(jp) if e[2] == snes_map and e[1] == "npc" and e[3]["npc"] == npc), None)


def _build(out, events, write, T, MG, PD, snes_maps):
    import csv
    import pr_script as Sc
    rom = load("ted")
    prog = E.Program(rom).walk_all()
    texts = Texts(rom)
    alloc = T.FlagAlloc(ALLOC)
    Tr = _translator_class()
    mod = MG.MagiciteMod(out, PD.GameData("ff6"), keys_name=KEYS_NAME)
    tilemaps = snes_maps.pr_tilemaps()
    packages = {}
    layer_edits = {}                    # (PR map, entity layer) -> {entity id: new script id}
    report = []
    ids = ScriptIds(SCRIPTS)
    names_by_id = {r["id"]: r["script_name"] for r in csv.DictReader(open(os.path.join(E.P.MASTER, "script.csv"), encoding="utf-8"))}
    for ev in events:
        off, snes_map, name, pr_map, layer, test_bits = (ev["event"], ev["map"], ev["name"], ev["pr_map"],
                                                         ev["layer"], ev["test_bits"])
        scripts = []
        # wired: the NPC's script in each entity layer it stands in becomes T-Edition's event with the
        # layer's own PR script grafted in for the vanilla talk the SNES event falls back to
        vanilla = _vanilla_npc_event(snes_map, ev["npc"])
        probe = Tr(rom, name, snes_map=snes_map, alloc=alloc, prog=prog, pr_map=pr_map)
        spot = probe.local(*next((e[3]["x"], e[3]["y"]) for e in E.entry_points(rom)
                                 if e[2] == snes_map and e[1] == "npc" and e[3]["npc"] == ev["npc"]))
        wired = []
        for k, (lay, obj, props) in enumerate(npc_objects(pr_map, spot)):
            orig = names_by_id.get(str(props["script_id"]))
            if not orig:
                continue
            nm = "%s_%s" % (name, lay.replace("ev_e_", "l"))
            t = Tr(rom, nm, snes_map=snes_map, alloc=alloc, prog=prog, pr_map=pr_map)
            t.texts, t.layers = texts, lay
            if vanilla is not None:
                t.fallbacks[vanilla] = Sc.load(orig)
            sc = t.translate(off)
            scripts.append((nm, sc, pr_map))
            scripts.extend((a, s2, w or pr_map) for a, s2, w in t.after)
            sid = ids.get(nm)
            mod.table("script").add({"script_name": nm}, id=sid)
            wired.append({"layer": lay, "entity": props.get("entity_id"), "was": orig, "now": nm, "script_id": sid})
            edits = layer_edits.setdefault((pr_map, lay), {})
            edits[props.get("entity_id")] = sid
        for nm, test in ((name, False), (name + "_test", True)):
            t = Tr(rom, nm, snes_map=snes_map, alloc=alloc, prog=prog, pr_map=pr_map)
            t.texts, t.layers = texts, layer
            preamble = []
            if test:
                preamble.append(T.op("SetEntities", s=[layer], comment="test: the layer with the scene's NPCs"))
                for b in test_bits:
                    cat, idx = t.flag(b)
                    preamble.append(T.op("SetFlag", i=[idx], s=[cat], comment="test: SNES bit %03X" % b))
            sc = t.translate(off, preamble=preamble)
            scripts.append((nm, sc, pr_map))
            scripts.extend((a, s, w or pr_map) for a, s, w in t.after)
            if not test:
                report.append({"event": E.fmt(off), "script": nm, "pr_map": pr_map, "translated": dict(t.done),
                               "stubs": dict(t.stubs), "wired": wired,
                               "detail": {"%s %s" % ch: v for ch, v in sorted(t.report.items())}})
        for nm, sc, where in scripts:
            room = os.path.dirname(tilemaps[where])
            folder = os.path.basename(os.path.dirname(room))
            group = os.path.relpath(room, E.P.VANILLA).replace(os.sep, "/").split("/")[0]
            container = "Assets/GameAssets/Serial/Res/Map/%s/%s/%s.json" % (folder, where, nm)
            mod.asset(group, container, json.dumps(sc, ensure_ascii=False, separators=(",", ":")),
                      key="%s/%s" % (where, nm))
            packages.setdefault((group, folder), {}).setdefault(where, []).append(nm)
    for (group, folder), rooms in packages.items():
        src = os.path.join(E.P.VANILLA, group, "Assets", "GameAssets", "Serial", "Res", "Map", folder, "package.json")
        pk = json.load(open(src, encoding="utf-8"))
        for room, names in rooms.items():
            entry = next(m for m in pk["map"] if m["name"] == room)
            for nm in names:
                if not any(x["name"] == nm for x in entry["script"]):
                    entry["script"].append({"name": nm, "asset": "%s/%s" % (room, nm)})
        mod.asset(group, "Assets/GameAssets/Serial/Res/Map/%s/package.json" % folder,
                  json.dumps(pk, ensure_ascii=False, separators=(",", ":")), key="package")
    for (pr_map, lay), edits in layer_edits.items():
        room = os.path.dirname(tilemaps[pr_map])
        folder = os.path.basename(os.path.dirname(room))
        group = os.path.relpath(room, E.P.VANILLA).replace(os.sep, "/").split("/")[0]
        doc = json.load(open(os.path.join(room, lay + ".json"), encoding="utf-8"))
        for layer_ in doc.get("layers", []):
            for o in layer_.get("objects") or []:
                props = {q["name"]: q for q in o.get("properties", [])}
                eid = props.get("entity_id", {}).get("value")
                if eid in edits and "script_id" in props:
                    props["script_id"]["value"] = edits[eid]
        mod.asset(group, "Assets/GameAssets/Serial/Res/Map/%s/%s/%s.json" % (folder, pr_map, lay),
                  json.dumps(doc, ensure_ascii=False, separators=(",", ":")), key="%s/%s" % (pr_map, lay))
    mod.text("story_mes_en").update(texts.mes)
    mod.text("story_cha_en").update(texts.cha)
    if write:
        mod.write()
        alloc.save()
        ids.save()
        with open(REPORT, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
    return report, mod


if __name__ == "__main__":
    rep, _ = build()
    print(json.dumps(rep, ensure_ascii=False, indent=1))
