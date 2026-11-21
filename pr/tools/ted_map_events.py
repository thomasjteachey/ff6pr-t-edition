"""T-Edition's events on its new maps (NPCs' talk, event tiles, entrance events) as PR scripts, into the
new maps' own folder (mods/TEditionMaps). Run by `tools/ted_maps.py build` (it places the objects
while the rooms are made, and writes the scripts after them).

The events: data/snes_event_ted_catalog.json's entries tagged owner "ted-maps" (until ted-events tags
them: those on new maps), translated by ted-events' TedTranslator (tools/ted_events.py, read only here)
through a subclass that knows the new maps (`MapTranslator`: their rooms' offsets, the NPC objects
placed here, their arrival points). On the rooms:
  * each SNES NPC -> a PR NPC object (gid 1024, action 2: talk; asset = its sprite number's PR look,
    data/ted_npc_looks.json from tools/ted_npc_looks.py) whose script_id runs its translated event;
  * each event tile -> a step trigger (gid 998, object type 2) running its event;
  * the entrance event -> the room's map script, after a prologue that hides the NPCs whose SNES show
    bit is clear (the SNES draws an NPC only while its bit 300-6FF is set; the bits map to PR flags
    through ted-events' shared allocator, ted_events.flag_alloc(); a vanilla bit with no PR tie: shown).
What the translator leaves as `SysCall "SNES:..."` stubs is written as Nop with the SNES bytes in the
comment (a stub's run-time behaviour is unproven; the report counts them). script.csv ids: 9600-9699
then 10000-10999 (data/ted_maps_scripts.json keeps each script's id).
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitpath  # noqa: E402,F401
import prdata as P  # noqa: E402

CATALOG = os.path.join(P.ROOT, "data", "snes_event_ted_catalog.json")
# ted-ex's pub quests on the new maps (its scripts, its script.csv rows, in mods/TEditionQuests): per SNES map
# {"npcs": [{"index", "script", "script_id", "asset_id"?, "direction"?}], "tiles": [{"x", "y", "script",
# "script_id"}], "entrance": {"script"}}. This build puts its NPCs' script ids and looks on the NPC objects it
# places anyway, adds the tiles' step triggers, lists the scripts in the rooms' package entries, and grafts
# the entrance script (read from QUESTS_DIR) into the room's map script after the visibility prologue.
# NPCs placed with a stand-in look (their sprite number has no PR look): rows in ted-events' list for art
# (bc-sprites), marked "by": "ted-maps" (each build replaces its own rows)
STANDINS = os.path.join(P.ROOT, "data", "ted_npc_standins.json")
QUESTS_JSON = os.path.join(P.ROOT, "data", "ted_quests_maps.json")
QUESTS_DIR = os.path.join(P.ROOT, "mods", "TEditionQuests")


def quests():
    if not os.path.exists(QUESTS_JSON):
        return {}
    with open(QUESTS_JSON, encoding="utf-8") as f:
        return {int(k): v for k, v in json.load(f).items() if str(k).isdigit()}


def quest_script(name):
    """ted-ex's script `name` (its JSON from mods/TEditionQuests), or None."""
    import glob
    hits = glob.glob(os.path.join(QUESTS_DIR, "**", name + ".json"), recursive=True)
    if not hits:
        return None
    with open(hits[0], encoding="utf-8") as f:
        return json.load(f)
SCRIPT_IDS_FILE = os.path.join(P.ROOT, "data", "ted_maps_scripts.json")
REPORT = os.path.join(P.ROOT, "data", "ted_map_events_report.json")
SCRIPT_IDS = list(range(9600, 9700)) + list(range(10000, 11000))   # the lead, 2026-11-20 (ted-events 11000+, ted-ex 12000+)
OWNER = "ted-maps"
NPC_GID, TRIGGER_GID = 1024, 998
DIRECTION = {0: 1, 1: 2, 2: 4, 3: 8}
NPC_BITS = 0x300            # an NPC's show bit is 300 + its record's bit (snes_events.entry_points)
DEFAULT_ASSET = 10          # a townsperson, for a sprite the PR never drew


def owned(catalog=None):
    """The catalog entries this session translates: owner "ted-maps", else (before the tags) every
    entry on a new map."""
    with open(catalog or CATALOG, encoding="utf-8") as f:
        cat = json.load(f)
    tagged = [e for e in cat if e.get("owner")]
    if tagged:
        return [e for e in cat if e.get("owner") == OWNER]
    return [e for e in cat if e.get("on_new_map")]


