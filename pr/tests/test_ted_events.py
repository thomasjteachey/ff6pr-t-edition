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
        d = prog().rom.data
        jp = E.load("jp").data
        tbl = lambda x, op: x[0x97F9 + 2 * (op - 0x35)] | x[0x97F9 + 2 * (op - 0x35) + 1] << 8
        for code in (0x5B, 0x67, 0xEE, 0xFC, 0xCB, 0xCC):
            self.assertNotEqual(tbl(d, code), tbl(jp, code), hex(code))

    def test_choices_in_any_layout(self):
        # a choice line may start with a space, and a line may hold two (dialogue 362: Left / Right)
        t = TE.Texts(prog().rom)
        keys, choices = t.keys(362)
        self.assertEqual([t.mes[k] for k in choices], ["(Straight)", "(Left)", "(Right)"])
        keys, choices = t.keys(10)
        self.assertEqual([t.mes[k] for k in choices], ["Yes", "No"])

    def test_dialogue(self):
        import ted_dialog as D
        d = D.rom_bytes()
        self.assertEqual(D.count(d, D.PTRS), 3452)
        self.assertEqual(D.count(d, D.PTRS2), 1267)
        self.assertEqual(D.mte(d)[0], b"\x26\x3e\x4c\x4d\x3a\x41\x45")      # "Gestahl"
        self.assertIn("save points?", D.text(d, D.file_of(d, D.PTRS, 10)))
        self.assertEqual(D.choices(d, D.file_of(d, D.PTRS, 10)), 2)
        self.assertTrue(D.text(d, D.file_of(d, D.PTRS2, 0)).startswith("Owzer: Hrm? That claw..."))


@unittest.skipUnless(HAVE_TED, "needs the JP ROM and Mato's T-Edition build")
class Songs(unittest.TestCase):
    def test_song_tables(self):
        # two drivers: C5 (map songs, F0/EF/F1) and bank 43 (76/9E/9F); vanilla's songs by their bytes
        import ted_songs as TS
        o = TS.build(write=False)
        self.assertEqual(o["songs"]["23"], 3)            # 17: Narshe, the PR's track 3
        self.assertEqual(o["songs"]["43"], 47)           # 2B: a few notes fixed, still vanilla's
        for slot in (0x25, 0x2F, 0x38, 0x3F, 0x49, 0x51, 0x55, 0xFE):   # T-Edition's music in C5
            self.assertIn(slot, o["new"], hex(slot))
            self.assertNotIn(str(slot), o["songs"])
        self.assertEqual(o["second"]["47"], 7)           # 2F: the victory fanfare, on the second driver
        self.assertEqual(o["second"]["56"], 74)          # 38: Good Night
        self.assertEqual(o["second_new"][:2], [0x25, 0x55])
        self.assertEqual(o["no_track"]["0"], "silence")
        # an event's songs: vanilla's keep their PR tracks; T-Edition's own get the music pack's ids
        # (ted/MEDIA_PLAN.md): 1000 + n on the main driver, 1256 + n on the second (9E & 7F)
        t = TE._translator_class()(prog().rom, "x", prog=prog())
        self.assertEqual(t.song_bgm(0x25, "ted_song"), 1256 + 0x25)
        self.assertEqual(t.song_bgm(0x2F | 0x80, "ted_song"), 7)
        self.assertEqual(t.song_bgm(0x17, "song"), 3)
        self.assertEqual(t.song_bgm(0x3F, "song"), 1000 + 0x3F)
        self.assertIsNone(t.song_bgm(0, "song"))                 # silence


