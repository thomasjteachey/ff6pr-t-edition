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
import collections
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


_choice_memo = {}


def _choices(rom):
    """ted_dialog.choice_counts, once per process per ROM (a copy each call: callers may change it)."""
    import hashlib
    import ted_dialog
    key = hashlib.sha1(bytes(rom.data)).hexdigest()
    if key not in _choice_memo:
        _choice_memo[key] = ted_dialog.choice_counts(rom.data)
    return dict(_choice_memo[key])


def load(name="ted"):
    path = EX if name == "ted-ex" else MATO
    rom = E.Rom(path, DIALECT, TABLES, name=name)
    try:
        rom.dialog_choices = _choices(rom)
    except ImportError:
        rom.dialog_choices = None
    return rom


# E.load("ted") / E.load("ted-ex") for the kit's tools: importing this module registers them
E.LOADERS.update({"ted": load, "ted-ex": load})


# --- T-Edition's events as PR scripts (tools/event_translate.py) -----------------------------------
import json  # noqa: E402

OUT = os.path.join(E.P.ROOT, "mods", "TEditionEvents")
ALLOC = os.path.join(E.P.ROOT, "data", "snes_event_alloc_tedition.json")
REPORT = os.path.join(E.P.ROOT, "data", "snes_event_ted_report.json")
KEYS_NAME = "ted_events"


def _json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()
# T-Edition's other Magicite folders (the porter's, ted-maps'): with `siblings` (`build --with-siblings`,
# for when they ship together) a map group's package.json one of them ships is the one this folder's
# copy starts from (one copy per group is read when two folders ship it); off by default, as this folder
# alone would then list rooms whose files it doesn't have (ted-maps' new rooms Map_20071_28/29)
SIBLING_FOLDERS = [os.path.join(E.P.ROOT, "mods", n) for n in ("TEdition", "TEditionMaps")]

# the events built so far: (event address, SNES map, PR script name, PR map, the entity layer whose
# NPCs the scene moves, bits the test entry sets so T-Edition's branch runs)
EVENTS = [
    # South Figaro, the old man who wants wine (map 86, NPC 1): T-Edition's new scene (his grandson,
    # a Yellow Globe, Hermes Shoes) when bit 161 or 1D5 is set, else vanilla's talk (CA/7B7E)
    dict(event=0x35850, map=86, npc=1, name="sc_ted_cd5850", pr_map="Map_20071_23", layer="ev_e_0038",
         test_bits=(0x161,)),
    # README "Ruby's Shine" (Carbuncle, formations 723-725 = the porter's parties 30723-30725): Narshe's
    # two townsfolk arguing about magic (map 20 NPCs 4/5: the PR's walk-ons 88/86 in ev_e_0018), the
    # Elder and Arvis (map 30 NPCs 22/24), the merchant (maps 305/306: one PR room, Map_20330; the
    # second is reported as a conflict and keeps the first's script)
    dict(event=0x349D0, map=20, npc=4),
    dict(event=0x34A10, map=20, npc=5),
    dict(event=0x31580, map=30, npc=22),
    dict(event=0x31540, map=30, npc=24),
    dict(event=0x29CE0, map=305, npc=0),
    dict(event=0x25DD3, map=306, npc=6),
    # README "Showdown at the Coliseum" / the Gilgamesh chain: Gilgamesh in the Colosseum (map 413 NPC 6),
    # a T-Edition NPC the PR has no entity or sprite for: a new NPC on a stand-in look (data/ted_npc_standins.json)
    dict(event=0x34E20, map=413, npc=6),
    # Big Bridge (map 384, tile 71,15): vanilla's staircase switch (the PR's own sc_e_0449 on its switch object),
    # then T-Edition's Gilgamesh and Enkidu (CD/3460: new entities on stand-in looks), and Zozo's new tile (map
    # 221, 38,51: a new step-on trigger). The Phantom Train's (CB/B7EE, map 153) has no PR room yet.
    dict(event=0x1316C, map=384, tile=(71, 15)),
    dict(event=0x333C0, map=221, tile=(38, 51)),
    # Kohlingen's pub-quest entrance (ted-ex's catalog, taken here: one owner per room load script)
    dict(event=0x26F41, map=191, entrance=True),
    # audit E38 "A Priestess's Concern": Figaro's priestess (map 57 NPC 1). T-Edition's CD/5EF0 first: with Sabin
    # here and bit 061 set, her new line and bit 1C3 (Sabin's costume unlock: ENGINE_STORY_BITS, a PR flag listed
    # in ted_flags.json for TedPlugin's dressing room); then vanilla's talk from CA/6C81 (the PR's own sc_e_0028)
    dict(event=0x06C7B, map=57, npc=1),
    # audit E4: Sabin's new lines at Gerad (map 169 NPC 10; its facing switch through vanilla's facing routine)
    dict(event=0x091D0, map=169, npc=10),
    # audit E5: Valigarmanda in the WoR needs Terra (map 35, tile 9,14; also the Test of Strength's last step)
    dict(event=0x2370F, map=35, tile=(9, 14)),
]
SCRIPTS = os.path.join(E.P.ROOT, "data", "snes_event_scripts_tedition.json")
# bits T-Edition (and EX) use for their own meaning, whatever vanilla used them for: they always get a
# flag of T-Edition's own (data/snes_event_alloc_tedition.json), never the tie learned from vanilla.
# EX's boss room: each of the 12 super-boss fights + Omega Weapon sets one of these, and 3.0.7's
# Collection Room (maps 469, 491, 494) reads them; reserved in this order, so the room (this session) and
# EX's fights (ted-ex, mods/TEditionEX) get the same flags from the shared file.
EX_BOSS_BITS = (0x267, 0x268, 0x269, 0x26A, 0x26C, 0x26D, 0x275, 0x2A1, 0x2C1, 0x2C2, 0x000, 0x002)
# Omega Weapon's win: a 13th fight ted-ex added (no SNES bit of its own): a pseudo-bit past the SNES's
# 0-6FF, so it has a key in the allocation file (ScenarioFlag4 17)
EX_OMEGA_BIT = 0x7F0
# vanilla story bits with no PR tie that only T-Edition's own event code (CD/0000 on) sets: it reuses them, so they get
# T-Edition's own flags (11-21 count: their setters are all in T-Edition's code, none in vanilla's CA-CC)
TED_REUSED_BITS = (0x087, 0x0BC, 0x174, 0x188, 0x238, 0x24E, 0x2A0, 0x2B0)
OWN_BITS = frozenset(EX_BOSS_BITS + (EX_OMEGA_BIT,) + TED_REUSED_BITS)
# script.csv rows by who makes the scripts (the events are split three ways, data/snes_event_ted_catalog.json
# "owner"): this session's events on vanilla maps, ted-maps' on T-Edition's new maps, ted-ex's pub quests
# (EX's own scenes: 9700-9715); 9801+: the porter's boxes, 9901+: merchants. Each owner keeps its own ids file.
SCRIPT_ID_RANGES = {
    "ted-events": list(range(9500, 9600)) + list(range(11000, 12000)),
    "ted-maps": list(range(9600, 9700)) + list(range(10000, 11000)),
    "ted-ex": list(range(9716, 9800)) + list(range(12000, 12500)) + list(range(13000, 14000)),
}
SCRIPT_IDS = SCRIPT_ID_RANGES["ted-events"]
EX_SCRIPT_IDS = range(9700, 9800)


_overrides = None


