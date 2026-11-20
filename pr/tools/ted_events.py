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
        """event_translate.Translator with T-Edition's text (Mato's lines as TED_* keys)."""
        texts = None

        def dialog(self, key):
            return self.texts.keys(key)

        def party_for(self, formation):
            """T-Edition's formations 576-767, and those holding its new monsters 384-511, wait for
            the porter's parties (none yet: their battles stay stubs, listed in needs_formations)."""
            import profile_tedition as PT
            mons = PT.formation_monsters(self.rom.data, PT.FORMATIONS, formation) if formation < 768 else []
            if formation >= 576 or any(m >= 384 for m in mons):
                return None
            return super().party_for(formation)

    return TedTranslator


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


# --- what T-Edition added or changed, event by event ----------------------------------------------
CATALOG = os.path.join(E.P.ROOT, "data", "snes_event_ted_catalog.json")
NEW_MAPS = 416          # T-Edition's maps 416-511 are its own (ted-maps: data/ted_maps.json)


def changed_entries(rom=None, prog=None, jp=None, jprog=None):
    """T-Edition's entry points whose scene is new or changed: the code it reaches isn't the JP ROM's
    at the same addresses, or the entry itself points elsewhere than the JP ROM's (same map, kind and
    NPC/tile). -> [(address, kind, map, detail)] (one per address)."""
    import event_translate as T
    rom = rom or load("ted")
    prog = prog or E.Program(rom).walk_all()
    jp = jp or E.load("jp")
    jentries = {}
    for off, kind, m, det in E.entry_points(jp):
        key = (kind, m, det["npc"] if isinstance(det, dict) else det)
        jentries[key] = off
    out, seen = [], set()
    for off, kind, m, det in prog.entries:
        if off in seen or (off, "vehicle" if m in E.WORLD_MAPS and kind != "npc" else "field") not in prog.code:
            continue
        key = (kind, m, det["npc"] if isinstance(det, dict) else det)
        moved = jentries.get(key) != off
        changed = moved
        if not changed:
            for ins in T.scene(prog, off):
                a = E.event_file(ins.off, len(rom.data))
                if a + ins.size > len(jp.data) or rom.data[a:a + ins.size] != jp.data[a:a + ins.size]:
                    changed = True
                    break
        if changed:
            seen.add(off)
            out.append((off, kind, m, det))
    return out


