"""The data T-Edition's plugin (plugin/TedPlugin) reads, exported from the port.

    .venv/Scripts/python tools/ted_plugin_data.py [OUT.json]     (default build/t-edition/plugin/ted_data.json)

Installed as BepInEx/TEdition/ted_data.json (tools/ted_testinstall.py; plugin data stays out of the
plugins folder). Read by TedRules/TedData.cs, so the offline tests (plugin/Ted.Tests) check the same file:

  items              T-Edition's item slots (SNES ids) -> the PR content id and row item identity gave
                     each (tools/item_identity.py, as port.py does), and the name the game should show
                     (the port's message text over vanilla's): `tedcheck` compares the game's names
  new_weapons        the weapon rows the port added (92+: content id, attack, name)
  drop_rates         MONSTER_DROP_RATE_1.. as the port sets them; drop_monsters: monsters with 3-4 slots
  half_ignore_defense  monsters with T-Edition's monster byte $12 bit 1 ($3C95 bit 1, rule 9 of
                     pr/ted/BATTLE_SPEC.md): PR ids (SNES id + 1; 1000 + id for the new 384-511), and the SNES ids 384+
  esper_bonus_vanilla  vanilla's esper level-up bonus codes by magicite content id (rule 4: T-Edition has none)
  named, rows        content ids and table rows the rules test for (Orichalcum $66, Elven Darts $6C, Valiant
                     Knife, Atma Weapon, ...; the PR keys Atma and Valiant Knife on weapon rows 30 and 11)

Reads the port's output (mods/TEdition) and T-Edition's ROM (profile_tedition.MATO); run after port.py tedition.
"""
import csv
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitpath  # noqa: E402,F401
import ff6snes as S  # noqa: E402
import idmap as M  # noqa: E402
import item_identity as I  # noqa: E402
import prdata as P  # noqa: E402

MOD = os.path.join(P.ROOT, "mods", "TEdition")
OUT = os.path.join(P.ROOT, "build", "t-edition", "plugin", "ted_data.json")
MASTER = os.path.join("master", "Assets", "GameAssets", "Serial", "Data", "Master")
MESSAGE = os.path.join("message", "Assets", "GameAssets", "Serial", "Data", "Message", "system_en.txt")
TYPES = {"item": "1", "weapon": "2", "armor": "3"}
# SNES spells the rules name: effect $2A no longer split (rule 37: Mysidian Rabbit $FE, Heal Force $87, Flare Star $C6)
NAMED_SPELLS = {"mysidian_rabbit": 0xFE, "heal_force": 0x87, "flare_star": 0xC6,
               "rampage": 0xEF,   # Umaro's Fight with the Power Belt (battle_commands.md §11)
               **{f"desperation_{c}": 0xF0 + c for c in range(14)}}   # rule 39: spell $F0 + character index
# item slots the rules name (T-Edition's ids; pr/ted/battle_commands.md)
NAMED_SLOTS = {"orichalcum": 0x66, "elven_darts": 0x6C, "valiant_knife": 0x08, "atma_weapon": 0x61,
               "dancing_dagger": 0x06, "dice": 0x50, "fixed_dice": 0x52}


# --- rule 49: percent damage (pr/ted/BATTLE_SPEC.md) -------------------------------------------------------------
# T-Edition's percent spells (spell byte 4 bit 7, "damage = HP x power / 16": vanilla's Demi 8, Quarter 12, Tornado
# 15) take current HP only for the ten its code lists (40/7680, from C2/0D7F); every other one takes max HP. The PR's
# fraction damage is function type 33 of function_group.csv (BaseValueFixedHPFunction.Calc): value1 2, value2 the
# mode (2 current HP x value3 / 100, 3 current HP / value3, 4 max HP x value3 / 100, 5 max HP / value3).
KEEP_CURRENT_HP = (0x1E, 0x34, 0x6E, 0x72, 0x9D, 0xAE, 0xB2, 0xBD, 0xCD, 0xDD)   # Gravity .. Missile (T-Edition's ids)
PERCENT_FLAG = 0x80        # Spell.flags3 (byte 4) bit 7
FRACTION = 33              # the PR's fraction-damage function
RAISE, RERAISE_ABILITY = 0x2D, 290   # rule 57: Reraise revives with T-Edition's Raise; the PR casts ability 290
REVIVE = 34                # the PR's revive with HP, the same value layout (vanilla Raise 34,2,5,8 = power 2)
DAMAGE = (2, 3)            # the PR's Physical / Magic damage functions (port_spells)