GEM_BOX = 270            # T-Edition: field command 80 with item FF gives this (ted-monsters)


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

    def __init__(self, rom, prefix="TED"):
        import ted_dialog as D
        self.D, self.d, self.prefix = D, rom.data, prefix      # EX's own tables: Texts(load("ted-ex"), "TEDX")
        self.mes, self.cha = {}, {}

    def keys(self, key):
        D, d = self.D, self.d
        ee = isinstance(key, tuple)
        n = key[1] if ee else key
        f = D.file_of(d, D.PTRS2 if ee else D.PTRS, n)
        base = "%s_%s%04d" % (self.prefix, "E" if ee else "D", n)
        text = D.text(d, f, tags=True)
        body, choices = [], []
        for line in text.split("\n"):
            # ">" is only ever the choice code (15): "> Yes", " >  The Chaotic", two on one line
            # ">  (Left)    >  (Right)"; text before the first one stays in the message
            if ">" in line:
                head, *opts = line.split(">")
                if head.strip():
                    body.append(head.rstrip())
                choices.extend(o.strip() for o in opts if o.strip())
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

        own_bits = OWN_BITS

        def untied(self, bit):
            """A vanilla bit with no PR flag learned for it, not one T-Edition took for its own, and not
            one already holding a flag in the shared file (earlier builds' flags stay as they were)."""
            import event_translate as T
            return (bit not in self.own_bits and bit in vanilla_bits() and T.maps()["flags"].get(bit) is None
                    and bit not in T.SCRATCH and bit not in T.ENGINE_BITS and bit not in T.CHAR_BITS
                    and bit not in (self.alloc.table if self.alloc is not None else ()))

        case_kind = None
        cmp_state = None     # after a compare: (category, index, value) its result test reads (cond)
        # the case word's loads the PR can test per character: DE (the active party) -> BranchByCharacter scope 0;
        # the recruited / available / any-party loads -> scope 1 (as the PR's "who's here at all" checks)
        CASE_SCOPE = {"case_party": 0, "case_created": 1, "case_recruited": 1, "case_available": 1, "case_parties": 1}

        def _instr_bits(self, ins, sub, last):
            if ins.name == "call" and ins.args.get("event") in facing_routines():
                # vanilla's "copy the facing into the case bits" (1B0-1B3 -> 1A0-1A3, FACING_PATTERN): nothing to run in
                # the PR; the case tests / switch that follow read the party's facing (cond, below)
                self.case_kind = "facing"
                self.done["flow"] += 1
                self.report[("flow", "facing -> case bits")] += 1
                return [], True
            if ins.name == "if_bit1E50_clear" and chest_flag(0x80 + ins.args["bit"]) is not None:
                # 5B b: "chest 128 + b not opened" (7E/1E40+ are the chest bits) -> a Branch on that chest's PR treasure
                # flag (ted-maps' new chests: data/ted_maps.json chest "bit" -> "flag_id")
                import event_translate as T
                cat, idx = chest_flag(0x80 + ins.args["bit"])
                tgt = next(x for k, x in ins.targets if k == "cond")
                self.done["flow"] += 1
                self.report[("flow", "chest bit -> treasure flag")] += 1
                return [T.op("Branch", i=[idx, 0, "@L_%06X" % tgt], s=[cat, T.EQ, "imm"],
                             comment="SNES 5B: chest bit %d" % (0x80 + ins.args["bit"]))], True
            if ins.name == "switch" and (self.case_kind == "facing" or self.case_kind in self.CASE_SCOPE):
                # BE: the first case whose case bit is set -> the facing (up/right/down/left: BranchByPlayerDirection's
                # four targets) or the character (BranchByCharacter per case, in order)
                import event_translate as T
                self.done["flow"] += 1
                self.report[("flow", "switch on " + ("facing" if self.case_kind == "facing" else "party"))] += 1
                cont = "sw_%06X" % ins.off
                if self.case_kind == "facing":
                    first = {}
                    for k, tgt in ins.args["cases"]:
                        if k < 4:
                            first.setdefault(k, tgt)
                    return [T.op("BranchByPlayerDirection", i=["@L_%06X" % first[d] if d in first else "@" + cont
                                                               for d in range(4)]), T.lab(cont)], True
                scope = self.CASE_SCOPE[self.case_kind]
                return [T.op("BranchByCharacter", i=[k + 1, 0, scope, "@L_%06X" % tgt], comment="SNES BE case %d" % k)
                        for k, tgt in ins.args["cases"] if k < 14], True
            if ins.name in ("tiles_set", "tiles_set_later", "tiles_refresh") and self.pr_map:
                # the PR changes map tiles only through regions its maps carry (TileAnimRegion objects, played
                # by CueAnim: the Big Bridge's staircase): a change over such a region cues it; 75 (redraw) needs
                # nothing; any other change -> TedPlugin's TED:tiles (copies each changed cell from a cell of the
                # same PR map that shows the new look; on passability changes the cell's PR collision too:
                # tile_plan), or nothing when the PR map already shows the change
                import event_translate as T
                if ins.name == "tiles_refresh":
                    self.done["map"] += 1
                    self.report[("map", "tiles redraw")] += 1
                    return [], True
                a_ = ins.args
                m, pr = self.snes_map, self.pr_map      # after a map load: a child translator on that map
                off = room_offset(m, pr) if m is not None else None
                px, py = (a_["x"] + off[0], (a_["y"] & 0x3F) + off[1]) if off else (a_["x"], a_["y"] & 0x3F)
                ents = tile_regions(pr, (px, py, max(1, a_["w"]), max(1, a_["h"])))
                if ents:
                    self.done["map"] += 1
                    self.report[("map", "tiles -> CueAnim")] += 1
                    return self.puppet_ops(ents, [[T.op("CueAnim", kind=2)] for _ in ents]), True
                if m is not None:
                    p = tile_plan(m, pr, a_["x"], a_["y"], a_["w"], a_["h"], bytes(ins.raw[5:]), tile_writes(self.prog))
                    if p["tag"] == "none":
                        self.done["map"] += 1
                        self.report[("map", "tiles: the PR map shows it")] += 1
                        return [], True
                    if p["cells"]:
                        self.done["map"] += 1
                        self.report[("map", "tiles -> TED:tiles " + p["tag"])] += 1
                        return [T.op("SysCall", s=[tiles_syscall(p["cells"])],
                                     comment="SNES %02X %s on map %d" % (ins.op, p["tag"], m))], True
            if ins.name in ("word_set", "word_add", "word_sub", "word_cmp") and ins.args["word"] in WORD_GLOBALS:
                # vanilla's word commands (E8-EB on 7E/1FC2+, words 0 1 5 6 7) -> the PR's ScenarioVariable
                # WORD_GLOBALS[n] (Calc); a compare leaves its operands for the result test (cond)
                import event_translate as T
                idx, v = WORD_GLOBALS[ins.args["word"]], ins.args["value"]
                self.done["flag"] += 1
                self.report[("flag", "word -> ScenarioVariable")] += 1
                if ins.name == "word_cmp":
                    self.case_kind, self.cmp_state = "cmp", ("ScenarioVariable", idx, v)
                    return [], True
                sym = {"word_set": "←", "word_add": "＋", "word_sub": "－"}[ins.name]
                return [T.op("Calc", i=[idx, v], s=["ScenarioVariable", sym, "imm"],
                             comment="SNES %s word %d %d" % (ins.name, ins.args["word"], v))], True
            if ins.name == "word1DD0_set" and VELDT_BITS[0] <= 0x1DD0 + 2 * ins.args["word"] + 1 \
                    and 0x1DD0 + 2 * ins.args["word"] < VELDT_BITS[1]:
                # 83 into 7E/1DDD-1E1C (the Veldt's "formations met" bits, one per formation): Gau's father opening every
                # Veldt formation (CB/681E -> CD/C113-C193, E32) -> TedPlugin's TED:veldt_open with those formations' PR parties
                import event_translate as T
                parties = veldt_parties(self.rom.data, ins.args["word"], ins.args["value"])
                self.done["flag"] += 1
                self.report[("flag", "Veldt formations -> TED:veldt_open")] += 1
                if not parties:
                    return [], True
                return [T.op("SysCall", s=["TED:veldt_open " + " ".join(map(str, parties))],
                             comment="SNES 83 %d %04X" % (ins.args["word"], ins.args["value"]))], True
            if ins.name.startswith("cmp_") or ins.name in ("word1DD0_set", "word1E40_set"):
                # T-Edition's compares of its RAM areas (67/68/69/6D/6E/6F/A4/FC: 1E70 counters, 1600 characters,
                # 1300...) and its word sets (83, ED) -> TedPlugin: TED:cmp writes equal / greater / less to map
                # variables 5 / 6 / 7 (the case bits 1A0 / 1A1 / 1A2 the next test reads); TED:set stores the word
                import event_translate as T
                a_ = ins.args
                self.done["flag"] += 1
                if ins.name.startswith("cmp_"):
                    self.report[("flag", "compare -> TED:cmp")] += 1
                    self.case_kind, self.cmp_state = "cmp", ("MapLocalVariable", None, None)
                    mask = CMP_MASKS.get((ins.name[4:], a_["word"]))
                    return [T.op("SysCall", s=["TED:cmp %s %d %d" % (ins.name[4:], a_["word"], a_["value"])
                                               + (" 0x%X" % mask if mask else "")],
                                 comment="SNES %02X" % ins.op)], True
                self.report[("flag", "word set -> TED:set")] += 1
                return [T.op("SysCall", s=["TED:set %s %d %d" % (ins.name[4:8], a_["word"], a_["value"])],
                             comment="SNES %02X" % ins.op)], True
            if ins.name in ("battle_bit_set", "battle_bit_clear", "if_battle_bit_clear") and \
                    ins.args["bit"] not in VANILLA_BATTLE_BITS:
                # T-Edition's own battle bits (B7-B9 on $1DC9+: 01-3E, 69-6F): story flags its events set and
                # test (the inn dreams' chapters), saved like event bits -> PR flags (allocator keys 1000 + bit, port_ai's)
                import event_translate as T
                cat, idx = self.flag(BATTLE_KEY + ins.args["bit"])
                note = "SNES battle bit %02X" % ins.args["bit"]
                self.done["flag"] += 1
                self.report[("flag", "battle bit -> flag")] += 1
                if ins.name == "if_battle_bit_clear":
                    tgt = next(t for kk, t in ins.targets if kk == "cond")
                    return [T.op("Branch", i=[idx, 0, "@L_%06X" % tgt], s=[cat, T.EQ, "imm"], comment=note)], True
                return [T.op("SetFlag" if ins.name == "battle_bit_set" else "ResetFlag", i=[idx], s=[cat],
                             comment=note)], True
            if ins.name == "if_bit1850_clear" and ins.args["bit"] & 7 != 6 and ins.args["bit"] >> 3 < 14:
                # A5's other bits (party number 0-2, battle order 3-4, back row 5): TedPlugin's TED:roster reads the
                # SNES-equivalent bit from the PR's party into map variable 0; clear -> the jump
                import event_translate as T
                c, k = ins.args["bit"] >> 3, ins.args["bit"] & 7
                tgt = next(t for kk, t in ins.targets if kk == "cond")
                self.done["flow"] += 1
                self.report[("flow", "A5 roster bit")] += 1
                return [T.op("SysCall", s=["TED:roster %d %d 0" % (c, k)], comment="SNES A5 %02X" % ins.args["bit"]),
                        T.op("Branch", i=[0, 0, "@L_%06X" % tgt], s=["MapLocalVariable", T.EQ, "imm"])], True
            if ins.name == "party_active" and 1 <= ins.args["party"] <= 3:
                # 46 n: party n takes over (multi-party scenes) -> the PR's ChangePartySlot [n, 1, 0] (its form where
                # paired vanilla scenes keep the switch)
                import event_translate as T
                self.done["party"] += 1
                self.report[("party", "party switch")] += 1
                return [T.op("ChangePartySlot", i=[ins.args["party"], 1, 0, 0], comment="SNES 46 %02X" % ins.args["party"])], True
            if ins.name == "if_bit1850_clear" and ins.args["bit"] & 7 == 6 and ins.args["bit"] >> 3 < 14:
                # T-Edition's A5: "if bit k of $1850 + c is clear". Bit 6 = character c is in a party (FF6's
                # $1850: party 0-2, battle order 3-4, row 5, in a party 6) -> the PR's BranchByCharacter (not here,
                # any party). The order bits have no PR form: stubs.
                import event_translate as T
                c = ins.args["bit"] >> 3
                tgt = next(t for k, t in ins.targets if k == "cond")
                self.done["flow"] += 1
                self.report[("flow", "A5 in a party")] += 1
                return [T.op("BranchByCharacter", i=[c + 1, 1, 1, "@L_%06X" % tgt],
                             comment="SNES A5 %02X: character %d in no party" % (ins.args["bit"], c))], True
            if ins.name == "item_add" and ins.args["item"] == 0xFF:
                # T-Edition's 80 FF gives the Gem Box (item 270, its second item bank: 4E/0C70), not nothing
                import idmap
                import event_translate as T
                try:
                    cid = idmap.item_content(GEM_BOX)
                except KeyError:
                    cid = 0
                if not cid:
                    return self.left(ins, "Gem Box (item 270) has no PR row yet")
                self.done[ins.cls] += 1
                self.report[(ins.cls, "Gem Box")] += 1
                return [T.op("GetItem", i=[cid, 1], comment="SNES 80 FF: T-Edition's Gem Box (item 270)")], True
            if ins.name == "status_remove":
                # 88 <char> <statuses>: the PR's own cure, RemoveCondition [0, 0, 0, 0] (its form in 223 vanilla
                # scripts, next to RecoveryHP/MP: the whole party's statuses)
                import event_translate as T
                self.done[ins.cls] += 1
                self.report[(ins.cls, "status cure")] += 1
                return [T.op("RemoveCondition", i=[0, 0, 0, 0],
                             comment="SNES 88 %s" % ins.raw[1:].hex(" ").upper())], True
            if ins.name in self.CASE_SCOPE or ins.name == "case_leader":
                self.case_kind = ins.name
                self.done[ins.cls] += 1
                self.report[(ins.cls, "case load")] += 1
                return [], True
            # setting a vanilla bit the PR has no flag for: left as a stub (a made-up flag would be read
            # by nothing of the PR's), counted, until event_translate learns its tie
            if ins.name in ("bit_set", "bit_clear") and self.untied(ins.args["bit"][0])                     and NPC_BITS <= ins.args["bit"][0] < 0x700 and self.snes_map is not None:
                # a vanilla NPC's show bit with no PR flag: what the scene means is "this NPC appears /
                # goes": Show / Hide its PR entity in this room (the PR keeps NPC visibility in entity layers)
                import event_translate as T
                bit, on = ins.args["bit"]
                ents = [e for n, rec in sorted(npc_records(self.snes_map).items())
                        if NPC_BITS + rec["show_bit"] == bit for e in [self.npc_entity(n)] if e is not None]
                if ents:
                    self.done["object"] += 1
                    self.report[("object", "NPC show bit -> %s" % ("Show" if on else "Hide"))] += 1
                    return self.puppet_ops(ents, [[T.op("Show" if on else "Hide", kind=2)] for _ in ents]), True
                # no NPC of this room shows by it (a scene's placeholder bit, 3FE): nothing to do in the PR
                self.done["flag"] += 1
                self.report[("flag", "NPC show bit, no NPC here")] += 1
                return [], True
            if ins.name in ("bit_set", "bit_clear") and 0x1B0 <= ins.args["bit"][0] < 0x1D0                     and ins.args["bit"][0] != 0x1BE and ins.args["bit"][0] not in self.story_engine_bits:
                # the field engine's own state (1CC: temporary song override, 1CE: party switching, 1C1/1C2:
                # sprint / menu off...): the PR keeps none of it; nothing to do
                self.done["flag"] += 1
                self.report[("flag", "engine bit, nothing in the PR")] += 1
                return [], True
            if ins.name in ("bit_set", "bit_clear") and self.untied(ins.args["bit"][0]):
                return self.left(ins, "vanilla bit %03X, no PR tie" % ins.args["bit"][0])
            return super().instr(ins, sub, last)

        def cond(self, ins):
            # case-word bits (1A0 + c after a party load): "character c is here" -> the PR's BranchByCharacter
            import copy
            import event_translate as T
            if self.case_kind == "case_leader" and any(0x1A0 <= b < 0x1AE for b, _ in ins.args["bits"]):
                # after E2 (the party's leader): "the leader is c" -> the PR's BranchByLeader [c+1, target]
                lead = [(b, w) for b, w in ins.args["bits"] if 0x1A0 <= b < 0x1AE]
                rest = [(b, w) for b, w in ins.args["bits"] if (b, w) not in lead]
                target = "@L_%06X" % ins.args["event"]
                self.done["flow"] += 1
                self.report[("flow", "leader check")] += 1
                out = []
                if ins.op >= 0xC8:                      # any
                    for k, (b, w) in enumerate(lead):
                        if w:
                            out.append(T.op("BranchByLeader", i=[b - 0x1A0 + 1, target]))
                        else:
                            other = "lead_%06X_%d" % (ins.off, k)
                            out += [T.op("BranchByLeader", i=[b - 0x1A0 + 1, "@" + other]), T.op("Jump", i=[target]),
                                    T.lab(other)]
                    if rest:
                        ins2 = copy.copy(ins)
                        ins2.args = dict(ins.args, bits=rest)
                        out += self.cond(ins2)
                    return out
                skip = "skip_%06X" % ins.off             # all
                for k, (b, w) in enumerate(lead):
                    if w:
                        ok_ = "lead_%06X_%d" % (ins.off, k)
                        out += [T.op("BranchByLeader", i=[b - 0x1A0 + 1, "@" + ok_]), T.op("Jump", i=["@" + skip]),
                                T.lab(ok_)]
                    else:
                        out.append(T.op("BranchByLeader", i=[b - 0x1A0 + 1, "@" + skip]))
                if rest:
                    ins2 = copy.copy(ins)
                    ins2.args = dict(ins.args, bits=rest)
                    out += self.cond(ins2)
                else:
                    out.append(T.op("Jump", i=[target]))
                return out + [T.lab(skip)]
            def facing_of(b):
                if 0x1B0 <= b <= 0x1B3:                 # the engine's "party faces up / right / down / left" (C0/BA80)
                    return b - 0x1B0
                if self.case_kind == "facing" and 0x1A0 <= b <= 0x1A3:     # copied to the case bits (facing routine)
                    return b - 0x1A0
                return None
            facing = [(facing_of(b), w) for b, w in ins.args["bits"] if facing_of(b) is not None]
            if facing:
                # the facing terms decide per direction -> BranchByPlayerDirection [up, right, down, left]; other bits
                # are tested after it as usual
                rest = [(b, w) for b, w in ins.args["bits"] if facing_of(b) is None]
                target = "@L_%06X" % ins.args["event"]
                self.done["flow"] += 1
                self.report[("flow", "facing test")] += 1
                if ins.op >= 0xC8:                      # any
                    dirs = {d for d in range(4) if any((d == k) == w for k, w in facing)}
                    cont = "dir_%06X" % ins.off
                    out = [T.op("BranchByPlayerDirection", i=[target if d in dirs else "@" + cont for d in range(4)]),
                           T.lab(cont)]
                    if rest:
                        ins2 = copy.copy(ins)
                        ins2.args = dict(ins.args, bits=rest)
                        out += self.cond(ins2)
                    return out
                dirs = {d for d in range(4) if all((d == k) == w for k, w in facing)}
                ok_, skip = "dirok_%06X" % ins.off, "skip_%06X" % ins.off
                out = [T.op("BranchByPlayerDirection", i=["@" + (ok_ if d in dirs else skip) for d in range(4)]),
                       T.lab(ok_)]
                if rest:
                    ins2 = copy.copy(ins)
                    ins2.args = dict(ins.args, bits=rest)
                    out += self.cond(ins2)
                else:
                    out.append(T.op("Jump", i=[target]))
                return out + [T.lab(skip)]
            if self.case_kind == "cmp" and self.cmp_state and any(0x1A0 <= b <= 0x1A2 for b, _ in ins.args["bits"]):
                # a compare's result (1A0 equal, 1A1 greater, 1A2 less: vanilla's pairs, e.g. Cid's thresholds on
                # 1A1 and CB/70C7's "EB 07 21" as the PR's "< 22") -> a Branch on the compared ScenarioVariable, or on
                # TED:cmp's map variables 5/6/7
                cat, idx, val = self.cmp_state
                target = "@L_%06X" % ins.args["event"]
                terms = [(b, w) for b, w in ins.args["bits"] if 0x1A0 <= b <= 0x1A2]
                rest = [(b, w) for b, w in ins.args["bits"] if (b, w) not in terms]
                syms = {0x1A0: ("＝", "≠"), 0x1A1: ("＞", "≦"), 0x1A2: ("＜", "≧")}
                flip = {"＝": "≠", "≠": "＝", "＞": "≦", "≦": "＞", "＜": "≧", "≧": "＜"}

                def branch(b, w, to, negate=False):
                    if cat == "ScenarioVariable":
                        sym = syms[b][0 if w else 1]
                        return T.op("Branch", i=[idx, val, to], s=[cat, flip[sym] if negate else sym, "imm"],
                                    comment="SNES compare bit %03X" % b)
                    return T.op("Branch", i=[5 + b - 0x1A0, (1 if w else 0) ^ int(negate), to], s=[cat, T.EQ, "imm"],
                                comment="SNES compare bit %03X (TED:cmp)" % b)
                self.done["flow"] += 1
                self.report[("flow", "compare result")] += 1
                if ins.op >= 0xC8:                      # any of them
                    out = [branch(b, w, target) for b, w in terms]
                    if rest:
                        ins2 = copy.copy(ins)
                        ins2.args = dict(ins.args, bits=rest)
                        out += self.cond(ins2)
                    return out
                skip = "skip_%06X" % ins.off             # all of them: a failing one skips the jump
                out = [branch(b, w, "@" + skip, negate=True) for b, w in terms]
                if rest:
                    ins2 = copy.copy(ins)
                    ins2.args = dict(ins.args, bits=rest)
                    out += self.cond(ins2)
                else:
                    out.append(T.op("Jump", i=[target]))
                return out + [T.lab(skip)]
            case = [(b, w) for b, w in ins.args["bits"]
                    if 0x1A0 <= b < 0x1AE and self.case_kind in self.CASE_SCOPE]
            if case:
                scope = self.CASE_SCOPE[self.case_kind]
                target = "@L_%06X" % ins.args["event"]
                rest = [(b, w) for b, w in ins.args["bits"] if (b, w) not in case]
                self.done["flow"] += 1
                self.report[("flow", "party check")] += 1
                char = lambda b: b - 0x1A0 + 1          # the PR's character ids: SNES id + 1
                if ins.op >= 0xC8:                      # any of them
                    out = [T.op("BranchByCharacter", i=[char(b), 0 if w else 1, scope, target],
                                comment="SNES %s bit %03X" % (self.case_kind, b)) for b, w in case]
                    if rest:
                        ins2 = copy.copy(ins)
                        ins2.args = dict(ins.args, bits=rest)
                        out += self.cond(ins2)
                    return out
                skip = "skip_%06X" % ins.off             # all of them: any failing test skips the jump
                out = [T.op("BranchByCharacter", i=[char(b), 1 if w else 0, scope, "@" + skip],
                            comment="SNES %s bit %03X" % (self.case_kind, b)) for b, w in case]
                if rest:
                    ins2 = copy.copy(ins)
                    ins2.args = dict(ins.args, bits=rest)
                    out += self.cond(ins2)
                else:
                    out.append(T.op("Jump", i=[target]))
                return out + [T.lab(skip)]
            bits = ins.args["bits"]
            # a test of an untied vanilla bit: dropped from the condition like the engine's bits (an "all"
            # takes it as met, an "any" as not met), noted as a stub
            gone = [b for b, _ in bits if self.untied(b)]
            if not gone:
                return super().cond(ins)
            self.stubs["flow"] += 1
            self.report[("flow", "stub:untied_bit")] += 1
            out = [T.op("SysCall", s=["SNES:untied_bit"], comment="%s %s: vanilla bits %s have no PR tie" % (
                E.fmt(ins.off), ins.raw.hex(" ").upper(), " ".join("%03X" % b for b in gone)))]
            kept = [(b, w) for b, w in bits if b not in gone]
            if kept:
                ins2 = copy.copy(ins)
                ins2.args = dict(ins.args, bits=kept)
                return out + super().cond(ins2)
            if ins.op < 0xC8:                  # "all" of nothing left: met
                out.append(T.op("Jump", i=["@L_%06X" % ins.args["event"]]))
            return out

        def dialog(self, key):
            return self.texts.keys(key)

        created = None       # {(PR map, SNES map, NPC): entity id} of NPC entities a build added

        def shop_ops(self, shop):
            # 9B <shop>: the PR's product group for that shop (the porter's match), opened by TedPlugin
            groups = shop_groups().get(shop)
            if not groups:
                return None
            import event_translate as T
            return [T.op("SysCall", s=["TED:shop %d" % groups[0]], comment="SNES shop %d" % shop)]

        def place(self, m, x, y):
            # T-Edition's own maps (415+): ted-maps' rooms and arrival points (data/ted_maps.json)
            if m >= NEW_MAPS - 1:
                import ted_maps
                r = ted_maps.arrival(m, x, y)
                if r:
                    return tuple(r)
            r = super().place(m, x, y)
            import event_translate as T
            if r and r[1] not in T.map_ids()[0]:       # a PR map that doesn't exist (a guessed room name)
                return None
            return r

        def npc_entity(self, n):
            e = self.created.get((self.pr_map, self.snes_map, n)) if self.created else None
            return e if e is not None else super().npc_entity(n)

        # T-Edition's 76/9E/9F play from its second sound driver (bank 43); F0/EF/F1 from C5, whose
        # slots 25-51 aren't all vanilla's songs any more: both through data/ted_songs.json
        song_commands = frozenset(("ted_song", "ted_song_volume", "ted_song_fade_in"))
        # engine-range bits only T-Edition's events touch (vanilla's never do): its own story flags (ENGINE_STORY_BITS)
        story_engine_bits = frozenset(ENGINE_STORY_BITS)

        def song_bgm(self, song, command):
            """Vanilla's songs: their PR tracks (data/ted_songs.json). T-Edition's own: the music pack's
            ids (ted/MEDIA_PLAN.md: ted_music.py's bgm.json): 1000 + song on the main driver, 1256 + song on
            the second (its fanfares and inn jingles). Silence and vanilla's sound-like songs: None."""
            import ted_songs
            second = command.startswith("ted_")
            if command == "ted_song":
                song &= 0x7F                       # 9E: AND #$7F, as F0
            b = ted_songs.pr_bgm(song, second=second)
            if b is not None:
                return b
            d = ted_songs.load()
            if song in d["second_new" if second else "new"]:
                return (1256 if second else 1000) + song
            return None

        vanilla_at = None    # {SNES address: PR script}: from there on the code is vanilla's, which that PR script does

        def instr(self, ins, sub, last):
            if ins.name == "sound" and T_maps_se(ins.args["sound"]) is None and ted_se(ins.args["sound"]) is not None:
                import event_translate as T
                self.done[ins.cls] += 1
                self.report[(ins.cls, "sound (ted_se_ties)")] += 1
                return [T.op("PlaySE", i=[ted_se(ins.args["sound"]), 1],
                             comment="SNES sound %02X (data/ted_se_ties.json)" % ins.args["sound"])], True
            if self.vanilla_at and ins.off in self.vanilla_at:
                import event_translate as T
                if not hasattr(self, "_vanilla_labels"):
                    self._vanilla_labels = {}
                if ins.off not in self._vanilla_labels:
                    self._vanilla_labels[ins.off] = self.graft(self.vanilla_at[ins.off])
                self.done["flow"] += 1
                self.report[("flow", "vanilla code: the PR's script")] += 1
                return [T.op("Jump", i=["@" + self._vanilla_labels[ins.off]],
                             comment="vanilla's code from %s: the PR's own script" % E.fmt(ins.off))], False
            if ins.name in ("obj_graphics", "obj_palette") and ins.args["obj"] < 14:
                # a character's look: T-Edition's costumes (the dressing room's 4 per character) are a
                # TedPlugin call, TED:costume <char> <k> (bc-sprites' data/ted_costume_art.json); the
                # palette that follows comes with the art
                k = costume(ins.args["obj"], ins.args["gfx"]) if ins.name == "obj_graphics" else None
                import event_translate as T
                if ins.name == "obj_palette" and costume(ins.args["obj"], None, palette=ins.args["pal"]) is not None:
                    self.done[ins.cls] += 1
                    self.report[(ins.cls, "costume palette")] += 1
                    return [], True
                if k is not None:
                    self.done[ins.cls] += 1
                    self.report[(ins.cls, "costume")] += 1
                    return [T.op("SysCall", s=["TED:costume %d %d" % (ins.args["obj"], k)],
                                 comment="SNES 37 %02X %02X" % (ins.args["obj"], ins.args["gfx"]))], True
            if ins.name in self.song_commands:
                # the second driver's songs are jingles over the map's music: the PR's own pattern is
                # PauseBGM, PlayBGM <jingle>, then ReplayBgm (SNES F3) to bring the music back
                song = ins.args["song"] & (0x7F if ins.name == "ted_song" else 0xFF)
                b = self.song_bgm(ins.args["song"], ins.name)
                if b is None:
                    return self.left(ins, "song not tied")
                import event_translate as T
                self.done[ins.cls] += 1
                self.report[(ins.cls, "jingle")] += 1
                return [T.op("PauseBGM", i=[0, 1]), T.op("PlayBGM", i=[b, 1], comment="SNES second-driver song %d" % song)], True
            return self._instr_bits(ins, sub, last)

        def battle_party(self, pack):
            """T-Edition's pack -> (formation, PR party): a formation that is a byte copy of a vanilla
            one (T-Edition moved 21 of vanilla's to 576+: 576 = vanilla 469, 600 = the empty scripted
            battle 504, 601 = 505's Kefka) fights vanilla's own PR party (its battle script and look),
            the one the same pack held in vanilla when that matches; a new formation (576+, or holding
            monsters 384-511; EX's 768-792) the porter's party (port_encounters.first_party_id: 2000 + f, 30000 + f
            from 600, ted-monsters); any other the party of its number (idmap.party). None: an empty
            formation with no vanilla twin."""
            import idmap
            import port_encounters as PE
            import profile_tedition as PT
            f = self.pack_formation(pack)
            if f is None:
                return f, None
            if f >= 768:                           # EX's bosses (768-792): the porter's 30000 + f
                return f, PE.first_party_id(f)
            raw = _formation(self.rom.data, PT.FORMATIONS, f)
            mons = PT.formation_monsters(self.rom.data, PT.FORMATIONS, f)
            new = f >= 576 or any(m >= 384 for m in mons)
            if not new:
                return f, idmap.party(f)
            twins = _vanilla_twins().get(raw, [])
            if twins:
                g = _vanilla_pack(pack)
                g = g if g in twins else twins[0]
                self.report[("battle", "vanilla twin")] += 1
                return f, idmap.party(g)
            if not any(raw[2 + k] != 0xFF or not raw[14] >> k & 1 for k in range(6)):
                return f, None                     # no monsters at all and no vanilla twin
            return f, PE.first_party_id(f)

    return TedTranslator


