"""FF6 T-Edition (Tsushiy; Mato's English translation, 3.0.7 A7 r1) for the shared porter.

    .venv/Scripts/python tools/port.py tedition        (writes mods/TEdition/, a feasibility port)

T-Edition is a Japanese-ROM mod (6 MB ExHiROM). tools/jp_layout.py turns it into the US v1.0 layout
the porter reads; this profile says where T-Edition keeps each table (found 2026-11-20 from the
code that loads them: T-Edition's long loads point into the expansion), converts the records it
reshaped, and gives the porter Mato's full English names. Nothing T-Edition-specific is in the
porter itself. Built from build/t-edition/T-Edition 3.0.7 (Mato).sfc (tools/build.py) and the
Japanese ROM; the US-layout image is held in memory (ff6snes.MEMORY), never written.

What the US layout can't hold is counted, not ported (pr/build/t-edition/layout_report.txt):
monsters 384-511 (T-Edition's ~94 new ones), formations 576-767, maps 416-511 and their chests,
per-character HP/MP growth, monster sprites T-Edition redrew, and everything in assembly.
"""
import os
import sys

import kitpath  # noqa: F401
import ff6snes as S
import idmap as M
import jp_layout as J
import prdata as P
import snes_ai as A
from profiles import PROJECT, Profile

MATO = os.path.join(PROJECT, "build", "t-edition", "T-Edition 3.0.7 (Mato).sfc")
REPORT = os.path.join(P.ROOT, "build", "t-edition", "layout_report.txt")

# --- where T-Edition 3.0.7 keeps things (file offsets in the 6 MB ROM; SNES address in comments)
ITEMS = 0x2D8F00          # ED/8F00 (C2/102B and 27 more loads); vanilla's D8/5000 now holds names
MONSTERS = 0x573E00       # 57/3E00 (C2/2D20), 32 bytes x 512
MONSTER_ITEMS = 0x41EA00  # 41/EA00 (jsl 41/D32D from C2/2C3B): 8 bytes: steals, 2 zero, 4 drops
FORMATIONS = 0x0F5900     # CF/5900 (C1/0E84, C2/3150), 15 bytes x 768
FORMATION_FLAGS = 0x0F2400  # CF/2400 (C2/3138)
SKETCHES = 0x0F1200       # CF/1200 (C2/3B42)
RAGES = 0x0F1600          # CF/1600 (C2/0609)
MAP_PROPS = 0x4D0000      # 4D/0000 (C0/1CBF), 33 bytes x 512
CHEST_PTRS, CHEST_DATA = 0x2D8584, 0x4B4000   # ED/8584 (C0/15E3: 513 offsets), 4B/4000
AP = 0x33F000             # F3/F000 (C2/5D84), 1 byte x 768
AI_PTRS, AI_DATA = 0x3FF300, 0x5F58F0   # FF/F300 (C2/2D73), 5F/58F0 (C2/1A3F)
CHAR_NAMES = 0x0478C0     # Mato's English, 6 bytes (C4/78C0, as the JP ROM)
# Mato's full-length name tables (each between "****LABEL****" markers in ASCII in his build)
LONG_ITEMS = 0x59A560, 20, 256       # "LONG ITEMS BEGIN": icon + 19 (280 there: the second bank's too)
ITEM_COUNT = 280                     # T-Edition's items: 256-279 a second bank of 24 relics (records ITEMS + 30 x 256)
ITEM_SNES_NAMES = {"Experience Egg": "Exp. Egg"}   # second-bank names no PR/SNES name matches (item identity)
CHEST_ITEM_BANK = 0x10, 256          # a chest's type bit 4: its content byte names item 256 + n (C0/4CA3 -> 4E/0C50)
LONG_MONSTERS = 0x55D650, 20, 384    # "ENEMY NAMES LONG" (512 there)
LONG_MAGIC = 0x557890, 8, 54         # "LONG MAGIC NAMES": spells 0-53
LONG_ATTACKS = 0x557C80, 20, 202     # "LONG ATTK NAMES": spells 54-255 (espers, then skills)

# T-Edition's four drop slots (41/D300, from the victory routine JP C2/5F06): one roll 0-255 per monster
# that ends the battle dead, slot 0 below 174, 1 below 224, 2 below 244, else 3 = 174/50/20/12 of 256;
# a picked empty slot drops nothing (the ted-battle session, 2026-11-20). Its roll reads past the RNG table
# for monsters 32+ (a T-Edition bug that skews their odds by id band): the intended odds are ported.
DROP_ODDS = (68, 19, 8, 5)


def mato_text(raw):
    """Mato's menu encoding: A-Z 20-39, a-z 3A-53, 0-9 54-5D, 7F space, FF pad, icons D8+."""
    out = []
    for b in raw:
        if 0x20 <= b <= 0x39:
            out.append(chr(65 + b - 0x20))
        elif 0x3A <= b <= 0x53:
            out.append(chr(97 + b - 0x3A))
        elif 0x54 <= b <= 0x5D:
            out.append(chr(48 + b - 0x54))
        elif b in (0x7F, 0xFF):
            out.append(" ")
        else:
            out.append({0x5E: "!", 0x5F: "?", 0x63: "'", 0x64: "-", 0x65: ".", 0x66: ","}.get(b, ""))
    return " ".join("".join(out).split())


# Mato's descriptions: the menu's pointer tables (2-byte offsets from a text base, each text ends at 00, 01
# breaks the line), found from the code that sets $E7 (table) and $EB/$ED (text): items C3/8A89, spells
# C3/623B, Lores C3/5D48. (table, text base, count). T-Edition has 280 items: 256-279 are its second item
# bank (relics: Black Belt, Dragon Horn, the Fiends' relics...; an inventory slot's quantity bit 7, 4E/0750)
DESC_TABLES = {"items": (0x041000, 0x5C0000, 280),   # C4/1000 -> 5C/xxxx
               "spells": (0x26F690, 0x180000, 54),   # E6/F690 -> D8/xxxx
               "lores": (0x0FFF3E, 0x550000, 24),    # CF/FF3E -> 55/xxxx
               "espers": (0x0FFE40, 0x550000, 27),   # CF/FE40 -> 55/xxxx ("ESPER ATTK DESCS"): each esper's summon
               "blitz": (0x0FFF9E, 0x550000, 8),     # CF/FF9E -> 55/xxxx
               "bushido": (0x0FFFAE, 0x550000, 8)}   # CF/FFAE -> 55/xxxx