def _fraction(power, current):
    """power/16 of HP as the PR's (mode, value3): an exact 1/n as mode 3/5, else a rounded percentage (mode 2/4)."""
    if 16 % power == 0:
        return (3 if current else 5), 16 // power
    return (2 if current else 4), int(power * 100 / 16 + 0.5)


def _share(mode, v3):
    return v3 / 100 if mode in (2, 4) else 1 / v3 if v3 else 0


# Umaro's Rampage (battle_commands.md §11: spell $EF, which the PR has no row for: idmap.spell(0xEF) is None):
# ability 9903 (reserved by ted_build: 9901/9902 Dancing Dagger / Animal), the PR's Snowstorm row (199, Umaro's) with
# T-Edition's numbers, physical damage (function group 27: the PR's plain physical) on every enemy, and its name.
RAMPAGE_ID, RAMPAGE_TEMPLATE, RAMPAGE_SPELL, PHYSICAL_GROUP = 9903, 199, 0xEF, 27
RAMPAGE_TEXT = "TED_ABILITY_RAMPAGE"


def rampage_rule(folder, log=print):
    """The Rampage ability row (+ its content row and name) in a staged port folder; idempotent."""
    import profile_tedition as T
    import ted_build as B
    T.build()
    sp = S.spells(S.Rom(T.MATO))[RAMPAGE_SPELL]
    name = (S.spell_names(S.Rom(T.MATO))[RAMPAGE_SPELL] or "Rampage").strip() or "Rampage"
    ab, ct = B.MasterRows(folder, "ability"), B.MasterRows(folder, "content")
    row = dict(ab.rows.get(RAMPAGE_TEMPLATE) or ab.van[RAMPAGE_TEMPLATE])
    row.update(id=str(RAMPAGE_ID), sort_id=str(RAMPAGE_ID), standard_value=str(sp.power), attribute_id="0",
               attribute_group_id="0", battle_function_group_id=str(PHYSICAL_GROUP), use_value="0")
    ab.add(row)
    src = next(r for r in ct.van if r["type_id"] == "4" and r["type_value"] == str(RAMPAGE_TEMPLATE))
    ct.add(dict(src, id=str(RAMPAGE_ID), type_value=str(RAMPAGE_ID), mes_id_name=RAMPAGE_TEXT))
    ab.save()
    ct.save()
    B.set_messages(folder, {RAMPAGE_TEXT: name})
    log(f"T-Edition Umaro: Rampage ability {RAMPAGE_ID} ('{name}', power {sp.power}, physical, all enemies; template {RAMPAGE_TEMPLATE})")


def data_rules(folder, log=print):
    """TedPlugin's data rules on a staged port folder (tools/ted_build.py calls it; idempotent)."""
    rampage_rule(folder, log)
    percent_damage(folder, log)
    chest_rule(folder, log)


CHEST_KEY = "TED_CHEST_{:02d}"   # + lead character 0-13 (TedChestLines.cs)


def chest_rule(folder, log=print):
    """Audit U9: T-Edition's chest line per lead character as text keys TED_CHEST_00..13 (English; the PR's own
    T0001_01_01 elsewhere and for Banon, Ghost, Leo or an empty lead slot): <CT> on every line as the PR's."""
    import ted_build as B
    lines = chest_lines()
    B.set_messages(folder, {CHEST_KEY.format(c): t.replace("\\n", "\\n<CT>") for c, t in enumerate(lines)})
    log(f"T-Edition chest lines: {len(lines)} keys {CHEST_KEY.format(0)}..{CHEST_KEY.format(len(lines) - 1)}")


