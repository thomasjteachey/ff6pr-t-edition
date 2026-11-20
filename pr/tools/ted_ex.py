"""T-Edition EX 2.0.6 (Mato) against T-Edition 3.0.7: what EX adds, where it keeps it, and how it joins
the T-Edition mod (one mod: EX's super-bosses behind the Mog House door, no save swap). Read only.

    .venv/Scripts/python tools/ted_ex.py              catalog -> build/t-edition/ex/catalog.json + catalog.txt
    .venv/Scripts/python tools/ted_ex.py tables       EX's table addresses next to T-Edition's
    .venv/Scripts/python tools/ted_ex.py content      the EX content set (packs, formations, monsters, maps)

EX is a second ROM hack built on an OLDER T-Edition (Tsushiy's EX 1.6.3 on T-Edition ~2.9; Mato's English
EX 2.0.6), meant to be played with a T-Edition save ("save swap": save in the Mog House, rename the save to
the EX ROM, load it there). Nearly everything in it is that older T-Edition (466 of T-Edition 3.0.7's 505
maps, the same item names, older monster stats, older event code); what is EX's own:

  * the boss room behind the Mog House door (SNES map 471, drawn by its entrance event EA/0000), a Moogle
    whose menu (EE dialogues 512-519) starts 12 boss battles: event packs 0-12 (pack 10 unused), formations
    0-22 and monsters 256-282, all written OVER T-Edition's slots of the same numbers (vanilla's early
    formations and boss monsters: why EX's random battles are "garbage"), each win setting one event bit
    T-Edition's Collection Room (maps 469/491/494) reads for its paintings; two item shops (107, 108);
  * Mog House changes (map 467): its entrance event opens a door at (79, 26) -> 471 and closes the one to
    the Developers' Room (80, 37); its Moogle offers to unequip the party (EE 516);
  * the "Dragon's Den" (maps 417-432, layouts 355-380, GBA-style), older T-Edition's super dungeon where
    3.0.7 now has its own; Omega Weapon (monster 460, formation 641) at its end is the one boss there
    that 3.0.7 doesn't have.

Tables (from the code that reads them; EX's C0/C1/C2 differ from 3.0.7's only in these operands):
    monsters        EA/7000  32 B x 512  (C2/0627, 2CA0-2E2E; 3.0.7: 57/3E00)
    monster AI      FF/F300 pointers (C2/2D73, as 3.0.7), scripts at E9/7000 + pointer (C2/1A40...; 3.0.7: 5F/58F0)
    steals/drops    41/EA00  8 B (as 3.0.7; EX's roll at 41/D300 is the older one: 178/50/20/8 of 256, no overrun)
    formations      CF/5900 x 768, flags CF/2400, event packs CF/5000, packs CF/4800, map packs CF/5600 (as 3.0.7)
    formation ids   C1/1595, 3C03, 3C08, C2/2F74, 5D80, C0/A43E, A44B: $2E9/$2EA -> $2D7/$2D8
    short exits     4B/1BFE + offsets DF/BB00 (C0/1A8F...; 3.0.7: 4B/9BFE)
    map graphics    DF/DA00 pointers (C0/26F8: the JP ROM's; 3.0.7: 40/0B00)
    everything else of the field (map properties 4D/0000, NPCs 4D/7CC0, event tiles 4B/0000, chests ED/8584 +
    4B/4000, palettes 4B/6000, layouts 41/0000, entrance events D1/FA00) at 3.0.7's addresses, other contents
    dialogue         4B/48: 5C/9CE0 is EMPTY in EX (one pointer to 52/0000): every 4B text box is blank in EX;
                     EX's own text is all in the EE table (51/E600, 1263 dialogues, EX's numbering)
    monster lines    CF/E000 pointers into bank 55 (EX's boss lines at 55/2B60...; AI F3 n)
    names            Mato's tables at 3.0.7's addresses (long monster names 55/D650 x 512, items 59/A560)
    items            ED/8F00 (30 records differ from 3.0.7, the same 256 names); the second table ED/AD00 is
                     T-Edition's own (in both ROMs); EX alone also reads it in battle (C2/271B, 2A5E -> 4E/0568,
                     05A0: item targeting/power when $1440 bit 0, a field-menu flag left over in battle)
    music           the same song tables as 3.0.7 (5F/0180, 5F/0300, CE/1400; one pointer differs, song 47)
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitpath  # noqa: E402,F401
import prdata as P  # noqa: E402

PROJECT = os.path.normpath(os.path.join(P.ROOT, ".."))
EX_ROM = os.path.join(PROJECT, "build", "t-edition", "T-Edition EX 2.0.6 (Mato).sfc")
TED_ROM = os.path.join(PROJECT, "build", "t-edition", "T-Edition 3.0.7 (Mato).sfc")
OUT = os.path.join(P.ROOT, "build", "t-edition", "ex")

# --- EX's tables (file offsets in the 6 MB ExHiROM) ------------------------------------------------
MONSTERS = 0x2A7000          # EA/7000, 32 B x 512
TED_MONSTERS = 0x573E00      # 3.0.7: 57/3E00
AI_PTRS = 0x3FF300           # FF/F300, 2 B x 512 (as 3.0.7, other contents)
AI_DATA = 0x297000           # E9/7000 (3.0.7: 5F/58F0)
TED_AI_DATA = 0x5F58F0
MONSTER_ITEMS = 0x41EA00     # 41/EA00, 8 B: 2 steals, 2 unused, 4 drops
FORMATIONS = 0x0F5900        # CF/5900, 15 B x 768
FORMATION_FLAGS = 0x0F2400   # CF/2400, 4 B x 768
PACKS = 0x0F4800             # CF/4800, 4 formations x 256
EVENT_PACKS = 0x0F5000       # CF/5000, 2 formations x 256
MAP_PACKS = 0x0F5600         # CF/5600, 1 B per map (C0/C306)
MONSTER_LINES = 0x0FE000     # CF/E000: 2-byte pointers into bank 55
LINES_BANK = 0x550000
LONG_MONSTERS = 0x55D650     # Mato's "ENEMY NAMES LONG", 20 B x 512
LONG_ITEMS = 0x59A560        # "LONG ITEMS", icon + 19
ITEMS, ITEMS2 = 0x2D8F00, 0x2DAD00   # ED/8F00, ED/AD00 (30 B x 256 each)
SHOPS = 0x047AC0             # C4/7AC0, 9 B
SPELLS = 0x046AC0            # C4/6AC0, 14 B x 256 (as 3.0.7); names: Mato's LONG MAGIC 55/7890 (0-53, 8 B),
LONG_MAGIC, LONG_ATTACKS = 0x557890, 0x557C80   # LONG ATTK 55/7C80 (54-255, 20 B)
EX_ABILITY_BASE = 7000       # proposed PR ability ids for EX's own attacks: 7000 + SNES spell id
DROP_ODDS_EX = (178, 50, 20, 8)      # 41/D319: CMP #$B2/#$E4/#$F8 (3.0.7: 174/50/20/12)

TABLES = [
    ("monsters", "EA/7000", "57/3E00", "C2/0627, C2/2CA0-2E2E (LDA $EA70xx,X)"),
    ("monster AI scripts", "E9/7000", "5F/58F0", "C2/1A40, 1A60, 1A67, 2D84"),
    ("monster AI pointers", "FF/F300", "FF/F300", "C2/2D73 (same operand, EX's own pointers)"),
    ("steals/drops", "41/EA00", "41/EA00", "41/D32D, 41/D328; EX's roll 41/D300 is the older inline one"),
    ("formations / flags / packs", "CF/5900, CF/2400, CF/4800, CF/5000", "same", "C1/0E84, C2/3150, C0/C191"),
    ("formation-id constants", "$2D7/$2D8", "$2E9/$2EA", "C0/A43E, A44B, C1/1595, 3C03, 3C08, C2/2F74, 5D80"),
    ("map packs", "CF/5600", "CF/5600", "C0/C306"),
    ("short exits", "4B/1BFE", "4B/9BFE", "C0/1A8F-1B5E (offsets DF/BB00 in both)"),
    ("map graphics pointers", "DF/DA00", "40/0B00", "C0/26F8, 2707 (EX keeps the JP ROM's table)"),
    ("map properties, NPCs, event tiles, chests, palettes, layouts, entrance events",
     "4D/0000, 4D/7CC0, 4B/0000, ED/8584+4B/4000, 4B/6000, 41/0000, D1/FA00", "same", "C0 (unchanged operands)"),
    ("dialogue 4B/48", "5C/9CE0 (empty: 1 pointer)", "5C/9CE0 (3452)", "C0/7FBF"),
    ("dialogue EE", "51/E600 (1263, EX's numbering)", "51/E600 (1267)", "C0/EE33"),
    ("monster battle lines (AI F3)", "CF/E000 -> bank 55", "CF/E000", "pointer to 'We are the Cloud of Darkness' at CF/E002"),
    ("item data", "ED/8F00 + ED/AD00", "same", "EX also reads ED/AD00 in battle: C2/271B, 2A5E -> 4E/0568, 05A0"),
    ("monster graphics entries", "CF/1A00 (5 B x 512)", "CF/1A00", "C1/2064, 24E6, C3/B8CC; EX's own for 256-282, 460"),
    ("song tables", "5F/0180, 5F/0300, 5F/0480, C5/3E96, CE/1400", "same", "C5/049B, 04DD, 01E2, 0538, 0630"),
]

# The boss room's menu (EE 513/514/518/519 choices) -> event pack, and the event bit each win sets
# (CD/A540-A750). Labels are the menu's.
HUB_MAP = 471
MOG_HOUSE = 467
HUB_BOSSES = [
    ("The Chaotic", 6, 629), ("The Tyrant", 7, 673), ("The Spectre", 0, 615), ("The Fiend", 1, 0),
    ("The Darkness", 2, 616), ("The Mighty Tree", 3, 617), ("The Hero", 4, 618), ("The Witch", 5, 620),
    ("The Reaper", 11, 706), ("The Unsent", 12, 2), ("The Royalty", 8, 621), ("The Divine Might", 9, 705),
]
DEN_MAPS = list(range(417, 433))         # the Dragon's Den (417-428) and its side rooms (429-432)
EX_MONSTER_BLOCK = range(256, 283)       # EX's own monsters, written over 3.0.7's 256-282
HUB_FORMATIONS = range(0, 24)            # EX's own formations, written over 3.0.7's 0-23
OMEGA_WEAPON, OMEGA_FORMATION, OMEGA_PACK = 460, 641, 168

# --- proposed ids in the merged mod (see the notes file "merge plan") -------------------------------
# Virtual SNES ids past T-Edition's ranges, so every porter keeps one number space per kind:
#   monsters  T-Ed 0-511 (PR: 1-384 vanilla rows, 1000 + e for 384-511)   EX: 512 + k  -> PR 1000 + 512 + k
#   formations T-Ed 0-767                                                  EX: 768 + k
#   maps      T-Ed 0-510 (PR 644+ for 416-510, ted-maps)                   EX: 512 + k
#   shops     T-Ed 0-127                                                   EX: 128, 129
EX_MONSTER_BASE, EX_FORMATION_BASE, EX_MAP_BASE, EX_SHOP_BASE = 512, 768, 512, 128


def _rom(path):
    with open(path, "rb") as f:
        return f.read()


def word(d, a):
    return d[a] | d[a + 1] << 8


def file_offset(bank, addr):
    return 0x400000 + ((bank - 0x40) << 16) + addr if 0x40 <= bank < 0x7E else ((bank & 0x3F) << 16) + addr


def snes(off):
    b = 0xC0 + (off >> 16) if off < 0x400000 else 0x40 + ((off - 0x400000) >> 16)
    return f"{b:02X}/{off & 0xFFFF:04X}"


def mato(raw):
    import profile_tedition as PT
    return PT.mato_text(raw)


def battle_text(d, f, limit=400):
    """Mato's battle-line encoding (as his menu text; 01 new line, 00 end; other codes dropped)."""
    import ted_dialog as D
    out = []
    for _ in range(limit):
        c = d[f]
        f += 1
        if c == 0:
            break
        out.append("\n" if c == 1 else D.glyph(c) if c >= 0x20 else "")
    return "".join(out)