class ScriptIds:
    def __init__(self, path=SCRIPT_IDS_FILE, ids=SCRIPT_IDS):
        self.path, self.ids = path, ids
        self.table = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.table = json.load(f)

    def get(self, name):
        if name not in self.table:
            used = set(self.table.values())
            free = next((i for i in self.ids if i not in used), None)
            if free is None:
                raise SystemExit(f"out of script ids {self.ids[0]}-{self.ids[-1]}: ask the lead for more")
            self.table[name] = free
        return self.table[name]

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.table, f, indent=0, sort_keys=True)
        os.replace(tmp, self.path)


def _translator(builder):
    import ted_events
    Ted = ted_events._translator_class()

    class MapTranslator(Ted):
        """TedTranslator on T-Edition's new maps: offsets of ted-maps' rooms, its NPC objects, its
        arrival points; vanilla maps as TedTranslator does."""

        def room(self):
            return next((r for r in builder.rooms.get(self.snes_map, []) if r.name == self.pr_map), None)

        def local(self, x, y):
            r = self.room()
            if r is None:
                return super().local(x, y)
            return x + r.dx, y + r.dy

        def npc_entity(self, n):
            if self.snes_map not in builder.rooms:
                return super().npc_entity(n)
            return builder.npc_ids.get((self.snes_map, n, self.pr_map))

        def _instr_bits(self, ins, sub, last):
            # tile changes (73/74/75) on a new map: ted-events' tile_plan reads vanilla PR maps only, and a new
            # room's look is snes_rooms' conversion: a stub (counted) until there's a plan for new rooms
            if ins.name in ("tiles_set", "tiles_set_later", "tiles_refresh") and self.room() is not None:
                if ins.name == "tiles_refresh":
                    return [], True
                return self.left(ins, "tile change on a new map")
            return super()._instr_bits(ins, sub, last)

        def place(self, m, x, y):
            if m in builder.rooms:
                hit = builder.place(m, x, y)
                tgt = builder.point(m, x, y)
                if hit and tgt:
                    r, px, py = hit
                    return tgt[0], r.name, px, py, tgt[1]
                return None
            return super().place(m, x, y)

    return MapTranslator


def _nops(sc):
    """The translator's SysCall "SNES:..." stubs -> Nop (the comment keeps the SNES bytes)."""
    n = 0
    for m in sc.get("Mnemonics", []):
        if m.get("mnemonic") == "SysCall" and str((m.get("operands", {}).get("sValues") or [""])[0]).startswith("SNES:"):
            what = m["operands"]["sValues"][0]
            m["mnemonic"] = "Nop"
            m["operands"] = {"iValues": [0] * 8, "rValues": [0] * 8, "sValues": [""] * 8}
            m["comment"] = (what + " " + m.get("comment", "")).strip()
            n += 1
    return n