@unittest.skipUnless(HAVE_TED and HAVE_DIALOG, "needs Mato's T-Edition build and build/dialog/dialog_map.json")
class WineOldMan(unittest.TestCase):
    def test_the_event(self):
        import event_translate as T
        from prkit import data as PD, magicite as MG
        out = os.path.join(tempfile.mkdtemp(), "TEditionEvents")
        report, mod = TE.build(out=out, write=False, prog=prog())
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
        wired = {w["layer"]: w for w in rep["wired"] if "room" not in w}
        self.assertEqual(sorted(wired), ["ev_e_0038", "ev_e_0063", "ev_e_0075"])
        # and his World of Ruin copy (South Figaro WoR, Map_20361_23: his pub quest is a WoR one)
        self.assertIn("Map_20361_23", {w.get("room") for w in rep["wired"]})
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

    def test_rubys_shine(self):
        # README "Ruby's Shine" / "Test of Strength" / "Stolen Magicite": Narshe's two walk-on townsfolk
        # (no PR script: they get ours), and Tzen's merchant on the one PR room for the SNES's World of
        # Balance (306) and World of Ruin (305) Tzen: one script that picks the scene by the PR's flag
        import event_translate as T
        out = os.path.join(tempfile.mkdtemp(), "TEditionEvents")
        ev = [e for e in TE.EVENTS if e["map"] in (20, 305, 306)]
        report, mod = TE.build(out=out, events=ev, write=False, prog=prog())
        mod.write()
        by = {r["event"]: r for r in report}
        for e in ("CD/49D0", "CD/4A10", "CC/9CE0", "CC/5DD3"):
            self.assertEqual(by[e]["stubs"], {}, e)
        self.assertEqual([(w["layer"], w["entity"], w["was"]) for w in by["CD/49D0"]["wired"]],
                         [("ev_e_0018", 88, None)])
        narshe = os.path.join(out, "map_20010", "Assets", "GameAssets", "Serial", "Res", "Map", "Map_20010", "Map_20010")
        walkon = [{q["name"]: q["value"] for q in o["properties"]} for lay in TE._json(os.path.join(narshe, "ev_e_0018.json"))["layers"]
                  for o in lay.get("objects") or [] if any(q["name"] == "entity_id" and q["value"] == 88 for q in o.get("properties", []))]
        self.assertEqual((walkon[0]["script_id"], walkon[0]["action_id"]), (by["CD/49D0"]["wired"][0]["script_id"], 2))
        self.assertEqual(TE.snes_world(305), 1)
        self.assertEqual(TE.snes_world(306), 0)
        # Tzen: the PR keeps a World of Balance room (Map_20190) and a World of Ruin one (Map_20330);
        # each SNES map's event goes to its own world's room. The WoB bandit stands 2 tiles off in the
        # PR (ev_e_0427), found by his look
        self.assertEqual((TE.pr_world("Map_20190"), TE.pr_world("Map_20330")), (0, 1))
        self.assertEqual([(by["CC/9CE0"]["pr_map"], w["entity"]) for w in by["CC/9CE0"]["wired"]], [("Map_20330", 1)])
        self.assertEqual([(by["CC/5DD3"]["pr_map"], w["layer"], w["entity"]) for w in by["CC/5DD3"]["wired"]],
                         [("Map_20190", "ev_e_0427", 58)])
        room = os.path.join(out, "map_20330", "Assets", "GameAssets", "Serial", "Res", "Map", "Map_20330", "Map_20330")
        sc = TE._json(os.path.join(room, by["CC/9CE0"]["wired"][0]["now"] + ".json"))
        self.assertEqual(T.check(sc), [])
        self.assertFalse([m for m in sc["Mnemonics"] if m["mnemonic"] == "SysCall"
                          and m["operands"]["sValues"][0].startswith("SNES:")])   # stubs are Nops
        fights = [m["operands"]["iValues"][0] for m in sc["Mnemonics"] if m["mnemonic"] == "Encount"]
        self.assertTrue({30723, 30724, 30725} <= set(fights), fights)    # the porter's new formations

    def test_new_npc(self):
        # Gilgamesh in the Colosseum (map 413 NPC 6): no PR entity and no PR sprite -> a new NPC object
        # (entity 5000+) on the guard's look in the room's entity_default, running the event; listed as a
        # stand-in for bc-sprites
        out = os.path.join(tempfile.mkdtemp(), "TEditionEvents")
        report, mod = TE.build(out=out, events=[dict(event=0x34E20, map=413, npc=6)], write=False, prog=prog())
        mod.write()
        w = report[0]["wired"][0]
        self.assertTrue(w["new"] and w["entity"] in TE.NEW_ENTITY_IDS)
        self.assertEqual(report[0]["build"]["standins"][0]["sprite"], 221)
        room = os.path.join(out, "map_20421", "Assets", "GameAssets", "Serial", "Res", "Map", "Map_20421", "Map_20421_2")
        objs = [{q["name"]: q["value"] for q in o["properties"]} for lay in TE._json(os.path.join(room, "entity_default.json"))["layers"]
                for o in lay.get("objects") or []]
        new = [o for o in objs if o.get("entity_id") == w["entity"]]
        self.assertEqual([(o["script_id"], o["action_id"], o["object_type"], o["asset_id"]) for o in new],
                         [(w["script_id"], 2, 6, TE.STANDIN_LOOK)])

    def test_party_checks(self):
        # DE (the active party) then "if any of bits 1A0+c": character c here -> the PR's BranchByCharacter
        # (its ids: SNES + 1; operand 2: 0 = here, 1 = not here; operand 3: 0 = the active party)
        import event_translate as T
        t = TE._translator_class()(prog().rom, "x", prog=prog())
        load = E.Instr.__new__(E.Instr)
        load.op, load.off, load.name, load.cls, load.args = 0xDE, 0, "case_party", "flow", {}
        self.assertEqual(t.instr(load, False, None), ([], True))
        ins = E.Instr.__new__(E.Instr)
        ins.op, ins.off, ins.args = 0xC8, 0x10, {"bits": [(0x1A3, True), (0x1A0, False)], "event": 0x20}
        ops = [(o["mnemonic"], o["operands"]["iValues"][:4]) for o in t.cond(ins)]
        self.assertEqual(ops, [("BranchByCharacter", [4, 0, 0, "@L_000020"]), ("BranchByCharacter", [1, 1, 0, "@L_000020"])])
        ins.op = 0xC0                                            # all of them: a failing test skips the jump
        ops = [(o["mnemonic"], o["operands"]["iValues"][:4]) for o in t.cond(ins)]
        self.assertEqual(ops, [("BranchByCharacter", [4, 1, 0, "@skip_000010"]), ("BranchByCharacter", [1, 0, 0, "@skip_000010"]),
                               ("Jump", ["@L_000020", 0, 0, 0][:len(ops[2][1])]), ("Nop", ops[3][1])])

    def test_changed_in_place(self):
        # Figaro's priestess (CA/6C7B): T-Edition only redirected her first test (bit 049 -> its costume
        # scene) and reworded a line; from the next instruction on the PR's own script does vanilla's part
        self.assertEqual(TE.vanilla_resume(E.parse_addr("CA/6C7B"), prog()), E.parse_addr("CA/6C81"))
        self.assertIsNone(TE.vanilla_resume(E.parse_addr("CD/5850"), prog()))       # new code, not in place
        out = os.path.join(tempfile.mkdtemp(), "TEditionEvents")
        report, mod = TE.build(out=out, events=[dict(event=E.parse_addr("CA/6C7B"), map=57, npc=1)], write=False, prog=prog())
        w = next(w for w in report[0]["wired"] if w["was"] == "sc_e_0028")
        mod.write()
        path = next(os.path.join(r, w["now"] + ".json") for r, ds, fs in os.walk(out) if w["now"] + ".json" in fs)
        ops = TE._json(path)["Mnemonics"]
        self.assertTrue(any(m["mnemonic"] == "Jump" and "the PR's own script" in (m.get("comment") or "") for m in ops))

    def test_leader_and_party_switch(self):
        # E2 (the leader) then "if 1A0+c": BranchByLeader [c+1, target]; 46 n: ChangePartySlot [n, 1, 0]
        t = TE._translator_class()(prog().rom, "x", prog=prog())
        load = E.Instr.__new__(E.Instr)
        load.op, load.off, load.name, load.cls, load.args = 0xE2, 0, "case_leader", "flow", {}
        t.instr(load, False, None)
        ins = E.Instr.__new__(E.Instr)
        ins.op, ins.off, ins.args = 0xC8, 0x10, {"bits": [(0x1A2, True)], "event": 0x20}
        self.assertEqual([(o["mnemonic"], o["operands"]["iValues"][:2]) for o in t.cond(ins)],
                         [("BranchByLeader", [3, "@L_000020"])])
        sw = E.Instr.__new__(E.Instr)
        sw.op, sw.off, sw.name, sw.cls, sw.args = 0x46, 0, "party_active", "party", {"party": 2}
        ops, cont = t.instr(sw, False, None)
        self.assertEqual([(o["mnemonic"], o["operands"]["iValues"][:3]) for o in ops], [("ChangePartySlot", [2, 1, 0])])

    def test_ex_boss_bits_have_fixed_flags(self):
        # EX's boss fights (ted-ex) and the Collection Room (here) read the same flags: reserved in the
        # shared file, and T-Edition's own meaning of these bits wins over any tie learned from vanilla
        import event_translate as T
        alloc = T.FlagAlloc(TE.ALLOC)
        self.assertEqual([alloc.table[b] for b in TE.EX_BOSS_BITS], [("ScenarioFlag4", 5 + k) for k in range(12)])
        t = TE._translator_class()(prog().rom, "x", alloc=alloc, prog=prog())
        T.maps()["flags"][0x000] = ("ScenarioFlag1", 1)           # as if vanilla had taught a tie for it
        try:
            self.assertEqual(t.flag(0x000), ("ScenarioFlag4", 15))
        finally:
            del T.maps()["flags"][0x000]

    def test_flags_stay_off_treasure_flags(self):
        # ted-maps gives T-Edition's 70 new chests treasure flags 300-369 (vanilla's chests 0-272): the event flags
        # are story flags, or treasure flags 512-767 (TreasureFlag3), which no chest or vanilla script uses
        with open(TE.ALLOC, encoding="utf-8") as f:
            alloc = json.load(f)
        self.assertTrue(all(v[0].startswith("ScenarioFlag") or v[0] == "TreasureFlag3" for v in alloc.values()))
        self.assertEqual(len(set(map(tuple, alloc.values()))), len(alloc))

    def test_battle_bits_are_flags(self):
        # the inn dreams' chapters (CD/CA60...) test T-Edition's own battle bits (B7 09, 3E, 2B): story flags ->
        # a Branch on the bit's own PR flag; vanilla's battle bits (40: the lost battle) stay event_translate's
        import event_translate as T
        t = TE._translator_class()(prog().rom, "x", alloc=T.FlagAlloc(None), prog=prog())
        ins = prog().code[(E.parse_addr("CD/CA68"), "field")]
        ops, ok = t.instr(ins, False, None)
        self.assertTrue(ok)
        self.assertEqual(ops[0]["mnemonic"], "Branch")
        self.assertEqual(ops[0]["operands"]["iValues"][1:3], [0, "@L_035AD0"])
        self.assertEqual(ops[0]["operands"]["sValues"][0], t.flag(TE.BATTLE_KEY + 9)[0])
        sets = [i for i in prog().code.values() if i.name == "battle_bit_set" and i.args["bit"] == 9]
        ops, ok = t.instr(sets[0], False, None)
        self.assertEqual((ops[0]["mnemonic"], ops[0]["operands"]["iValues"][0]), ("SetFlag", t.flag(TE.BATTLE_KEY + 9)[1]))
        lost = next(i for i in prog().code.values() if i.name == "if_battle_bit_clear" and i.args["bit"] == 0x40)
        ops, ok = t.instr(lost, False, None)
        self.assertFalse(any("battle bit" in (o.get("comment") or "") for o in ops or []))

    def test_party_menu_and_walk_in_bits(self):
        # vanilla's "change party members?" routine (CA/CB99: 99 81 00 00, bit 7 a mode bit) -> the PR's party menu
        import event_translate as T
        t = TE._translator_class()(prog().rom, "x", alloc=T.FlagAlloc(None), prog=prog())
        ops, ok = t.instr(prog().code[(E.parse_addr("CA/CB99"), "field")], False, None)
        self.assertEqual([(o["mnemonic"], o["operands"]["sValues"][0]) for o in ops], [("SysCall", T.PARTY_MENU.format("１"))])
        # entrance tests of 1CC (an event's song carries over) and 1B6 (loaded by an event) are clear on a walk-in
        self.assertEqual(t.cond(prog().code[(E.parse_addr("CD/3290"), "field")]), [])       # if 1CC set -> never
        ops = t.cond(prog().code[(E.parse_addr("CD/4A90"), "field")])                       # if 1CC clear -> always
        self.assertEqual([(o["mnemonic"], o["operands"]["iValues"][0]) for o in ops], [("Jump", "@L_034E00")])

    def test_word_compares(self):
        # vanilla's word commands -> ScenarioVariable WORD_GLOBALS[n]; a compare's result test -> a Branch with the
        # comparison (1A0 equal, 1A1 greater, 1A2 less); T-Edition's own compares (FC: CE/63A0) -> TED:cmp and a
        # Branch on its map variable 5 (equal)
        import event_translate as T
        t = TE._translator_class()(prog().rom, "x", alloc=T.FlagAlloc(None), prog=prog())

        def ins(op, name, args, off=0):
            i = E.Instr.__new__(E.Instr)
            i.op, i.off, i.name, i.cls, i.args, i.size = op, off, name, "flag", args, 4
            i.mode = i.next_mode = "field"
            i.flow, i.targets, i.raw = "next", [], bytes([op])
            return i
        ops, _ = t.instr(ins(0xE9, "word_add", {"word": 5, "value": 3}), False, None)
        self.assertEqual([(o["mnemonic"], o["operands"]["iValues"][:2], o["operands"]["sValues"][:2]) for o in ops],
                         [("Calc", [TE.WORD_GLOBALS[5], 3], ["ScenarioVariable", "＋"])])
        self.assertEqual(t.instr(ins(0xEB, "word_cmp", {"word": 7, "value": 21}), False, None), ([], True))
        test = ins(0xC8, "if_any", {"bits": [(0x1A1, False)], "event": 0x10}, off=8)          # not greater: <= 21
        self.assertEqual([(o["operands"]["iValues"][:3], o["operands"]["sValues"][:2]) for o in t.cond(test)],
                         [([TE.WORD_GLOBALS[7], 21, "@L_000010"], ["ScenarioVariable", "≦"])])
        cmp_ = prog().code[(E.parse_addr("CE/63A0"), "field")]
        ops, _ = t.instr(cmp_, False, None)
        self.assertEqual(ops[0]["operands"]["sValues"][0], "TED:cmp 1300 0 512")
        ops = t.cond(prog().code[(E.parse_addr("CE/63A4"), "field")])
        self.assertEqual([(o["mnemonic"], o["operands"]["iValues"][:2], o["operands"]["sValues"][0]) for o in ops][:2],
                         [("Branch", [5, 0], "MapLocalVariable"), ("Jump", ["@L_046680", 0], "")])

    def test_veldt_open(self):
        # Gau's father (CB/681E -> CD/C113-C193, E32): 83 writes into the Veldt's formation bits (7E/1DDD+) -> one
        # TED:veldt_open per write with those formations' PR parties (CD/C113: 83 06 FF00 = formations 0-7 = parties 1-8)
        import event_translate as T
        t = TE._translator_class()(prog().rom, "x", alloc=T.FlagAlloc(None), prog=prog())
        ops, _ = t.instr(prog().code[(E.parse_addr("CD/C113"), "field")], False, None)
        self.assertEqual(ops[0]["operands"]["sValues"][0], "TED:veldt_open 1 2 3 4 5 6 7 8")

    def test_facing(self):
        # the engine's facing bits 1B0-1B3 (up/right/down/left) -> BranchByPlayerDirection [up, right, down, left];
        # vanilla's facing routine (CA/CA5A: 1B0-1B3 -> case bits 1A0-1A3) is nothing in the PR, its case tests and
        # BE switch read the facing too
        import event_translate as T
        t = TE._translator_class()(prog().rom, "x", alloc=T.FlagAlloc(None), prog=prog())
        ins = E.Instr.__new__(E.Instr)
        ins.op, ins.off, ins.args = 0xC0, 0x20, {"bits": [(0x1B1, True)], "event": 0x10}       # if facing right
        ops = t.cond(ins)
        self.assertEqual((ops[0]["mnemonic"], ops[0]["operands"]["iValues"][:4]),
                         ("BranchByPlayerDirection", ["@skip_000020", "@dirok_000020", "@skip_000020", "@skip_000020"]))
        call = next(i for i in prog().code.values() if i.name == "call" and i.args.get("event") == E.parse_addr("CA/CA5A"))
        self.assertEqual(t.instr(call, False, None), ([], True))
        ins.op, ins.args = 0xC8, {"bits": [(0x1A2, True)], "event": 0x10}                      # case bit 2: down
        self.assertEqual(t.cond(ins)[0]["operands"]["iValues"][:4], ["@dir_000020", "@dir_000020", "@L_000010", "@dir_000020"])

    def test_chest_bits(self):
        # 5B b = "chest 128 + b not opened" -> a Branch on ted-maps' PR treasure flag for that chest (EA/230B: bit 138 ->
        # chest 266 -> flag 300 = TreasureFlag2 44)
        import event_translate as T
        t = TE._translator_class()(prog().rom, "x", alloc=T.FlagAlloc(None), prog=prog())
        ops, _ = t.instr(prog().code[(E.parse_addr("EA/230B"), "field")], False, None)
        self.assertEqual((ops[0]["mnemonic"], ops[0]["operands"]["iValues"][:2], ops[0]["operands"]["sValues"][0]),
                         ("Branch", [TE.chest_flag(266)[1], 0], TE.chest_flag(266)[0]))

    def test_script_edits(self):
        # Cid (CA/5366): the PR's sc_e_0616 with T-Edition's doubled health per fish (Calc ScenarioVariable 2: 32 -> 64,
        # 12 -> 24), and sc_e_0625 with T-Edition's three tests (CD/4130: bits 0C1 0C9 0CD) just before "I'm all better
        # now!", each to its own lines; both well formed
        import event_translate as T
        Tr, texts = TE._translator_class(), TE.Texts(prog().rom)
        sc, _ = TE.script_edit(TE.SCRIPT_EDITS[0], prog().rom, prog(), T.FlagAlloc(None), Tr, texts)
        self.assertEqual(T.check(sc), [])
        calc = [m["operands"]["iValues"][:2] for m in sc["Mnemonics"] if m["mnemonic"] == "Calc"
                and m["operands"]["sValues"][0] == "ScenarioVariable"]
        self.assertEqual(calc[:2], [[2, 64], [2, 24]])
        sc, _ = TE.script_edit(TE.SCRIPT_EDITS[1], prog().rom, prog(), T.FlagAlloc(None), Tr, texts)
        self.assertEqual(T.check(sc), [])
        ms = sc["Mnemonics"]
        at = next(i for i, m in enumerate(ms) if m["mnemonic"] == "Msg" and m["operands"]["sValues"][0] == "E0616_00_191_a_08")
        self.assertEqual([m["mnemonic"] for m in ms[at - 3:at]], ["Branch"] * 3)
        self.assertTrue(any(m["mnemonic"] == "Msg" and m["operands"]["sValues"][0].startswith("TED_") for m in ms))

    def test_tile_changes(self):
        # CA/13F4 draws a 3x4 picture over walls on map 126 (Map_20451_2): a passability change, its cells with a
        # look (a cell of the map to copy, or the converter's gids; its bottom row's tile 74 over BG2 128 no
        # vanilla room has: "-", the collision alone) and every changed cell's collision
        ins = prog().code[(E.parse_addr("CA/13F4"), "field")]
        a = ins.args
        p = TE.tile_plan(126, "Map_20451_2", a["x"], a["y"], a["w"], a["h"], bytes(ins.raw[5:]))
        self.assertEqual(p["tag"], "passability")
        self.assertEqual(len(p["cells"]), 12)
        self.assertGreaterEqual(sum(src is not None for _, _, src, _ in p["cells"]), 9)
        self.assertEqual(sum(attr is not None for _, _, _, attr in p["cells"]), 10)   # 2 stay walls: no attr
        s = TE.tiles_syscall(p["cells"])
        self.assertRegex(s, r"^TED:tiles( \d+,\d+=(\d+,\d+|#\d+/\d+/\d+/\d+|-)(:\d+)?)+$")
        # a cell the PR map already shows the new way is left out; one another event changes is put back
        x, y = a["x"], a["y"] & 0x3F
        bg1 = TE.tile_layers(126)[0]
        same = TE.tile_plan(126, "Map_20451_2", x, y, 1, 1, bytes([bg1[y][x]]))
        self.assertEqual((same["tag"], same["cells"]), ("none", []))
        back = TE.tile_plan(126, "Map_20451_2", x, y, 1, 1, bytes([bg1[y][x]]), {(126, 0, x, y): True})
        dx, dy = TE.room_offset(126, "Map_20451_2")
        self.assertEqual([c[:3] for c in back["cells"]], [(x + dx, y + dy, (x + dx, y + dy))])


if __name__ == "__main__":
    unittest.main()