# per owner (catalog "owner"): its Magicite folder, script.csv ids file, Magicite keys name, report
OWNER_FILES = {
    "ted-events": (OUT, SCRIPTS, KEYS_NAME, REPORT),
    "ted-maps": (os.path.join(E.P.ROOT, "mods", "TEditionMaps"),
                 os.path.join(E.P.ROOT, "data", "snes_event_scripts_ted_maps.json"), "ted_maps_events",
                 os.path.join(E.P.ROOT, "data", "snes_event_ted_report_maps.json")),
    "ted-ex": (os.path.join(E.P.ROOT, "mods", "TEditionQuests"),
               os.path.join(E.P.ROOT, "data", "snes_event_scripts_ted_quests.json"), "ted_quests",
               os.path.join(E.P.ROOT, "data", "snes_event_ted_report_quests.json")),
}


def build(out=None, events=EVENTS, write=True, siblings=False, prog=None, owner="ted-events"):
    """Translates NPC events (EVENTS: dict(event=, map=, npc=), optionally name, pr_map, layer,
    test_bits) into a Magicite folder: each script (and its after-battle / after-warp scripts) in its PR
    map's folder, wired to the NPC's PR entity in each entity layer it stands in (the layer's own PR
    script grafted in for the vanilla talk the event falls back to), a test entry <name>_test, the map
    group's package.json listing them, the story text. `owner` picks the folder, script.csv id range,
    ids file, keys name and report (OWNER_FILES, SCRIPT_ID_RANGES); flags come from the one shared
    allocator (flag_alloc). -> (report, MagiciteMod). `prog`: a walked Program of T-Edition's ROM to
    reuse (tests)."""
    import event_translate as T
    from prkit import data as PD, magicite as MG
    import snes_maps
    import idmap as M
    saved = dict(M.ITEM_OVERRIDES)            # T-Edition's item rows while translating, then back
    M.ITEM_OVERRIDES.clear()
    M.ITEM_OVERRIDES.update(item_overrides())
    try:
        return _build(out or OWNER_FILES[owner][0], events, write, T, MG, PD, snes_maps, siblings, prog, owner)
    finally:
        M.ITEM_OVERRIDES.clear()
        M.ITEM_OVERRIDES.update(saved)


class Session:
    """T-Edition's ROM walked once, with its text, item rows and the shared flag allocator, for
    translating events one at a time (ted-maps' rooms, ted-ex's quests: scripts the caller places and
    wires itself). Use as a context manager: T-Edition's item rows are in idmap while it is open.

        with TE.Session() as s:
            sc, after, t = s.translate(0x34E20, snes_map=413, name="sc_ted_cd4e20", pr_map="Map_...")
        s.texts.mes / s.texts.cha: the story text keys to ship (story_mes_en / story_cha_en)
    """

    def __init__(self, prog=None, persist=True):
        import event_translate as T
        self.T = T
        self.prog = prog or E.Program(load("ted")).walk_all()
        self.rom = self.prog.rom
        self.texts = Texts(self.rom)
        self.alloc = flag_alloc(persist=persist)
        self.Tr = _translator_class()

    def __enter__(self):
        import idmap as M
        self._saved = dict(M.ITEM_OVERRIDES)
        M.ITEM_OVERRIDES.clear()
        M.ITEM_OVERRIDES.update(item_overrides())
        return self

    def __exit__(self, *exc):
        import idmap as M
        M.ITEM_OVERRIDES.clear()
        M.ITEM_OVERRIDES.update(self._saved)

    def translate(self, event, snes_map, name, pr_map=None, layer=None, mode=None, fallbacks=None, preamble=()):
        """One event -> (PR script, [(after-script name, script, PR map or None)], the translator: its
        .stubs / .done counters, .needs_formations). `layer`: the entity layer whose entities the scene's
        NPCs are; `fallbacks`: {SNES call target: PR script} grafted where the event calls vanilla's
        routine; mode "vehicle" for a world-map tile event (default: by map)."""
        mode = mode or ("vehicle" if snes_map in E.WORLD_MAPS else "field")
        t = self.Tr(self.rom, name, snes_map=snes_map, alloc=self.alloc, prog=self.prog, pr_map=pr_map)
        t.texts = self.texts
        if layer:
            t.layers = layer
        for k, v in (fallbacks or {}).items():
            t.fallbacks[k] = v
        sc = t.translate(event, mode, preamble=preamble)
        return sc, list(t.after), t


def _formation(d, base, f):
    return bytes(d[base + 15 * f:base + 15 * f + 15])


_twins = None


def _vanilla_twins():
    """{a vanilla formation's 15 bytes: [vanilla formations with exactly those]} (US ROM)."""
    global _twins
    if _twins is None:
        import prdata as P
        with open(P.VANILLA_ROM, "rb") as fh:
            us = fh.read()
        _twins = {}
        for g in range(576):
            _twins.setdefault(_formation(us, 0x0F6200, g), []).append(g)
    return _twins


def _vanilla_pack(pack):
    """The formation vanilla's event pack held (US ROM, first of its two)."""
    import prdata as P
    with open(P.VANILLA_ROM, "rb") as fh:
        fh.seek(0x0F5000 + 4 * pack)
        b = fh.read(2)
    return (b[0] | b[1] << 8) & 0x7FFF


WOR_FLAG = ("ScenarioFlag2", 41)      # the PR's "after the collapse" (37 map scripts pick their WoR layers by it)
_worlds = None


def snes_world(m):
    """0 (World of Balance), 1 (World of Ruin) or None (both, or neither): the world map whose exits
    lead to SNES map m, following exits room to room (T-Edition's exit tables, ted_maps.TED)."""
    global _worlds
    if _worlds is None:
        import snes_maps
        import ted_maps
        rom = ted_maps.rom()
        seen = {}
        for w in (0, 1):
            todo, got = [w], {w}
            while todo:
                for x in snes_maps.exits(rom, todo.pop(), ted_maps.TED):
                    d = x["dest"]
                    if d not in got and 3 <= d < 0x1FF:
                        got.add(d)
                        todo.append(d)
            for d in got:
                seen.setdefault(d, set()).add(w)
        _worlds = {m_: next(iter(ws)) if len(ws) == 1 else None for m_, ws in seen.items()}
    return _worlds.get(m)


_pr_worlds = None


def pr_world(pr_map):
    """0 (World of Balance), 1 (World of Ruin) or None (both, or not reached): the world map whose
    exits lead to a PR map, following the PR's own exits room to room (snes_maps.pr_links)."""
    global _pr_worlds
    if _pr_worlds is None:
        import snes_maps
        import event_translate as T
        dirs = snes_maps.pr_map_dirs()
        names = T.map_ids()[1]
        seen = {}
        for w, start in ((0, "Map_10010"), (1, "Map_10020")):
            todo, got = [start], {start}
            while todo:
                n = todo.pop()
                if n not in dirs:
                    continue
                for x, y, dest, pt in snes_maps.pr_links(dirs[n])[0]:
                    dn = names.get(dest)
                    if dn and dn not in got and not dn.startswith("Map_100"):
                        got.add(dn)
                        todo.append(dn)
            for n in got:
                seen.setdefault(n, set()).add(w)
        _pr_worlds = {n: next(iter(ws)) if len(ws) == 1 else None for n, ws in seen.items()}
    return _pr_worlds.get(pr_map)


_jp_looks = None


def npc_looks(snes_map, n):
    """The PR looks (asset ids) learned for SNES NPC n of a map: its T-Edition sprite's and the JP
    ROM's sprite for the same NPC (T-Edition repainted some: Narshe's Elder, Tzen's bandit)."""
    import event_translate as T
    import snes_maps
    global _jp_looks
    out = []
    rec = npc_records(snes_map).get(n)
    if rec:
        out += list(T.sprite_assets(load("ted")).get(rec["sprite"], ()))
    jp = E.load("jp")
    if _jp_looks is None:
        _jp_looks = T.sprite_assets(jp)
    try:
        jrec = {x["index"]: x for x in snes_maps.npcs(jp.data, snes_map)}.get(n)      # JP keeps the US tables
    except Exception:
        jrec = None
    if jrec:
        out += list(_jp_looks.get(jrec["sprite"], ()))
    return tuple(dict.fromkeys(out))