def percent_damage(folder, log=print):
    """Rule 49 on a staged port folder (its partial function_group / ability / item CSVs over the game's;
    tools/ted_build.data_rules calls it; idempotent). For every ability row holding one of T-Edition's spells:
      * a percent spell: its group's fraction function at T-Edition's power, current HP for the ten listed
        spells and max HP for the rest; a group with no fraction function gets one in place of its damage
        function (Diabolos and Wave Cannon: the porter's templates are plain damage spells);
      * a spell that is no percent spell in T-Edition but sits on a fraction group (the porter's template was
        vanilla's percent spell of that name: Snowball, Mustard Bomb, ...): Magic or Physical damage instead;
    rows that hold none of T-Edition's spells (the PR's own monster-skill copies: 282 (unnamed), 1240 and 1503 Missile, 1443 Sonic
    Boom, 1537 Cave-In) and items stay as the PR has them. A group used by rows that now want
    different functions is cloned (new ids after the table's highest) and those rows repointed. Revives (type 34,
    the same layout) get T-Edition's power of max HP (Raise 4 = 1/4, Phoenix 10); the fraction modes of other
    formulas (value1 1: Revenge, Self-Destruct) are left as they are."""
    import profile_tedition as T
    import ted_build as B
    T.build()
    rom = S.Rom(T.MATO)
    spells, names = S.spells(rom), S.spell_names(rom)
    ab, fg, it = B.MasterRows(folder, "ability"), B.MasterRows(folder, "function_group"), B.MasterRows(folder, "item")
    spell_of = {}
    for i in range(255):
        k = M.spell(i)
        if k is not None:
            spell_of.setdefault(k, i)

    def current(table, rid):
        return table.rows.get(rid) or table.van.rows.get(rid)

    def funcs(gid):
        r = current(fg, gid)
        if r is None:
            return None
        return tuple(tuple(int(r[f"function{k}_{c}"] or 0) for c in ("id", "value1", "value2", "value3")) for k in (1, 2, 3))

    notes, kinds = [], {}

    def want(kind, rid, col, gid):
        """The functions this row's group should have (None: the group as it is)."""
        f = funcs(gid)
        if f is None:
            return None
        out = [list(x) for x in f]
        fr = [i for i, x in enumerate(out) if x[0] == FRACTION and x[1] == 2 and x[2] in (2, 3, 4, 5)]
        sid = spell_of.get(rid) if kind == "ability" else None
        s = spells[sid] if sid is not None else None
        tag = f"{sid:02X} {names[sid] or '?'} (ability {rid})" if s is not None else f"{kind} {rid}"
        if s is not None and col == "battle_function_group_id" and s.flags3 & PERCENT_FLAG and s.power:
            keep = sid in KEEP_CURRENT_HP
            mode, v3 = _fraction(s.power, keep)
            rv = [i for i, x in enumerate(out) if x[0] == REVIVE and x[1] == 2 and x[2] in (2, 3, 4, 5)]
            if rv:                                                  # a revive: power/16 of max HP (Raise, Phoenix)
                mode, v3 = _fraction(s.power, False)
                x = out[rv[0]]
                if x[2] in (4, 5) and abs(_share(x[2], x[3]) - _share(mode, v3)) < 0.006:
                    return None
                out[rv[0]] = [REVIVE, 2, mode, v3]
                kinds.setdefault("revive", []).append(tag)
            elif s.power >= 16 and not fr and not any(x[0] in DAMAGE for x in out):
                return None                                         # whole HP: vanilla's Arise (no type 34)
            elif fr:
                x = out[fr[0]]
                if (x[2] in (2, 3)) == keep and abs(_share(x[2], x[3]) - _share(mode, v3)) < 0.006:
                    return None                                     # already T-Edition's share (50% = 1/2)
                out[fr[0]] = [FRACTION, 2, mode, v3]
                kinds.setdefault("percent", []).append(tag)
            else:
                dmg = [i for i, x in enumerate(out) if x[0] in DAMAGE]
                if not dmg:
                    notes.append(f"{tag}: power {s.power} percent spell, group {gid} {[x for x in f if x[0]]} has no damage "
                                 f"function to replace (left as the porter made it)")
                    return None
                out[dmg[0]] = [FRACTION, 2, mode, v3]
                kinds.setdefault("made percent", []).append(tag)
        elif s is not None and fr and not s.flags3 & PERCENT_FLAG:
            out[fr[0]] = ([2, 0, 0, 0] if s.flags1 & 0x01 else [3, 1, 0, 0]) if s.power else [0, 0, 0, 0]
            out = [x for x in out if x[0]] + [x for x in out if not x[0]]
            kinds.setdefault("not percent", []).append(tag)
        else:
            return None
        return tuple(tuple(x) for x in out)

    # every row that names a function group, and what it should name
    users = {}
    for kind, table in (("ability", ab), ("item", it)):
        for rid in sorted(table.ids()):
            r = current(table, rid)
            for col in ("battle_function_group_id", "menu_function_group_id"):
                gid = int(r.get(col) or 0)
                if gid:
                    users.setdefault(gid, []).append((kind, table, rid, col, want(kind, rid, col, gid)))
    next_id = max(fg.ids()) + 1
    made, edited, moved, changed_tables = {}, 0, 0, set()

    def write(gid, fs):
        row = fg.row(gid) if gid in fg.ids() else None
        if row is None:
            row = {c: "0" for c in fg.header}
            row["id"] = str(gid)
            fg.add(row)
            row = fg.rows[gid]
        for k, x in enumerate(fs, 1):
            for c, v in zip(("id", "value1", "value2", "value3"), x):
                row[f"function{k}_{c}"] = str(v)

    for gid, us in sorted(users.items()):
        wanted = [u[4] for u in us]
        if all(w is None for w in wanted):
            continue
        variants = {}
        for u in us:
            variants.setdefault(u[4], []).append(u)
        # the group itself keeps the rows that leave it as it is; else it takes its most common new functions
        stay = None if None in variants else max(variants, key=lambda v: len(variants[v]))
        if stay is not None:
            write(gid, stay)
            edited += 1
        for fs, rows in variants.items():
            if fs is None or fs == stay:
                continue
            if fs not in made:
                made[fs] = next_id
                next_id += 1
                write(made[fs], fs)
            for kind, table, rid, col, _ in rows:
                table.row(rid)[col] = str(made[fs])
                changed_tables.add(kind)
                moved += 1
    # rule 57: Reraise revives with T-Edition's Raise ($2D; C2/079C), the PR with ability 290 (ReraiseConditionFunction.
    # ExecuteReraise: vanilla's Life, 1/8 of max HP): its revive function at Raise's power. (The PR's SOS Shell /
    # Protect cast its own rows 242 / 243, T-Edition's effects already; Doom's expiry kills, as T-Edition's Kill.)
    raise_spell = spells[RAISE]
    r290 = current(ab, RERAISE_ABILITY)
    gid = int(r290["battle_function_group_id"] or 0) if r290 else 0
    f = funcs(gid) if gid else None
    rv = [i for i, x in enumerate(f or ()) if x[0] == REVIVE and x[1] == 2 and x[2] in (2, 3, 4, 5)]
    if rv and raise_spell.power:
        mode, v3 = _fraction(raise_spell.power, False)
        x = f[rv[0]]
        if not (x[2] in (4, 5) and abs(_share(x[2], x[3]) - _share(mode, v3)) < 0.006):
            fs = tuple(tuple([REVIVE, 2, mode, v3]) if i == rv[0] else x for i, x in enumerate(f))
            others = [u for u in users.get(gid, []) if not (u[0] == "ability" and u[2] == RERAISE_ABILITY)]
            if others:
                if fs not in made:
                    made[fs] = next_id
                    next_id += 1
                    write(made[fs], fs)
                ab.row(RERAISE_ABILITY)["battle_function_group_id"] = str(made[fs])
                changed_tables.add("ability")
                moved += 1
            else:
                write(gid, fs)
                edited += 1
            kinds.setdefault("reraise (rule 57)", []).append(f"ability {RERAISE_ABILITY}: {x[2]}/{x[3]} -> {mode}/{v3}")
    if edited or made:
        fg.save()
        for kind, table in (("ability", ab), ("item", it)):
            if kind in changed_tables:
                table.save()
    for k, tags in kinds.items():
        log(f"T-Edition rule 49 ({k}): {len(tags)}: {', '.join(tags[:12])}{' ...' if len(tags) > 12 else ''}")
    for n in notes:
        log(f"T-Edition rule 49: {n}")
    log(f"T-Edition rule 49 (percent damage): {edited} function groups changed in place, {len(made)} cloned "
        f"({moved} rows repointed)")
    return {"kinds": kinds, "notes": notes, "edited": edited, "cloned": len(made), "moved": moved}