class Roms:
    """EX, T-Edition 3.0.7 and the JP ROM, with event walks and map tables on demand."""

    def __init__(self):
        self.ex, self.ted = _rom(EX_ROM), _rom(TED_ROM)
        self._prog = {}

    @property
    def maps(self):
        import snes_maps as SM
        import ted_maps as TM
        if not hasattr(self, "_maps"):
            self._maps = (SM.Tables(name="T-Edition EX 2.0.6", maps=511, props=0x4D0000, layout_ptrs=0x410000,
                                    exit_data=0x4B1BFE, npc_data=0x4D7CC0, event_data=0x4B0000,
                                    chest_ptrs=0x2D8584, chest_data=0x4B4000, palettes=0x4B6000,
                                    gfx_ptrs=0x1FDA00), TM.TED)
        return self._maps

    def prog(self, name):
        import snes_events as E
        import ted_events as TE
        if name not in self._prog:
            rom = TE.load(name)
            self._prog[name] = (rom, E.Program(rom).walk_all())
        return self._prog[name]

    def name(self, d, e):
        return mato(d[LONG_MONSTERS + 20 * e:LONG_MONSTERS + 20 * e + 20])

    def item(self, d, i):
        return mato(d[LONG_ITEMS + 20 * i + 1:LONG_ITEMS + 20 * i + 20]) if i != 0xFF else ""

    def formation(self, d, f, listed=False):
        """Monsters present (byte 1's mask), or `listed`: every slot that names one (hidden ones the AI
        brings in, F5, and leftovers)."""
        r = d[FORMATIONS + 15 * f:FORMATIONS + 15 * f + 15]
        return [r[2 + s] | ((r[14] >> s & 1) << 8) for s in range(6)
                if (r[2 + s] != 0xFF if listed else r[1] >> s & 1)]

    def event_pack(self, d, p):
        return [word(d, EVENT_PACKS + 4 * p + 2 * k) & 0x7FFF for k in range(2)]

    def spell(self, d, s):
        return mato(d[LONG_MAGIC + 8 * s:LONG_MAGIC + 8 * s + 8] if s < 54 else
                    d[LONG_ATTACKS + 20 * (s - 54):LONG_ATTACKS + 20 * (s - 54) + 20])

    def map_data(self, which, m):
        import snes_maps as SM
        d = self.ex if which == "ex" else self.ted
        return SM.map_data(d, m, self.maps[0] if which == "ex" else self.maps[1])

    def used_maps(self, d):
        return [m for m in range(511) if any(d[0x4D0000 + 33 * m:0x4D0000 + 33 * m + 33])]


