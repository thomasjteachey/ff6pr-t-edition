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


if __name__ == "__main__":
    unittest.main()