RAGE_BASE = 799   # a rage's PR ability: 799 + the PR monster id (SNES monster n + 1; TedVictory, Worlds Collide)
RELIC_BITS = ((9, 0), (9, 1), (9, 2), (9, 3), (11, 0), (11, 2), (11, 7), (12, 0), (12, 2), (12, 7), (13, 2), (13, 4),
              (13, 5), (13, 6), (5, 0), (5, 1))


CHEST_LINES = 657   # EE dialogues 657-670: T-Edition's "found an item" line per lead character (change.html §1)


def chest_lines():
    """T-Edition's chest message for each lead character 0-13 (Terra..Umaro), as a PR line: name tags, (ITEM_N)
    for the item, literal \n line breaks, centred like the PR's own T0001_01_01."""
    import ted_dialog as D
    d = D.rom_bytes()
    out = []
    for c in range(14):
        t = D.text(d, D.file_of(d, D.PTRS2, CHEST_LINES + c), tags=True)
        assert "<item>" in t, (c, t)
        out.append("<CT>" + t.strip("\n").replace("<item>", "(ITEM_N)").replace("\n", "\\n"))
    return out


def relic_bits(rom):
    """{"9.0": [item slots], ...}: T-Edition's items (its US-layout image) setting each relic bit."""
    out = {}
    for it in S.items(rom):
        for byte, bit in RELIC_BITS:
            if it.raw[byte] >> bit & 1:
                out.setdefault(f"{byte}.{bit}", []).append(it.id)
    return out