# --- EX's records for the merged mod (decided with the user, 2026-11-20: the boss room, its 12 fights and
# Omega Weapon as a 13th; pr/ted/EX_PLAN.md) ----------------------------------------------------------
# EX's monsters get ids past T-Edition's 512 (PR 1000 + id, idmap.MONSTER_EXT), its formations ids past
# 768 (party 30000 + f). A fight whose monsters change formation (AI F2: Golbez's second form...) is ONE
# formation here, every form listed, the later ones hidden at the start: the kit's AI host has no F2, so
# tools/ted_ex_ai.py turns each F2 into F5 show/hide over these slots.
EX_IDS = {e: EX_MONSTER_BASE + e - 256 for e in EX_MONSTER_BLOCK}
EX_IDS[OMEGA_WEAPON] = EX_MONSTER_BASE + len(EX_MONSTER_BLOCK)          # 539
OMEGA_REWARD = bytes((239, 239, 0, 0, 230, 230, 230, 230))   # Mato's optional patch (41/F860): steal Megalixir
# x2, drop item 230 Omega Weapon ("Alternative Omega Weapon Steal And Drop EX ONLY.ips")
SPECIAL_NAMES = 0x54D730     # Mato's "ENEMY MOVES" table (as 3.0.7): 20 B x 512
MONSTER_GRAPHICS = 0x0F1A00  # CF/1A00, 5 B x 512 (as 3.0.7)
FORMATION_AP = 0x33F000      # F3/F000, 1 B x 768


def fights(R=None):
    """The 13 boss-room fights: [{label, pack (EX's; None for Omega), entry (EX formation), formation (the
    merged one's id, 768+), bit (SNES event bit set on a win; None = to allocate), bg (SNES battle
    background of the 4D command)}]."""
    R = R or Roms()
    rom, prog = R.prog("ted-ex")
    bgs = {}
    for (off, mode), ins in prog.code.items():
        if ins.name == "battle" and HUB_MAP in prog.maps_of[off]:
            bgs[ins.args["pack"]] = ins.args["bg"]
    out = []
    for label, pack, bit in HUB_BOSSES:
        f0 = R.event_pack(R.ex, pack)[0]
        out.append({"label": label, "pack": pack, "entry": f0, "formation": EX_FORMATION_BASE + f0, "bit": bit,
                    "bg": bgs.get(pack)})
    out.append({"label": "Omega Weapon", "pack": None, "entry": OMEGA_FORMATION,
                "formation": EX_FORMATION_BASE + len(HUB_FORMATIONS), "bit": None, "bg": 25})   # 792; the den's bg
    return out


def _slots(d, f):
    """{slot: (EX monster, position byte, shown at the start)} of every slot formation f names."""
    r = d[FORMATIONS + 15 * f:FORMATIONS + 15 * f + 15]
    return {s: (r[2 + s] | ((r[14] >> s & 1) << 8), r[8 + s], bool(r[1] >> s & 1)) for s in range(6) if r[2 + s] != 0xFF}


def fight_layout(R, f0):
    """One fight's merged formation: its entry formation's slots, then every formation its monsters' AI
    changes to (F2, transitively), each of those slots kept where it is when free (or holding the same
    monster), else moved to a free slot. -> (slots {slot: (EX monster, pos, shown)}, maps {formation:
    {its slot: merged slot}}, order [formations])."""
    d = R.ex
    merged = {s: v for s, v in _slots(d, f0).items()}
    maps = {f0: {s: s for s in merged}}
    order, todo = [f0], [f0]
    while todo:
        f = todo.pop(0)
        for s, (e, _, _) in _slots(d, f).items():
            main, ctr = ai(d, e)
            for n, a in main + ctr:
                if n != "formation":
                    continue
                g = (a[1] | a[2] << 8) & 0x3FF
                if g in maps:
                    continue
                m = {}
                for t, (ge, pos, shown) in sorted(_slots(d, g).items()):
                    if t in merged and merged[t][0] == ge:
                        m[t] = t
                        continue
                    k = t if t not in merged else next(k for k in range(6) if k not in merged)
                    merged[k] = (ge, pos, False)       # a later form: hidden until its F2
                    m[t] = k
                maps[g] = m
                order.append(g)
                todo.append(g)
    return merged, maps, order