# the SNES spell slots of those three (port_spells: espers' summons 54-80, Bushido 85-92, Blitz 93-100)
DESC_SLOTS = {"espers": 54, "bushido": 85, "blitz": 93}
SPELL_RECORDS = 0x046AC0, 14   # the US layout's spell records (Lores from spell 139)
LORE_FIRST = 139
# the small font's punctuation (the US font's order, 0x60 below it), and Mato's own brackets B3/B4 and quotes 73/AA
DESC_CHARS = {0x01: "\n", 0x5E: "!", 0x5F: "?", 0x60: "/", 0x61: ":", 0x62: '"', 0x63: "'", 0x64: "-", 0x65: ".",
              0x66: ",", 0x67: "...", 0x68: ";", 0x69: "#", 0x6A: "+", 0x6B: "(", 0x6C: ")", 0x6D: "%", 0x6E: "~",
              0x73: '"', 0xAA: '"', 0xA0: "&", 0xB3: "(", 0xB4: ")"}


def mato_desc(raw):
    """One of Mato's description texts (ends at 00): lines kept ("\\n"), spaces tidied."""
    out = []
    for b in raw[:raw.index(0)] if 0 in raw else raw:
        if 0x20 <= b <= 0x39:
            out.append(chr(65 + b - 0x20))
        elif 0x3A <= b <= 0x53:
            out.append(chr(97 + b - 0x3A))
        elif 0x54 <= b <= 0x5D:
            out.append(chr(48 + b - 0x54))
        elif b in (0x7F, 0xFF):
            out.append(" ")
        else:
            out.append(DESC_CHARS.get(b, ""))
    return "\n".join(t for t in (" ".join(line.split()) for line in "".join(out).split("\n")) if t)


def mato_descriptions():
    """{"items": [280], "spells": [54], "lores": [24]} of Mato's descriptions (his build's menu tables)."""
    if getattr(_Image, "descs", None) is None:
        build()
        rom = _Image.mod
        out = {}
        for name, (table, text, count) in DESC_TABLES.items():
            ptrs = [int.from_bytes(rom[table + 2 * i:table + 2 * i + 2], "little") for i in range(count)]
            out[name] = [mato_desc(rom[text + p:text + p + 256]) for p in ptrs]
        _Image.descs = out
    return _Image.descs


def monster_items(raw):
    """T-Edition's 8-byte steals/drops -> the SNES's 4 (rare steal, common steal, rare drop, common
    drop): the likeliest filled drop slot is the common drop, the next one the rare drop."""
    drops = [raw[4 + k] for k in sorted(range(4), key=lambda k: -DROP_ODDS[k]) if raw[4 + k] != 0xFF]
    common = drops[0] if drops else 0xFF
    rare = drops[1] if len(drops) > 1 else 0xFF
    return bytes((raw[0], raw[1], rare, common))


TABLES = [
    J.Table("characters", 0x2D7CA0, 22, 64),
    J.Table("items", 0x185000, 30, 256, mod=ITEMS),
    J.Table("spells (incl. lores)", 0x046AC0, 14, 256),
    J.Table("espers", 0x186E00, 11, 27, mod=0x26F567),
    J.Table("monsters", 0x0F0000, 32, 384, mod=MONSTERS),
    J.Table("monster items", 0x0F3000, 4, 384, mod=MONSTER_ITEMS, mod_size=8, convert=monster_items),
    J.Table("formations", 0x0F6200, 15, 576, mod=FORMATIONS),
    J.Table("formation flags", 0x0F5900, 4, 576, mod=FORMATION_FLAGS),
    J.Table("packs", 0x0F4800, 8, 256),
    J.Table("event packs", 0x0F5000, 4, 256),
    J.Table("zones", 0x0F5400, 4, 128),
    J.Table("map packs", 0x0F5600, 1, 416),
    J.Table("encounter rates", 0x0F5800, 1, 0xE8),
    J.Table("map properties", 0x2D8F00, 33, 416, mod=MAP_PROPS),
    J.Table("formation AP", 0x1FB400, 1, 512, mod=AP),
    J.Table("shops", 0x047AC0, 9, 128),
    J.Table("morph", 0x047F40, 4, 26),
    J.Table("sketches", 0x0F4300, 2, 384, mod=SKETCHES),
    J.Table("rages", 0x0F4600, 2, 256, mod=RAGES),
    J.Table("dances", 0x0FFE80, 4, 8),
    J.Table("natural magic", 0x2CE3C0, 2, 32),
    J.Table("blitz/bushido levels", 0x26F490, 1, 16),
    J.Table("level growth", 0x26F4A0, 1, 196),
]

IMAGE_SIZE = 0x400000
IMG_AI_PTRS, IMG_AI_DATA = 0x300000, 0x300400   # past the US ROM's 3 MB: T-Edition's AI (30 KB)
# T-Edition's grown tables, whole, past the AI (0x300000-0x3103FF) in the image (ff6snes.extended;
# port_monster_ext), each with room for EXT_ROOM records (EX's bosses go on past T-Edition's: ted_ex.ex_records):
# (name, T-Edition's file offset, record size, count)
EXT_BASE, EXT_ROOM = 0x320000, 1024
EXT_TABLES = [
    ("formations", FORMATIONS, 15, 768),
    ("formation_flags", FORMATION_FLAGS, 4, 768),
    ("formation_ap", AP, 1, 768),
    ("monsters", MONSTERS, 32, 512),
    ("monster_items", MONSTER_ITEMS, 8, 512),   # written as the US layout's 4 bytes
    ("sketches", SKETCHES, 2, 512),
    ("monster_graphics", 0x0F1A00, 5, 512),     # CF/1A00 (C1/2064, C1/24E6, C3/B8CC; vanilla D2/7000)
    ("map_properties", MAP_PROPS, 33, 512),
    ("items", ITEMS, 30, ITEM_COUNT),          # all 280: 256-279 are its second bank of relics (ff6snes.items)
]
ENEMY_NAMES_512 = 0x55D650, 20, 512   # "ENEMY NAMES LONG": all 512
SPECIAL_NAMES = 0x54D730, 20, 512     # "ENEMY MOVES BEGN": each monster's special attack name
# Monster sprites (T-Edition's C1/2045 hook stores the monster id at $6400, C0/D978 picks the tiles'
# bank by it): tiles at F0/0000 + 8 x pointer (vanilla E9/7000), F4/0000 for monsters 417-431, F5/0000
# for 480-511; palettes 41/6200 (vanilla D2/7820); stencils as vanilla (D2/A820, its big ones moved)
SPRITE_PALETTES = 0x416200