class Events:
    """Prepare (objects on the rooms, translated scripts) before the rooms are written; write the
    scripts, package entries, script.csv rows and text after."""

    def __init__(self, builder, log=print):
        import ted_events
        import event_translate as T
        self.b, self.log = builder, log
        self.ted = ted_events
        self.T = T
        self.rom = builder.ev
        self.prog = None
        self.texts = ted_events.Texts(self.rom)
        self.alloc = ted_events.flag_alloc()   # THE shared allocator (its FLAG_RANGES; each flag saved as handed out)
        self.ids = ScriptIds()
        self.scripts = []              # (PR map, name, script)
        self.map_scripts = {}          # PR map -> script (the room's map script)
        self.report = []
        self.stats = collections.Counter()

    def prepare(self):
        import idmap as M
        import snes_events as E
        b = self.b
        b.npc_ids = {}
        entries = owned()
        mine = {(E.parse_addr(e["event"]), e["kind"], e["map"]) for e in entries}
        qs = quests()
        self.listed = collections.defaultdict(list)     # PR room -> other folders' scripts its package lists
        # ted-ex's after-battle / after-warp scripts, by the PR room they run in ("_list"): listed too
        if os.path.exists(QUESTS_JSON):
            with open(QUESTS_JSON, encoding="utf-8") as f:
                for room, names in json.load(f).get("_list", {}).items():
                    self.listed[room] += list(names)
        self.standins = []
        self.prog = E.Program(self.rom).walk_all()
        Tr = _translator(b)
        saved = dict(M.ITEM_OVERRIDES)
        M.ITEM_OVERRIDES.clear()
        M.ITEM_OVERRIDES.update(self.ted.item_overrides())
        import ted_npc_looks
        looks = dict(self.T.sprite_assets(self.rom))
        looks.update(ted_npc_looks.looks())      # data/ted_npc_looks.json: voted, same sheet, look-alike
        try:
            for m in b.new:
                if not b.rooms.get(m):
                    continue
                d = b.tables[m]
                # NPC objects (all of the map's: a decoration NPC has no event of its own)
                ents = collections.Counter()
                for n in d["npcs"]:
                    hit = b.place(m, n["x"], n["y"])
                    if not hit:
                        continue
                    r, px, py = hit
                    ents[r.name] += 1
                    eid = ents[r.name]
                    b.npc_ids[(m, n["index"], r.name)] = eid
                    n["_room"], n["_eid"], n["_at"] = r, eid, (px, py)
                for n in d["npcs"]:
                    if "_room" not in n:
                        continue
                    addr = n["event"] - 0xCA0000
                    sid = 0
                    q = next((x for x in qs.get(m, {}).get("npcs", []) if x["index"] == n["index"]), None)
                    if (addr, "npc", m) in mine:
                        name = "sc_tedm_%06X" % addr
                        sid = self.translate(Tr, m, n["_room"].name, name, addr, "npc")
                    r, eid, (px, py) = n["_room"], n["_eid"], n["_at"]
                    asset = (looks.get(n["sprite"]) or (DEFAULT_ASSET,))[0]
                    # bit 7 of the record's x byte (snes_maps' "no_face"): a special-graphics NPC, a decoration
                    # whose event bytes are graphics (ted-ex, 2026-11-21): no talk, no turning
                    special = n["no_face"]
                    if special:
                        sid = 0
                        self.stats["special-graphics npcs (decorations)"] += 1
                    if not looks.get(n["sprite"]) or special:
                        self.standins.append({"sprite": n["sprite"], "snes_map": m, "npc": n["index"], "pr_map": r.name,
                                              "look": DEFAULT_ASSET, "entity": eid, "special_graphics": bool(special),
                                              "event": "%02X/%04X" % (n["event"] >> 16, n["event"] & 0xFFFF),
                                              "by": OWNER})
                    if q and not sid and not special:    # ted-ex's pub quest NPC
                        sid, asset = q["script_id"], q.get("asset_id") or asset
                        n["direction"] = q.get("direction", n["direction"])
                        self.listed[n["_room"].name].append(q["script"])
                        self.stats["ted-ex npcs"] += 1
                    r.objects.append({"name": "TEditionNPC%d" % n["index"], "x": px, "y": py, "gid": NPC_GID,
                                      "properties": {
                                          "accept_action_direction": 15, "action_id": 0 if special else 2, "affected": False,
                                          "all_layers": False, "asset_id": asset, "birdview_puppet": False,
                                          "direction": DIRECTION.get(n["direction"], 4), "entity_id": eid,
                                          "eye_contact": False if special else True, "first_interval": True,
                                          "flight_altitude_ratio": 1, "idling": True, "interactive_icon_v_offset": 12,
                                          "link_object_id": 0, "message_key": "", "move_interval_id": 0,
                                          "move_speed_id": 0, "move_step": 0, "move_type": 0,
                                          "move_while_display_message": False, "object_id": 0, "object_type": 6,
                                          "pushed": True, "script_id": sid, "talk_target_transportation_ids": "",
                                          "target_character_status_id": 0, "turn_around": not (special or n["const_sprite"]),
                                          "visible_minimap": False}})
                    self.stats["npcs"] += 1
                # event tiles: step triggers
                for q in qs.get(m, {}).get("tiles", []):
                    hit = b.place(m, q["x"], q["y"])
                    if not hit:
                        continue
                    r, px, py = hit
                    ents[r.name] += 1
                    r.objects.append({"name": "TEditionTile", "x": px, "y": py, "gid": TRIGGER_GID, "properties": {
                        "action_id": 2, "direction": 0, "entity_id": ents[r.name], "gimmick": False,
                        "ignore_route_link_object_id": -1, "link_object_id": 0, "object_id": 0, "object_type": 2,
                        "script_id": q["script_id"], "target_transportation_ids": ""}})
                    self.listed[r.name].append(q["script"])
                    self.stats["ted-ex tiles"] += 1
                for k, e in enumerate(d["events"]):
                    addr = e["event"] - 0xCA0000
                    if (addr, "tile", m) not in mine:
                        continue
                    hit = b.place(m, e["x"], e["y"])
                    if not hit:
                        continue
                    r, px, py = hit
                    name = "sc_tedm_%06X" % addr
                    sid = self.translate(Tr, m, r.name, name, addr, "tile")
                    ents[r.name] += 1
                    r.objects.append({"name": "TEditionTile", "x": px, "y": py, "gid": TRIGGER_GID, "properties": {
                        "action_id": 2, "direction": 0, "entity_id": ents[r.name], "gimmick": False,
                        "ignore_route_link_object_id": -1, "link_object_id": 0, "object_id": 0, "object_type": 2,
                        "script_id": sid, "target_transportation_ids": ""}})
                    self.stats["tiles"] += 1
                # the entrance event (every room of the map: the SNES runs it on any arrival) after the
                # NPC visibility prologue
                import ted_maps as TM
                entrance = TM.entrance_event(b.data, m)
                own = (entrance, "entrance", m) in mine
                for r in b.rooms[m]:
                    t = Tr(self.rom, f"sc_map_{r.name[4:].lower()}", snes_map=m, alloc=self.alloc, prog=self.prog,
                           pr_map=r.name)
                    t.texts = self.texts
                    pre = []
                    for n in d["npcs"]:
                        if n.get("_room") is not r:
                            continue
                        bit = NPC_BITS + n["show_bit"]
                        if t.untied(bit):
                            # a vanilla bit the PR has no flag for: shown (ted-events' rule: a made-up
                            # flag would never follow the PR's story, and nothing would ever set it)
                            self.stats["npcs shown always (untied vanilla bit)"] += 1
                            continue
                        cat, idx = t.flag(bit)
                        skip = "shown_%d" % n["_eid"]
                        pre.append(self.T.op("Branch", i=[idx, 1, "@" + skip], s=[cat, "＝", "imm"],
                                             comment="SNES NPC %d: shown while bit %03X" % (n["index"], NPC_BITS + n["show_bit"])))
                        pre += t.puppet_ops([n["_eid"]], [[self.T.op("Hide", kind=2)]])
                        pre.append(self.T.lab(skip))
                    qe = qs.get(m, {}).get("entrance")
                    their = quest_script(qe["script"]) if qe and not own else None
                    if their is not None:                # ted-ex's entrance event, grafted after the prologue
                        pre.append(self.T.op("Jump", i=["@" + t.graft(their)], comment="ted-ex: " + qe["script"]))
                        self.stats["ted-ex entrances"] += 1
                    elif qe and not own:
                        self.log(f"  ted-ex entrance {qe['script']} for map {m}: not in {QUESTS_DIR} yet")
                    sc = t.translate(entrance if own else 0x5EA9, preamble=pre)
                    self.stats["stubs as nops"] += _nops(sc)
                    sc["Name"] = f"sc_{r.name}"
                    self.map_scripts[r.name] = sc
                    for a, s2, w in t.after:
                        self.stats["stubs as nops"] += _nops(s2)
                        self.scripts.append((w or r.name, a, s2))
                    if own:
                        self.stats["entrances"] += 1
                        self.report.append({"event": "%06X" % (0xCA0000 + entrance), "kind": "entrance", "map": m,
                                            "pr_map": r.name, "stubs": dict(t.stubs), "translated": dict(t.done)})
        finally:
            M.ITEM_OVERRIDES.clear()
            M.ITEM_OVERRIDES.update(saved)

    _done = None

    def translate(self, Tr, m, pr_map, name, addr, kind):
        """One event as a script in `pr_map` (once per name and room); its script.csv id."""
        if self._done is None:
            self._done = {}
        key = (name, pr_map)
        nm = name if not any(k[0] == name and k[1] != pr_map for k in self._done) else f"{name}_{pr_map[4:].lower()}"
        if key not in self._done:
            t = Tr(self.rom, nm, snes_map=m, alloc=self.alloc, prog=self.prog, pr_map=pr_map)
            t.texts = self.texts
            sc = t.translate(addr)
            self.stats["stubs as nops"] += _nops(sc)
            self.scripts.append((pr_map, nm, sc))
            for a, s2, w in t.after:
                self.stats["stubs as nops"] += _nops(s2)
                self.scripts.append((w or pr_map, a, s2))
            self._done[key] = self.ids.get(nm)
            self.report.append({"event": "%06X" % (0xCA0000 + addr), "kind": kind, "map": m, "pr_map": pr_map,
                                "script": nm, "script_id": self._done[key], "stubs": dict(t.stubs),
                                "translated": dict(t.done)})
            self.stats["scripts"] += 1
        return self._done[key]

    def write(self, out):
        """Scripts into their rooms' folders, listed in the group's package.json; map scripts; script.csv
        rows; story text; ids, flags, report saved."""
        import snes_rooms as R
        b = self.b
        room_of = {r.name: r for rs in b.rooms.values() for r in rs}
        tilemaps = __import__("snes_maps").pr_tilemaps()
        rows = []
        by_group = collections.defaultdict(list)
        for where, nm, sc in self.scripts:
            r = room_of.get(where)
            if r is not None:
                group, folder = r.group, r.name.rsplit("_", 1)[0]
            else:                       # an after-battle / arrival script on a vanilla map: not ours
                self.stats["scripts for vanilla maps (skipped)"] += 1
                continue
            by_group[(group, folder)].append((where, nm, sc))
        for (group, folder), items in by_group.items():
            base = os.path.join(out, group, *R.RES.split("/"), folder)
            with open(os.path.join(base, "package.json"), encoding="utf-8") as f:
                pkg = json.load(f)
            assets = []
            for where, nm, sc in items:
                with open(os.path.join(base, where, nm + ".json"), "w", encoding="utf-8") as f:
                    json.dump(sc, f, ensure_ascii=False, separators=(",", ":"))
                entry = next(e for e in pkg["map"] if e["name"] == where)
                if not any(x["name"] == nm for x in entry["script"]):
                    entry["script"].append({"name": nm, "asset": f"{where}/{nm}"})
                assets.append((f"{where}/{nm}", f"{R.RES}/{folder}/{where}/{nm}"))
                if nm in self.ids.table:
                    rows.append({"id": str(self.ids.table[nm]), "script_name": nm})
            with open(os.path.join(base, "package.json"), "w", encoding="utf-8") as f:
                json.dump(pkg, f, ensure_ascii=False)
            R.add_keys(out, group, "new_maps", assets)
        for room, names in self.listed.items():   # ted-ex's scripts (its files, in its folder)
            r = room_of.get(room)
            if r is None:
                self.log(f"  ted-ex scripts for {room}: not a room of this build")
                continue
            folder = r.name.rsplit("_", 1)[0]
            path = os.path.join(out, r.group, *R.RES.split("/"), folder, "package.json")
            with open(path, encoding="utf-8") as f:
                pkg = json.load(f)
            entry = next(e for e in pkg["map"] if e["name"] == room)
            for nm in names:
                if not any(x["name"] == nm for x in entry["script"]):
                    entry["script"].append({"name": nm, "asset": f"{room}/{nm}"})
            with open(path, "w", encoding="utf-8") as f:
                json.dump(pkg, f, ensure_ascii=False)
        for name, sc in self.map_scripts.items():
            r = room_of[name]
            folder = r.name.rsplit("_", 1)[0]
            path = os.path.join(out, r.group, *R.RES.split("/"), folder, r.name, f"sc_map_{r.name[4:].lower()}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(sc, f, ensure_ascii=False)
        if rows:
            R.add_rows(out, "script", rows)
        # story text (Mato's lines as TED_* keys, as ted-events writes them)
        for fname, table in (("story_mes_en", self.texts.mes), ("story_cha_en", self.texts.cha)):
            if not table:
                continue
            msg = "Assets/GameAssets/Serial/Data/Message/" + fname
            path = os.path.join(out, "message", *msg.split("/")) + ".txt"
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(f"{k}\t{v}" for k, v in sorted(table.items())) + "\n")
            R.add_keys(out, "message", "ted_maps", [(fname, msg)])
        self.ids.save()
        self.alloc.save()
        if os.path.exists(STANDINS):
            with open(STANDINS, encoding="utf-8") as f:
                doc = json.load(f)
            doc["npcs"] = [x for x in doc.get("npcs", []) if x.get("by") != OWNER] + self.standins
            tmp = STANDINS + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=1, ensure_ascii=False)
            os.replace(tmp, STANDINS)
        tmp = REPORT + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"stats": dict(self.stats), "events": self.report}, f, indent=1, ensure_ascii=False)
        os.replace(tmp, REPORT)
        stubs = collections.Counter()
        for e in self.report:
            stubs.update(e["stubs"])
        self.log(f"events on new maps: {dict(self.stats)}; stubs by class: {dict(stubs.most_common(8))}")
        _ = tilemaps