def ex_records(R=None):
    """EX's records renumbered for the merged mod, in port_monster_ext's grown-table formats:
    monsters {512..539: 32 B}, monster_items {id: 8 B} (Omega Weapon: Mato's optional reward),
    monster_graphics {id: 5 B}, monster_names / special_names {id: str}, formations {768+: 15 B, the entry
    formation's record with monster bytes of EX's ids}, formation_monsters {768+: [(id, x, y, shown)]} (the
    merged fight: authoritative, ids past 511), formation_flags {f: 4 B}, formation_ap {f: int},
    event_backgrounds {f: SNES battle background}, layouts {f: fight_layout()}, ex_slot {id: EX's own slot}."""
    R = R or Roms()
    d = R.ex
    out = {k: {} for k in ("monsters", "monster_items", "monster_graphics", "monster_names", "special_names",
                           "formations", "formation_monsters", "formation_flags", "formation_ap", "event_backgrounds",
                           "layouts", "ex_slot")}
    for e, i in EX_IDS.items():
        out["monsters"][i] = d[MONSTERS + 32 * e:MONSTERS + 32 * e + 32]
        out["monster_items"][i] = OMEGA_REWARD if e == OMEGA_WEAPON else d[MONSTER_ITEMS + 8 * e:MONSTER_ITEMS + 8 * e + 8]
        out["monster_graphics"][i] = d[MONSTER_GRAPHICS + 5 * e:MONSTER_GRAPHICS + 5 * e + 5]
        out["monster_names"][i] = R.name(d, e)
        out["special_names"][i] = mato(d[SPECIAL_NAMES + 20 * e:SPECIAL_NAMES + 20 * e + 20])
        out["ex_slot"][i] = e
    for fi in fights(R):
        f0, f = fi["entry"], fi["formation"]
        slots, maps, order = fight_layout(R, f0)
        out["formations"][f] = d[FORMATIONS + 15 * f0:FORMATIONS + 15 * f0 + 15]
        out["formation_monsters"][f] = [(EX_IDS[e], pos >> 4, pos & 15, shown) for s, (e, pos, shown) in sorted(slots.items())]
        out["formation_flags"][f] = d[FORMATION_FLAGS + 4 * f0:FORMATION_FLAGS + 4 * f0 + 4]
        out["formation_ap"][f] = d[FORMATION_AP + f0]
        out["event_backgrounds"][f] = fi["bg"]
        out["layouts"][f] = {"slots": {s: (EX_IDS[e], pos, shown) for s, (e, pos, shown) in slots.items()},
                             "maps": maps, "order": order}
    return out


class ExSprites:
    """EX's monster sprites for the merged ids 512-539 (port_monster_ext's art matching: sprite(e) ->
    snes_sprites.Sprite). EX keeps 3.0.7's sprite layout (graphics entries CF/1A00, tiles by monster id
    F0/F4/F5, palettes 41/6200: 48 monsters with 3.0.7's entries have 3.0.7's palettes there; EX's code
    copies in banks 44/45/47 that read 43/0000 aren't run), so profile_tedition's reader reads its ROM."""

    def __init__(self, R=None):
        import profile_tedition as PT
        self._r = PT.MonsterSprites((R or Roms()).ex)
        self._slot = {v: k for k, v in EX_IDS.items()}

    def sprite(self, e):
        s = self._slot.get(e)
        return self._r.sprite(s) if s is not None else None


# --- the EX content set -------------------------------------------------------------------------------
def by_map(prog):
    out = collections.defaultdict(list)
    for (off, mode), ins in prog.code.items():
        for m in prog.maps_of[off]:
            out[m].append(ins)
    return out


def ai(d, e, data=AI_DATA):
    import snes_ai as A
    return A.parse(d, data + word(d, AI_PTRS + 2 * e))


def content(R=None):
    """What is EX's own: the boss room's and the Dragon's Den's battles (event packs and the den's random
    packs), the formations their AI switches to (F2), the monsters of all of these, and the maps."""
    R = R or Roms()
    d = R.ex
    rom, prog = R.prog("ted-ex")
    bm = by_map(prog)
    packs = {}
    for m in [HUB_MAP] + DEN_MAPS:
        for ins in bm[m]:
            if ins.name in ("battle", "battle_nogameover"):
                packs.setdefault(ins.args["pack"], {"maps": set(), "at": set()})
                packs[ins.args["pack"]]["maps"].add(m)
                packs[ins.args["pack"]]["at"].add(ins.off)
    forms = {}
    for p, v in packs.items():
        for f in R.event_pack(d, p):
            forms.setdefault(f, set()).add(f"pack {p}")
    for f in HUB_FORMATIONS:              # EX's block (23: Eald'narche + Orbital, its battle event's)
        forms.setdefault(f, set()).add("EX block 0-23")
    for m in DEN_MAPS:
        md = R.map_data("ex", m)
        if md["properties"]["random_battles"]:
            pk = d[MAP_PACKS + m]
            for k in range(4):
                forms.setdefault(word(d, PACKS + 8 * pk + 2 * k) & 0x3FF, set()).add(f"random pack {pk} (map {m})")
    todo = list(forms)
    while todo:                            # AI formation changes (F2 a lo hi)
        f = todo.pop()
        for e in R.formation(d, f, listed=True):
            main, ctr = ai(d, e)
            for n, a in main + ctr:
                if n == "formation":
                    g = (a[1] | a[2] << 8) & 0x3FF
                    if g not in forms:
                        forms[g] = set()
                        todo.append(g)
                    forms[g].add(f"AI of monster {e}")
    monsters = sorted({e for f in forms for e in R.formation(d, f, listed=True)})
    return {"packs": packs, "formations": forms, "monsters": monsters, "hub_formations": list(HUB_FORMATIONS)}


# --- catalog sections ---------------------------------------------------------------------------------
def monsters(R, C):
    """Per monster slot: EX's against 3.0.7's (same / older data / Mato's older name / EX's own), and every
    monster of the EX content in detail."""
    d, t = R.ex, R.ted
    tnames = collections.defaultdict(list)
    for e in range(512):
        tnames[R.name(t, e)].append(e)
    classes = collections.Counter()
    slots = []
    for e in range(512):
        en, tn = R.name(d, e), R.name(t, e)
        er, tr = d[MONSTERS + 32 * e:MONSTERS + 32 * e + 32], t[TED_MONSTERS + 32 * e:TED_MONSTERS + 32 * e + 32]
        if e in EX_MONSTER_BLOCK or e == OMEGA_WEAPON:
            k = "ex"
        elif en == tn:
            k = "same" if er == tr else "older data"
        elif en in tnames:
            k = "moved"
        else:
            k = "older name"
        classes[k] += 1
        if k != "same":
            slots.append({"id": e, "ex": en, "ted": tn, "class": k})
    detail = []
    lines = set()
    for e in C["monsters"]:
        r = d[MONSTERS + 32 * e:MONSTERS + 32 * e + 32]
        it = d[MONSTER_ITEMS + 8 * e:MONSTER_ITEMS + 8 * e + 8]
        main, ctr = ai(d, e)
        msgs = sorted({a[0] | a[1] << 8 for n, a in main + ctr if n == "message"})
        lines |= set(msgs)
        forms = sorted({(a[1] | a[2] << 8) & 0x3FF for n, a in main + ctr if n == "formation"})
        same_name_in_ted = [x for x in tnames.get(R.name(d, e), []) if x != e]
        detail.append({
            "id": e, "name": R.name(d, e), "hp": word(r, 8), "mp": word(r, 10), "level": r[16],
            "own": e in EX_MONSTER_BLOCK or e == OMEGA_WEAPON,
            "overwrites_ted": R.name(t, e), "same_name_in_ted": same_name_in_ted,
            "ai_ops": len(main) + len(ctr), "ai_formations": forms, "lines": msgs,
            "steals": [R.item(d, it[0]), R.item(d, it[1])], "drops": [R.item(d, x) for x in it[4:8]],
            "proposed_id": (EX_MONSTER_BASE + e - 256 if e in EX_MONSTER_BLOCK else
                            EX_MONSTER_BASE + len(EX_MONSTER_BLOCK) if e == OMEGA_WEAPON else None)})
    texts = {}
    for n in sorted(lines):
        p = word(d, MONSTER_LINES + 2 * n)
        texts[n] = " ".join(battle_text(d, LINES_BANK + p).split())
    return {"classes": dict(classes), "slots": slots, "content": detail, "lines": texts}