def word(d, a):
    return d[a] | d[a + 1] << 8


def formation_monsters(d, base, f):
    r = d[base + 15 * f:base + 15 * f + 15]
    return [r[2 + s] | ((r[14] >> s & 1) << 8) for s in range(6) if r[1] >> s & 1]


class _Image:
    data = None
    mod = None      # Mato's ROM as it is (T-Edition's own layout)
    report = []
    names = None


def build():
    """The US-layout image of T-Edition (cached), registered in ff6snes.MEMORY under the Mato ROM's
    path, and T-Edition's AI hooked into snes_ai.script."""
    if _Image.data is not None:
        return _Image.data
    with open(MATO, "rb") as f:
        mod = f.read()
    jp = S.rom_bytes(J.jp_rom_path())
    us = S.rom_bytes(P.VANILLA_ROM)
    img, stats = J.build_us_image(mod, jp, us, TABLES, IMAGE_SIZE)
    rep = ["T-Edition 3.0.7 (Mato) -> US layout: records T-Edition changed (vs the JP ROM), by table"]
    rep += [f"  {name}: {c} of {n}" for name, (c, n) in stats.items()]

    # T-Edition grew the monster and formation tables (512 / 768; the US layout holds 384 / 576): the
    # whole grown tables go past 3 MB in the image too, registered below for the porter
    # (ff6snes.extended; tools/port_monster_ext.py: PR monster rows 1000 + e, parties for formations
    # 576-767 and for those under 576 that now hold new monsters). Packs keep T-Edition's formations.
    new_monsters = sorted({e for f in range(768) for e in formation_monsters(mod, FORMATIONS, f) if e >= 384})
    under = [f for f in range(576) if any(e >= 384 for e in formation_monsters(mod, FORMATIONS, f))]
    new_forms = {f for f in range(576, 768) if any(mod[FORMATIONS + 15 * f:FORMATIONS + 15 * f + 15])}
    ext, at = {}, EXT_BASE
    ex, ex_note = ex_records()
    for name, src, size, count in EXT_TABLES:
        raw = mod[src:src + size * count]
        if name == "monster_items":   # T-Edition's 8 bytes -> the US layout's 4
            size, raw = 4, b"".join(monster_items(raw[8 * e:8 * e + 8]) for e in range(count))
        img[at:at + len(raw)] = raw
        for i, rec in sorted((ex.get(name) or {}).items()):   # EX's records past T-Edition's (ids it renumbered)
            rec = monster_items(rec) if name == "monster_items" else bytes([rec]) if isinstance(rec, int) else rec
            assert len(rec) == size and i < EXT_ROOM, (name, i)
            img[at + size * i:at + size * (i + 1)] = rec
            count = max(count, i + 1)
        ext[name] = (at, size, count)
        at += (size * EXT_ROOM + 0xFF) & ~0xFF
    # the second bank's menu names (US font, 13 bytes; Mato's full names come through hook_readers)
    long = mato_names(mod)
    ext["item_names"] = (at, 13, ITEM_COUNT)
    for i in range(256, ITEM_COUNT):
        img[at + 13 * i:at + 13 * (i + 1)] = J.encode_us_name(long.items[i][:12], 13, 0xFF)
    at += (13 * EXT_ROOM + 0xFF) & ~0xFF
    assert at <= IMAGE_SIZE
    refs = sum(1 for p in range(256) for k in range(4) if (word(img, 0x0F4800 + 8 * p + 2 * k) & 0x3FF) >= 576)
    erefs = sum(1 for p in range(256) for k in range(2) if (word(img, 0x0F5000 + 4 * p + 2 * k) & 0x3FF) >= 576)
    rep.append(f"  new monsters (384-511) in T-Edition's formations: {len(new_monsters)}; formations "
               f"576-767 in use: {len(new_forms)}; formations under 576 now holding new monsters: {len(under)}")
    rep.append(f"  grown tables past 3 MB (port_monster_ext): {', '.join(ext)}; random pack slots on "
               f"formations 576+: {refs}, event pack slots: {erefs}")

    # chests: T-Edition's 513 offsets (maps 0-511) into its own data; the US layout has 416 maps
    ptrs = [word(mod, CHEST_PTRS + 2 * m) for m in range(513)]
    jptr = [word(jp, 0x2D82F4 + 2 * m) for m in range(417)]
    out, offs, changed_maps, new_map_chests = bytearray(), [], 0, 0
    for m in range(416):
        offs.append(len(out))
        mine = mod[CHEST_DATA + ptrs[m]:CHEST_DATA + ptrs[m + 1]]
        vanilla = jp[0x2D8634 + jptr[m]:0x2D8634 + jptr[m + 1]]
        changed_maps += mine != vanilla
        out += mine
    offs.append(len(out))
    new_map_chests = (ptrs[511] - ptrs[416]) // 5   # 511 maps; ptrs[511] ends the table
    room = 0x2D8F00 - 0x2D8634
    if len(out) > room:
        raise SystemExit(f"T-Edition's chests ({len(out)} bytes) don't fit the US table ({room})")
    img[0x2D8634:0x2D8634 + len(out)] = out
    for m, o in enumerate(offs):
        img[0x2D82F4 + 2 * m:0x2D82F4 + 2 * m + 2] = o.to_bytes(2, "little")
    rep.append(f"  chests: {len(out) // 5} on maps 0-415 ({changed_maps} maps' chests changed), "
               f"{new_map_chests} on new maps 416-511")
    new_maps = sum(1 for m in range(416, 512) if any(mod[MAP_PROPS + 33 * m:MAP_PROPS + 33 * m + 33]))
    rep.append(f"  maps 416-511 with properties (new maps): {new_maps}")

    # AI: T-Edition's 30 KB of scripts don't fit the US table (14.6 KB): past the 3 MB, read through
    # the snes_ai.script hook below
    img[IMG_AI_PTRS:IMG_AI_PTRS + 1024] = mod[AI_PTRS:AI_PTRS + 1024]   # all 512 monsters' (384+: port_monster_ext)
    ai = mod[AI_DATA:AI_DATA + 0x10000]   # (the ROM ends 0xA710 bytes after AI_DATA: a shorter slice
    img[IMG_AI_DATA:IMG_AI_DATA + len(ai)] = ai   # here would shrink the image and move what follows)
    ai_changed = sum(A.parse(img, IMG_AI_DATA + word(img, IMG_AI_PTRS + 2 * e)) !=
                     A.parse(jp, A.AI_DATA + word(jp, A.AI_PTRS + 2 * e)) for e in range(384))
    rep.append(f"  monster AI: {ai_changed} of 384 scripts changed "
               f"({max(word(mod, AI_PTRS + 2 * e) for e in range(384))} bytes of scripts)")
    sprites = sum(mod[0x127000 + 5 * e:0x127005 + 5 * e] != jp[0x127000 + 5 * e:0x127005 + 5 * e] for e in range(384))
    rep.append(f"  monster sprite entries T-Edition changed (graphics not carried over): {sprites}")
    rep.append("  per-character HP/MP growth (T-Edition's own code, C0/A1C8): not carried over")

    data = bytes(img)
    S.MEMORY[os.path.abspath(MATO)] = data
    _Image.data, _Image.mod, _Image.report = data, mod, rep
    import port_monster_ext as X
    names, specials = long_names(mod, ENEMY_NAMES_512), long_names(mod, SPECIAL_NAMES)
    for lst, key in ((names, "monster_names"), (specials, "special_names")):
        for i, n in sorted((ex.get(key) or {}).items()):
            lst += [""] * (i + 1 - len(lst))
            lst[i] = n
    X.register(data, ext, monster_base=1000, monster_names=names, special_names=specials,
               sprites=MonsterSprites(mod, ex_sprites() if ex else None), event_maps=event_maps(),
               formation_monsters=ex.get("formation_monsters") or {},
               event_backgrounds={**event_backgrounds(mod), **(ex.get("event_backgrounds") or {})},
               drop_slots={i: list(rec[4:8]) for i, rec in (ex.get("monster_items") or {}).items()},   # EX's 4 slots
               map_packs=new_map_packs(), map_sets_file="ted_map_sets.json",   # PR sets for the new maps' packs
               chest_item_bank=CHEST_ITEM_BANK)
    rep.append(f"  EX (tools/ted_ex.py ex_records): {ex_note}")
    hook_readers(mato_names(mod))
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(rep) + "\n")
    print("\n".join(rep))
    return data