def npc_rooms(snes_map, xy, primary=None, looks=()):
    """[(PR room, its tile for the SNES tile xy)]: every PR map of the SNES map that is walkable there,
    has an NPC at that spot and belongs to the SNES map's world (snes_world / pr_world; a map of both
    worlds takes every room); `primary` (or else the room snes_maps.to_pr draws there, when it is of
    the right world) first."""
    import snes_maps
    world = snes_world(snes_map)
    ok_world = lambda room: world is None or pr_world(room) in (None, world)
    out = []
    for mt in [mt for mt in snes_maps.pr_maps(snes_map) if mt.pr in snes_maps.pr_tilemaps()]:
        spot = (xy[0] + mt.dx, xy[1] + mt.dy)
        if mt.pr == primary:
            out.append((mt.pr, spot))
            continue
        if not ok_world(mt.pr):
            continue
        wk = snes_maps.pr_walkable(mt.pr)
        if not any((spot[0] + a, spot[1] + b) in wk for a in (-1, 0, 1) for b in (-1, 0, 1)):
            continue
        if not npc_objects(mt.pr, spot, looks):
            continue
        out.append((mt.pr, spot))
    if primary and not any(r == primary for r, _ in out):
        r = snes_maps.to_pr(snes_map, *xy, pr=primary)
        out.insert(0, (primary, (r[1], r[2]) if r else tuple(xy)))
    drawn_at = (snes_maps.to_pr(snes_map, *xy) or [None])[0]
    first = primary or drawn_at
    out.sort(key=lambda rs: rs[0] != first)
    if not out:
        # no PR NPC at the spot in any room of this world (T-Edition added the NPC, or the PR left it
        # out of this world's copy: Tzen's World of Balance bandit): the room it would stand in
        for mt in [mt for mt in snes_maps.pr_maps(snes_map) if mt.pr in snes_maps.pr_tilemaps()]:
            spot = (xy[0] + mt.dx, xy[1] + mt.dy)
            wk = snes_maps.pr_walkable(mt.pr)
            if ok_world(mt.pr) and any((spot[0] + a, spot[1] + b) in wk for a in (-1, 0, 1) for b in (-1, 0, 1)):
                return [(mt.pr, spot)]
        if drawn_at:
            r = snes_maps.to_pr(snes_map, *xy)
            out = [(r[0], (r[1], r[2]))]
    return out


_jp_prog = None


def ted_part(off, prog=None, mode="field"):
    """Where T-Edition's code at a vanilla entry stops being vanilla's: following both ROMs' code from
    `off` (fall-through; a conditional jump must jump alike), the address of the first instruction whose
    bytes differ from the JP ROM's at the same address -> that address, or None when the whole path is
    the JP ROM's (T-Edition only changed what it calls). For a vanilla event T-Edition changed in place
    (CB/316C: vanilla's staircase switch, then T-Edition's Gilgamesh instead of vanilla's last lines),
    the part before it is the PR's own script's job."""
    global _jp_prog
    if _jp_prog is None:
        _jp_prog = E.Program(E.load("jp")).walk_all()
    prog = prog or E.Program(load("ted")).walk_all()
    a = off
    seen = set()
    while (a, mode) not in seen:
        seen.add((a, mode))
        t, j = prog.code.get((a, mode)), _jp_prog.code.get((a, mode))
        if t is None:
            return None
        if j is None or t.raw != j.raw:
            return a
        if t.flow in ("end", "choice"):
            return None
        a, mode = a + t.size, t.next_mode
    return None


def vanilla_resume(off, prog):
    """For a vanilla event T-Edition changed in place: when only its first instruction differs from the
    JP ROM's (the same command, another target: the Figaro priestess's "if bit 049" now leads to T-Edition's
    costume scene) and the code after it is the JP ROM's, the address after that instruction (the PR's own
    script does the rest); else None."""
    global _jp_prog
    if _jp_prog is None:
        _jp_prog = E.Program(E.load("jp")).walk_all()
    t, j = prog.code.get((off, "field")), _jp_prog.code.get((off, "field"))
    if t is None or j is None or t.raw[:1] != j.raw[:1] or t.size != j.size or t.raw == j.raw:
        return None
    nxt = off + t.size
    if (nxt, "field") not in prog.code:
        return None
    # the rest: the JP ROM's code, but for sounds and lines (a song's mode bit; T-Edition's reworded line:
    # the PR's own line is shown instead)
    a, seen = nxt, set()
    while (a, "field") not in seen:
        seen.add((a, "field"))
        ti, ji = prog.code.get((a, "field")), _jp_prog.code.get((a, "field"))
        if ti is None or ji is None or ti.size != ji.size:
            return None
        if ti.raw != ji.raw and not (ti.cls == ji.cls and ti.cls in ("sound", "dialog")):
            return None
        if ti.flow in ("end", "choice"):
            return nxt
        a += ti.size
    return nxt


_ted_se = None
TED_SE_TIES = os.path.join(E.P.ROOT, "data", "ted_se_ties.json")


def ted_se(sound):
    """A PR SE for an SNES sound the kit's learned ties lack (data/ted_se_ties.json: dialogue-anchored), or None."""
    global _ted_se
    if _ted_se is None:
        import event_translate as T
        _ted_se = {int(k): v for k, v in (T.read_json(TED_SE_TIES)["se"].items() if os.path.exists(TED_SE_TIES) else [])}
    return _ted_se.get(sound)


def T_maps_se(sound):
    import event_translate as T
    return T.maps()["se"].get(sound)


_tile_layers, _tile_models, _mod_tilemaps = {}, {}, None


def mod_tilemaps():
    """{PR map name: tilemap.json} of ted-maps' new rooms (mods/TEditionMaps)."""
    global _mod_tilemaps
    if _mod_tilemaps is None:
        import glob
        _mod_tilemaps = {os.path.basename(os.path.dirname(p)): p for p in glob.glob(os.path.join(
            E.P.ROOT, "mods", "TEditionMaps", "map_*", "Assets", "GameAssets", "Serial", "Res", "Map", "*", "*",
            "tilemap.json"))}
    return _mod_tilemaps


def pr_cells(pr_map):
    """snes_rooms' per-cell rows ((Bottom, Ground, Upper, Ceil refs), collision) of a vanilla PR map or of
    one of ted-maps' new rooms; None when it has no tilemap."""
    import snes_maps as SM
    import snes_rooms as R
    tm = SM.pr_tilemaps()
    added = pr_map not in tm and pr_map in mod_tilemaps()
    if pr_map not in tm and not added:
        return None
    if added:
        tm[pr_map] = mod_tilemaps()[pr_map]
    try:
        return R._cells(pr_map)[0]
    finally:
        if added:
            del tm[pr_map]


def tile_layers(m):
    """(BG1, BG2, (US BG1, US BG2) or None, tile props) of T-Edition map m as its entrance event leaves it;
    the US layouts for a vanilla map (the PR drew those)."""
    if m not in _tile_layers:
        import snes_maps as SM
        import snes_rooms as R
        import ted_maps as TM
        data = TM.rom()
        bg1, bg2, _ = TM.shown_layouts(data, load("ted"), m)
        us = None
        if m < TM.VANILLA_MAPS:
            u = R.vanilla().us
            us = (SM.layout(u, m, 0), SM.layout(u, m, 1))
        _tile_layers[m] = (bg1, bg2, us, SM.tile_props(data, m, TM.TED.props))
    return _tile_layers[m]


def room_offset(m, pr_map):
    """(dx, dy): SNES map m's tile -> PR map pr_map's tile, or None."""
    import snes_maps as SM
    import ted_maps as TM
    if m < TM.VANILLA_MAPS:
        mt = next((mt for mt in SM.pr_maps(m) if mt.pr == pr_map), None)
        if mt:
            return mt.dx, mt.dy
    for r in (TM.table()["maps"].get(str(m)) or {}).get("rooms", []):
        if r["pr_map"] == pr_map:
            return r["dx"], r["dy"]
    return None


def pr_group(pr_map):
    """The Magicite asset group of a vanilla PR map, or of one of ted-maps' new rooms (data/ted_maps.json)."""
    import snes_maps as SM
    import snes_rooms as R
    import ted_maps as TM
    if pr_map in SM.pr_tilemaps():
        return R.group_of(pr_map)
    for rec in TM.table()["maps"].values():
        for r in rec.get("rooms", []):
            if r["pr_map"] == pr_map:
                return r.get("group")
    return None


def _tile_model(m, pr_map, bg1, bg2):
    if (m, pr_map) not in _tile_models:
        import snes_rooms as R
        import ted_maps as TM
        _tile_models[(m, pr_map)] = R.model(TM.rom(), m, TM.TED.props, group=pr_group(pr_map), rows=bg1,
                                            t=TM.TED, rows2=bg2)
    return _tile_models[(m, pr_map)]


_tile_writes = None


def tile_writes(prog=None):
    """{(SNES map, layer, x, y): True if some write there changes the BG1 tile's SNES properties} for every
    T-Edition tile change in the catalog's events (data/snes_event_ted_catalog.json), against the map as its
    entrance event leaves it: the cells a later change may have to put back (tile_plan)."""
    global _tile_writes
    if _tile_writes is None:
        import event_translate as T
        prog = prog or E.Program(load("ted")).walk_all()
        out, seen = {}, set()
        for row in _json(CATALOG):
            m = row["map"]
            if m in E.WORLD_MAPS:
                continue
            for ins in T.scene(prog, E.parse_addr(row["event"]), "field"):
                if ins.op not in (0x73, 0x74) or (ins.off, m) in seen:
                    continue
                seen.add((ins.off, m))
                a, tiles = ins.args, bytes(ins.raw[5:])
                layer, y = a["y"] >> 6, a["y"] & 0x3F
                bg1, bg2, _, props = tile_layers(m)
                L = (bg1, bg2)[layer] if layer < 2 else None
                if not L:
                    continue
                for j in range(a["h"]):
                    for i in range(a["w"]):
                        cx, cy, n = (a["x"] + i) % len(L[0]), (y + j) % len(L), j * a["w"] + i
                        if n >= len(tiles) or L[cy][cx] == tiles[n]:
                            continue
                        k = (m, layer, cx, cy)
                        out[k] = out.get(k, False) or (layer == 0 and props[L[cy][cx]] != props[tiles[n]])
        _tile_writes = out
    return _tile_writes


def tile_plan(m, pr_map, x, y, w, h, tiles, writes=None):
    """T-Edition's tile change (73/74: x, y | layer << 6, w, h, tiles) on SNES map m, drawn on PR map pr_map (a vanilla
    room or one of ted-maps' new ones): the kit's snes_rooms.tile_plan with T-Edition's layouts as its entrance event
    leaves them, vanilla's layouts as what the PR drew (a vanilla map), its model and `writes` (tile_writes(): the cells
    T-Edition's other changes write) -> {"tag", "cells": [(px, py, source, attr)], "why"}."""
    import snes_rooms as R
    off = room_offset(m, pr_map)
    cells = pr_cells(pr_map) if off else None
    if cells is None:
        return {"tag": "no PR tiles", "cells": [], "why": collections.Counter()}
    bg1, bg2, us, props = tile_layers(m)
    mine = {(k[1], k[2], k[3]): v for k, v in (writes or {}).items() if k[0] == m}
    return R.tile_plan(cells, off, bg1, bg2, props, x, y, w, h, tiles, drawn=us,
                       model=lambda: _tile_model(m, pr_map, bg1, bg2), tilesets=R._tilesets_of.get(pr_map), writes=mine)


def ted_flags(alloc):
    """TedPlugin's story flags (ted_flags.json, top level of TEditionEvents -> BepInEx/TEdition): [category, index]
    of the PR flags its rules read. "wor": the World of Ruin has begun; Humbaba's two vanilla bits (I18's WoR prices:
    T-Edition's price code wasn't found, so both); "engine_story_bits": T-Edition's own flags in the engine's range
    (ENGINE_STORY_BITS; 1C3 = Sabin's costume from Figaro's priestess), allocated here so the mapping is stable."""
    import event_translate as T
    ties = T.maps()["flags"]
    return {"about": "ted-events (tools/ted_events.py ted_flags): PR flags [category, index] for TedPlugin's rules",
            "wor": list(WOR_FLAG),
            "humbaba_scared_off": list(ties[0x0BF]),     # SNES 0BF: set after the first WoR Mobliz fight (CC/5035)
            "humbaba_returns": list(ties[0x292]),        # SNES 292: set as he comes back for the last fight (CC/4C07)
            "engine_story_bits": {"%03X" % b: list(alloc.get(b)) for b in ENGINE_STORY_BITS},
            **ngplus_flags(alloc)}


NGPLUS_SET = (0x1B2, 0x1CC, 0x1E3, 0x2E0, 0x2F0, 0x2FE)   # T-Edition's story reset sets these after clearing (C0/DA9C)
NGPLUS_NPC_TABLE = 0x00E0A0                                # its initial NPC show bits (300-6FF), copied to 7E/1EE0


def ngplus_flags(alloc):
    """TedPlugin's TED:ngplus lists, from T-Edition's story reset (the Beginner's House clerk's CB on map 104: C0/DB58 ->
    C0/DA9C clears 7E/1E80-1EDF = event bits 000-2FF, sets NGPLUS_SET, copies the NPC show bits 300-6FF from
    C0/E0A0): "ngplus_clear" / "ngplus_set" = the PR flags those bits are (vanilla's ties and T-Edition's own flags,
    its costume / dream bits included; battle bits aren't touched). Bits with no PR flag (engine bits, characters)
    are left out."""
    import event_translate as T
    import ted_maps as TM
    ties = T.maps()["flags"]
    own = {k: tuple(v) for k, v in {**alloc._disk(), **alloc.table}.items() if k < 0x700}
    flags = lambda b: {f for f in (ties.get(b), own.get(b)) if f}
    want = {b: False for b in range(0x300)}
    want.update({b: True for b in NGPLUS_SET})
    data = TM.rom()
    for i in range(0x80):
        for k in range(8):
            want[0x300 + 8 * i + k] = bool(data[NGPLUS_NPC_TABLE + i] >> k & 1)
    clear, set_ = set(), set()
    for b, on in want.items():
        (set_ if on else clear).update(flags(b))
    clear -= set_
    return {"ngplus_clear": [list(f) for f in sorted(clear)], "ngplus_set": [list(f) for f in sorted(set_)]}


TILE_CELLS = os.path.join(E.P.ROOT, "data", "ted_tile_cells.json")


def tile_cells(path=TILE_CELLS, log=print):
    """TedPlugin's walkability table: {PR map: [[x, y, collision as the map loads], ...]} for every cell a T-Edition
    tile change (any workstream's: the catalog's events) may make walkable or blocked, in every PR room of its SNES
    map (vanilla rooms and ted-maps' new ones). The plugin keeps it per room and TED:tiles' ":attr" updates it.
    Slow (every change planned in every room): `python tools/ted_events.py tilecells [path]`."""
    import event_translate as T
    import snes_maps as SM
    import ted_maps as TM
    prog = E.Program(load("ted")).walk_all()
    writes = tile_writes(prog)
    seen, out, n = set(), collections.defaultdict(dict), 0
    for row in _json(CATALOG):
        m = row["map"]
        if m in E.WORLD_MAPS:
            continue
        rooms = ([mt.pr for mt in SM.pr_maps(m)] if m < TM.VANILLA_MAPS else []) + \
                [r["pr_map"] for r in (TM.table()["maps"].get(str(m)) or {}).get("rooms", [])]
        for ins in T.scene(prog, E.parse_addr(row["event"]), "field"):
            if ins.op not in (0x73, 0x74) or (ins.off, m) in seen:
                continue
            seen.add((ins.off, m))
            a = ins.args
            for pr in dict.fromkeys(rooms):
                p = tile_plan(m, pr, a["x"], a["y"], a["w"], a["h"], bytes(ins.raw[5:]), writes)
                cells = pr_cells(pr) if p["cells"] else None
                for px, py, _, attr in p["cells"]:
                    if attr is not None:
                        out[pr][(px, py)] = cells[py][px][1]
                n += 1
    doc = {pr: [[x, y, c] for (x, y), c in sorted(v.items(), key=lambda kv: (kv[0][1], kv[0][0]))]
           for pr, v in sorted(out.items())}
    T.write_json(path, doc, indent=0)
    log("tile cells: %d plans, %d rooms, %d cells -> %s" % (n, len(doc), sum(len(v) for v in doc.values()), path))
    return doc


VELDT_BITS = (0x1DDD, 0x1E1D)     # 7E/1DDD-1E1C: one bit per formation 0-511 met (the Veldt's Leap draws from them)