def spells(R, C):
    """The spells EX's content AI casts (attack bytes, F0 random picks): which of them EX changed against
    3.0.7 (its bosses' own attacks were written over 3.0.7's enemy attacks 172-237: new abilities in the
    merged mod), and which are 3.0.7's as they are."""
    d, t = R.ex, R.ted
    used = collections.Counter()
    for e in C["monsters"]:
        main, ctr = ai(d, e)
        for n, a in main + ctr:
            if n == "attack":
                used[a[0]] += 1
            elif n == "random":
                used.update(x for x in a if x != 0xFE)
    rows = []
    for s in sorted(used):
        a, b = d[SPELLS + 14 * s:SPELLS + 14 * s + 14], t[SPELLS + 14 * s:SPELLS + 14 * s + 14]
        en, tn = R.spell(d, s), R.spell(t, s)
        if a == b and en == tn:
            continue
        own = en != tn and len([k for k in range(14) if a[k] != b[k]]) >= 3
        rows.append({"spell": s, "ex": en, "ted": tn, "bytes": [k for k in range(14) if a[k] != b[k]],
                     "kind": "EX's own attack" if own else "3.0.7's (retuned/renamed)",
                     "proposed_ability": EX_ABILITY_BASE + s if own else None})
    return {"used_by_content_ai": len(used), "differing": rows,
            "all_spells_data_differ": sum(d[SPELLS + 14 * s:SPELLS + 14 * s + 14] != t[SPELLS + 14 * s:SPELLS + 14 * s + 14]
                                          for s in range(256))}


def formations(R, C):
    d, t = R.ex, R.ted
    rows = []
    for f in sorted(C["formations"]):
        ms = R.formation(d, f)
        hidden = [e for e in R.formation(d, f, listed=True) if e not in ms]
        hub = f in C["hub_formations"]
        rows.append({"id": f, "why": sorted(C["formations"][f]), "monsters": [(e, R.name(d, e)) for e in ms],
                     "listed_not_present": [(e, R.name(d, e)) for e in hidden],
                     "raw": d[FORMATIONS + 15 * f:FORMATIONS + 15 * f + 15].hex(" "),
                     "flags": d[FORMATION_FLAGS + 4 * f:FORMATION_FLAGS + 4 * f + 4].hex(" "),
                     "ted_slot": [R.name(t, e) for e in R.formation(t, f)],
                     "hub": hub,
                     "proposed_id": EX_FORMATION_BASE + f if hub else None})
    return rows


def maps(R, C):
    """Map slots EX against 3.0.7 (counts), and EX's own maps in detail."""
    d, t = R.ex, R.ted
    ue, ut = R.used_maps(d), R.used_maps(t)
    strip = lambda rs: [{x: v for x, v in r.items() if x not in ("index", "event")} for r in rs]
    changed = collections.Counter()
    differ_layout = []
    for m in sorted(set(ue) & set(ut)):
        a, b = R.map_data("ted", m), R.map_data("ex", m)
        pa, pb = a["properties"], b["properties"]
        if (pa["layouts"], pa["graphic_sets"], pa["bg1_size"]) != (pb["layouts"], pb["graphic_sets"], pb["bg1_size"]):
            differ_layout.append(m)
        for k in ("npcs", "events", "exits", "chests"):
            if strip(a[k]) != strip(b[k]):
                changed[k] += 1
    own = [MOG_HOUSE, HUB_MAP] + DEN_MAPS
    rows = []
    for m in own:
        md = R.map_data("ex", m)
        p = md["properties"]
        rows.append({
            "map": m, "proposed_id": (EX_MAP_BASE + own.index(m) - 1) if m != MOG_HOUSE else None,
            "size": p["bg1_size"], "layouts": p["layouts"], "graphic_sets": p["graphic_sets"],
            "tilesets": p["tilesets"], "music": p["music"], "random_battles": p["random_battles"],
            "pack": d[MAP_PACKS + m] if p["random_battles"] else None,
            "entrance": _fmt_ev(_entrance(d, m)),
            "npcs": [{"n": r["index"], "x": r["x"], "y": r["y"], "sprite": r["sprite"], "event": _fmt_ev(r["event"])}
                     for r in md["npcs"]],
            "exits": [(r["tiles"][0], r["dest"] & 0x1FF, r.get("dest_x"), r.get("dest_y")) for r in md["exits"]],
            "chests": [{"x": r["x"], "y": r["y"], "bit": r["bit"], "type": r["type"],
                        "item": R.item(d, r["contents"]) if r["type"] == "item" else r["contents"]}
                       for r in md["chests"]],
            "ted_slot": {k: R.map_data("ted", m)["properties"][k] for k in ("layouts", "bg1_size", "music")}})
    lay = {}
    for m in DEN_MAPS + [HUB_MAP]:
        for L in R.map_data("ex", m)["properties"]["layouts"]:
            if L and L not in lay:
                users_t = [x for x in ut if L in R.map_data("ted", x)["properties"]["layouts"]]
                same = d[0x410000 + 3 * L:0x410000 + 3 * L + 3] == t[0x410000 + 3 * L:0x410000 + 3 * L + 3]
                lay[L] = {"used_by_ted_maps": users_t, "same_pointer_as_ted": same}
    return {"ex_maps": len(ue), "ted_maps": len(ut), "ted_only": sorted(set(ut) - set(ue)),
            "changed_tables": dict(changed), "layout_differs": differ_layout, "own": rows, "layouts": lay}


def _entrance(d, m):
    a = 0x11FA00 + 3 * m
    return d[a] | d[a + 1] << 8 | d[a + 2] << 16


def _fmt_ev(off):
    import snes_events as E
    return E.fmt(off)