def ex_records():
    """(EX's records for the grown tables, a note): tools/ted_ex.py's ex_records() (the ted-ex workstream: EX's
    bosses as monsters 512-539, formations 768-792), or nothing when it can't give them (logged, the build goes on)."""
    try:
        import ted_ex
        ex = ted_ex.ex_records()
    except Exception as err:   # the EX workstream's module: its trouble mustn't stop T-Edition's builds
        return {}, f"not added ({type(err).__name__}: {err})"
    return ex, (f"monsters {min(ex['monsters'])}-{max(ex['monsters'])}, formations {min(ex['formations'])}-"
                f"{max(ex['formations'])}" if ex.get("monsters") and ex.get("formations") else "none")


def ex_sprites():
    """EX's monster sprites (ted_ex.ExSprites: 512-539), or None when the EX workstream can't give them."""
    try:
        import ted_ex
        return ted_ex.ExSprites()
    except Exception:
        return None


def long_names(mod, table):
    a, w, n = table
    return [mato_text(mod[a + w * i:a + w * (i + 1)]) for i in range(n)]


def new_map_packs():
    """{SNES map: (pack, battle background)} of T-Edition's new maps with random battles (ted-maps' data/ted_maps.json:
    maps.<m>.pack, properties byte 2): port_monster_ext makes PR monster sets for them, written to ted_map_sets.json
    beside the port, which ted-maps' build reads for the new maps' monster_set_id."""
    import json
    path = os.path.join(P.ROOT, "data", "ted_maps.json")
    try:
        maps = json.load(open(path, encoding="utf-8"))["maps"]
    except (OSError, ValueError, KeyError):
        return {}
    out = {}
    for m, v in maps.items():
        if v.get("random_battles") in (True, "True") and v.get("properties"):
            out[int(m)] = (int(v["pack"]), bytes.fromhex(v["properties"])[2])
    return out


def event_maps():
    """{formation: [SNES maps]} where T-Edition's events fight it (ted-events' catalog,
    data/snes_event_ted_catalog.json, when built): the porter's default look for their parties."""
    import json
    path = os.path.join(P.ROOT, "data", "snes_event_ted_catalog.json")
    if not os.path.exists(path):
        return {}
    out = {}
    for ev in json.load(open(path, encoding="utf-8")):
        for b in ev.get("battles") or []:
            out.setdefault(b["formation"], set()).add(ev["map"])
    return {f: sorted(m) for f, m in out.items()}


