"""T-Edition's events (tools/ted_events.py, tools/ted_dialog.py) on the kit's decoder and translator.

  * decoding: every event script reachable from every map of Mato's build decodes with no unknown
    command, T-Edition's own commands among them (sizes read from its handlers);
  * its dialogue: both pointer tables, the 112-word dictionary, choices;
  * the event built into pr/mods/TEditionEvents (South Figaro's wine old man) translates with no stub,
    is wired to the NPC in each of its entity layers with the layer's own PR script grafted in, and
    the Magicite folder loads (prkit.magicite.validate).

Needs the JP ROM and Mato's T-Edition build (skipped without them); the event test also
build/dialog/dialog_map.json.

  pr/.venv/Scripts/python -m unittest discover -s pr/tests -p "test_ted_events.py" -v
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PR = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PR, "tools"))
import kitpath  # noqa: E402,F401  (T-Edition's repository: the kit's tools on the path)
import snes_events as E  # noqa: E402
import ted_events as TE  # noqa: E402

HAVE_TED = os.path.exists(TE.MATO) and os.path.exists(E.JP_ROM)
HAVE_DIALOG = os.path.exists(os.path.join(PR, "build", "dialog", "dialog_map.json"))
_prog = None


def prog():
    global _prog
    if _prog is None:
        _prog = E.Program(TE.load("ted")).walk_all()
    return _prog


@unittest.skipUnless(HAVE_TED, "needs the JP ROM and Mato's T-Edition build")
class Decoding(unittest.TestCase):
    def test_every_ted_script_decodes(self):
        c = prog().coverage()
        self.assertEqual(c["unknown"], {})
        self.assertEqual(c["obj_unknown"], {})
        self.assertGreater(c["instructions"], 60000)
        by = prog().by_op
        for name in ("dialog2", "cmp_1300", "if_bit1850_clear", "ted_song_volume", "word1DD0_set"):
            self.assertGreater(by[name], 0, name)

    def test_new_command_sizes(self):
        ops = TE.DIALECT.ops
        for code, size in ((0x5B, 5), (0xA3, 5), (0xA5, 5), (0xEC, 5), (0x67, 4), (0xFC, 4), (0x83, 4),
                           (0xED, 4), (0xE5, 2), (0x66, 3), (0x76, 3), (0x9E, 2), (0x9F, 3), (0xEE, 3), (0xCC, 2)):
            self.assertEqual(ops[code].size, size, hex(code))
        # the ROM's handlers for them are T-Edition's own (the JP ROM's table at the same place)
        d = TE.load("ted").data
        jp = E.load("jp").data
        tbl = lambda x, op: x[0x97F9 + 2 * (op - 0x35)] | x[0x97F9 + 2 * (op - 0x35) + 1] << 8
        for code in (0x5B, 0x67, 0xEE, 0xFC, 0xCB, 0xCC):
            self.assertNotEqual(tbl(d, code), tbl(jp, code), hex(code))

    def test_dialogue(self):
        import ted_dialog as D
        d = D.rom_bytes()
        self.assertEqual(D.count(d, D.PTRS), 3452)
        self.assertEqual(D.count(d, D.PTRS2), 1267)
        self.assertEqual(D.mte(d)[0], b"\x26\x3e\x4c\x4d\x3a\x41\x45")      # "Gestahl"
        self.assertIn("save points?", D.text(d, D.file_of(d, D.PTRS, 10)))
        self.assertEqual(D.choices(d, D.file_of(d, D.PTRS, 10)), 2)
        self.assertTrue(D.text(d, D.file_of(d, D.PTRS2, 0)).startswith("Owzer: Hrm? That claw..."))


@unittest.skipUnless(HAVE_TED and HAVE_DIALOG, "needs Mato's T-Edition build and build/dialog/dialog_map.json")
class WineOldMan(unittest.TestCase):
    def test_the_event(self):
        import event_translate as T
        from prkit import data as PD, magicite as MG
        out = os.path.join(tempfile.mkdtemp(), "TEditionEvents")
        report, mod = TE.build(out=out, write=False)
        mod.write()
        rep = report[0]
        self.assertEqual(rep["stubs"], {})
        self.assertGreaterEqual(rep["translated"]["dialog"], 11)
        problems, notes = MG.validate(out, PD.GameData("ff6"))
        self.assertEqual(problems, [])
        room = os.path.join(out, "map_20071", "Assets", "GameAssets", "Serial", "Res", "Map", "Map_20071", "Map_20071_23")
        sc = TE._json(os.path.join(room, "sc_ted_cd5850.json"))
        self.assertEqual(T.check(sc), [])
        ops = [(m["mnemonic"], m["operands"]["iValues"][:2], m["operands"]["sValues"][0]) for m in sc["Mnemonics"]]
        self.assertIn(("GetItem", [287, 1], ""), ops)            # Hermes Shoes = the PR's Angel Wings
        self.assertIn(("ChangeMap", [38, 10], ""), ops)          # out to South Figaro
        self.assertIn(("Msg", [0, 0], "TED_E0317_a_01"), ops)
        mes = mod.texts["story_mes_en"]
        self.assertTrue(mes["TED_E0320_a_01"].endswith("Hermes Shoes!"))
        # wired: the old man in each of his three entity layers runs T-Edition's event, which falls
        # back on that layer's own PR script (grafted in)
        wired = {w["layer"]: w for w in rep["wired"]}
        self.assertEqual(sorted(wired), ["ev_e_0038", "ev_e_0063", "ev_e_0075"])
        self.assertEqual(wired["ev_e_0038"]["was"], "sc_npc_20071_23_1")
        w = TE._json(os.path.join(room, "sc_ted_cd5850_l0038.json"))
        self.assertEqual(T.check(w), [])
        msgs = [m["operands"]["sValues"][0] for m in w["Mnemonics"] if m["mnemonic"] == "Msg"]
        self.assertIn("N004_C00_061_01_01", msgs)                 # the PR's own line, grafted
        self.assertIn("TED_E0317_a_01", msgs)
        layer = TE._json(os.path.join(room, "ev_e_0038.json"))
        ids = [q["value"] for lay in layer["layers"] for o in lay["objects"] for q in o["properties"]
               if q["name"] == "script_id" and q["value"] >= 9500]
        self.assertEqual(ids, [wired["ev_e_0038"]["script_id"]])

    def test_ex_boss_bits_have_fixed_flags(self):
        # EX's boss fights (ted-ex) and the Collection Room (here) read the same flags: reserved in the
        # shared file, and T-Edition's own meaning of these bits wins over any tie learned from vanilla
        import event_translate as T
        alloc = T.FlagAlloc(TE.ALLOC)
        self.assertEqual([alloc.table[b] for b in TE.EX_BOSS_BITS], [("ScenarioFlag4", 5 + k) for k in range(12)])
        t = TE._translator_class()(TE.load("ted"), "x", alloc=alloc, prog=prog())
        T.maps()["flags"][0x000] = ("ScenarioFlag1", 1)           # as if vanilla had taught a tie for it
        try:
            self.assertEqual(t.flag(0x000), ("ScenarioFlag4", 15))
        finally:
            del T.maps()["flags"][0x000]

    def test_flags_stay_off_treasure_flags(self):
        # ted-maps gives T-Edition's 70 new chests treasure flags 300-369: the event flags are story flags
        with open(TE.ALLOC, encoding="utf-8") as f:
            alloc = json.load(f)
        self.assertTrue(all(v[0].startswith("ScenarioFlag") for v in alloc.values()))


if __name__ == "__main__":
    unittest.main()
