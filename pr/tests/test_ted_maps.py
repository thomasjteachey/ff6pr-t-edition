"""Offline tests for T-Edition's maps (tools/ted_maps.py, data/ted_maps.json, mods/TEditionMaps).

  pr/.venv/Scripts/python -m unittest discover -s pr/tests -p "test_ted_maps.py" -v

  * T-Edition's map tables (counts found 2026-11-20), map 130's out-of-order exits, the new layouts,
    entrance-event tile commands
  * the build (after `python tools/ted_maps.py build`): every buildable map built, every door the build
    made leads to an arrival point that exists, every chest with a treasure flag of its own in the agreed
    range, every file in the Magicite folder named by a keys entry
Tests needing the T-Edition build, the US ROM or the PR extract skip without them. The kit's own map
tools are tested in tests/test_snes_maps.py.
"""
import glob
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import prdata as P  # noqa: E402
import snes_maps as SM  # noqa: E402
import ted_maps as T  # noqa: E402


def ted_rom():
    if not os.path.exists(T.MATO):
        raise unittest.SkipTest("no T-Edition build (build/t-edition)")
    return T.rom()


def flat(layers):
    """Every object of an entity file, in groups too."""
    out = []
    for lay in layers:
        out += lay.get("objects") or []
        out += flat(lay.get("layers", []))
    return out


class Tables(unittest.TestCase):
    def test_counts(self):
        data = ted_rom()
        self.assertEqual(len(T.used_maps(data)), 505)
        self.assertEqual(len(T.new_maps(data)), 95)   # 93 + the reused slots 415 and 5 (REUSED)
        tot = {k: sum(len(SM.map_data(data, m, T.TED)[k]) for m in T.used_maps(data))
               for k in ("npcs", "events", "exits", "chests")}
        self.assertEqual(tot, {"npcs": 2720, "events": 1695, "exits": 1482, "chests": 367})
        self.assertEqual(sum(len(SM.chests(data, m, T.TED)) for m in T.new_maps(data)), 70)

    def test_map_130(self):
        data = ted_rom()
        self.assertEqual(len([e for e in SM.exits(data, 130, T.TED) if e["kind"] == "short"]), 3)
        self.assertEqual([e for e in SM.exits(data, 129, T.TED) if e["kind"] == "short"], [])

    def test_new_layouts(self):
        data = ted_rom()
        users = {m for m in T.new_maps(data) if SM.properties(data, m, T.TED.props)["layouts"][0] >= 381}
        self.assertEqual(users, {429, 431, 432, 433, 434})
        self.assertIsNotNone(SM.layout(data, 431, 0, t=T.TED))

    def test_tiles(self):
        bg1 = [[1] * 4 for _ in range(4)]
        out = T.apply_tiles([bg1, None, None], ((4, 4), (4, 4), (4, 4)),
                            [(1, 1, 2, 1, bytes([7, 8])), (0, 64 + 2, 1, 1, bytes([9]))])
        self.assertEqual(out[0][1], [1, 7, 8, 1])
        self.assertEqual(out[1][2][0], 9)        # y bits 6-7: the layer (64 = BG2)
        self.assertEqual(bg1[1], [1, 1, 1, 1])  # the input untouched

    def test_battle_backgrounds(self):
        """G8: the backgrounds T-Edition recoloured, each from the vanilla painting with its graphics and layout."""
        import ted_battle_bgs as B
        import ff6snes as S
        data = ted_rom()
        got = [(b, base) for b, base, _, _ in B.changes(data, S.rom_bytes(P.VANILLA_ROM))]
        self.assertEqual(got, [(4, 4), (5, 5), (10, 8), (43, 18), (49, 17), (56, 43)])
        self.assertEqual(B.pr_group(49), "bg_ff6_50")
        # a flat color repeated in vanilla's palette takes the mean of T-Edition's; padding black stays black
        old = [(0, 0, 0)] + [(10, 20, 60)] * 15 + [(0, 0, 0)] * 32
        new = [(0, 0, 0)] + [(200, 200, 200)] * 7 + [(0, 0, 0)] * 8 + [(0, 0, 0)] * 32
        px = bytes([10, 20, 60, 255, 0, 0, 0, 255])
        out = B.recolor(px, old, new)
        self.assertTrue(80 < out[0] < 140)
        self.assertEqual(out[4:], bytes([0, 0, 0, 255]))