def catalog(write=True):
    """Every new or changed T-Edition event, translated (not written): its map, kind, first line,
    translated/stub counts, battles (pack, formation, whether it needs the porter's new monsters
    384-511 or formations 576-767) and warps into T-Edition's new maps. -> list (and
    data/snes_event_ted_catalog.json)."""
    import event_translate as T
    import idmap as M
    import profile_tedition as PT
    import ted_dialog as D
    saved = dict(M.ITEM_OVERRIDES)
    M.ITEM_OVERRIDES.clear()
    M.ITEM_OVERRIDES.update(item_overrides())
    try:
        rom = load("ted")
        prog = E.Program(rom).walk_all()
        texts = Texts(rom)
        Tr = _translator_class()
        d = rom.data
        rows = []
        for off, kind, m, det in changed_entries(rom, prog):
            mode = "vehicle" if m in E.WORLD_MAPS and kind != "npc" else "field"
            sc = T.scene(prog, off, mode)
            summ = T.snes_summary(sc)
            first = ""
            for k in summ.get("dialogs", []):
                ee = isinstance(k, tuple)
                first = D.text(d, D.file_of(d, D.PTRS2 if ee else D.PTRS, k[1] if ee else k))
                first = " ".join(first.split())[:90]
                if first:
                    break
            battles = []
            for ins in sc:
                if ins.name in ("battle", "battle_nogameover", "v_battle"):
                    a = 0x0F5000 + 4 * ins.args["pack"]
                    f = (d[a] | d[a + 1] << 8) & 0x7FFF
                    mons = PT.formation_monsters(d, PT.FORMATIONS, f) if f < 768 else []
                    battles.append({"at": E.fmt(ins.off), "pack": ins.args["pack"], "formation": f,
                                    "monsters": mons, "needs_porter": f >= 576 or any(x >= 384 for x in mons)})
            new_maps = sorted({ins.args["map"] for ins in sc if ins.name in ("map", "map_fade", "v_map", "v_map2")
                               and NEW_MAPS <= ins.args["map"] < 0x1FF})
            row = {"event": E.fmt(off), "kind": kind, "map": m, "detail": det if not isinstance(det, dict) else
                   {k: det[k] for k in ("npc", "x", "y")}, "first_line": first, "instructions": len(sc),
                   "battles": battles, "new_maps": new_maps, "on_new_map": m >= NEW_MAPS}
            try:
                t = Tr(rom, "x", snes_map=m, alloc=T.FlagAlloc(None), prog=prog)
                t.texts = texts
                t.translate(off, mode)
                row["translated"] = sum(t.done.values())
                row["stubs"] = dict(t.stubs)
                row["needs_formations"] = sorted(t.needs_formations)
            except Exception as ex:          # noted, not hidden
                row["error"] = f"{type(ex).__name__}: {ex}"
            rows.append(row)
    finally:
        M.ITEM_OVERRIDES.clear()
        M.ITEM_OVERRIDES.update(saved)
    if write:
        with open(CATALOG, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
    return rows


if __name__ == "__main__" and sys.argv[1:2] == ["catalog"]:
    rows = catalog()
    vanilla = [r for r in rows if not r["on_new_map"]]
    print(f"{len(rows)} new or changed events ({len(vanilla)} on vanilla maps, {len(rows) - len(vanilla)} on new maps)")
    need = sorted({b["formation"] for r in rows for b in r["battles"] if b["needs_porter"]})
    print(f"formations needing the porter (576+ or new monsters): {len(need)}: {need}")
    sys.exit(0)


# the README's events (NEW EVENT DETAILS, then NEW PUB QUEST DETAILS), each found by what its scenes
# say (a pattern over Mato's lines): its entry points, maps, translation counts and battles
README_EVENTS = [
    ("Ruby's Shine", r"Carbuncle"),
    ("Test of Strength", r"[Tt]est (you|of)|worthy of my power"),
    ("Stolen Magicite", r"Golem"),
    ("Deep Earth Dweller", r"[Dd]weller|[Dd]eep [Ee]arth"),
    ("Encounter / Reunion / Big Bridge (Gilgamesh)", r"Gilgamesh"),
    ("Titan", r"Titan"),
    ("Descendants of the Summoners", r"[Ss]ummoner|Mist Dragon"),
    ("Odin", r"\bOdin\b"),
    ("Lord of the Seas", r"Leviathan"),
    ("Love Eternal", r"Asura"),
    ("The Eight Dragons", r"[Dd]ragon"),
    ("Diabolos", r"Diabolos"),
    ("Sealed Legends", r"sealed weapon|[Cc]rystal"),
    ("Father and Daughter / A Mother's Love", r"Relm.*Strago|Strago.*Shadow"),
    ("Successorship", r"Vargas"),
    ("Monsters Love It", r"Veldt.*monsters|monsters.*Veldt"),
    ("Owzer's Collection", r"Owzer"),
    ("Molulu's Present", r"Molulu"),
    ("Showdown at the Coliseum", r"Excalibur"),
    ("Long Live Ultros", r"Ultros"),
]


def readme_table(write=True):
    """[(README event, [(entry, kind, map, on a new map, stubs, needs formations)])], from the
    catalog's events whose scenes show a line matching the event's pattern."""
    import re
    import event_translate as T
    import ted_dialog as D
    rom = load("ted")
    prog = E.Program(rom).walk_all()
    d = rom.data
    with open(CATALOG, encoding="utf-8") as f:
        cat = json.load(f)
    lines = {}

    def says(key):
        if key not in lines:
            ee = isinstance(key, tuple)
            lines[key] = " ".join(D.text(d, D.file_of(d, D.PTRS2 if ee else D.PTRS, key[1] if ee else key)).split())
        return lines[key]

    scene_lines = {}
    for r in cat:
        off = E.parse_addr(r["event"])
        mode = "vehicle" if r["map"] in E.WORLD_MAPS and r["kind"] != "npc" else "field"
        scene_lines[r["event"]] = [says(k) for k in T.snes_summary(T.scene(prog, off, mode)).get("dialogs", [])]
    out = []
    for name, rx in README_EVENTS:
        hits = []
        for r in cat:
            if any(re.search(rx, t) for t in scene_lines[r["event"]]):
                hits.append({"event": r["event"], "kind": r["kind"], "map": r["map"], "on_new_map": r["on_new_map"],
                             "instructions": r["instructions"], "stubs": r.get("stubs"),
                             "needs_formations": r.get("needs_formations", []), "new_maps": r["new_maps"]})
        out.append({"readme": name, "events": hits})
    if write:
        with open(os.path.join(E.P.ROOT, "data", "snes_event_ted_readme.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__" and sys.argv[1:2] == ["readme"]:
    for row in readme_table():
        ev = row["events"]
        vanilla = [e for e in ev if not e["on_new_map"]]
        need = sorted({f for e in ev for f in e["needs_formations"]})
        print(f"{row['readme']}: {len(ev)} events ({len(vanilla)} on vanilla maps); formations waiting: {need}")
        for e in ev[:6]:
            print(f"    {e['event']} {e['kind']} map {e['map']}{' (new)' if e['on_new_map'] else ''} "
                  f"{e['instructions']} instr, stubs {e['stubs']}, new maps {e['new_maps']}")
    sys.exit(0)


if __name__ == "__main__":
    rep, _ = build()
    print(json.dumps(rep, ensure_ascii=False, indent=1))