def events(R, C):
    """EX's own scenes (the boss room, the Mog House, the den) and the decoder's coverage."""
    import snes_events as E
    import ted_dialog as D
    rom, prog = R.prog("ted-ex")
    d = R.ex
    bm = by_map(prog)
    cov = prog.coverage()
    scenes = []
    for m in [MOG_HOUSE, HUB_MAP] + DEN_MAPS:
        for off, kind, mm, det in prog.entries:
            if mm != m:
                continue
            mode = "vehicle" if m in E.WORLD_MAPS and kind != "npc" else "field"
            ok = (off, mode) in prog.code
            scenes.append({"map": m, "kind": kind, "at": E.fmt(off), "walked": ok,
                           "detail": det if not isinstance(det, dict) else {k: det[k] for k in ("npc", "x", "y", "sprite")}})
    ee = collections.Counter()
    b4 = collections.Counter()
    ops = collections.Counter()
    for m in [MOG_HOUSE, HUB_MAP] + DEN_MAPS:
        for ins in bm[m]:
            ops[ins.name] += 1
            if ins.name == "dialog2":
                ee[ins.args["dlg"]] += 1
            elif ins.name == "dialog":
                b4[ins.args["dlg"]] += 1
    ee_text = {n: " ".join(D.text(d, D.file_of(d, D.PTRS2, n)).split())[:160] for n in sorted(ee)}
    unknown = {k: [E.fmt(x) for x in v] for k, v in prog.unknown_at.items()}
    unknown_maps = {f"{m} {b:#x}": sorted({mm for x in v for mm in prog.maps_of.get(_prev(prog, x), [])})
                    for (m, b), v in prog.unknown_at.items()}
    bits_set = sorted({ins.args["bit"][0] for m in [HUB_MAP] + DEN_MAPS for ins in bm[m]
                       if ins.name in ("bit_set", "bit_clear") and isinstance(ins.args.get("bit"), tuple)})
    return {"coverage": {k: cov[k] for k in ("entries", "instructions", "bytes", "unknown")},
            "unknown_at": {str(k): v for k, v in unknown.items()}, "unknown_maps": unknown_maps,
            "dialog_4b_table": "5C/9CE0 holds one pointer (52/0000): every 4B/48 text box in EX is blank",
            "scenes": scenes, "ee_dialogues": ee_text, "dialog_4b_used": dict(b4),
            "ops": dict(ops.most_common()), "bits_set_by_ex_content": bits_set}


def _prev(prog, off):
    """The walked instruction just before an undecodable byte (to name its map)."""
    best = None
    for (o, mode) in prog.code:
        if o < off and (best is None or o > best):
            best = o
    return best


def items(R, C):
    d, t = R.ex, R.ted
    diff = []
    for i in range(256):
        a, b = d[ITEMS + 30 * i:ITEMS + 30 * i + 30], t[ITEMS + 30 * i:ITEMS + 30 * i + 30]
        if a != b:
            diff.append({"id": i, "name": R.item(t, i), "bytes": [k for k in range(30) if a[k] != b[k]]})
    names_differ = [i for i in range(256) if R.item(d, i) != R.item(t, i)]
    second = sum(1 for i in range(256) if d[ITEMS2 + 30 * i:ITEMS2 + 30 * i + 30] != t[ITEMS2 + 30 * i:ITEMS2 + 30 * i + 30])
    shops = {}
    for s in (107, 108):
        rows = {}
        for nm, dd in (("ex", d), ("ted", t)):
            r = dd[SHOPS + 9 * s:SHOPS + 9 * s + 9]
            rows[nm] = [R.item(dd, i) for i in r[1:] if i != 0xFF]
        shops[s] = rows
    rewards = collections.Counter()
    for e in C["monsters"]:
        it = d[MONSTER_ITEMS + 8 * e:MONSTER_ITEMS + 8 * e + 8]
        for x in list(it[:2]) + list(it[4:]):
            rewards[R.item(d, x)] += 1
    return {"names_differ": names_differ, "records_differ": diff, "second_table_records_differ": second,
            "hub_shops": shops, "content_monster_items": dict(rewards)}


def music(R, C):
    d, t = R.ex, R.ted
    tabs = {}
    for name, (b, a, n) in {"5F/0180": (0x5F, 0x180, 0x180), "5F/0300": (0x5F, 0x300, 0x180),
                            "5F/0480": (0x5F, 0x480, 0x2000), "C5/3E96": (0xC5, 0x3E96, 0xFF),
                            "CE/1400": (0xCE, 0x1400, 0x400)}.items():
        o = file_offset(b, a)
        tabs[name] = sum(1 for i in range(n) if d[o + i] != t[o + i])
    rom, prog = R.prog("ted-ex")
    bm = by_map(prog)
    songs = collections.Counter()
    for m in [MOG_HOUSE, HUB_MAP] + DEN_MAPS:
        songs[("map", R.map_data("ex", m)["properties"]["music"])] += 1
        for ins in bm[m]:
            if ins.name in ("song", "song_fade_in", "song_volume", "ted_song", "ted_song_fade_in", "ted_song_volume"):
                songs[(ins.name, ins.args["song"])] += 1
    return {"table_bytes_differing_from_ted": tabs, "songs_used": [f"{k[0]} {k[1]}" for k in sorted(songs)]}


def save_swap(R, C):
    """What EX writes that T-Edition reads back (the save swap's purpose), and where 3.0.7 reads it."""
    import snes_events as E
    trom, tprog = R.prog("ted")
    rom, prog = R.prog("ted-ex")
    bits = {bit for _, _, bit in HUB_BOSSES}
    readers = collections.defaultdict(set)
    for (off, mode), ins in tprog.code.items():
        for b, s in ins.args.get("bits", []) if isinstance(ins.args.get("bits"), list) else []:
            if b in bits:
                readers[b] |= set(tprog.maps_of[off])
    writers_ted = collections.defaultdict(set)
    for (off, mode), ins in tprog.code.items():
        bt = ins.args.get("bit")
        if ins.name in ("bit_set", "bit_clear") and isinstance(bt, tuple) and bt[0] in bits:
            writers_ted[bt[0]] |= set(tprog.maps_of[off])
    rows = []
    for label, pack, bit in HUB_BOSSES:
        fs = R.event_pack(R.ex, pack)
        rows.append({"menu": label, "pack": pack, "formation": fs[0],
                     "monsters": [R.name(R.ex, e) for e in R.formation(R.ex, fs[0])],
                     "bit": bit, "bit_hex": f"{bit:03X}", "ted_reads_on_maps": sorted(readers[bit]),
                     "ted_sets_on_maps": sorted(writers_ted[bit])})
    return {"bosses": rows,
            "carried": "the whole SRAM (party, items, gil, espers, every event bit, position); EX only adds the "
                       "12 bits above (and whatever the den sets); back in 3.0.7 the Collection Room's paintings "
                       "read them (maps 469, 491, 494). Nothing else of EX's state matters to 3.0.7."}


