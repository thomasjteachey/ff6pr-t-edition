"""T-Edition EX's boss room scenes as PR scripts, through ted-events' translator (tools/event_translate.py
with T-Edition's dialect and text, tools/ted_events.py).

    .venv/Scripts/python tools/ted_ex_events.py          (translates; prints what each scene came out as)

Scenes (EX ROM, map 471): the Moogle (NPC 0, CD/A780: EE 512/513 and three more menu pages -> a fight:
EE 515's effects, 4D <pack>, CA/5E9F, the win's bit), the two shopkeepers (CD/8100, CD/8103: shops 107/108
-> the merged mod's 128/129), the room's entrance (EA/0000: the room drawn by tile commands, then the
Moogle's dance CD/A760).

Omega Weapon, the 13th fight (the user's choice, 2026-11-20), is added to EX's own code in memory before
translating (EX_PATCH; the ROM file isn't touched): the last menu page's EXIT becomes NEXT (EE 519, same
length), which leads to a new page (EE 1263: "Omega Weapon / EXIT") and a fight written as EX writes the
others (call CD/A620, 4D A8 = pack 168, EX's Omega pack, call CA/5E9F, the win's bit). That bit is a
stand-in (OMEGA_STANDIN, 2DF) for ted_events.EX_OMEGA_BIT: the flag ted-events pinned for it.

Ids: packs 0-12 and 168 -> the merged fights' parties 30000 + formation (ted_ex.fights()); text keys
TEDX_E<n>_* (EX's own EE table: ted_events.Texts(rom, "TEDX")); flags from the shared allocation file
(ted_events.ALLOC; the 12 boss bits and Omega's pinned there); script ids 9700-9799 (ted_events.EX_SCRIPT_IDS).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitpath  # noqa: E402,F401
import prdata as P  # noqa: E402
import ted_ex as X  # noqa: E402

SCRIPT_IDS_FILE = os.path.join(P.ROOT, "data", "ted_ex_scripts.json")
OMEGA_STANDIN = 0x2DF            # the patch's bit for Omega's win (ted_events.EX_OMEGA_BIT's flag;
                                 # not 2E0-2FF: the translator reads those as characters' bits)
OMEGA_PACK = X.OMEGA_PACK        # 168: EX's pack for formation 641
NEW_PAGE_EE = 1263               # the new menu page (EX's EE table holds 1263)
MENU_CODE, FIGHT_CODE, PAGE_TEXT = 0x2A1000, 0x2A1040, 0x2A1100    # free space in bank EA (EA/0E9B-4DFF)
SHOPS = {107: 128, 108: 129}     # EX's shops -> the merged mod's (T-Edition's 107/108 are other shops)
SCENES = [                       # (name, EX event address, kind, NPC)
    ("sc_tedx_moogle", "CD/A780", "npc", 0),
    ("sc_tedx_shop_items", "CD/8100", "npc", 1),
    ("sc_tedx_shop_cures", "CD/8103", "npc", 2),
    ("sc_tedx_room_enter", "EA/0000", "entrance", None),
]


def _ev(snes_addr):
    import snes_events as E
    return E.parse_addr(snes_addr)


def _addr3(off):
    return bytes((off & 0xFF, off >> 8 & 0xFF, off >> 16 & 0xFF))


def _text(s):
    """Mato's encoding for the new page: A-Z 20, a-z 3A, space 7F, 01 new line, 15 a choice line."""
    out = bytearray()
    for ch in s:
        if ch == "\n":
            out.append(0x01)
        elif ch == ">":
            out.append(0x15)
        elif "A" <= ch <= "Z":
            out.append(0x20 + ord(ch) - 65)
        elif "a" <= ch <= "z":
            out.append(0x3A + ord(ch) - 97)
        else:
            out.append(0x7F)
    return bytes(out) + b"\x00"