def mod_csv(name):
    path = os.path.join(MOD, MASTER, name + ".csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def mod_messages():
    out = {}
    path = os.path.join(MOD, MESSAGE)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\r\n")
                if "\t" in line:
                    k, v = line.split("\t", 1)
                    out[k] = v
    return out


def main(argv):
    out_path = argv[0] if argv else OUT
    import profile_tedition as T
    T.build()                                   # T-Edition in the US layout (memory) + Mato's names
    rom = S.Rom(T.MATO)
    names = T._Image.names
    slots = I.identify(I.mod_items_from(rom, names.items, names.item_icons), log=lambda *_: None)

    # content rows as the game will have them: vanilla's, then the port's (new rows, changed keys)
    content = {int(r["id"]): r for r in P.Table("content")}
    for r in mod_csv("content"):
        content[int(r["id"])] = r
    by_row = {(r["type_id"], int(r["type_value"])): cid for cid, r in content.items() if r["type_id"] in TYPES.values()}
    vmsg, mmsg = P.messages(), mod_messages()

    def text(key):
        return mmsg.get(key, vmsg.get(key, ""))

    items, missing = [], []
    for s in slots:
        cid = by_row.get((TYPES[s.table], s.pr_id))
        if cid is None:
            missing.append(s.slot)
            continue
        items.append({"slot": s.slot, "content": cid, "table": s.table, "row": s.pr_id,
                      "name": text(content[cid]["mes_id_name"]), "how": s.how,
                      "moved": (s.table, s.pr_id) != M.default_item(s.slot)})
    # the porter's own slot table (ted_items.json: {slot: {table, id, content, name}}) wins where it exists: one
    # source for every T-Edition slot (the second bank 256-279 included), as the port installed it
    porter = os.path.join(MOD, "ted_items.json")
    if os.path.exists(porter):
        with open(porter, encoding="utf-8") as f:
            table = json.load(f)["items"]
        mine = {i["slot"]: i for i in items}
        items, missing = [], []
        for k, v in sorted(table.items(), key=lambda kv: int(kv[0])):
            slot, cid = int(k), int(v["content"])
            if cid not in content:
                missing.append(slot)
                continue
            how = mine.get(slot, {}).get("how", "porter") if mine.get(slot, {}).get("content") == cid else "porter"
            items.append({"slot": slot, "content": cid, "table": v["table"], "row": int(v["id"]),
                          "name": text(content[cid]["mes_id_name"]) or v.get("name", ""), "how": how,
                          "moved": (v["table"], int(v["id"])) != M.default_item(slot)})

    weapons = []
    for r in mod_csv("weapon"):
        row = int(r["id"])
        if row < 92:
            continue
        cid = by_row.get(("2", row))
        weapons.append({"row": row, "content": cid or 0, "attack": int(r["attack"]),
                        "name": text(content[cid]["mes_id_name"]) if cid else ""})

    rates = {r["key_name"]: int(r["value1"]) for r in mod_csv("game_constant_int")}
    drop_rates = [rates.get(f"MONSTER_DROP_RATE_{k}", 0) for k in range(1, 5)]
    drop_monsters = sum(1 for r in mod_csv("monster") if r.get("drop_content_id3", "0") not in ("", "0"))

    with open(T.MATO, "rb") as f:            # the 6 MB ROM itself (S.Rom(T.MATO) is the US-layout image)
        raw = f.read()
    half = [e for e in range(512) if raw[T.MONSTERS + 32 * e + 0x12] & 0x02]
    named, rows = {}, {}
    for role, slot in NAMED_SLOTS.items():
        it = next((i for i in items if i["slot"] == slot), None)
        if it:
            named[role] = it["content"]
            rows[role] = it["row"]
    data = {
        "version": "T-Edition 3.0.7 (Mato A7 r1)",
        "made": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "drop_rates": drop_rates,
        "drop_monsters": drop_monsters,
        "items": items,
        "new_weapons": weapons,
        # PR monster id: SNES e + 1 for 0-383, 1000 + e for T-Edition's new 384-511 (idmap MONSTER_EXT, the lead)
        "half_ignore_defense": {"pr": [e + 1 if e < 384 else 1000 + e for e in half], "snes_new": [e for e in half if e >= 384]},
        "named": named,
        "rows": rows,
        # rule 4: T-Edition skips the esper level-up bonus call for everyone (C2/60B2-60DE): the plugin
        # answers every esper as "none" (PrKit SnesEsperBonus), which needs vanilla's codes by content id
        # PR abilities of the SNES spells the rules name (idmap.spell; T-Edition relocates none)
        # T-Edition's relic effect bits the porter can't carry as data (the PR keys those effects on its own items'
        # ids): byte.bit -> the T-Edition item slots that set it (audit I5; scratchpad relic_bits.json decoding)
        "relic_bits": relic_bits(rom),
        # TED:cmp's $1D28 area (known techniques as SNES bitfields): PR ability per bit, 0 = none (TedRam)
        "known_bits": {"swdtech": [M.spell(0x55 + i) or 0 for i in range(8)],
                       "lore": [M.spell(0x8B + i) or 0 for i in range(24)],
                       "rage": [RAGE_BASE + 1 + n for n in range(256)]},
        "abilities": {**{name: M.spell(spell) for name, spell in NAMED_SPELLS.items() if M.spell(spell) is not None},
                      "rampage": RAMPAGE_ID},
        "esper_bonus_vanilla": [[M.esper_content(e), r[10]] for e, r in enumerate(S.Rom(P.VANILLA_ROM).table(*S.ESPERS))],
        # audit U9: the chest line by party lead (Terra..Umaro), PR text with (ITEM_N) for the item (TedChestLines)
        "chest_lines": chest_lines(),
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"{out_path}: {len(items)} items ({sum(1 for i in items if i['moved'])} on moved rows"
          f"{f', {len(missing)} without a content row: {missing}' if missing else ''}), {len(weapons)} new weapon rows, "
          f"drop rates {drop_rates} ({drop_monsters} monsters with 3-4 slots), "
          f"{len(half)} half-damage monsters ({len(data['half_ignore_defense']['snes_new'])} of them 384+), named {named}")


if __name__ == "__main__":
    main(sys.argv[1:])