def problems(R, C):
    """EX's own defects, measured where the ROM shows them."""
    import snes_events as E
    d = R.ex
    rom, prog = R.prog("ted-ex")
    over_f, over_m = set(HUB_FORMATIONS), set(EX_MONSTER_BLOCK)
    garbage = collections.Counter()
    maps_hit = []
    for m in R.used_maps(d):
        p = R.map_data("ex", m)["properties"]
        if not p["random_battles"] or m in DEN_MAPS:
            continue
        pk = d[MAP_PACKS + m]
        fs = [word(d, PACKS + 8 * pk + 2 * k) & 0x3FF for k in range(4)]
        bad = [f for f in fs if f in over_f or any(e in over_m for e in R.formation(d, f))]
        garbage["maps with random battles"] += 1
        if bad:
            garbage["maps whose pack holds an EX boss formation/monster"] += 1
            maps_hit.append((m, pk, bad))
    stale = [{"formation": f, "monsters": [R.name(d, e) for e in R.formation(d, f, listed=True)]}
             for f in range(24, 768) if any(e in over_m for e in R.formation(d, f, listed=True))]
    bad_npcs = [{"map": m, "kind": k, "at": E.fmt(o), "detail": {x: det[x] for x in ("npc", "x", "y", "sprite")}
                 if isinstance(det, dict) else det}
                for o, k, m, det in prog.bad_entries if m in DEN_MAPS + [HUB_MAP, MOG_HOUSE]]
    den_npc_sprites = collections.Counter()
    for m in DEN_MAPS:
        for r in R.map_data("ex", m)["npcs"]:
            den_npc_sprites[r["sprite"]] += 1
    it = d[MONSTER_ITEMS + 8 * OMEGA_WEAPON:MONSTER_ITEMS + 8 * OMEGA_WEAPON + 8]
    # EX stripped what its boss room doesn't use: battle lines past 29, steals/drops outside its block,
    # the 4B dialogue table, EE dialogues of the old content
    import ted_dialog as D
    empty_lines = [n for n in range(30, 256) if d[LINES_BANK + word(d, MONSTER_LINES + 2 * n)] == 0]
    no_items = [e for e in range(512) if not any(d[MONSTER_ITEMS + 8 * e:MONSTER_ITEMS + 8 * e + 8])]
    ee_blank = [n for n in range(D.count(d, D.PTRS2)) if not D.text(d, D.file_of(d, D.PTRS2, n)).strip()]
    talk_4b = []
    for m in DEN_MAPS:
        for off, kind, mm, det in prog.entries:
            ins = prog.code.get((off, "field"))
            if mm == m and kind == "npc" and ins is not None and ins.name == "dialog":
                talk_4b.append((m, det["npc"], det["sprite"], E.fmt(off)))
    import snes_ai as A

    def ai_len(e):
        st = i = AI_DATA + word(d, AI_PTRS + 2 * e)
        ends = 0
        while ends < 2:
            op = d[i]
            i += A.SIZES.get(op, 1) if op >= 0xF0 else 1
            ends += op == 0xFF
        return i - st
    block_end = max(word(d, AI_PTRS + 2 * e) + ai_len(e) for e in EX_MONSTER_BLOCK)
    ai_in_block = [e for e in range(512) if e not in EX_MONSTER_BLOCK and word(d, AI_PTRS + 2 * e) < block_end]
    block_ai_lines = sorted({(e, n) for e in range(512) if e not in EX_MONSTER_BLOCK
                             for nm, a in sum(ai(d, e), []) if nm == "message"
                             for n in [a[0] | a[1] << 8] if 1 <= n <= 29})
    block_ai_forms = sorted({(e, g) for e in range(512) if e not in EX_MONSTER_BLOCK
                             for nm, a in sum(ai(d, e), []) if nm == "formation"
                             for g in [(a[1] | a[2] << 8) & 0x3FF] if g in HUB_FORMATIONS})
    return {"random_battles": dict(garbage), "random_battle_maps": maps_hit[:40],
            "battle_lines_empty_30_255": len(empty_lines),
            "monsters_with_no_steals_drops": len(no_items),
            "ai_scripts_overwritten": {"block_scripts_end": snes(AI_DATA + block_end),
                                       "other_monsters_pointing_inside": len(ai_in_block)},
            "ee_dialogues_blank": {"count": len(ee_blank), "first": ee_blank[:12]},
            "dialog_4b_table_entries": __import__("ted_dialog").count(d, __import__("ted_dialog").PTRS),
            "den_npcs_talking_4b": talk_4b,
            "other_monsters_using_ex_lines_1_29": block_ai_lines,
            "other_monsters_switching_to_formations_0_23": block_ai_forms,
            "formations_naming_overwritten_monsters": stale,
            "npc_entries_not_code": bad_npcs, "den_npc_sprites": dict(den_npc_sprites),
            "omega_weapon_items": {"steals": [R.item(d, it[0]), R.item(d, it[1])],
                                   "drops": [R.item(d, x) for x in it[4:]]},
            "smelling_salts_byte27": {"ex": d[ITEMS + 30 * 249 + 27], "ted": R.ted[ITEMS + 30 * 249 + 27]}}


def catalog(write=True):
    R = Roms()
    C = content(R)
    out = {"tables": [dict(zip(("table", "ex", "ted", "code"), r)) for r in TABLES],
           "content": {"packs": {p: {"maps": sorted(v["maps"]), "formations": R.event_pack(R.ex, p)}
                                 for p, v in sorted(C["packs"].items())},
                       "formations": sorted(C["formations"]), "hub_formations": C["hub_formations"],
                       "monsters": C["monsters"]},
           "monsters": monsters(R, C), "spells": spells(R, C), "formations": formations(R, C), "maps": maps(R, C),
           "events": events(R, C), "items": items(R, C), "music": music(R, C),
           "save_swap": save_swap(R, C), "problems": problems(R, C)}
    if write:
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, "catalog.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
        with open(os.path.join(OUT, "catalog.txt"), "w", encoding="utf-8") as f:
            f.write(text_report(out))
    return out