class Build(unittest.TestCase):
    UNBUILT = []   # 433 (a look of T-Edition's own: drawn from the nearest pictures) and 435 (391's copy) built 2026-11-20

    def setUp(self):
        if not os.path.exists(T.MAPS_JSON) or not os.path.isdir(T.OUT):
            raise unittest.SkipTest("no T-Edition map build (python tools/ted_maps.py build)")
        with open(T.MAPS_JSON, encoding="utf-8") as f:
            self.doc = json.load(f)

    def objects(self):
        """{PR map id: [objects]} of every map file in the folder."""
        ids = {r["map_name"]: int(r["id"]) for r in P.Table("map")}
        for rec in self.doc["maps"].values():
            for r in rec["rooms"]:
                ids[r["pr_map"]] = r["pr_id"]
        out = {}
        for p in glob.glob(os.path.join(T.OUT, "map_*", "**", "entity_default.json"), recursive=True):
            with open(p, encoding="utf-8") as f:
                out[ids[os.path.basename(os.path.dirname(p))]] = flat(json.load(f)["layers"])
        return out

    def test_all_built(self):
        # 93 new maps (417-510 less 496) and the two vanilla slots T-Edition reuses (ted_maps.REUSED: 415, 5)
        self.assertEqual(len(self.doc["maps"]), 93 + len(T.REUSED))
        self.assertEqual([m for m, r in self.doc["maps"].items() if not r["rooms"]], self.UNBUILT)

    def test_doors_lead_somewhere(self):
        """Every door the build made (on its maps, and those added to vanilla maps) leads to an
        arrival point that exists: on a new map, its PointIn; on a vanilla map, one of its own or
        one the build added."""
        objs = self.objects()
        new_ids = {r["pr_id"] for rec in self.doc["maps"].values() for r in rec["rooms"]}
        dirs = SM.pr_map_dirs()
        by_id = {int(r["id"]): r["map_name"] for r in P.Table("map")}
        props = lambda o: {x["name"]: x["value"] for x in o.get("properties", [])}
        doors = [(mid, o) for mid in new_ids for o in objs.get(mid, []) if o["name"] == "GotoMap"]
        added = self.doc["additions"]
        doors += [(pr, {"name": o["name"], "x": 16 * o["x"], "properties": [{"name": k, "value": v} for k, v in
                                                                            o["properties"].items()]})
                  for pr, os_ in added.items() for o in os_ if o["name"] == "GotoMap"]
        self.assertGreater(len(doors), 300)
        # doors other workstreams asked for (data/ted_ex_maps.json...) lead into their own folders' maps
        external = set()
        for path in T.EXTRA_JSONS:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    external |= {tuple(e["to"]) for rec in json.load(f).values() if isinstance(rec, dict)
                                 for e in rec.get("exits", [])}
        missing = []
        for where, o in doors:
            p = props(o)
            tgt, pt = p["map_id"], p["point_id"]
            if (tgt, pt) in external:
                continue
            if tgt in new_ids:
                points = {props(q).get("object_id") for q in objs.get(tgt, []) if q["name"] == "PointIn"}
            else:
                name = by_id.get(tgt)
                points = set(SM.pr_links(dirs[name])[1]) if name in dirs else set()
                points |= {q["properties"]["object_id"] for q in added.get(name, []) if q["name"] == "PointIn"}
            if pt not in points:
                missing.append((where, o["x"] // 16, tgt, pt))
        self.assertEqual(missing, [])

    def test_every_room_has_an_arrival(self):
        objs = self.objects()
        rooms = [r["pr_id"] for rec in self.doc["maps"].values() for r in rec["rooms"]]
        self.assertEqual([m for m in rooms if not any(o["name"] == "PointIn" for o in objs.get(m, []))], [])

    def test_ids_stay(self):
        """Rooms keep their PR ids from build to build; ids stay in ted-maps' range (644-779)."""
        ids = [r["pr_id"] for rec in self.doc["maps"].values() for r in rec["rooms"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(644 <= i <= 779 for i in ids))
        self.assertEqual(self.doc["maps"]["497"]["rooms"][0]["pr_id"], 735)   # as ted-maps-1 (QA batch ted-8) uses

    def test_titles(self):
        """Every title a new map or arrival uses is one of the folder's TEDMAP_NAME keys (T-Edition's
        location names, Mato's English); the names decode (126 of them, 75 = Forbidden Land Eureka)."""
        path = os.path.join(T.OUT, "message", *T.MESSAGE.split("/")) + ".txt"
        with open(path, encoding="utf-8") as f:
            keys = dict(line.split("\t", 1) for line in f.read().splitlines() if "\t" in line)
        self.assertEqual(keys.get("TEDMAP_NAME_75"), "Forbidden Land Eureka")
        used = {r["title"] for r in self.doc["maps"].values() if r.get("title")}
        for o in [o for os_ in self.objects().values() for o in os_ if o["name"] == "PointIn"]:
            t = {x["name"]: x["value"] for x in o.get("properties", [])}.get("title_id")
            if t and t.startswith("TEDMAP_"):
                used.add(t)
        self.assertGreater(len(used), 20)
        self.assertEqual(sorted(used - set(keys)), [])

    def test_event_scripts(self):
        """The new maps' events (tools/ted_map_events.py): every NPC / step trigger's script_id is a
        script.csv row of this folder whose script file is in that room and listed in its package; no
        translator stub is left as a SysCall (they become Nops)."""
        path = os.path.join(T.OUT, "master", "Assets", "GameAssets", "Serial", "Data", "Master", "script.csv")
        if not os.path.exists(path):
            self.skipTest("built without events")
        import csv
        import ted_map_events as TE
        with open(path, encoding="utf-8") as f:
            names = {int(r["id"]): r["script_name"] for r in csv.DictReader(f)}
        bad, used = [], 0
        for p in glob.glob(os.path.join(T.OUT, "map_*", "**", "entity_default.json"), recursive=True):
            room = os.path.dirname(p)
            if not os.path.exists(os.path.join(os.path.dirname(room), "package.json")):
                continue        # a vanilla map's entity file with objects added (its package is the game's)
            with open(os.path.join(os.path.dirname(room), "package.json"), encoding="utf-8") as f:
                pkg = json.load(f)
            entry = next((m for m in pkg["map"] if m["name"] == os.path.basename(room)), None)
            listed = {x["name"] for x in (entry or {}).get("script", [])}
            with open(p, encoding="utf-8") as f:
                objs = flat(json.load(f)["layers"])
            for o in objs:
                if o["name"].startswith("TEdition") and o["name"] != "TEditionChest":
                    sid = {x["name"]: x["value"] for x in o.get("properties", [])}.get("script_id")
                    if not sid or sid not in TE.SCRIPT_IDS:     # none, or ted-ex's (its own script.csv)
                        continue
                    used += 1
                    nm = names.get(sid)
                    if nm is None or nm not in listed or not os.path.exists(os.path.join(room, nm + ".json")):
                        bad.append((os.path.basename(room), o["name"], sid, nm))
        self.assertGreater(used, 100)
        self.assertEqual(bad, [])
        import event_translate as ET
        stubs, jumps = [], []
        for p in glob.glob(os.path.join(T.OUT, "map_*", "**", "sc_*.json"), recursive=True):
            with open(p, encoding="utf-8") as f:
                sc = json.load(f)
            ms = sc.get("Mnemonics", [])
            stubs += [os.path.basename(p) for m in ms if m.get("mnemonic") == "SysCall" and
                      str((m.get("operands", {}).get("sValues") or [""])[0]).startswith("SNES:")]
            # every jump lands on a labelled Nop of its own script (index 0 = "none" in a Branch's
            # second target)
            for n, m in enumerate(ms):
                for k in ET.JUMP_OPERANDS.get(m["mnemonic"], ()):
                    t = m["operands"]["iValues"][k]
                    if t == 0 and k > 0:
                        continue
                    if not (isinstance(t, int) and 0 <= t < len(ms) and ms[t]["mnemonic"] == "Nop" and ms[t]["label"]):
                        jumps.append((os.path.basename(p), n, m["mnemonic"], t))
        self.assertEqual(stubs, [])
        self.assertEqual(jumps[:10], [])

    def test_npc_looks(self):
        """tools/ted_npc_looks.py: every sprite number the new maps use has a record; 72 of 112 a PR look
        (2026-11-20; mapobject ids); the cast rule (SNES 0-13 -> mapobject 120 + n); a tile's pixels."""
        import ted_npc_looks as L
        if not os.path.exists(L.OUT):
            self.skipTest("no data/ted_npc_looks.json")
        with open(L.OUT, encoding="utf-8") as f:
            doc = json.load(f)
        self.assertEqual(len(doc["looks"]), 112)
        self.assertGreaterEqual(len(L.looks()), 72)
        self.assertTrue(all(0 < a < 1000 or a >= 3001 for v in L.looks().values() for a in v))   # 3001+: ted_npc_art rows
        tile = bytes([0xFF, 0x00] * 8 + [0x00] * 16)            # plane 0 set: every pixel colour 1
        self.assertEqual(set(L.pixels(tile)), {1})
        self.assertEqual(L.iou([1, 1, 0, 0], [1, 0, 0, 0]), 0.5)

    def test_vanilla_chests(self):
        """Chests T-Edition added on vanilla maps (audit I19): each in its vanilla PR room's entity file, its own
        treasure flag in VANILLA_CHEST_FLAGS, none twice."""
        vc = self.doc.get("vanilla_chests", [])
        if not vc:
            self.skipTest("a build before the vanilla-map chests")
        flags = [c["flag_id"] for c in vc]
        lo, hi = T.VANILLA_CHEST_FLAGS
        self.assertEqual(len(flags), len(set(flags)))
        self.assertTrue(all(lo <= f <= hi for f in flags))
        added = self.doc["additions"]
        for c in vc:
            self.assertTrue(any(o["name"] == "TEditionChest" and o["properties"]["flag_id"] == c["flag_id"]
                                for o in added.get(c["pr_map"], [])), c)

    def test_chest_flags(self):
        flags = [c["flag_id"] for r in self.doc["maps"].values() for c in r["chests"] if c["placed"]]
        self.assertEqual(len(flags), len(set(flags)))
        lo, hi = self.doc.get("chest_flags", T.CHEST_FLAGS)
        self.assertTrue(all(lo <= f <= hi for f in flags))

    def test_keys(self):
        named = set()
        for k in glob.glob(os.path.join(T.OUT, "*", "keys", "*.json")):
            group = os.path.basename(os.path.dirname(os.path.dirname(k)))
            with open(k, encoding="utf-8") as f:
                named |= {(group, v) for v in json.load(f)["values"]}
        files = set()
        for p in glob.glob(os.path.join(T.OUT, "*", "Assets", "**", "*.*"), recursive=True):
            group, rest = os.path.relpath(p, T.OUT).replace("\\", "/").split("/", 1)
            files.add((group, os.path.splitext(rest)[0]))
        self.assertEqual(sorted(files - named), [])


if __name__ == "__main__":
    unittest.main()