def formation_party(data, f):
    """T-Edition formation f -> the PR monster party that fights it, as TedTranslator.battle_party does without a pack:
    EX's (768+) and new formations (576+, or with monsters 384+) the porter's party unless a vanilla formation is
    its byte copy (that one's PR party); others idmap.party. None: an empty formation."""
    import idmap
    import port_encounters as PE
    import profile_tedition as PT
    if f >= 768:
        return PE.first_party_id(f)
    mons = PT.formation_monsters(data, PT.FORMATIONS, f)
    if not (f >= 576 or any(m >= 384 for m in mons)):
        return idmap.party(f)
    raw = _formation(data, PT.FORMATIONS, f)
    twins = _vanilla_twins().get(raw, [])
    if twins:
        return idmap.party(twins[0])
    if not any(raw[2 + k] != 0xFF or not raw[14] >> k & 1 for k in range(6)):
        return None
    return PE.first_party_id(f)


def veldt_parties(data, word, value):
    """The PR parties of the formations an 83 n v write into the Veldt bits turns on (word n = 7E/1DD0 + 2n, low
    byte first)."""
    out = []
    for k in range(16):
        addr = 0x1DD0 + 2 * word + k // 8
        if value >> k & 1 and VELDT_BITS[0] <= addr < VELDT_BITS[1]:
            p = formation_party(data, (addr - VELDT_BITS[0]) * 8 + k % 8)
            if p is not None and p not in out:
                out.append(p)
    return out


# T-Edition events that are vanilla's code with a few changes, ported as edits of the PR's own scripts (shipped under
# their names): "calc" {(ScenarioVariable index, old value): new} on its Calc ops; "branches": T-Edition's tests (SNES
# addresses) put before the PR line "before_line", each to its own translated code, which ends the event
SCRIPT_EDITS = [
    # CA/5366, Cid's fish: each fish raises his health twice as much as vanilla (CA/5390, CA/539C: word 7 +64 / +32
    # for vanilla's +32 / +16; the PR's sc_e_0616 keeps it in ScenarioVariable 2 with +32 / +12 -> 64 / 24)
    dict(event="CA/5366", script="sc_e_0616", pr_map="Map_20291_1", calc={(2, 32): 64, (2, 12): 24}),
    # ... and at "Cid: I'm all better now!" (0x880, the PR's sc_e_0625) T-Edition's CD/4130 (audit E33 "Thoughts and
    # Wishes"): bit 0C1 -> its line D56, 0C9 -> D45 and the scene with Celes and Locke (the Tynar Rouge), 0CD -> D44
    dict(event="CA/5366", script="sc_e_0625", pr_map="Map_20291_1", snes_map=397, before_line="E0616_00_191_a_08",
         branches=(0x34130, 0x34136, 0x3413C)),
]


def script_edit(spec, rom, prog, alloc, Tr, texts):
    """SCRIPT_EDITS entry -> the PR script with T-Edition's changes (a script dict), and the translator's report."""
    import copy
    import event_translate as T
    import pr_script as S
    sc = copy.deepcopy(S.load(spec["script"]))
    t = Tr(rom, spec["script"], snes_map=spec.get("snes_map"), alloc=alloc, prog=prog, pr_map=spec["pr_map"])
    t.texts = texts
    if spec.get("calc"):
        todo = dict(spec["calc"])
        for m in sc["Mnemonics"]:
            o = m.get("operands") or {}
            key = tuple((o.get("iValues") or [0, 0])[:2])
            if m["mnemonic"] == "Calc" and (o.get("sValues") or [""])[0] == "ScenarioVariable" and key in todo:
                o["iValues"][1] = todo.pop(key)
                m["comment"] = "T-Edition: was %d" % key[1]
        if todo:
            raise ValueError("%s: no Calc %s" % (spec["script"], sorted(todo)))
    if not spec.get("branches"):
        return sc, t
    label = t.graft(sc)
    block = next(b for name, b in t.blocks if name == label)
    at = next(i for i, m in enumerate(block) if m["mnemonic"] == "Msg" and m["operands"]["sValues"][0] == spec["before_line"])
    tests = []
    for a in spec["branches"]:
        ins = prog.code[(a, "field")]
        tests += t.cond(ins)
        tgt = next(x for k, x in ins.targets if k == "cond")
        seg = "ted_%06X" % tgt
        t.blocks.append((seg, [T.lab(seg)] + t.body(tgt, "field", sub=False) + [T.op("Exit")]))
    block[at:at] = tests
    return t.assemble(spec["script"], [T.lab("Main"), T.op("Jump", i=["@" + label])], t.blocks), t


_chest_flags = None