def event_backgrounds(mod):
    """{formation: SNES battle background} that T-Edition's event battles ask for (the battle command 4C/4D's
    second byte at each battle of ted-events' catalog; low 6 bits 0x3F = the map's own, left to event_maps):
    the commonest where one formation is fought on several."""
    import collections
    import json
    path = os.path.join(P.ROOT, "data", "snes_event_ted_catalog.json")
    if not os.path.exists(path):
        return {}
    votes = collections.defaultdict(collections.Counter)
    for ev in json.load(open(path, encoding="utf-8")):
        for b in ev.get("battles") or []:
            bank, off = b["at"].split("/")
            a = ((int(bank, 16) - 0xC0) << 16) | int(off, 16)
            if mod[a] in (0x4C, 0x4D) and mod[a + 1] == b["pack"] and mod[a + 2] & 0x3F != 0x3F:
                votes[b["formation"]][mod[a + 2] & 0x3F] += 1
    return {f: c.most_common(1)[0][0] for f, c in votes.items()}


class MonsterSprites:
    """T-Edition's monster sprites as snes_sprites.Sprites reads vanilla's (entries CF/1A00, tiles by
    monster id, palettes 41/6200): port_monster_ext matches each new monster with vanilla's art."""

    def __init__(self, mod, past=None):
        import snes_sprites as SS
        self.past = past   # a reader for monsters 512+ (EX's: ted_ex.ExSprites)

        class _Rom:
            data = mod

            def b(self, a, n):
                return mod[a:a + n]

        class _Sprites(SS.Sprites):
            def entry(self, i):
                e = mod[0x0F1A00 + 5 * i:0x0F1A05 + 5 * i]
                return e[0] | e[1] << 8, bool(e[2] & 0x80), (e[2] & 3) << 8 | e[3], e[4]

            def palette(self, pal_index, bpp3):
                raw = mod[SPRITE_PALETTES + 16 * pal_index:SPRITE_PALETTES + 16 * pal_index + (16 if bpp3 else 32)]
                return [SS.snes_rgb(raw[2 * k] | raw[2 * k + 1] << 8) for k in range(len(raw) // 2)]

            def sprite(self, i):
                self.bank = 0xF5 if i >= 0x1E0 else 0xF4 if 0x1A1 <= i < 0x1B0 else 0xF0
                return super().sprite(i)

            def tile(self, at, bpp3):   # snes_sprites asks for E9/7000 + 8 x pointer + n
                return super().tile(((self.bank - 0xC0) << 16) + at - SS.GFX, bpp3)
        self._s = _Sprites(_Rom())

    def sprite(self, e):
        if e < 512:
            return self._s.sprite(e)
        return self.past.sprite(e) if self.past is not None else None   # EX's (512+) are in EX's ROM


def shops_data(rom):
    """{"pairs": {SNES shop: PR product group the porter matched (port_shops.pairs)}, "unmatched": {SNES shop:
    [content ids]}} for T-Edition's 128 shops (the US-layout image's table: shop type byte, 8 item slots): a shop with
    stock the porter paired with no PR group (T-Edition's own shops: repopulated Narshe, Kohlingen WoB...) gets a group of
    its own from ted_build.shop_rule, which completes "shops" {SNES shop: group} for ted-events' TED:shop."""
    import sys
    port_mod = next((m for m in (sys.modules.get("port"), sys.modules.get("__main__"))
                     if m is not None and hasattr(getattr(m, "port_shops", None), "pairs")), None)
    pairs = {}
    for shop, g in (port_mod.port_shops.pairs if port_mod else []):
        pairs.setdefault(str(shop), g)
    unmatched = {}
    for shop in range(128):
        raw = rom.data[0x047AC0 + 9 * shop:0x047AC0 + 9 * shop + 9]
        stock = [M.item_content(x) for x in raw[1:] if x != 0xFF]
        if stock and str(shop) not in pairs:
            unmatched[str(shop)] = {"type": raw[0], "stock": [c for c in stock if c]}
    return {"pairs": pairs, "unmatched": unmatched}


FORMATION_REWARDS = 0x4B4A00   # 4B/4A00: one byte per formation, FF none, else second-bank item 256 + n (C2/FC40 -> 4E/0D30)
COLISEUM = 0x10F140, 4, 280   # D0/F140: per wagered item (id + 256 x bank flag): opponent, ?, reward, hidden (C3/BB99)


def rewards_data():
    """T-Edition's item rewards the PR has no data column for, for TedPlugin (ted-monsters; pr notes ted-items2):
    - "boss_rewards" {PR party: content id}: a boss formation's extra item, added at victory (21 formations; the
      phase formations a fight changes into (no pack names them: 677, 688, 698, 699) also on the parties of the formations
      whose monsters' scripts change into them, since the PR fight keeps its party);
    - "coliseum" [[wager content, 0, 0, party, reward content, hidden, PR monster]] for every wager (WcColiseum's rows:
      a match's opponent party as seed_info.coliseum picks it; records 256-278 give their wager back, 279 can't be wagered).
    Second-bank items (256-279) have content ids once item identity sees them (the held kit patches): till then their
    entries are left out. Medium confidence on the banking of both (ted-items2/FINDINGS.md): confirm in the PR runs."""
    import csv
    import collections
    import port_encounters as E
    import port_monster_ext as X
    import snes_ai as A
    mod, data = _Image.mod, _Image.data
    rom = S.Rom(MATO)
    tables = X._STATE.get("tables") or {}
    mp = tables.get("monster_party") or P.Table("monster_party")

    def content(i):
        try:
            return M.item_content(i) if i != 0xFF else 0
        except Exception:  # noqa: BLE001 - an item with no PR row (yet)
            return 0

    def parties(f):
        out = list(E.party_ids(f, mp.rows))
        if f < 576 and M.party(f) in mp.rows:
            out.append(M.party(f))
        return out
    changes = collections.defaultdict(set)   # a formation -> the formations whose monsters' scripts change into it
    for g in range(X.formation_count(rom)):
        for e in X.members(rom, g):
            if e >= 512:
                continue
            main, counter = A.script(rom, e)
            for op, args in main + counter:
                if op == "formation":
                    changes[(args[1] | args[2] << 8) & 0x3FF].add(g)
    rewards, phases = {}, {}
    for f in range(768):
        b = mod[FORMATION_REWARDS + f]
        if b == 0xFF:
            continue
        cid = content(256 + b)
        ps = parties(f)
        if changes.get(f):   # also on the fights that change into it (the PR fight keeps its party to the end)
            ps += [p for g in sorted(changes[f]) for p in parties(g)]
            phases[f] = sorted(changes[f])
        for p in ps:
            if cid:
                rewards.setdefault(str(p), cid)
    # the Coliseum: an opponent's party as WcColiseum expects (seed_info.coliseum's pick: its Coliseum copy, else a
    # battle with it alone)
    master = os.path.join(P.VANILLA, "master", "Assets", "GameAssets", "Serial", "Data", "Master")
    key = {int(r["id"]): r["mes_id_name"] for r in csv.DictReader(open(os.path.join(master, "monster.csv"), encoding="utf-8"))}
    party_of_key, alone = {}, {}
    for r in P.Table("monster_party"):
        ms = [int(r[f"monster{k}"]) for k in range(1, 10) if r[f"monster{k}"] not in ("0", "")]
        if len(ms) == 1:
            if int(r["id"]) >= 1000 and key.get(ms[0]):
                party_of_key.setdefault(key[ms[0]], int(r["id"]))
            elif int(r["id"]) < 1000:
                alone.setdefault(ms[0], int(r["id"]))
    at, size, count = COLISEUM
    coliseum = []
    for wager in range(count):
        if wager in (0xFF, 279):
            continue
        rec = mod[at + size * wager:at + size * (wager + 1)]
        wc = content(wager)
        reward = content(rec[2] + (256 if wager >= 256 else 0)) if rec[2] != 0xFF else 0
        if wc <= 0:
            continue
        opp = M.monster(rec[0])
        coliseum.append([wc, 0, 0, party_of_key.get(key.get(opp)) or alone.get(opp, 0), reward, int(rec[3] != 0), opp])
    return {"boss_rewards": rewards, "phase_formations": {str(f): g for f, g in phases.items()},
            "coliseum": coliseum}


class Names:
    def __init__(self, items, item_icons, spells, spell_icons, monsters, characters):
        self.items, self.item_icons, self.spells, self.spell_icons = items, item_icons, spells, spell_icons
        self.monsters, self.characters = monsters, characters


def mato_names(mod):
    """T-Edition's names in Mato's full-length tables, by T-Edition's own slots."""
    def text(tab, i):
        a, w, _ = tab
        return mato_text(mod[a + w * i:a + w * (i + 1)])
    items = [text(LONG_ITEMS, i) for i in range(ITEM_COUNT)]
    item_icons = [mod[LONG_ITEMS[0] + LONG_ITEMS[1] * i] for i in range(ITEM_COUNT)]
    spells = [text(LONG_MAGIC, i) for i in range(54)] + [text(LONG_ATTACKS, i) for i in range(202)]
    spell_icons = [mod[0x55C730 + 9 * i] for i in range(54)] + [None] * 202   # "LARG MAG W ICONS"
    monsters = [text(LONG_MONSTERS, e) for e in range(384)]
    characters = [mato_text(mod[CHAR_NAMES + 6 * c:CHAR_NAMES + 6 * c + 6]) for c in range(14)]
    return Names(items, item_icons, spells, spell_icons, monsters, characters)


def hook_readers(names):
    """The porter's readers see T-Edition through the US layout; these give it what that layout
    can't hold: the AI past 3 MB, and Mato's full names (so the spell porter's look-by-name
    templates follow T-Edition's re-slotted spells). Other ROMs read as before."""
    _Image.names = names
    script, items, spell_names, espers = A.script, S.items, S.spell_names, S.espers

    def ai_script(rom, enemy_id):
        if rom.data is _Image.data:
            return A.parse(rom.data, IMG_AI_DATA + word(rom.data, IMG_AI_PTRS + 2 * enemy_id))
        return script(rom, enemy_id)

    def mod_items(rom):
        out = items(rom)
        if rom.data is _Image.data:
            for it in out:
                it.name = names.items[it.id] or it.name
        return out

    def mod_spell_names(rom):
        out = spell_names(rom)
        if rom.data is _Image.data:
            out = [names.spells[i] or n for i, n in enumerate(out)]
        return out

    def mod_espers(rom):
        out = espers(rom)
        if rom.data is _Image.data:
            for e in out:
                e.name = names.spells[54 + e.id] or e.name
        return out
    A.script, S.items, S.spell_names, S.espers = ai_script, mod_items, mod_spell_names, mod_espers


def same_name(a, b):
    norm = lambda s: "".join(ch for ch in s.lower() if ch.isalnum())
    return norm(a) == norm(b)


def icon_tags(pairs):
    """Mato icon byte -> the PR's <IC_...> tag, learned from slots whose name is the PR's."""
    import collections
    votes = collections.defaultdict(collections.Counter)
    for byte, tag in pairs:
        if byte is not None and tag:
            votes[byte][tag] += 1
    return {b: c.most_common(1)[0][0] for b, c in votes.items()}


class TEdition(Profile):
    name = "tedition"
    mod_name = "TEdition"
    rename_all = False

    @property
    def out(self):
        """The porter's own output: tools/ted_build.py merges it with the workstreams' folders into
        mods/TEdition (what is installed), so a bare `port.py tedition` never overwrites that."""
        return os.path.join(P.ROOT, "mods", "TEditionPort")

    # T-Edition rebuilt FF6's item list (110 vanilla items in other slots, weapons in shield slots...):
    # each slot's PR row and look by name and kind (tools/item_identity.py)
    item_identity = True
    # its four drop slots: the PR picks a drop slot by these game-wide odds (MONSTER_DROP_RATE_1..8);
    # its damage cap 32000 (C2/0C88) and Near Fatal at a quarter of max HP (C2/4523): pr/ted/BATTLE_SPEC.md 12, 47
    game_constants = dict({f"MONSTER_DROP_RATE_{k + 1}": (odds, 0) for k, odds in enumerate(DROP_ODDS + (0,) * 4)},
                          MAX_HIT_VALUE=(32000, 0), RATE_HAVE_NEAR_DEATH=(4, 0))
    # Image is lost on a dodge half the time (vanilla a quarter; C2/232C): the spec's rule 22
    condition_tuning = {19: {"until_value": "50"}}
    # monsters on T-Edition's own SNES AI in the plugin (the kit's SnesAiHost; TedPlugin/TedEnemyAi.cs): no AI engine
    # changes in the spec, status effects of scripts off until its fights are tested (the plugin's [Battle] option)
    snes_ai = True
    snes_ai_rules = "vanilla"
    snes_ai_status = False
    # the battle bits T-Edition's monster scripts read (FC 0C/0D/14/15) or write (F8/F9), from a scan of all 512 scripts
    # (ted-ex, 2026-11-21): port_ai gives them PR flags from the event sessions' shared allocator, so scenes and fights
    # see the same bit
    snes_ai_event_bits = [*range(0x00, 0x08), 0x29, 0x41, 0x48, 0x49, 0x4C, 0x4D, *range(0x60, 0x68)]
    snes_event_alloc = os.path.join(P.ROOT, "data", "snes_event_alloc_tedition.json")
    # T-Edition's Veldt records every won formation up to $1FF (C2/49D4: the "not on the Veldt" check is gone; the spec's rule 58)
    veldt_all_formations = True
    # every weapon's critical hit rate: T-Edition rolls random(256) < 20 (vanilla < 8; C2/33FE): the spec's rule 18
    weapon_critical_rate = 8
    # relic command swaps (the spec's rule 31): T-Edition's 8 swaps (CE/01E8 -> CE/01F8, C2/5390) are item byte 10
    # bit 7 - k for entry k, not vanilla's bits 2-6 (its Gem Box has bit 4, vanilla's Fake Mustache's): every bit by
    # hand, PR command ids by port.SNES_CMD (function 61: from, to). Pray, Spirit and Animal are the vanilla command
    # rows 27, 29 and 24 that ted_build.command_rule turns into them
    relic_bit_funcs = {(10, 7): {(61, 10, 11, 0)},   # Steal -> Capture (Thief Gloves)
                       (10, 6): {(61, 20, 21, 0)},   # Slot -> GP Rain (Heiji's Jitte)
                       (10, 5): {(61, 9, 28, 0)},    # Morph -> Shock (Zeidrich)
                       (10, 4): {(61, 7, 31, 0)},    # Magic -> X-Magic (Gem Box)
                       (10, 3): {(61, 1, 30, 0)},    # Fight -> Jump (Dragoon Boots, Dragon Horn)
                       (10, 2): {(61, 16, 27, 0)},   # Runic -> Pray (Maiden's Prayer)
                       (10, 1): {(61, 18, 29, 0)},   # Sketch -> Spirit (Embroidered Tippet)
                       (10, 0): {(61, 22, 24, 0)},   # Dance -> Animal (Pheasant Strap)
                       # passive bits on T-Edition's other items, as the PR's wear function 62 on vanilla's own (TedPlugin
                       # decoded them, the audit's I5; the rest, PR-hardcoded per item id, are TedPlugin's TedRelics)
                       (9, 2): {(62, 286, 0, 0)},    # HP +25% (Red Cap's): Mutsunokami, Grand Helm, Maximillian
                       (9, 3): {(62, 288, 0, 0)},    # HP +50% (Muscle Belt's): Floral Fallal
                       (12, 0): {(62, 253, 0, 0)}}   # Offering's four hits: Elven Dart, Offering

    def extra_data(self, rom):
        """Data beside the Magicite groups for T-Edition's other tools and its plugin.
        ted_items.json: each item slot's PR table, row and content id as the item identity step chose them
        (rows it made exist only after the port), so ted_maps fills new maps' chests from it."""
        items = {}
        names = _Image.names.items if _Image.names else []
        for s in [i for i in range(280) if i != 255]:   # 256-279: the second bank (rows once item identity sees them)
            m = M.item(s)
            if m:
                items[str(s)] = {"table": m[0], "id": m[1], "content": M.item_content(s),
                                 "name": names[s] if s < len(names) else ""}
        out = {"ted_items.json": {"items": items}}
        # ted_rewards.json: T-Edition's boss rewards and Coliseum for TedPlugin (ted-monsters; rewards_data)
        out["ted_rewards.json"] = rewards_data()
        # ted_shops.json: every SNES shop's PR product group (ted_build.shop_rule makes groups for the unmatched ones)
        out["ted_shops.json"] = shops_data(rom)
        # ted_ai.json: the monsters' SNES scripts for the plugin's SnesAiHost (TedEnemyAi reads it from BepInEx/TEdition)
        import port_ai
        sa = getattr(port_ai.port, "snes_ai", None)
        if sa is not None and self.snes_ai:
            import port_monster_ext
            port_monster_ext.snes_ai_extend(sa)   # T-Edition's monsters 384-511 and formations 576-767 (ted-monsters)
            out["ted_ai.json"] = {"snes_ai": sa}
        return out

    def item_mod_items(self, rom):
        import item_identity as I
        items = I.mod_items_from(rom, _Image.names.items, _Image.names.item_icons)
        for mi in items:   # a second name where Mato's matches no PR/SNES name (Experience Egg: the SNES's Exp. Egg)
            alias = ITEM_SNES_NAMES.get(mi.names[0]) if mi.names else None
            if alias:
                mi.names.append(alias)
        return items

    def monster_drop_slots(self, e):
        """T-Edition's four drop slots of monster e (SNES item ids, 0xFF empty), in DROP_ODDS order."""
        return list(_Image.mod[MONSTER_ITEMS + 8 * e + 4:MONSTER_ITEMS + 8 * e + 8])

    @property
    def rom(self):
        build()
        return MATO

    def rage_descriptions(self):
        """No texts of T-Edition's own: port_dances.describe_rages then names each Rage's attacks from its ported
        abilities (what the Rage menu shows in T-Edition: the attack)."""
        return {}

    def descriptions(self):
        """Mato's descriptions by slot: items 0-255 (the porter's slots; T-Edition's second bank 256-279
        is mato_descriptions()["items"][256:]), spells 0-53, Lores."""
        d = mato_descriptions()
        return {"items": d["items"][:256], "spells": d["spells"], "lores": d["lores"]}

    def vanilla_descriptions(self):
        """What the porter compares Mato's descriptions with (it writes a slot's text where the two differ):
        a slot T-Edition left as FF6 had it keeps the PR's own text, every other slot gets Mato's. Left as
        it was: the item record of the vanilla item whose PR row the slot has (item_identity's baseline)
        the same but for who equips it and its price; a spell's record the same but for its MP cost.
        That keeps 12 of 255 items and 4 of 78 spells and Lores in the PR's words."""
        d = mato_descriptions()
        img, van = _Image.data, S.Rom(P.VANILLA_ROM).data
        base = S.MEMORY.get(os.path.abspath(P.VANILLA_ROM) + "#item-identity", van)   # the porter's (item_identity.prepare)
        at, size = S.ITEMS[0], S.ITEMS[1]

        def same(a, b, skip):
            return all(a[k] == b[k] for k in range(len(a)) if k not in skip)
        items = [text if i < 255 and same(img[at + size * i:at + size * (i + 1)], base[at + size * i:at + size * (i + 1)],
                                          (1, 2, 28, 29)) else None
                 for i, text in enumerate(d["items"][:256])]
        sp, n = SPELL_RECORDS

        def spell(i):
            return same(img[sp + n * i:sp + n * (i + 1)], van[sp + n * i:sp + n * (i + 1)], (5,))
        return {"items": items,
                "spells": [t if spell(i) else None for i, t in enumerate(d["spells"])],
                "lores": [t if spell(LORE_FIRST + i) else None for i, t in enumerate(d["lores"])]}

    def extra_messages(self, rom):
        """The final name of every slot T-Edition names: the PR's own text where Mato's name is the
        same (the porter wrote Mato's spelling over it), else Mato's full name with the icon of
        T-Edition's item/spell type. Also counts names that moved to another slot (re-slotted)."""
        names = _Image.names
        vmsg = P.messages()
        content = P.Table("content")
        content4 = {int(r["type_value"]): r for r in content if r["type_id"] == "4"}
        mo = P.Table("monster")
        out, counts = {}, {}

        def tag(text):
            return text[:text.index(">") + 1] if text.startswith("<IC_") else ""

        def slots(kind):
            if kind == "items":
                for i in range(len(names.items)):   # 256-279: the second bank (its rows keep their old names otherwise)
                    m = M.item(i)
                    cid = M.content_id(*m) if m else None
                    if cid in content.rows:   # a new row (item_identity) was named when it was made
                        yield i, content[cid]["mes_id_name"], names.items[i], names.item_icons[i]
            elif kind == "spells":
                for i in range(256):
                    if M.spell(i) in content4:
                        yield i, content4[M.spell(i)]["mes_id_name"], names.spells[i], names.spell_icons[i]
            elif kind == "monsters":
                for e in range(384):
                    if e + 1 in mo.rows:
                        yield e, mo[e + 1]["mes_id_name"], names.monsters[e], None
            else:
                for c in range(14):
                    yield c, f"MSG_CHAR_NAME_{c + 1:02d}", names.characters[c], None

        for kind in ("items", "spells", "monsters", "characters"):
            rows = [r for r in slots(kind) if r[1] in vmsg and r[2]]   # keys the game's text has
            pr_names = {"".join(ch for ch in P.strip_tags(vmsg.get(k, "")).lower() if ch.isalnum()) for _, k, _, _ in rows}
            icons = icon_tags((byte, tag(vmsg.get(k, ""))) for _, k, n, byte in rows
                              if same_name(P.strip_tags(vmsg.get(k, "")), n))
            same = renamed = moved = 0
            for i, key, name, byte in rows:
                old = vmsg.get(key, "")
                if same_name(P.strip_tags(old), name):
                    out[key] = old
                    same += 1
                    continue
                out[key] = icons.get(byte, tag(old)) + name
                if "".join(ch for ch in name.lower() if ch.isalnum()) in pr_names:
                    moved += 1
                else:
                    renamed += 1
            counts[kind] = f"{same} as the PR's, {moved} moved from another slot, {renamed} new or renamed"
        line = "names (Mato's full names vs the PR's, by slot): " + "; ".join(f"{k}: {v}" for k, v in counts.items())
        print(line)
        _Image.report.append("  " + line)
        # the rows item_identity made start with their template's description: Mato's instead
        descs, made = mato_descriptions()["items"], 0
        for i in [i for i in range(len(descs)) if i != 255]:
            m = M.item(i)
            row = content.rows.get(M.content_id(*m)) if m else None
            # (256-279, the second bank: every row, as port_item_text describes slots 0-255 only)
            if row and (row["mes_id_description"].startswith("MSG_PORT_") or i >= 256) and descs[i]:
                out[row["mes_id_description"]] = " ".join(descs[i].split("\n"))
                made += 1
        line = f"descriptions: Mato's on {made} new item rows (the PR's slots: port_item_text)"
        print(line)
        _Image.report.append("  " + line)
        # Mato's descriptions of the espers' summons, Bushido and Blitz (T-Edition changed all of them; port_spells
        # describes only spells and Lores for a mod that isn't rename_all): onto each slot's ability description key
        md, by_kind = mato_descriptions(), {}
        for kind, first in DESC_SLOTS.items():
            for k, text in enumerate(md[kind]):
                row = content4.get(M.spell(first + k))
                key = row["mes_id_description"] if row else ""
                if text and key not in ("", "None") and key in vmsg:
                    out[key] = " ".join(text.split("\n"))
                    by_kind[kind] = by_kind.get(kind, 0) + 1
        line = "descriptions: Mato's on " + ", ".join(f"{n} {k}" for k, n in by_kind.items())
        print(line)
        _Image.report.append("  " + line)
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write("\n".join(_Image.report) + "\n")
        return out


PROFILE = TEdition()

if __name__ == "__main__":
    sys.exit("run tools/port.py tedition")