def ex_patch(data):
    """Omega Weapon's menu page and fight written into EX's code (a copy): -> bytes."""
    import snes_events as E
    import ted_dialog as D
    d = bytearray(data)
    size = len(d)
    # EE 519's fourth choice: "EXIT" -> "NEXT" (same length) and its B6 target -> the new page
    f519 = D.file_of(bytes(d), D.PTRS2, 519)
    end = d.index(0, f519)
    i = d.rindex(bytes((0x24, 0x37, 0x28, 0x33)), f519, end)       # E X I T
    d[i:i + 4] = bytes((0x2D, 0x24, 0x37, 0x33))                    # N E X T
    b6 = E.event_file(_ev("CD/A6E3"), size)
    assert d[b6] == 0xB6 and d[b6 + 10:b6 + 13] == _addr3(_ev("CA/5EA9")), "EX's last menu page moved"
    menu, fight = _ev("EA/1000"), _ev("EA/1040")
    d[b6 + 10:b6 + 13] = _addr3(menu)
    # the new page: EE 1263 "> Omega Weapon / > EXIT", then B6 -> the fight / CA/5EA9 (EX's exit)
    text = _text(" >  Omega Weapon\n >  EXIT")
    d[PAGE_TEXT:PAGE_TEXT + len(text)] = text
    p = D.PTRS2 + 3 * NEW_PAGE_EE
    assert not any(d[p:p + 3]), "EX's EE table has grown"
    d[p:p + 3] = bytes((0x00, 0x11, 0xEA))                          # EA/1100
    code = bytes((0xEE, NEW_PAGE_EE & 0xFF, NEW_PAGE_EE >> 8, 0xB6)) + _addr3(fight) + _addr3(_ev("CA/5EA9"))
    d[MENU_CODE:MENU_CODE + len(code)] = code
    # the fight, as EX writes the other twelve (CD/A540...)
    code = (bytes((0xB2,)) + _addr3(_ev("CD/A620")) + bytes((0x4D, OMEGA_PACK, 25, 0xB2)) + _addr3(_ev("CA/5E9F")) +
            bytes((0xD4, OMEGA_STANDIN & 0xFF, 0x96, 0x5C, 0x3A, 0xFE)))
    d[FIGHT_CODE:FIGHT_CODE + len(code)] = code
    # Ultimecia (CD/A5EB): "if battle bit $44 clear: bit 26C, else vanilla's game-over scene". Her AI never
    # sets $44 (only her battle event F7 04 could; battle events aren't ported), and the translator can't
    # test battle bits (it would fall into the game over after a win): a win sets 26C, as in EX when $44 is clear
    u = E.event_file(_ev("CD/A5EB"), size)
    assert bytes(d[u:u + 10]) == bytes.fromhex("b744a0a603b25ce502fe"), "EX's Ultimecia ending moved"
    d[u:u + 10] = bytes((0xD4, 0x6C, 0x96, 0x5C, 0x3A, 0xFE, 0xFE, 0xFE, 0xFE, 0xFE))
    # CA/5E9F after every fight: "if the party lost, vanilla's game-over scene" (CC/E55C, whose text EX's empty
    # dialogue table can't show): a lost event battle is the PR's own game over, so the routine just returns
    g = E.event_file(_ev(LOST_CHECK), size)
    assert bytes(d[g:g + 10]) == bytes.fromhex("b740a85e00b25ce502fe"), "CA/5E9F moved"
    d[g] = 0xFE
    return bytes(d)


def load():
    """EX's ROM as ted_events reads it, with the Omega patch: (rom, Program)."""
    import snes_events as E
    import ted_events as TE
    rom = TE.load("ted-ex")
    rom.data = ex_patch(rom.data)
    rom.dialog_choices = TE._choices(rom)
    return rom, E.Program(rom).walk_all()


def parties():
    """{EX event pack: (merged formation, PR party)} of the 13 fights."""
    out = {}
    for fi in X.fights():
        pack = fi["pack"] if fi["pack"] is not None else OMEGA_PACK
        out[pack] = (fi["formation"], 30000 + fi["formation"])
    return out


def translator_class(fight_parties, room=None):
    """ted-events' T-Edition translator, for EX: its packs, shops, Omega's stand-in bit, its rooms."""
    import event_translate as T
    import ted_events as TE
    TedT = TE._translator_class()

    class ExTranslator(TedT):
        own_bits = TE.OWN_BITS
        rooms = room or {}          # SNES map -> (PR map id, PR map name, dx, dy) (ted-maps' rooms)

        def battle_party(self, pack):
            if pack in fight_parties:
                return fight_parties[pack]
            return super().battle_party(pack)

        def flag(self, bit):
            return super().flag(TE.EX_OMEGA_BIT if bit == OMEGA_STANDIN else bit)

        def shop_ops(self, shop):
            if shop in SHOPS:
                return [T.op("SysCall", s=[f"TED:shop {shop_group(SHOPS[shop])}"],
                             comment=f"EX shop {shop} = T-Edition EX shop {SHOPS[shop]}")]
            return None

        def place(self, m, x, y):
            if m in self.rooms:
                pid, name, dx, dy = self.rooms[m]
                return pid, name, x + dx, y + dy, None
            return super().place(m, x, y)

    return ExTranslator


SHOP_GROUP_BASE = 9100           # product_group ids of EX's shops: 9100 + merged shop (9228, 9229)


def shop_group(shop):
    return SHOP_GROUP_BASE + shop


LOST_CHECK = "CA/5E9F"           # after every fight: "if the party lost, vanilla's game-over scene (CC/E55C)"


def translate(room=None, pr_map=None, write_ids=False, log=print):
    """Every scene: -> [(name, PR script, [after-scripts], translator)] and the texts {file: {key: text}}."""
    import event_translate as T
    import ted_events as TE
    rom, prog = load()
    texts = TE.Texts(rom, prefix="TEDX")      # EX's own EE table; its " >  The Chaotic" lines are choices there
    alloc = T.FlagAlloc(TE.ALLOC)
    for bit in TE.EX_BOSS_BITS + (TE.EX_OMEGA_BIT,):
        alloc.get(bit)
    Tr = translator_class(parties(), room)
    out = []
    for name, addr, kind, npc in SCENES:
        t = Tr(rom, name, snes_map=X.HUB_MAP, alloc=alloc, prog=prog, pr_map=pr_map)
        t.texts = texts
        sc = t.translate(_ev(addr))
        out.append((name, sc, list(t.after), t))
        log(f"{name} ({addr}): translated {sum(t.done.values())}, stubs {dict(t.stubs)}, "
            f"after-scripts {[a for a, _, _ in t.after]}, needs formations {sorted(t.needs_formations)}")
    return out, {"story_mes_en": texts.mes, "story_cha_en": texts.cha}, alloc


if __name__ == "__main__":
    res, texts, _ = translate()
    print(f"{len(texts['story_mes_en'])} story lines: " + "; ".join(f"{k}={v[:40]!r}" for k, v in list(texts["story_mes_en"].items())[:6]))