def chest_flag(bit):
    """SNES chest bit (7E/1E40 + bit/8) -> the PR treasure flag (category, index) of that chest: ted-maps' chests
    (data/ted_maps.json: "bit" -> "flag_id", T-Edition's new maps' chests 300-369 and the 13 it added on vanilla maps,
    "vanilla_chests", 370-382); None for others."""
    global _chest_flags
    if _chest_flags is None:
        import ted_maps as TM
        doc = TM.table()
        chests = [c for rec in doc["maps"].values() for c in rec.get("chests") or []] + list(doc.get("vanilla_chests") or [])
        _chest_flags = {c["bit"]: c["flag_id"] for c in chests if isinstance(c, dict) and c.get("flag_id") is not None}
    f = _chest_flags.get(bit)
    return None if f is None else ("TreasureFlag%d" % (1 + f // 256), f % 256)


# vanilla's routine copying the party's facing (engine bits 1B0-1B3: up/right/down/left, set from the leader's facing
# when an event starts, C0/BA80) into the case bits 1A0-1A3: T-Edition CA/CA5A, US CA/CA64
FACING_PATTERN = bytes.fromhex("D3A0D3A1D3A2D3A3C0B001")
_facing = None


def facing_routines():
    """Event offsets of T-Edition's copies of the facing routine (FACING_PATTERN)."""
    global _facing
    if _facing is None:
        import re
        d = load("ted").data
        _facing = {m.start() - 0x0A0000 for m in re.finditer(re.escape(FACING_PATTERN), d) if m.start() >= 0x0A0000}
    return _facing


def build_lock(log=print):
    """ted_build's lock (mods/TEdition.building: one writer of T-Edition's folders at a time, so its merge never reads
    a half-written sibling folder); none when this process already holds it."""
    import contextlib
    import ted_build
    try:
        with open(os.path.join(ted_build.LOCK, "owner.txt"), encoding="utf-8") as f:
            if int(f.read().split()[0]) == os.getpid():
                return contextlib.nullcontext()
    except (OSError, ValueError, IndexError):
        pass
    return ted_build._lock(log)


def swap_dir(new, out, tries=40):
    """Puts folder `new` in place of `out` with two renames (out -> out.old, new -> out), retrying while a reader
    holds a file open (Windows refuses the rename then), and deletes the old one."""
    import shutil
    import time
    old = out + ".old"
    if os.path.isdir(old):
        shutil.rmtree(old, ignore_errors=True)
    for k in range(tries):
        try:
            if os.path.isdir(out):
                os.replace(out, old)
            os.replace(new, out)
            break
        except PermissionError:
            if k == tries - 1:
                raise
            time.sleep(0.25)
    shutil.rmtree(old, ignore_errors=True)


def tiles_syscall(cells):
    """TedPlugin's TED:tiles string, one item per cell: "px,py=sx,sy" (copy every tile layer of PR cell
    (sx, sy) as the map loaded), "px,py=#b/g/u/c" (these gids: Bottom, Ground, Upper, Ceil; 0 = none) or
    "px,py=-" (no look), then ":attr" when the cell's collision changes."""
    def look(src):
        if src is None:
            return "-"
        if src[0] == "gids":
            return "#" + "/".join(str(g) for g in src[1])
        return "%d,%d" % src
    return "TED:tiles " + " ".join("%d,%d=%s%s" % (px, py, look(src), "" if attr is None else ":%d" % attr)
                                   for px, py, src, attr in cells)


_tile_regions = {}


def tile_regions(pr_map, rect):
    """The entity ids of the PR room's TileAnimRegion objects (its pre-made tile changes, played by CueAnim)
    that overlap rect (x, y, w, h in the room's tiles)."""
    if pr_map not in _tile_regions:
        import snes_maps
        out = []
        tm = snes_maps.pr_tilemaps().get(pr_map)
        if tm:
            room = os.path.dirname(tm)
            pk = _json(os.path.join(os.path.dirname(room), "package.json"))
            entry = next((m for m in pk["map"] if m["name"] == pr_map), {})
            for nm in [x["name"] for x in entry.get("entity", [])] + ["entity_default"]:
                f = os.path.join(room, nm + ".json")
                if not os.path.exists(f):
                    continue
                for lay in _json(f).get("layers", []):
                    for o in lay.get("objects") or []:
                        if not str(o.get("name", "")).startswith("TileAnimRegion"):
                            continue
                        p = {q["name"]: q["value"] for q in o.get("properties", [])}
                        x0, y0 = o["x"] / 16, o["y"] / 16 - (1 if "gid" in o else 0)
                        out.append((x0, y0, o.get("width", 16) / 16, o.get("height", 16) / 16, p.get("entity_id")))
        _tile_regions[pr_map] = out
    x, y, w, h = rect
    return sorted({e for x0, y0, w0, h0, e in _tile_regions[pr_map]
                   if e and x0 < x + w and x < x0 + w0 and y0 < y + h and y < y0 + h0})


def same_code(prog, t_addr, j_addr, limit=4000):
    """Whether T-Edition's code at t_addr is the JP ROM's code at j_addr, relocated: the same instructions
    with the same arguments, jumps and calls leading to code that matches in turn (any address); lines and
    sounds may differ (T-Edition rewords). Follows both programs in step, up to `limit` instructions."""
    global _jp_prog
    if _jp_prog is None:
        _jp_prog = E.Program(E.load("jp")).walk_all()
    pairs, seen = [(t_addr, j_addr, "field")], {}
    while pairs:
        ta, ja, md = pairs.pop()
        while True:
            if (ta, md) in seen:
                if seen[(ta, md)] != ja:
                    return False
                break
            seen[(ta, md)] = ja
            if len(seen) > limit:
                return False
            ti, ji = prog.code.get((ta, md)), _jp_prog.code.get((ja, md))
            if ti is None or ji is None:
                return ti is None and ji is None
            # a reworded line, another song or jingle, another pose in an object's moves (the same moves otherwise)
            soft = ti.cls == ji.cls and ti.cls in ("dialog", "sound") or                 ti.name == ji.name == "obj" and ti.args.get("obj") == ji.args.get("obj")
            if (ti.name != ji.name and not soft) or ti.size != ji.size or len(ti.targets) != len(ji.targets):
                return False
            if not soft:
                a1 = {k: v for k, v in ti.args.items() if k not in ("event", "events", "targets")}
                a2 = {k: v for k, v in ji.args.items() if k not in ("event", "events", "targets")}
                if a1 != a2:
                    return False
            for (k1, t1), (k2, t2) in zip(ti.targets, ji.targets):
                if k1 != k2:
                    return False
                pairs.append((t1, t2, md))
            if ti.flow in ("end", "choice"):
                break
            ta, ja, md = ta + ti.size, ja + ji.size, ti.next_mode
    return True


def vanilla_copy(off, vanilla, prog, mode="field"):
    """The first address in T-Edition's scene from `off` (not `off` itself) where its code is a relocated copy of
    the JP ROM's event at `vanilla` (same_code), or None: from there the PR's own script does it."""
    import event_translate as T
    for ins in T.scene(prog, off, mode):
        if ins.off != off and ins.name == (_jp_prog or E.Program(E.load("jp")).walk_all()).code.get((vanilla, "field"), ins).name                 and same_code(prog, ins.off, vanilla):
            return ins.off
    return None


def nop_stubs(sc):
    """The script with every `SysCall "SNES:..."` stub turned into a Nop that keeps the stub in its
    comment (what the game does with an unknown SysCall is unproven; the counts stay in the report)."""
    out = dict(sc)
    ops = []
    for m in sc["Mnemonics"]:
        if m["mnemonic"] == "SysCall" and str(m["operands"]["sValues"][0]).startswith("SNES:"):
            m = dict(m, mnemonic="Nop", comment=("%s %s" % (m["operands"]["sValues"][0], m.get("comment", ""))).strip())
            m["operands"] = dict(m["operands"], sValues=[""] + list(m["operands"]["sValues"][1:]))
        ops.append(m)
    out["Mnemonics"] = ops
    return out


# bits in the engine's range (1B0-1CF) that vanilla's events never touch and T-Edition's do (11-21 count over both
# ROMs' event code): its own story flags (1C3 = Sabin's costume from Figaro's priestess, CD/5EF0; 1C4/1C5/1C7/1C8/1C9 =
# the inn dreams' chapters; 1BC/1BD/1C0 set once and tested), allocated like its other story bits
ENGINE_STORY_BITS = (0x1BC, 0x1BD, 0x1C0, 0x1C3, 0x1C4, 0x1C5, 0x1C7, 0x1C8, 0x1C9)
# vanilla's event words (E8-EB on 7E/1FC2 + 2n; T-Edition's events use 0 1 5 6 7) -> the PR's ScenarioVariable (16 of them,
# DataStorage.kGlobalVariables). The PR's own scenes keep word 0 in 2 and word 7 in 7 (Cid's health, also word 7, in 2:
# its own sc_e_0616), and use 0 2 3 5 7 10; T-Edition's other words take free ones (TedPlugin keeps 1 4 6 8 9 14 15).
# Not T-Edition's $1E70 counters (its 67 / TED:counter): those are TedPlugin's.
WORD_GLOBALS = {0: 2, 7: 7, 1: 11, 5: 12, 6: 13}
# T-Edition's compares that look at part of their word (its handlers: 69's 58/E4CC compares word 52, $1868, as one byte;
# 6E's 58/E52A masks word 37, $1D4A, with 7FFF) -> TED:cmp's 4th argument: compare (word & mask) with (value & mask)
CMP_MASKS = {("58E4CC", 52): 0xFF, ("58E52A", 37): 0x7FFF}
BATTLE_KEY = 0x1000    # flag allocator key of battle bit b: 1000 + b, the kit's (port_ai event_bits: SnesAiHost
                        # loads/saves those flags around a fight, so fights and scenes share them)
# the battle bits vanilla's events use (38-3A, 40 lost battle, 41-4D): left to event_translate; T-Edition's own
# (01-3E, 69-6F) are story flags its events set and test
VANILLA_BATTLE_BITS = frozenset(range(0x38, 0x3B)) | frozenset(range(0x40, 0x50))
NPC_BITS = 0x300                        # an NPC record's show bit n is event bit 300 + n
NEW_ENTITY_IDS = range(5000, 5500)      # objects ted-events adds to vanilla PR entity files (lead: 5000+)
NEW_ENTITY_RANGES = {"ted-events": NEW_ENTITY_IDS, "ted-ex": range(5500, 6000),   # ted-maps' own rooms: 3000+
                     "ted-maps": range(6000, 6500)}
STANDIN_LOOK = 51                       # the PR's guard: the look of a T-Edition sprite the PR has none of
DIRECTION = {0: 1, 1: 2, 2: 4, 3: 8}    # SNES facing up/right/down/left -> the PR's (votes over vanilla's NPCs)
STANDINS = os.path.join(E.P.ROOT, "data", "ted_npc_standins.json")   # NPCs on stand-in looks, for bc-sprites
_npc_records = {}


def npc_records(snes_map):
    """{NPC index: record} of a SNES map in T-Edition (snes_maps.npcs on its tables: x, y, sprite,
    direction, show_bit...)."""
    if snes_map not in _npc_records:
        import snes_maps
        import ted_maps
        _npc_records[snes_map] = {n["index"]: n for n in snes_maps.npcs(ted_maps.rom(), snes_map, ted_maps.TED)}
    return _npc_records[snes_map]


def npc_look(rom, sprite):
    """An SNES NPC sprite -> (PR asset id, stand-in?): the look the PR gave that sprite (learned,
    event_translate.sprite_assets), else STANDIN_LOOK."""
    import event_translate as T
    looks = T.sprite_assets(rom).get(sprite)
    return (looks[0], False) if looks else (STANDIN_LOOK, True)


# a PR field NPC's properties (as the PR's own, e.g. Narshe's townsfolk), with the values that vary set by npc_object
_NPC_PROPS = [("accept_action_direction", "int", 15), ("action_id", "int", 2), ("affected", "bool", False),
              ("all_layers", "bool", False), ("asset_id", "int", 0), ("birdview_puppet", "bool", False),
              ("direction", "int", 4), ("entity_id", "int", 0), ("eye_contact", "bool", True),
              ("first_interval", "bool", True), ("flight_altitude_ratio", "float", 1), ("idling", "bool", False),
              ("interactive_icon_v_offset", "int", 12), ("link_object_id", "int", 0), ("message_key", "string", ""),
              ("move_interval_id", "int", 0), ("move_speed_id", "int", 0), ("move_step", "int", 0),
              ("move_type", "int", 0), ("move_while_display_message", "bool", False), ("object_id", "int", 0),
              ("object_type", "int", 6), ("pushed", "bool", True), ("script_id", "int", 0),
              ("talk_target_transportation_ids", "string", ""), ("target_character_status_id", "int", 0),
              ("turn_around", "bool", True), ("visible_minimap", "bool", False)]


def npc_object(px, py, eid, look, direction, script_id, name):
    """A PR field NPC (Tiled tile object; its y is the tile's bottom edge) at PR tile (px, py): talking
    runs `script_id` (action_id 2), none = it doesn't talk (action_id 0)."""
    vals = {"action_id": 2 if script_id else 0, "asset_id": look, "direction": direction, "entity_id": eid,
            "script_id": script_id}
    return {"gid": 1024, "height": 16, "id": eid, "name": name, "rotation": 0, "type": "", "visible": True,
            "width": 16, "x": px * 16, "y": (py + 1) * 16,
            "properties": [{"name": n, "type": t, "value": vals.get(n, v)} for n, t, v in _NPC_PROPS]}


# load scripts another T-Edition workstream ships (one owner per map script): ted-ex's TEditionQuests places vanilla
# NPCs the PR dropped in these rooms (11-21)
OTHERS_MAP_SCRIPTS = {"sc_map_20270", "sc_map_20460", "sc_map_30641_5", "sc_map_30811_5"}


def map_script_name(pr_map):
    """The PR room's own load script: sc_map_<room> in its folder (what runs as the room loads and picks
    its entity layers; Worlds Collide edits the same), or None."""
    import snes_maps
    name = "sc_map_" + pr_map[len("Map_"):]
    room = os.path.dirname(snes_maps.pr_tilemaps()[pr_map])
    return name if os.path.exists(os.path.join(room, name + ".json")) else None


_costumes = None
COSTUME_ART = os.path.join(E.P.ROOT, "data", "ted_costume_art.json")


def costume(char, slot, palette=None):
    """T-Edition's costume k (0 = the default look) of character `char` (0-13) for the graphic slot an
    event sets (37 c s), or None when that slot isn't one of its costumes (a vanilla look change: an
    Imperial disguise, a dream). With `palette` (43 c p): k of a costume using that palette, so the 43
    after a costume's 37 needs nothing (bc-sprites' data/ted_costume_art.json)."""
    global _costumes
    if _costumes is None:
        import event_translate as T
        d = T.read_json(COSTUME_ART) if os.path.exists(COSTUME_ART) else {"characters": {}}
        _costumes = list(d["characters"].values())
    if char >= len(_costumes):
        return None
    looks = _costumes[char]
    if palette is not None:
        return next((c["costume"] for c in looks if c["pal"] == palette and c["costume"]), None)
    if slot == char:
        return 0
    return next((c["costume"] for c in looks if c["slot"] == slot and c["costume"]), None)


TRIGGER_TYPES = (2, 5, 30, 10)          # the PR's forms of an event tile: step-on (2), examine (5, 10), step switch (30)


def trigger_objects(pr_map, spot, near=1):
    """[(layer, object, its properties)] for the PR room's scripted triggers (action_id 2) of an SNES event
    tile: a step-on trigger on the spot, else an object to examine or a switch within `near` tiles (the PR
    made some tiles a thing to examine next to them: the Big Bridge's staircase switch)."""
    import snes_maps
    room = os.path.dirname(snes_maps.pr_tilemaps()[pr_map])
    pk = _json(os.path.join(os.path.dirname(room), "package.json"))
    entry = next(m for m in pk["map"] if m["name"] == pr_map)
    out = []
    for nm in [x["name"] for x in entry.get("entity", [])] + ["entity_default"]:
        f = os.path.join(room, nm + ".json")
        if not os.path.exists(f):
            continue
        best = None
        for lay in _json(f).get("layers", []):
            for o in lay.get("objects") or []:
                props = {q["name"]: q["value"] for q in o.get("properties", [])}
                kind = props.get("object_type")
                if kind not in TRIGGER_TYPES or props.get("action_id") != 2 or "script_id" not in props:
                    continue
                at = (int(o["x"] // 16), int(o["y"] // 16) - (1 if "gid" in o else 0))
                d = abs(at[0] - spot[0]) + abs(at[1] - spot[1])
                if (d == 0 or (kind != 2 and d <= near)) and (best is None or d < best[0]):
                    best = (d, o, props)
        if best is not None:
            out.append((nm, best[1], best[2]))
    return out


def tile_rooms(snes_map, xy, primary=None):
    """[(PR room, its tile)]: the PR rooms of the SNES map's world walkable at (or next to) the tile,
    `primary` (else the room snes_maps.to_pr draws there) first."""
    import snes_maps
    world = snes_world(snes_map)
    out = []
    for mt in [mt for mt in snes_maps.pr_maps(snes_map) if mt.pr in snes_maps.pr_tilemaps()]:
        spot = (xy[0] + mt.dx, xy[1] + mt.dy)
        if mt.pr != primary:
            if world is not None and pr_world(mt.pr) not in (None, world):
                continue
            wk = snes_maps.pr_walkable(mt.pr)
            if not any((spot[0] + a, spot[1] + b) in wk for a in (-1, 0, 1) for b in (-1, 0, 1)):
                continue
        out.append((mt.pr, spot))
    first = primary or (snes_maps.to_pr(snes_map, *xy) or [None])[0]
    out.sort(key=lambda rs: rs[0] != first)
    return out


def _vanilla_tile_event(snes_map, xy):
    """The JP ROM's event tile at a map's spot (its address), or None."""
    jp = E.load("jp")
    return next((e[0] for e in E.entry_points(jp) if e[2] == snes_map and e[1] == "tile" and tuple(e[3]) == tuple(xy)), None)


def trigger_object(px, py, eid, script_id, name):
    """A PR step-on trigger (object_type 2, Tiled tile object) at PR tile (px, py) running `script_id`."""
    vals = {"action_id": 2, "direction": 0, "entity_id": eid, "gimmick": False, "ignore_route_link_object_id": -1,
            "link_object_id": 0, "object_id": 0, "object_type": 2, "script_id": script_id,
            "target_transportation_ids": ""}
    types = {bool: "bool", int: "int", str: "string"}
    return {"gid": 998, "height": 16, "id": eid, "name": name, "rotation": 0, "type": "", "visible": True,
            "width": 16, "x": px * 16, "y": (py + 1) * 16,
            "properties": [{"name": k, "type": types[type(v)], "value": v} for k, v in vals.items()]}


_shop_groups = None
TED_SHOPS = os.path.join(E.P.ROOT, "mods", "TEditionPort", "ted_shops.json")


def shop_groups():
    """{SNES shop: [PR product groups]}: the porter's own match of vanilla's shops to the PR's groups by
    stock (port.port_shops, run read-only on the US ROM: the PR keeps a town's WoB and WoR shops as two
    groups). T-Edition's shops keep vanilla's numbers; the porter writes their stock into these groups."""
    global _shop_groups
    if _shop_groups is None and os.path.exists(TED_SHOPS):
        # ted-monsters' map (mods/TEditionPort/ted_shops.json): every stocked T-Edition shop -> its PR product
        # group, the porter's matched ones and the new groups 900 + shop that ted_build's shop rule makes
        import event_translate as T
        d = T.read_json(TED_SHOPS)
        shops = d.get("shops") or {**d.get("pairs", {}), **{k: 900 + int(k) for k in d.get("unmatched", {})}}
        _shop_groups = {int(k): [int(v)] for k, v in shops.items()}
    if _shop_groups is None:
        import idmap
        import port
        van = E.load("us")
        saved = dict(idmap.ITEM_OVERRIDES)        # vanilla's items for vanilla's stock (a build has T-Edition's in)
        idmap.ITEM_OVERRIDES.clear()
        try:
            port.port_shops(van, van, {})
        finally:
            idmap.ITEM_OVERRIDES.update(saved)
        _shop_groups = {}
        for shop, group in port.port_shops.pairs:
            _shop_groups.setdefault(shop, []).append(group)
    return _shop_groups


def npc_objects(pr_map, spot, looks=(), near=2):
    """[(layer, object, its properties)] for each entity layer of a PR map (and entity_default) with the
    NPC: the one at `spot`, else (the PR moved some by a tile or two: Tzen's World of Balance bandit,
    Narshe's Elder in one story state) the nearest within `near` tiles that has the NPC's look: an
    asset of the exact matches in the other layers, or one of `looks` (the PR looks learned for its
    SNES sprite). NPCs that run a script (script_id > 0) or drawn ones with none (script_id 0: walk-ons
    the PR made of some talking SNES NPCs, Narshe's townsfolk)."""
    import snes_maps
    room = os.path.dirname(snes_maps.pr_tilemaps()[pr_map])
    pk = _json(os.path.join(os.path.dirname(room), "package.json"))
    entry = next(m for m in pk["map"] if m["name"] == pr_map)
    exact, close = {}, {}
    order = [x["name"] for x in entry.get("entity", [])] + ["entity_default"]
    for nm in order:
        f = os.path.join(room, nm + ".json")
        if not os.path.exists(f):
            continue
        for lay in _json(f).get("layers", []):
            for o in lay.get("objects") or []:
                props = {q["name"]: q["value"] for q in o.get("properties", [])}
                if "script_id" not in props or not (props["script_id"] or "gid" in o):
                    continue
                kind = props.get("object_type")
                # NPCs; on the very spot also what the PR made of some SNES NPCs: a shopkeeper (17), an
                # object to examine (5, 10: a letter, a switch). Not triggers, doors, chests.
                if kind not in (None, 6, 5, 10, 17):
                    continue
                at = (int(o["x"] // 16), int(o["y"] // 16) - (1 if "gid" in o else 0))
                d = abs(at[0] - spot[0]) + abs(at[1] - spot[1])
                if d == 0:
                    exact.setdefault(nm, (o, props))
                elif d <= near and kind in (None, 6):
                    close.setdefault(nm, []).append((d, o, props))
    ref = {p.get("asset_id") for o, p in exact.values()} | set(looks)
    out = []
    for nm in order:
        if nm in exact:
            out.append((nm,) + exact[nm])
        elif nm in close and ref:
            c = sorted((d, i, o, p) for i, (d, o, p) in enumerate(close[nm]) if p.get("asset_id") in ref)
            if c:
                out.append((nm, c[0][2], c[0][3]))
    return out


class ScriptIds:
    """script.csv ids for new scripts, kept in a JSON file so a script keeps its id."""

    def __init__(self, path, ids=SCRIPT_IDS):
        self.path, self.ids = path, ids
        self.table = {}
        if os.path.exists(path):
            import event_translate as T
            self.table = T.read_json(path)

    def get(self, name):
        if name not in self.table:
            used = set(self.table.values())
            self.table[name] = next(i for i in self.ids if i not in used)
        return self.table[name]

    def save(self):
        """Writes the table merged with the file as it is now (one id on two names is an error)."""
        import event_translate as T
        disk = T.read_json(self.path) if os.path.exists(self.path) else {}
        for k, v in disk.items():
            self.table.setdefault(k, v)
        by_id = {}
        for k, v in self.table.items():
            if v in by_id and by_id[v] != k:
                raise ValueError("%s: script id %d given to %s and %s" % (self.path, v, by_id[v], k))
            by_id[v] = k
        T.write_json(self.path, self.table, indent=0, sort_keys=True)


# The PR's flags no vanilla script or master table uses (one 1024-flag array, ScenarioFlag1-4 x 256; the
# minimap's map_flag uses SF4 132-206): T-Edition's own bits get these, in this order. 366 flags for the 262
# bits only T-Edition uses (2026-11-20 count over every catalog event); full on 11-21 with the battle bits, so
# also TreasureFlag3 (the PR's 1024 treasure flags 512-767: chests use 0-272, ted-maps' new chests 300-369, no
# vanilla script or map object touches 512+ but TreasureFlag4 135/136, the airship's): 256 more.
FLAG_RANGES = (("ScenarioFlag4", 0, 131), ("ScenarioFlag3", 80, 255), ("ScenarioFlag4", 207, 255),
               ("ScenarioFlag3", 23, 31), ("TreasureFlag3", 0, 255))


def flag_alloc(path=None, persist=True):
    """The one flag allocator for every T-Edition event tool (this session, ted-maps, ted-ex share
    data/snes_event_alloc_tedition.json), handing out FLAG_RANGES in order. With `persist`, each new
    flag is written to the file the moment it is handed out, so two sessions building at once can't
    hand out the same flag (a clash found on saving: the file's entries are taken, and the bit gets the
    next free flag)."""
    import event_translate as T

    class SharedFlagAlloc(T.FlagAlloc):
        def _take(self, bit):
            for k, v in self._disk().items():
                self.table.setdefault(k, v)
            if bit not in self.table:
                used = set(self.table.values())
                free = next(((c, i) for c, a, b in FLAG_RANGES for i in range(a, b + 1) if (c, i) not in used), None)
                if free is None:
                    raise RuntimeError("%s: every free PR flag is taken (FLAG_RANGES); bit %03X has none"
                                       % (self.path, bit))
                self.table[bit] = free

        def get(self, bit):
            if bit in self.table:
                return self.table[bit]
            self._take(bit)
            if persist and self.path:
                for _ in range(5):
                    try:
                        self.save()
                        break
                    except ValueError:          # another session took that flag meanwhile
                        del self.table[bit]
                        self._take(bit)
                else:
                    raise RuntimeError("%s: no free flag for bit %03X after 5 tries" % (self.path, bit))
            return self.table[bit]

    return SharedFlagAlloc(path or ALLOC)


_vanilla_bits = None


def vanilla_bits():
    """The event and NPC bits vanilla's own scripts (the JP ROM's, every reachable one) or NPC records
    use. Such a bit means what vanilla meant: its PR flag is the tie event_translate learned, never a
    new one (T-Edition's events test vanilla's story by them)."""
    global _vanilla_bits
    if _vanilla_bits is None:
        jp = E.load("jp")
        p = E.Program(jp).walk_all()
        bits = set()
        for i in p.code.values():
            a = i.args
            if "bit" in a and isinstance(a["bit"], tuple):
                bits.add(a["bit"][0])
            for b, _ in a.get("bits", ()):
                bits.add(b)
        for e in E.entry_points(jp):
            if e[1] in ("npc", "npc_object") and isinstance(e[3], dict) and isinstance(e[3].get("bit"), int):
                bits.add(e[3]["bit"])
        _vanilla_bits = frozenset(bits)
    return _vanilla_bits


def _vanilla_npc_event(snes_map, npc):
    """The JP ROM's event address for an NPC (what a T-Edition event that wraps it calls)."""
    jp = E.load("jp")
    return next((e[0] for e in E.entry_points(jp) if e[2] == snes_map and e[1] == "npc" and e[3]["npc"] == npc), None)


def _build(out, events, write, T, MG, PD, snes_maps, siblings=False, prog=None, owner="ted-events"):
    _, ids_file, keys_name, report_file = OWNER_FILES[owner]
    import csv
    import io
    import pr_script as Sc
    rom = prog.rom if prog is not None else load("ted")
    prog = prog if prog is not None else E.Program(rom).walk_all()
    texts = Texts(rom)
    alloc = flag_alloc(persist=write)
    for bit in EX_BOSS_BITS + (EX_OMEGA_BIT,):   # fixed flags for the bits EX and the Collection Room share
        alloc.get(bit)
    Tr = _translator_class()
    created = Tr.created = {}           # (PR map, SNES map, NPC) -> entity id of an NPC object added here
    new_objs = {}                       # PR map -> [NPC objects to add to its entity_default]
    prologue = {}                       # PR map -> [(SNES map, NPC, show bit, entity id)] hidden until shown
    standins = []                       # NPCs on a stand-in look (bc-sprites converts their sprites later)
    added_ids = set()                   # entity ids of the triggers added
    entrances = {}                      # PR map -> [(SNES map, T-Edition's entrance script)] run after its load script
    mod = MG.MagiciteMod(out, PD.GameData("ff6"), keys_name=keys_name)
    tilemaps = dict(snes_maps.pr_map_dirs())        # every PR map's folder (with entities) ...
    tilemaps = {k: os.path.join(v, "tilemap.json") for k, v in tilemaps.items()}
    tilemaps.update(snes_maps.pr_tilemaps())        # ... the drawn ones' tilemaps (the folder is what's used)
    packages = {}
    layer_edits = {}                    # (PR map, entity layer) -> {entity id: new script id}
    firsts = {}                         # (PR map, entity layer, entity id) -> (script name, script, SNES map)
    report = []
    ids = ScriptIds(ids_file, SCRIPT_ID_RANGES[owner])
    names_by_id = {r["id"]: r["script_name"] for r in csv.DictReader(io.StringIO(_text(os.path.join(E.P.MASTER, "script.csv"))))}
    def add_npc(pr_map, snes_map, n, dx, dy, off):
        """A new NPC object for SNES NPC n in the PR room's entity_default (hidden by the room's map script
        while its show bit is clear) -> its entity id, or None (no such NPC record)."""
        rec = npc_records(snes_map).get(n)
        if rec is None:
            return None
        eid = next(i for i in NEW_ENTITY_RANGES[owner] if i not in set(created.values()) | added_ids)
        look, standin = npc_look(rom, rec["sprite"])
        created[(pr_map, snes_map, n)] = eid
        new_objs.setdefault(pr_map, []).append(npc_object(rec["x"] + dx, rec["y"] + dy, eid, look,
                                                          DIRECTION.get(rec["direction"], 4), 0,
                                                          "TEditionNPC_%d_%d" % (snes_map, n)))
        prologue.setdefault(pr_map, []).append((snes_map, n, NPC_BITS + rec["show_bit"], eid))
        if standin:
            standins.append({"sprite": rec["sprite"], "snes_map": snes_map, "npc": n, "pr_map": pr_map,
                             "look": look, "entity": eid, "event": E.fmt(off)})
        return eid

    def add_scene_npcs(pr_map, snes_map, dx, dy, layer, off, mode="field"):
        """Entities for the NPCs the event's scene moves that the PR room has none for."""
        probe = Tr(rom, "probe", snes_map=snes_map, alloc=alloc, prog=prog, pr_map=pr_map)
        probe.layers = layer
        for n in sorted({i.args["obj"] - 0x10 for i in T.scene(prog, off, mode)
                         if isinstance(i.args.get("obj"), int) and 0x10 <= i.args["obj"] < 0x30}):
            if (pr_map, snes_map, n) not in created and probe.npc_entity(n) is None:
                add_npc(pr_map, snes_map, n, dx, dy, off)

    for ev in events:
        off, snes_map, test_bits = ev["event"], ev["map"], ev.get("test_bits", ())
        name = ev.get("name") or "sc_ted_%s" % E.fmt(off).replace("/", "").lower()
        scripts = []
        if ev.get("entrance"):
            # an entrance event: the PR room's own load script (sc_map_<room>) does vanilla's entrance; after it
            # runs T-Edition's part (from where its code leaves vanilla's: ted_part; a call to vanilla's
            # entrance does nothing), in every room of the map's world that has a load script
            jp_entry = next((e[0] for e in E.entry_points(E.load("jp")) if e[2] == snes_map and e[1] == "entrance"), None)
            start = ted_part(off, prog) if off == jp_entry else off
            world = snes_world(snes_map)
            rooms = [mt.pr for mt in snes_maps.pr_maps(snes_map) if mt.pr in tilemaps and map_script_name(mt.pr)
                     and (world is None or pr_world(mt.pr) in (None, world))]
            rooms = list(dict.fromkeys(rooms))
            if start is None or not rooms:
                report.append({"event": E.fmt(off), "script": None, "pr_map": None, "translated": {}, "stubs": {},
                               "wired": [], "skipped": "the same as vanilla's" if start is None else
                               "no PR room with a load script for SNES map %d" % snes_map})
                continue
            pr_map, layer, wired = rooms[0], "entity_default", []
            empty = Tr(rom, "empty", snes_map=snes_map, alloc=alloc, prog=prog).assemble(
                "empty", [T.lab("Main"), T.op("Exit")], [])
            for room in rooms:
                nm = "%s_%s" % (name, room.replace("Map_", "m"))
                t = Tr(rom, nm, snes_map=snes_map, alloc=alloc, prog=prog, pr_map=room)
                t.texts, t.layers = texts, layer
                if jp_entry is not None and jp_entry != off:
                    t.fallbacks[jp_entry] = empty
                sc = t.translate(start)
                scripts.extend((a_, s2, w or room) for a_, s2, w in t.after)
                entrances.setdefault(room, []).append((snes_map, sc))
                wired.append({"layer": map_script_name(room), "entity": None, "was": map_script_name(room), "now": nm,
                              "script_id": None, "entrance": True,
                              **({"from": E.fmt(start)} if start != off else {}),
                              **({} if room == pr_map else {"room": room})})
        elif "tile" in ev:
            # an event tile: the PR room's trigger at that spot runs T-Edition's event (in every room of the
            # map's world); a vanilla tile event T-Edition changed in place keeps the PR's own script for the
            # part that is still vanilla's (ted_part) and goes on with T-Edition's; a tile T-Edition added
            # gets a new step-on trigger
            xy = tuple(ev["tile"])
            rooms = tile_rooms(snes_map, xy, ev.get("pr_map"))
            if not rooms:
                report.append({"event": E.fmt(off), "script": None, "pr_map": None, "translated": {}, "stubs": {},
                               "wired": [], "skipped": "no PR room for SNES map %d" % snes_map})
                continue
            pr_map, layer, wired = rooms[0][0], ev.get("layer") or "entity_default", []
            add_scene_npcs(pr_map, snes_map, rooms[0][1][0] - xy[0], rooms[0][1][1] - xy[1], layer, off,
                           "vehicle" if snes_map in E.WORLD_MAPS else "field")
            vanilla = _vanilla_tile_event(snes_map, xy)
            part = ted_part(off, prog) if vanilla == off else None
            for room, spot in rooms:
                for lay, obj, props in trigger_objects(room, spot):
                    orig = names_by_id.get(str(props["script_id"]))
                    if props["script_id"] and not orig:
                        continue
                    edits = layer_edits.setdefault((room, lay), {})
                    eid = props.get("entity_id")
                    if obj["id"] in edits:
                        continue
                    nm = "%s_%s" % (name, lay.replace("ev_e_", "l")) if room == pr_map else \
                        "%s_%s_%s" % (name, room.replace("Map_", "m"), lay.replace("ev_e_", "l"))
                    t = Tr(rom, nm, snes_map=snes_map, alloc=alloc, prog=prog, pr_map=room)
                    t.texts, t.layers = texts, lay
                    extra = {}
                    if orig and part not in (None, off):
                        label = t.graft(Sc.load(orig), callable_=True)
                        sc = t.translate(part, preamble=[T.op("Call", i=["@" + label],
                                                              comment="the PR's own %s: vanilla's part (to %s)" % (orig, E.fmt(part)))])
                        extra["vanilla_part"] = orig
                    else:
                        if vanilla is not None and vanilla != off and orig:
                            t.fallbacks[vanilla] = Sc.load(orig)
                        sc = t.translate(off)
                    scripts.append((nm, sc, room))
                    scripts.extend((a_, s2, w or room) for a_, s2, w in t.after)
                    sid = ids.get(nm)
                    mod.table("script").add({"script_name": nm}, id=sid)
                    edits[obj["id"]] = sid
                    wired.append({"layer": lay, "entity": eid, "was": orig, "now": nm, "script_id": sid,
                                  "object_type": props.get("object_type"), **extra,
                                  **({} if room == pr_map else {"room": room})})
            if not wired:
                spot = rooms[0][1]
                eid = next(i for i in NEW_ENTITY_RANGES[owner] if i not in set(created.values()) | added_ids)
                added_ids.add(eid)
                nm = "%s_trig" % name
                t = Tr(rom, nm, snes_map=snes_map, alloc=alloc, prog=prog, pr_map=pr_map)
                t.texts, t.layers = texts, layer
                sc = t.translate(off)
                scripts.append((nm, sc, pr_map))
                scripts.extend((a_, s2, w or pr_map) for a_, s2, w in t.after)
                sid = ids.get(nm)
                mod.table("script").add({"script_name": nm}, id=sid)
                new_objs.setdefault(pr_map, []).append(trigger_object(spot[0], spot[1], eid, sid,
                                                                      "TEditionTile_%d_%d_%d" % (snes_map, xy[0], xy[1])))
                wired.append({"layer": "entity_default", "entity": eid, "was": None, "now": nm, "script_id": sid,
                              "object_type": 2, "new": True})
        else:
            # wired: the NPC's script in each entity layer it stands in becomes T-Edition's event with the
            # layer's own PR script grafted in for the vanilla talk the SNES event falls back to
            vanilla = _vanilla_npc_event(snes_map, ev["npc"])
            xy = next(((e[3]["x"], e[3]["y"]) for e in E.entry_points(rom)
                       if e[2] == snes_map and e[1] in ("npc", "npc_object") and e[3]["npc"] == ev["npc"]), None)
            if xy is None and ev["npc"] in npc_records(snes_map):
                rec_ = npc_records(snes_map)[ev["npc"]]
                xy = (rec_["x"], rec_["y"])
            if xy is None:
                report.append({"event": E.fmt(off), "script": None, "pr_map": None, "translated": {}, "stubs": {},
                               "wired": [], "skipped": "no NPC %d on SNES map %d" % (ev["npc"], snes_map)})
                continue
            # every PR room of the event's world where the NPC stands (the PR often has a World of Balance
            # and a World of Ruin copy of one SNES map: Kohlingen, Tzen, South Figaro), the main one first
            rec_ = npc_records(snes_map).get(ev["npc"])
            if rec_ is not None and rec_.get("no_face"):
                # bit 7 of the x byte: a special-graphics decoration (an actor column); its "event" is graphics
                report.append({"event": E.fmt(off), "script": None, "pr_map": None, "translated": {}, "stubs": {},
                               "wired": [], "skipped": "a decoration NPC (special graphics), no event"})
                continue
            looks = npc_looks(snes_map, ev["npc"])
            rooms = npc_rooms(snes_map, xy, ev.get("pr_map"), looks)
            if not rooms:                       # a SNES map the PR has no room for (a scene-only map)
                report.append({"event": E.fmt(off), "script": None, "pr_map": None, "translated": {}, "stubs": {},
                               "wired": [], "skipped": "no PR room for SNES map %d" % snes_map})
                continue
            pr_map = rooms[0][0]
            objs = npc_objects(pr_map, rooms[0][1], looks)
            layer = ev.get("layer") or next((lay for lay, o, p in objs if lay != "entity_default"), "entity_default")
            wired = []
            # T-Edition's NPCs the PR room has no entity for (the event's own NPC, the ones its scene moves):
            # new NPC objects in the room's entity_default, hidden by the map script while their show bit is clear
            own_missing = not any(True for room, spot in rooms for _ in npc_objects(room, spot, looks))
            dx, dy = rooms[0][1][0] - xy[0], rooms[0][1][1] - xy[1]
            probe = Tr(rom, name, snes_map=snes_map, alloc=alloc, prog=prog, pr_map=pr_map)
            probe.layers = layer
            scene_npcs = sorted({i.args["obj"] - 0x10 for i in T.scene(prog, off)
                                 if isinstance(i.args.get("obj"), int) and 0x10 <= i.args["obj"] < 0x30})
            for n in scene_npcs + ([ev["npc"]] if own_missing else []):
                if (pr_map, snes_map, n) in created or (n != ev["npc"] or not own_missing) and probe.npc_entity(n) is not None:
                    continue
                add_npc(pr_map, snes_map, n, dx, dy, off)
            for k, (room, lay, obj, props) in enumerate((room, lay, obj, props) for ri, (room, spot) in enumerate(rooms)
                                                        for lay, obj, props in npc_objects(room, spot, looks)):
                orig = names_by_id.get(str(props["script_id"]))
                if props["script_id"] and not orig:
                    continue
                edits = layer_edits.setdefault((room, lay), {})
                eid = props.get("entity_id")
                nm = "%s_%s" % (name, lay.replace("ev_e_", "l")) if room == pr_map else                 "%s_%s_%s" % (name, room.replace("Map_", "m"), lay.replace("ev_e_", "l"))
                t = Tr(rom, nm, snes_map=snes_map, alloc=alloc, prog=prog, pr_map=room)
                t.texts, t.layers = texts, lay
                if vanilla is not None and orig:     # no PR script (a walk-on): vanilla's SNES talk, translated
                    t.fallbacks[vanilla] = Sc.load(orig)
                    resume = vanilla_resume(off, prog) if vanilla == off else None
                    if resume is None:                # vanilla's event copied elsewhere (the inns' CD/CFE0)
                        resume = vanilla_copy(off, vanilla, prog)
                    if resume is not None:           # changed in place: only its first test differs
                        t.vanilla_at = {resume: Sc.load(orig)}
                sc = t.translate(off)
                scripts.extend((a, s2, w or room) for a, s2, w in t.after)
                if obj["id"] in edits:
                    # two SNES NPCs on one PR entity: the PR merged a World of Balance room and its World of
                    # Ruin twin (Tzen: maps 306 / 305). One script under the first event's name and id runs
                    # either scene by the PR's "after the collapse" flag (ScenarioFlag2 41, SNES bit 0A4).
                    nm1, sc1, map1 = firsts[(room, lay, obj["id"])]
                    worlds = {snes_world(map1), snes_world(snes_map)}
                    if worlds != {0, 1}:
                        wired.append({"layer": lay, "entity": eid, "was": orig,    # the earlier event keeps it
                                      "conflict": "entity runs script %d (an earlier event)" % edits[obj["id"]]})
                        continue
                    tw = Tr(rom, nm1, snes_map=map1, alloc=alloc, prog=prog, pr_map=room)
                    la, lb = tw.graft(sc1), tw.graft(sc)
                    wor, wob = (la, lb) if snes_world(map1) == 1 else (lb, la)
                    main = [T.lab("Main"),
                            T.op("Branch", i=[WOR_FLAG[1], 1, "@" + wor], s=[WOR_FLAG[0], T.EQ, "imm"],
                                 comment="World of Ruin: SNES map %d's scene" % (map1 if wor == la else snes_map)),
                            T.op("Jump", i=["@" + wob]), T.op("Exit")]
                    merged = tw.assemble(nm1, main, tw.blocks)
                    scripts.append((nm1, merged, room))
                    firsts[(room, lay, obj["id"])] = (nm1, merged, None)
                    wired.append({"layer": lay, "entity": eid, "was": orig, "now": nm1, "script_id": edits[obj["id"]],
                                  "merged": "%s: World of Ruin -> map %d's scene, else map %d's" % (
                                      nm1, map1 if wor == la else snes_map, snes_map if wor == la else map1)})
                    continue
                scripts.append((nm, sc, room))
                firsts[(room, lay, obj["id"])] = (nm, sc, snes_map)
                sid = ids.get(nm)
                mod.table("script").add({"script_name": nm}, id=sid)
                wired.append({"layer": lay, "entity": eid, "was": orig, "now": nm, "script_id": sid,
                              "object_type": props.get("object_type"), **({} if room == pr_map else {"room": room})})
                edits[obj["id"]] = sid
            if own_missing and (pr_map, snes_map, ev["npc"]) in created:
                eid = created[(pr_map, snes_map, ev["npc"])]
                nm = "%s_new" % name
                t = Tr(rom, nm, snes_map=snes_map, alloc=alloc, prog=prog, pr_map=pr_map)
                t.texts, t.layers = texts, layer
                sc = t.translate(off)
                scripts.append((nm, sc, pr_map))
                scripts.extend((a, s2, w or pr_map) for a, s2, w in t.after)
                sid = ids.get(nm)
                mod.table("script").add({"script_name": nm}, id=sid)
                for o in new_objs[pr_map]:
                    if o["id"] == eid:
                        for q in o["properties"]:
                            if q["name"] in ("script_id", "action_id"):
                                q["value"] = sid if q["name"] == "script_id" else 2
                wired.append({"layer": "entity_default", "entity": eid, "was": None, "now": nm, "script_id": sid,
                              "new": True})
        for nm, test in ((name, False), (name + "_test", True)):
            t = Tr(rom, nm, snes_map=snes_map, alloc=alloc, prog=prog, pr_map=pr_map)
            t.texts, t.layers = texts, layer
            preamble = []
            if test:
                preamble.append(T.op("SetEntities", s=[layer], comment="test: the layer with the scene's NPCs"))
                for b in test_bits:
                    if t.untied(b):
                        continue
                    cat, idx = t.flag(b)
                    preamble.append(T.op("SetFlag", i=[idx], s=[cat], comment="test: SNES bit %03X" % b))
            sc = t.translate(off, preamble=preamble)
            scripts.append((nm, sc, pr_map))
            scripts.extend((a, s, w or pr_map) for a, s, w in t.after)
            if not test:
                # what runs in game: the wired scripts (with their after-battle / after-warp scripts), whose
                # stubs can be fewer than the event's own (the PR's script doing vanilla's part)
                wired_names = {w["now"] for w in wired if w.get("now")}
                ws = collections.Counter()
                for nm_, sc_, _ in scripts:
                    if nm_ in wired_names or any(nm_.startswith(x + "_b") for x in wired_names):
                        for m_ in sc_["Mnemonics"]:
                            if m_["mnemonic"] == "SysCall" and str(m_["operands"]["sValues"][0]).startswith("SNES:"):
                                ws[m_["operands"]["sValues"][0][5:]] += 1
                report.append({"event": E.fmt(off), "script": nm, "pr_map": pr_map, "translated": dict(t.done),
                               "stubs": dict(t.stubs), "wired": wired,
                               **({"wired_stubs": dict(ws)} if wired_names and not ev.get("entrance") else {}),
                               "detail": {"%s %s" % ch: v for ch, v in sorted(t.report.items())}})
        for nm, sc, where in scripts:
            sc = nop_stubs(sc)
            if where not in tilemaps:          # a room the PR doesn't have: keep the script with the event's
                where = pr_map
            room = os.path.dirname(tilemaps[where])
            folder = os.path.basename(os.path.dirname(room))
            group = os.path.relpath(room, E.P.VANILLA).replace(os.sep, "/").split("/")[0]
            container = "Assets/GameAssets/Serial/Res/Map/%s/%s/%s.json" % (folder, where, nm)
            mod.asset(group, container, json.dumps(sc, ensure_ascii=False, separators=(",", ":")),
                      key="%s/%s" % (where, nm))
            packages.setdefault((group, folder), {}).setdefault(where, []).append(nm)
    for (group, folder), rooms in packages.items():
        # a map group's package.json is one file per Magicite folder, and of two folders that ship one
        # only one is read (BNW's won over ours in the runner's ted-3): start from T-Edition's other
        # folders' copy when one ships it (the porter's chests, ted-maps' rooms), so ours holds theirs too
        tail = (group, "Assets", "GameAssets", "Serial", "Res", "Map", folder, "package.json")
        src = next((os.path.join(f, *tail) for f in (SIBLING_FOLDERS if siblings else ())
                    if os.path.exists(os.path.join(f, *tail))), os.path.join(E.P.VANILLA, *tail))
        pk = _json(src)
        for room, names in rooms.items():
            entry = next(m for m in pk["map"] if m["name"] == room)
            for nm in names:
                if not any(x["name"] == nm for x in entry["script"]):
                    entry["script"].append({"name": nm, "asset": "%s/%s" % (room, nm)})
        mod.asset(group, "Assets/GameAssets/Serial/Res/Map/%s/package.json" % folder,
                  json.dumps(pk, ensure_ascii=False, separators=(",", ":")), key="package")
    for room_ in new_objs:
        layer_edits.setdefault((room_, "entity_default"), {})
    for (pr_map, lay), edits in layer_edits.items():
        room = os.path.dirname(tilemaps[pr_map])
        folder = os.path.basename(os.path.dirname(room))
        group = os.path.relpath(room, E.P.VANILLA).replace(os.sep, "/").split("/")[0]
        doc = _json(os.path.join(room, lay + ".json"))
        for layer_ in doc.get("layers", []):
            for o in layer_.get("objects") or []:
                props = {q["name"]: q for q in o.get("properties", [])}
                if o.get("id") in edits and "script_id" in props:      # keyed by the Tiled object id
                    props["script_id"]["value"] = edits[o["id"]]
                    # an NPC that only showed a line (action_id 4: its message_key) or did nothing (0)
                    # runs the script now (action_id 2, as the PR's 570 talking NPCs with scripts)
                    if "action_id" in props and props["action_id"]["value"] in (0, 4):
                        props["action_id"]["value"] = 2
        if lay == "entity_default" and new_objs.get(pr_map):
            # each added object goes in the object group holding its kind (NPCs, triggers), else the first
            groups = [g for g in doc.get("layers", []) if g.get("type") == "objectgroup"]
            for new in new_objs[pr_map]:
                kind = next(q["value"] for q in new["properties"] if q["name"] == "object_type")
                g = next((g for g in groups if any(q["name"] == "object_type" and q["value"] == kind
                                                  for o in g.get("objects") or [] for q in o.get("properties", []))),
                         groups[0] if groups else None)
                if g is not None:
                    g.setdefault("objects", []).append(new)
        mod.asset(group, "Assets/GameAssets/Serial/Res/Map/%s/%s/%s.json" % (folder, pr_map, lay),
                  json.dumps(doc, ensure_ascii=False, separators=(",", ":")), key="%s/%s" % (pr_map, lay))
    # the rooms' map scripts: hide each added NPC while its SNES show bit is clear (a vanilla show bit the
    # PR has no tie for: always shown), then the PR's own map script (grafted in)
    hidden, left_owner = [], []
    for pr_map in sorted(set(prologue) | set(entrances)):
        items = prologue.get(pr_map, [])
        ms = map_script_name(pr_map)
        if ms is None:
            continue
        if ms in OTHERS_MAP_SCRIPTS:           # one owner per load script: another workstream ships it
            left_owner.append(ms)
            continue
        t = Tr(rom, ms, snes_map=(items or entrances[pr_map])[0][0], alloc=alloc, prog=prog, pr_map=pr_map)
        ops = []
        for snes_map_, n, bit, eid in items:
            if t.untied(bit):
                continue
            cat, idx = t.flag(bit)
            skip = "shown_%d" % eid
            ops += [T.op("Branch", i=[idx, 1, "@" + skip], s=[cat, T.EQ, "imm"],
                         comment="SNES map %d NPC %d: shown while bit %03X is set" % (snes_map_, n, bit))]
            ops += t.puppet_ops([eid], [[T.op("Hide", kind=2)]])
            ops += [T.lab(skip)]
            hidden.append((pr_map, eid, bit))
        tail = [T.op("Call", i=["@" + t.graft(sc_, callable_=True)], comment="T-Edition's entrance (SNES map %d)" % m_)
                for m_, sc_ in entrances.get(pr_map, [])]
        if not ops and not tail:
            continue
        label = t.graft(Sc.load(ms), callable_=True)
        sc = t.assemble(ms, [T.lab("Main")] + ops + [T.op("Call", i=["@" + label], comment="the PR's own " + ms)]
                        + tail + [T.op("Exit")], t.blocks)
        room = os.path.dirname(tilemaps[pr_map])
        folder = os.path.basename(os.path.dirname(room))
        group = os.path.relpath(room, E.P.VANILLA).replace(os.sep, "/").split("/")[0]
        mod.asset(group, "Assets/GameAssets/Serial/Res/Map/%s/%s/%s.json" % (folder, pr_map, ms),
                  json.dumps(nop_stubs(sc), ensure_ascii=False, separators=(",", ":")), key="%s/%s" % (pr_map, ms))
        packages.setdefault((group, folder), {}).setdefault(pr_map, [])
    # T-Edition's edits of the PR's own scripts (SCRIPT_EDITS: vanilla code with a few changes), shipped under their names
    edited = []
    for spec in (SCRIPT_EDITS if owner == "ted-events" else ()):
        sc, t = script_edit(spec, rom, prog, alloc, Tr, texts)
        room = os.path.dirname(tilemaps[spec["pr_map"]])
        folder = os.path.basename(os.path.dirname(room))
        group = os.path.relpath(room, E.P.VANILLA).replace(os.sep, "/").split("/")[0]
        mod.asset(group, "Assets/GameAssets/Serial/Res/Map/%s/%s/%s.json" % (folder, spec["pr_map"], spec["script"]),
                  json.dumps(nop_stubs(sc), ensure_ascii=False, separators=(",", ":")),
                  key="%s/%s" % (spec["pr_map"], spec["script"]))
        edited.append({"event": spec["event"], "script": spec["script"], "pr_map": spec["pr_map"], "stubs": dict(t.stubs)})
    if report:
        report[0].setdefault("build", {}).update({"added_npcs": sum(len(v) for v in new_objs.values()),
                                                 "hidden_by_map_script": len(hidden), "standins": standins,
                                                 "map_scripts_left_to_owner": left_owner,
                                                 "script_edits": edited})
    mod.text("story_mes_en").update(texts.mes)
    mod.text("story_cha_en").update(texts.cha)
    if write:
        # written beside the folder, then swapped in: other workstreams' builds (ted_build's merge) read this folder
        # at any time and must never see it half written
        final, mod.out = out, out + ".new"
        with build_lock():     # ted_build's lock: its merge never reads this folder mid-swap
            mod.write()
            if owner == "ted-events" and os.path.exists(TILE_CELLS):
                # TedPlugin's walkability table for TED:tiles (top level: ted_build merges it into mods/TEdition, the
                # test install copies that folder's *.json to BepInEx/TEdition)
                import shutil
                shutil.copyfile(TILE_CELLS, os.path.join(mod.out, os.path.basename(TILE_CELLS)))
            if owner == "ted-events":
                T.write_json(os.path.join(mod.out, "ted_flags.json"), ted_flags(alloc), indent=1)
            swap_dir(mod.out, final)
        mod.out = final
        alloc.save()
        ids.save()
        T.write_json(report_file, report, ensure_ascii=False, indent=1)
        if owner == "ted-events":
            T.write_json(STANDINS, {"about": "NPCs ted-events gave a stand-in look (the PR has no sprite for "
                                             "their SNES sprite): bc-sprites converts T-Edition's sprites later",
                                    "npcs": standins}, ensure_ascii=False, indent=1)
    return report, mod


# --- what T-Edition added or changed, event by event ----------------------------------------------
CATALOG = os.path.join(E.P.ROOT, "data", "snes_event_ted_catalog.json")
NEW_MAPS = 416          # T-Edition's maps 416-511 are its own (ted-maps: data/ted_maps.json)
PUB_QUESTS = os.path.join(E.P.ROOT, "data", "snes_event_ted_pub_quests.json")
# events kept here whatever the rule says: built or started before the splits (the wine old man, South
# Figaro's pub quest; Ruby's Shine's Tzen bandit on 305/306; the Gilgamesh chain across maps 153-413)
BUILT_HERE = {"CA/5366", "CD/5850", "CC/9CE0", "CC/5DD3", "CB/B7EE", "CD/33C0", "CB/316C", "CD/4E20",
              "CD/3BD0", "CC/6F41"}   # + Nikeah's and Kohlingen's entrances (pub quests; one folder per map script)
EX_VANILLA_MAPS = range(200, 416)      # vanilla maps whose events ted-ex translates (mods/TEditionQuests)
# new maps whose events ted-ex translates (the lead's X8/X10, 11-21): 467 the EX Moogle's Mog House side, 469 the
# Collection Room (handed to ted-maps through data/ted_quests_maps.json)
EX_NEW_MAPS = frozenset({467, 469})
# single events given to another workstream than the rules say: Mr. Clio (map 415 NPC 0, audit E44) stands in
# ted-maps' room of map 510 and is no pub quest
OWNER_OVERRIDES = {"CD/FD10": "ted-maps"}


def owner(row, quests=None):
    """Who translates a catalog event: a pub quest's -> "ted-ex" (mods/TEditionQuests), else one on
    T-Edition's new maps (416+) -> "ted-maps" (mods/TEditionMaps), else on vanilla maps 200-415 ->
    "ted-ex" too, else "ted-events" (mods/TEditionEvents); BUILT_HERE stays "ted-events"."""
    if quests is None:
        quests = pub_quests()
    if row["event"] in BUILT_HERE:
        return "ted-events"
    if row["event"] in OWNER_OVERRIDES:
        return OWNER_OVERRIDES[row["event"]]
    if row["event"] in quests:
        return "ted-ex"
    if row["map"] in EX_NEW_MAPS:
        return "ted-ex"
    if row["map"] >= NEW_MAPS:
        return "ted-maps"
    return "ted-ex" if row["map"] in EX_VANILLA_MAPS else "ted-events"


def pub_quests():
    """{catalog event: its pub} from data/snes_event_ted_pub_quests.json."""
    import event_translate as T
    if not os.path.exists(PUB_QUESTS):
        return {}
    return {e: pub for pub, es in T.read_json(PUB_QUESTS)["pubs"].items() for e in es}


def tag_owners(rows=None, write=True):
    """Adds "owner" (and "pub" for a pub quest's event) to every catalog row."""
    import event_translate as T
    rows = rows if rows is not None else T.read_json(CATALOG)
    quests = pub_quests()
    for r in rows:
        r["owner"] = owner(r, quests)
        if r["event"] in quests:
            r["pub"] = quests[r["event"]]
        else:
            r.pop("pub", None)
    if write:
        T.write_json(CATALOG, rows, ensure_ascii=False, indent=1)
    return rows


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
    tag_owners(rows, write=False)
    if write:
        T.write_json(CATALOG, rows, ensure_ascii=False, indent=1)
    return rows


if __name__ == "__main__" and sys.argv[1:2] == ["owners"]:
    import collections
    rows = tag_owners()
    print(dict(collections.Counter(r["owner"] for r in rows)), "->", CATALOG)
    sys.exit(0)


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
    cat = T.read_json(CATALOG)
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
        T.write_json(os.path.join(E.P.ROOT, "data", "snes_event_ted_readme.json"), out, ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__" and sys.argv[1:2] == ["tilecells"]:
    tile_cells(sys.argv[2] if len(sys.argv) > 2 else TILE_CELLS)
    sys.exit(0)


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


BATCH = os.path.join(E.P.ROOT, "data", "snes_event_ted_batch.json")


def all_events():
    """EVENTS (hand-checked) + the bulk batch (data/snes_event_ted_batch.json): what mods/TEditionEvents holds."""
    import event_translate as T
    have = {e["event"] for e in EVENTS}
    bulk = [dict(event=E.parse_addr(r["event"]), map=r["map"],
                 **({"tile": tuple(r["tile"])} if "tile" in r else {"entrance": True} if r.get("entrance") else {"npc": r["npc"]}))
            for r in (T.read_json(BATCH)["events"] if os.path.exists(BATCH) else [])]
    return EVENTS + [e for e in bulk if e["event"] not in have]


if __name__ == "__main__":
    rep, _ = build(events=all_events(), siblings="--with-siblings" in sys.argv)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
