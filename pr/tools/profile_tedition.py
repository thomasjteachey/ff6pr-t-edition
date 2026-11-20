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
LONG_ITEMS = 0x59A560, 20, 256       # "LONG ITEMS BEGIN": icon + 19
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

    # formations that now hold T-Edition's new monsters (384+) keep the US formation (the PR has no
    # such monsters yet); packs and event packs pointing at formations 576+ (new) or at those fall
    # back on another formation of the same pack, or the US pack
    new_monsters = sorted({e for f in range(768) for e in formation_monsters(mod, FORMATIONS, f) if e >= 384})
    kept = [f for f in range(576) if any(e >= 384 for e in formation_monsters(mod, FORMATIONS, f))]
    for f in kept:
        img[0x0F6200 + 15 * f:0x0F6200 + 15 * f + 15] = us[0x0F6200 + 15 * f:0x0F6200 + 15 * f + 15]
    bad = set(kept)
    new_forms = {f for f in range(576, 768) if any(mod[FORMATIONS + 15 * f:FORMATIONS + 15 * f + 15])}

    def fix_packs(base, count, n):
        refs = lost = whole = 0
        for p in range(count):
            at = base + 2 * n * p
            ids = [word(img, at + 2 * k) for k in range(n)]
            ok = [v for v in ids if (v & 0x3FF) < 576 and (v & 0x3FF) not in bad]
            if len(ok) == n:
                continue
            refs += n - len(ok)
            if ok:
                for k, v in enumerate(ids):
                    if v not in ok:
                        img[at + 2 * k:at + 2 * k + 2] = ok[0].to_bytes(2, "little")
                lost += 1
            else:
                img[at:at + 2 * n] = us[at:at + 2 * n]
                whole += 1
        return refs, lost, whole
    pr, pl, pw = fix_packs(0x0F4800, 256, 4)
    er, el, ew = fix_packs(0x0F5000, 256, 2)
    rep.append(f"  new monsters (384-511) in T-Edition's formations: {len(new_monsters)}; formations "
               f"576-767 in use: {len(new_forms)}; formations under 576 now holding new monsters (kept US): {len(kept)}")
    rep.append(f"  random packs: {pr} formation slots on new formations/monsters ({pl} packs kept their "
               f"other formations, {pw} packs kept the US pack); event packs: {er} slots ({el} partly, {ew} US pack)")

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
    img[IMG_AI_PTRS:IMG_AI_PTRS + 768] = mod[AI_PTRS:AI_PTRS + 768]
    img[IMG_AI_DATA:IMG_AI_DATA + 0x10000] = mod[AI_DATA:AI_DATA + 0x10000]
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
    hook_readers(mato_names(mod))
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(rep) + "\n")
    print("\n".join(rep))
    return data


class Names:
    def __init__(self, items, item_icons, spells, spell_icons, monsters, characters):
        self.items, self.item_icons, self.spells, self.spell_icons = items, item_icons, spells, spell_icons
        self.monsters, self.characters = monsters, characters


def mato_names(mod):
    """T-Edition's names in Mato's full-length tables, by T-Edition's own slots."""
    def text(tab, i):
        a, w, _ = tab
        return mato_text(mod[a + w * i:a + w * (i + 1)])
    items = [text(LONG_ITEMS, i) for i in range(256)]
    item_icons = [mod[LONG_ITEMS[0] + LONG_ITEMS[1] * i] for i in range(256)]
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
    # its four drop slots: the PR picks a drop slot by these game-wide odds (MONSTER_DROP_RATE_1..8)
    game_constants = {f"MONSTER_DROP_RATE_{k + 1}": (odds, 0) for k, odds in enumerate(DROP_ODDS + (0,) * 4)}

    def item_mod_items(self, rom):
        import item_identity as I
        return I.mod_items_from(rom, _Image.names.items, _Image.names.item_icons)

    def monster_drop_slots(self, e):
        """T-Edition's four drop slots of monster e (SNES item ids, 0xFF empty), in DROP_ODDS order."""
        return list(_Image.mod[MONSTER_ITEMS + 8 * e + 4:MONSTER_ITEMS + 8 * e + 8])

    @property
    def rom(self):
        build()
        return MATO

    def descriptions(self):
        return None   # the PR's own descriptions (Mato's are pointer tables in his build: later)

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
                for i in range(256):
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
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write("\n".join(_Image.report) + "\n")
        return out


PROFILE = TEdition()

if __name__ == "__main__":
    sys.exit("run tools/port.py tedition")