def text_report(c):
    L = ["T-Edition EX 2.0.6 (Mato) against T-Edition 3.0.7: catalog (tools/ted_ex.py)", ""]
    L.append("TABLES (EX | 3.0.7 | code)")
    L += [f"  {r['table']}: {r['ex']} | {r['ted']} | {r['code']}" for r in c["tables"]]
    L += ["", "BOSS ROOM (map 471): menu -> event pack -> formation -> monsters, bit set on a win; 3.0.7 reads it on"]
    for b in c["save_swap"]["bosses"]:
        L.append(f"  {b['menu']:<17} pack {b['pack']:>2} form {b['formation']:>3} {', '.join(b['monsters']):<34} "
                 f"bit {b['bit_hex']}  3.0.7 reads on maps {b['ted_reads_on_maps']}")
    m = c["monsters"]
    L += ["", f"MONSTER SLOTS EX vs 3.0.7: {m['classes']}", "", "EX CONTENT MONSTERS"]
    for r in m["content"]:
        own = "EX's own" if r["own"] else "older T-Ed"
        L.append(f"  {r['id']:>3} {r['name']:<18} HP {r['hp']:>5} MP {r['mp']:>5} Lv {r['level']:>3} {own:<10} "
                 f"(3.0.7 slot: {r['overwrites_ted']}) AI {r['ai_ops']} ops, F2 {r['ai_formations']}, "
                 f"lines {r['lines']}; steal {r['steals']} drop {r['drops'][0]}; proposed {r['proposed_id']}")
    L += ["", "EX BATTLE LINES (AI F3 n: CF/E000 -> bank 55)"]
    L += [f"  {n}: {t[:110]}" for n, t in m["lines"].items()]
    sp = c["spells"]
    L += ["", f"SPELLS cast by EX's content AI: {sp['used_by_content_ai']}; differing from 3.0.7: {len(sp['differing'])} "
              f"(all 256: {sp['all_spells_data_differ']} records differ)"]
    L += [f"  {r['spell']:>3} EX {r['ex']!r:<20} 3.0.7 {r['ted']!r:<20} {r['kind']:<26} bytes {r['bytes']} "
          f"proposed {r['proposed_ability']}" for r in sp["differing"]]
    L += ["", "EX CONTENT FORMATIONS"]
    for r in c["formations"]:
        L.append(f"  {r['id']:>3} {', '.join(f'{e} {n}' for e, n in r['monsters']):<52} {'; '.join(r['why'])[:60]} "
                 f"| 3.0.7 slot: {', '.join(r['ted_slot'])[:40]} | proposed {r['proposed_id']}")
    mp = c["maps"]
    L += ["", f"MAPS: EX {mp['ex_maps']} slots, 3.0.7 {mp['ted_maps']}; 3.0.7-only {mp['ted_only']}",
          f"  tables differing on shared slots (older T-Ed): {mp['changed_tables']}",
          f"  layout/graphics/size differ: {mp['layout_differs']}", "EX'S OWN MAPS"]
    for r in mp["own"]:
        L.append(f"  {r['map']} -> {r['proposed_id']}: {r['size']} layouts {r['layouts']} gfx {r['graphic_sets']} "
                 f"music {r['music']} random {r['random_battles']} pack {r['pack']} entrance {r['entrance']}; "
                 f"{len(r['npcs'])} NPCs, exits {r['exits']}, chests {[(x['x'], x['y'], x['item']) for x in r['chests']]}"
                 f" | 3.0.7 slot {r['ted_slot']}")
    L.append(f"  layouts of EX's maps: {mp['layouts']}")
    ev = c["events"]
    L += ["", f"EVENTS: coverage {ev['coverage']}", f"  unknown at {ev['unknown_at']}", f"  4B: {ev['dialog_4b_table']}",
          f"  4B dialogues EX's own scenes use (blank in EX): {ev['dialog_4b_used']}",
          f"  bits EX's content sets: {ev['bits_set_by_ex_content']}", "  EE dialogues of EX's scenes:"]
    L += [f"    {n}: {t}" for n, t in ev["ee_dialogues"].items()]
    L += ["  entries:"] + [f"    {s}" for s in ev["scenes"]]
    it = c["items"]
    L += ["", f"ITEMS: names differing {it['names_differ']}; records differing {len(it['records_differ'])}: "
              f"{[(r['id'], r['name'], r['bytes']) for r in it['records_differ']]}",
          f"  second table ED/AD00 records differing: {it['second_table_records_differ']}",
          f"  boss room shops: {it['hub_shops']}", f"  content monsters' steals/drops: {it['content_monster_items']}"]
    L += ["", f"MUSIC: song-table bytes differing from 3.0.7 {c['music']['table_bytes_differing_from_ted']}; "
              f"used by EX's maps/scenes: {c['music']['songs_used']}"]
    L += ["", f"SAVE SWAP: {c['save_swap']['carried']}"]
    p = c["problems"]
    L += ["", f"PROBLEMS: random battles {p['random_battles']}", f"  maps (map, pack, bad formations): {p['random_battle_maps']}",
          f"  formations 24-767 naming EX's monsters 256-282 (old T-Ed fights now showing EX bosses): "
          f"{len(p['formations_naming_overwritten_monsters'])}: {[x['formation'] for x in p['formations_naming_overwritten_monsters']]}",
          f"  NPC entries that aren't code on EX's maps: {p['npc_entries_not_code']}",
          f"  den NPC sprites: {p['den_npc_sprites']}", f"  Omega Weapon: {p['omega_weapon_items']}",
          f"  stripped: battle lines 30-255 empty {p['battle_lines_empty_30_255']}/226; monsters with no steals/drops "
          f"{p['monsters_with_no_steals_drops']}/512; EE dialogues blank {p['ee_dialogues_blank']}; 4B table entries "
          f"{p['dialog_4b_table_entries']}; AI: {p['ai_scripts_overwritten']}",
          f"  den NPCs whose talk starts with a 4B dialogue (pointer 0 -> text read from 00/0000 = WRAM: blank or "
          f"a crash): {p['den_npcs_talking_4b']}",
          f"  other monsters' AI showing lines 1-29 (now EX's boss lines): {p['other_monsters_using_ex_lines_1_29']}",
          f"  other monsters' AI switching to formations 0-23 (now EX's bosses): {p['other_monsters_switching_to_formations_0_23']}",
          f"  Smelling Salts byte 27: {p['smelling_salts_byte27']}"]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "catalog"
    if arg == "tables":
        for r in TABLES:
            print(f"{r[0]}: EX {r[1]} | 3.0.7 {r[2]} | {r[3]}")
    elif arg == "content":
        C = content()
        print("packs", {p: sorted(v["maps"]) for p, v in sorted(C["packs"].items())})
        print("formations", sorted(C["formations"]))
        print("monsters", C["monsters"])
    else:
        c = catalog()
        print(text_report(c)[:3000])
        print(f"... written to {OUT}")
