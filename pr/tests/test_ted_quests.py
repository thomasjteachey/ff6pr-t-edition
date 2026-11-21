"""T-Edition's pub quests (tools/ted_quests.py): the events, the PR NPCs they're wired to, a small build.

    .venv/Scripts/python -m unittest tests.test_ted_quests      (~45 s: the translator needs T-Edition's item rows)
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

import ted_quests as Q  # noqa: E402

MATO = os.path.join(HERE, "..", "..", "build", "t-edition", "T-Edition 3.0.7 (Mato).sfc")


@unittest.skipUnless(os.path.exists(MATO), "T-Edition's ROM isn't built")
class Quests(unittest.TestCase):
    def test_tagged_events(self):
        ev = Q.catalog_events()
        if not ev:
            self.skipTest("the catalog has no owner tags yet")
        self.assertIn("CA/7D09", [e for e, _, _ in ev])          # South Figaro's pub owner

    def test_pub_owner_entities(self):
        # Kohlingen's pub owner (SNES map 191, NPC 4 at (24, 11)): the PR NPC in the WoB and the WoR room
        rooms = {(pr, lay) for pr, _, _, _, lay, _, _ in Q.npc_entities(191, 24, 11)}
        self.assertIn(("Map_20131_1", "entity_default"), rooms)
        self.assertIn(("Map_20381_1", "entity_default"), rooms)

    def test_small_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "TEditionQuests")
            events = [("CC/6F1F", "pub_kohlingen", "Rest in Peace"), ("CD/FAC0", "pub_zozo", "Super Doctor D")]
            rep = Q.build(out=out, events=events, write=False, log=lambda *a: None)
            wired = [w for r in rep for w in r.get("wired", [])]
            self.assertGreaterEqual(len(wired), 3)
            self.assertTrue(all(w["script_id"] in Q.SCRIPT_IDS for w in wired))
            self.assertTrue(all(sum(w["stubs"].values()) <= 5 for w in wired))


class Folder(unittest.TestCase):
    """mods/TEditionQuests as the last build wrote it: every entity it rewired runs a script it ships, listed
    in script.csv and in the room's package entry (what talking to the NPC needs; the harness can't talk)."""

    def test_entities_run_shipped_scripts(self):
        import csv
        import glob
        root = os.path.join(HERE, "..", "mods", "TEditionQuests")
        rep_path = os.path.join(HERE, "..", "build", "t-edition", "quests", "report.json")
        if not os.path.isdir(root) or not os.path.exists(rep_path):
            self.skipTest("no quests build yet")
        rows = {}
        for f in glob.glob(os.path.join(root, "master", "**", "script.csv"), recursive=True):
            with open(f, encoding="utf-8") as fh:
                rows.update({int(r["id"]): r["script_name"] for r in csv.DictReader(fh)})
        wired = [w for r in json.load(open(rep_path, encoding="utf-8")) for w in r.get("wired", [])]
        self.assertTrue(wired)
        for w in wired:
            self.assertEqual(rows.get(w["script_id"]), w["now"], w)
            room = glob.glob(os.path.join(root, "map_*", "**", w["pr_map"], w["layer"] + ".json"), recursive=True)
            self.assertTrue(room, w)
            ids = [q["value"] for lay in json.load(open(room[0], encoding="utf-8"))["layers"]
                   for o in lay.get("objects") or [] for q in o.get("properties", []) if q["name"] == "script_id"]
            self.assertIn(w["script_id"], ids, w)
            pk = glob.glob(os.path.join(root, "map_*", "**", "package.json"), recursive=True)
            listed = {s["name"] for p in pk for m in json.load(open(p, encoding="utf-8"))["map"]
                      if m["name"] == w["pr_map"] for s in m["script"]}
            self.assertIn(w["now"], listed, w)

    def test_every_script_is_listed(self):
        """Every script file the folder ships is in a room package (the game loads nothing else): this
        folder's own package for vanilla rooms; on ted-maps' new rooms, their package (main scripts) or
        data/ted_quests_maps.json "_list" (after-battle / after-warp scripts, which ted-maps lists); an
        entrance script is grafted into ted-maps' map script instead."""
        import glob
        root = os.path.join(HERE, "..", "mods", "TEditionQuests")
        maps_json = os.path.join(HERE, "..", "data", "ted_quests_maps.json")
        if not os.path.isdir(root) or not os.path.exists(maps_json):
            self.skipTest("no quests build yet")
        listed = set()
        for p in glob.glob(os.path.join(root, "map_*", "**", "package.json"), recursive=True):
            with open(p, encoding="utf-8") as f:
                listed |= {(m["name"], s["name"]) for m in json.load(f)["map"] for s in m.get("script", [])}
        with open(maps_json, encoding="utf-8") as f:
            qm = json.load(f)
        for_maps = {(r, n) for r, ns in qm.get("_list", {}).items() for n in ns}
        mains = {x["script"] for k, v in qm.items() if k.isdigit() for x in v.get("npcs", []) + v.get("tiles", [])}
        entrances = {v["entrance"]["script"] for k, v in qm.items() if k.isdigit() and v.get("entrance")}
        missing = []
        for f in glob.glob(os.path.join(root, "map_*", "**", "sc_*.json"), recursive=True):
            room, sn = os.path.basename(os.path.dirname(f)), os.path.basename(f)[:-5]
            with open(f, encoding="utf-8") as fh:
                doc = json.load(fh)
            self.assertTrue(isinstance(doc, dict) and doc.get("Mnemonics"), f"{room}/{sn} isn't a script")
            if sn.startswith("sc_map_"):
                continue                 # a room's own load script, replaced (listed in the vanilla package)
            if not ((room, sn) in listed or (room, sn) in for_maps or sn in mains or sn in entrances):
                missing.append((room, sn))
        self.assertEqual(missing, [])

    def test_listed_scripts_exist(self):
        """The other way round: every sc_tedq script a package names (this folder's, or ted-maps' for its
        rooms from data/ted_quests_maps.json) has its file in that room here. A name the room can't load
        makes the game refuse it (ted-7: one event on several SNES maps had one file for many rooms)."""
        import glob
        mods = os.path.join(HERE, "..", "mods")
        if not os.path.isdir(os.path.join(mods, "TEditionQuests")):
            self.skipTest("no quests build yet")
        missing = []
        for d in ("TEditionQuests", "TEditionMaps"):
            for p in glob.glob(os.path.join(mods, d, "map_*", "**", "package.json"), recursive=True):
                with open(p, encoding="utf-8") as f:
                    pk = json.load(f)
                rel = os.path.relpath(os.path.dirname(p), os.path.join(mods, d))
                for m in pk["map"]:
                    for s in m.get("script", []):
                        if s["name"].startswith("sc_tedq_") and not os.path.exists(
                                os.path.join(mods, "TEditionQuests", rel, s["asset"] + ".json")):
                            missing.append((d, m["name"], s["name"]))
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
