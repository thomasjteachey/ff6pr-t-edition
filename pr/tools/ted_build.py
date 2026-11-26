"""T-Edition's Magicite folder, pr/mods/TEdition: the porter's output with every workstream's folder merged in.

    .venv/Scripts/python tools/ted_build.py [--no-port] [--test] [--full] [--verify]

1. The porter (`port.py tedition`) into mods/TEditionPort (it wipes its output folder each run), unless
   --no-port reuses the last one.
2. mods/TEdition as a fresh copy of it with each workstream's Magicite folder merged in (SIBLINGS, in
   order; those that exist) by the kit's three-way merge (tools/magicite_merge.py): the game reads one
   copy of each map package, entity file and master table, so T-Edition ships one folder. Only output
   paths whose inputs changed since the last build are redone (merge_into, mods/TEdition.manifest.json);
   --full redoes everything, --verify checks the result against a full merge file by file. One build at a
   time (mods/TEdition.building, a lock several sessions share).
   T-Edition's data rules the porter has no field for (data_rules: every weapon's critical rate) go onto the
   porter's output first.
3. The kit's Magicite check (prkit magicite.validate) on the result; --test also runs test_mod, the porter's
   own checks, on mods/TEditionPort (its map checks expect only the porter's changes).
Conflicts (two workstreams changing the same thing differently) are listed and fail the build.

mods/TEdition is what gets installed (StreamingAssets/Magicite/TEdition) and packaged. The workstreams'
own folders (TEditionMaps, TEditionEvents) are never installed by themselves.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitpath  # noqa: E402,F401
import prdata as P  # noqa: E402

OUT = os.path.join(P.ROOT, "mods", "TEdition")
STAGE = os.path.join(P.ROOT, "mods", "TEditionPort")   # the porter's own output (test_mod checks it), never installed
SIBLINGS = ["TEditionMaps", "TEditionEvents", "TEditionEX", "TEditionQuests"]   # new maps (+ their events), events on
# vanilla maps, EX's boss room, the pub quests (ted-maps, ted-events, ted-ex; each session writes only its own folder)
# left out of the merge, so out of tests and the player zip: the pub quests (0.1.0 "Act 1 preview", 2026-11-25: none
# ran through its trigger yet, and talking to South Figaro's quest giver left the party unable to leave map 42)
LEAVE_OUT = []   # (tried 2026-11-25: TEditionMaps' room load scripts call the quests' entrance scripts, so they stay)
MERGED = [s for s in SIBLINGS if s not in LEAVE_OUT]


def port():
    import port as PORT
    import profile_tedition as T
    base = T.PROFILE
    Cls = type("TEditionStaged", (type(base),), {"out": property(lambda self: STAGE)})
    prof = Cls()
    prof.__dict__.update(base.__dict__)
    PORT.main(prof)


def data_rules(folder, log=print):
    """T-Edition's data rules the porter has no field for, on its output (idempotent). Today: every weapon's
    critical hit rate (profile weapon_critical_rate: T-Edition rolls random(256) < 20 for every weapon, the PR
    keeps the rate per weapon row, 3 in vanilla)."""
    import csv
    import io
    import profile_tedition as T
    rate = getattr(T.PROFILE, "weapon_critical_rate", None)
    if rate is None:
        return
    path = os.path.join(folder, "master", "Assets", "GameAssets", "Serial", "Data", "Master", "weapon.csv")
    van = P.Table("weapon")
    rows, header = {}, van.columns
    if os.path.exists(path):
        with open(path, encoding="utf-8", newline="") as f:
            r = list(csv.reader(io.StringIO(f.read())))
        header, rows = r[0], {int(x[0]): dict(zip(r[0], x)) for x in r[1:] if x}
    n = 0
    for wid, vrow in van.rows.items():
        row = rows.get(wid) or dict(vrow)
        if row["critical_rate"] not in ("0", str(rate)) and vrow["type_id"] == "1":
            row["critical_rate"] = str(rate)
            rows[wid] = row
            n += 1
    for wid, row in rows.items():                  # rows the port made (item identity's new weapons)
        if wid not in van.rows and row["critical_rate"] not in ("0", str(rate)):
            row["critical_rate"] = str(rate)
            n += 1
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(header)
    for wid in sorted(rows):
        w.writerow([rows[wid][c] for c in header])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out.getvalue())
    _ensure_master_key(folder, "weapon")
    log(f"T-Edition data rules: weapon critical rate {rate} on {n} rows")
    for rule in (growth_rule, relm_magic_rule, command_rule, dancing_dagger_rule, consumable_rule, shop_rule,
                 desperation_rule, umaro_rule):
        rule(folder, log)
    import ted_plugin_data   # the TedPlugin session's data: rule 49's percent damage and the rows its rules need
    if hasattr(ted_plugin_data, "data_rules"):
        ted_plugin_data.data_rules(folder, log)
    else:
        ted_plugin_data.percent_damage(folder, log)


class MasterRows:
    """A port folder's partial master table (its rows over the game's), changed in place: row(id) is the port's
    row or a copy of the game's, add(row) a new one; save() writes only the port's rows and those changed here,
    and lists the table in the folder's master keys."""

    def __init__(self, folder, table):
        import csv
        import io
        self.folder, self.table, self.van = folder, table, P.Table(table)
        self.path = os.path.join(folder, "master", "Assets", "GameAssets", "Serial", "Data", "Master", table + ".csv")
        self.header, self.rows = self.van.columns, {}
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8", newline="") as f:
                r = list(csv.reader(io.StringIO(f.read())))
            self.header, self.rows = r[0], {int(x[0]): dict(zip(r[0], x)) for x in r[1:] if x}

    def row(self, rid):
        if rid not in self.rows:
            self.rows[rid] = dict(self.van[rid])
        return self.rows[rid]

    def ids(self):
        return set(self.van.rows) | set(self.rows)

    def add(self, row):
        self.rows[int(row["id"])] = {c: str(row.get(c, "0")) for c in self.header}

    def save(self):
        import csv
        import io
        out = io.StringIO()
        w = csv.writer(out, lineterminator="\n")
        w.writerow(self.header)
        for rid in sorted(self.rows):
            w.writerow([self.rows[rid].get(c, "0") for c in self.header])
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8", newline="") as f:
            f.write(out.getvalue())
        _ensure_master_key(self.folder, self.table)


GROWTH_HP, GROWTH_MP, GROWTH_SIZE = 0x41DD00, 0x41E320, 112   # 41/DD00, 41/E320: 112 bytes per character 0-13
GROWTH_GROUP_BASE = 100   # growth_curve groups 101-114: characters 0-13 (group 1 stays the guests' shared curve)
RELM_MAGIC = 0x2CE3A0     # EC/E3A0: Relm's 16 (spell, level) pairs (Terra's at E3C0, Celes' at E3E0)
RELM = 8


def growth_rule(folder, log=print):
    """Per-character HP/MP growth (the spec's rule 3): T-Edition's HP gain for character c at level L is
    41/DD00[112 c + L - 2], MP 41/E320[...] (C2/60CF), for the 14 party characters; guests keep the shared tables
    (the game's growth_curve group 1, which the porter already holds). Each party character gets a growth_curve
    group of its own (GROWTH_GROUP_BASE + c + 1: group 1's rows with hp_value1 / mp_value1 from T-Edition's tables),
    set on its character_status rows (1-14, and the other rows with its name: Terra's 17-18, Mog's 29). Idempotent."""
    import profile_tedition as T
    with open(T.MATO, "rb") as f:
        mod = f.read()
    gc, cs = MasterRows(folder, "growth_curve"), MasterRows(folder, "character_status")
    base = {int(r["lv"]): r for r in (gc.rows.get(i) or gc.van[i] for i in gc.van.rows) if r["group_id"] == "1"}
    names = {cs.van[c + 1]["mes_id_name"]: c for c in range(14)}
    rows = 0
    for c in range(14):
        g = GROWTH_GROUP_BASE + c + 1
        hp = mod[GROWTH_HP + GROWTH_SIZE * c:GROWTH_HP + GROWTH_SIZE * c + 98]
        mp = mod[GROWTH_MP + GROWTH_SIZE * c:GROWTH_MP + GROWTH_SIZE * c + 98]
        for lv in sorted(base):
            row = dict(base[lv], id=str(100 * g + lv), group_id=str(g))
            if lv >= 2:
                row["hp_value1"], row["mp_value1"] = str(hp[lv - 2]), str(mp[lv - 2])
            gc.add(row)
            rows += 1
    chars = 0
    for rid in sorted(cs.ids()):
        c = names.get((cs.rows.get(rid) or cs.van[rid])["mes_id_name"])
        if c is not None:
            cs.row(rid)["growth_curve_group_id"] = str(GROWTH_GROUP_BASE + c + 1)
            chars += 1
    gc.save()
    cs.save()
    log(f"T-Edition data rules: per-character growth: {rows} growth_curve rows in groups "
        f"{GROWTH_GROUP_BASE + 1}-{GROWTH_GROUP_BASE + 14}, {chars} character_status rows on them")


DESPERATION_NEW = (226, 227)   # T-Edition's $FC Punish Meteor (Gogo) and $FD Aura Boost (Umaro): vanilla's ability type 621


def desperation_rule(folder, log=print):
    """Gogo's and Umaro's desperation attacks (T-Edition's $FC/$FD, PR abilities 226/227) as desperation rows like the
    other 12 (228-239: type 620, condition group 414), so TedPlugin's TedDesperation picks them (the audit's M31). Their own
    battle function groups (the attacks' effects) stay. Idempotent."""
    ab = MasterRows(folder, "ability")
    for a in DESPERATION_NEW:
        row = ab.row(a)
        row["type_id"], row["condition_group_id"] = "620", "414"
    ab.save()
    log(f"T-Edition data rules: desperation attacks {list(DESPERATION_NEW)} as type 620, condition group 414")


UMARO_ROW = 14                    # character_status: Umaro (SNES character 13)
UMARO_COMMANDS = [1, 26, 19, 7, 3, 0]   # Attack, the PR's hidden Magitek slot, Control = Snowstorm (command_rule), Magic, Items


def umaro_rule(folder, log=print):
    """Umaro takes the player's commands in T-Edition: his SNES list is Fight, Control (= Snowstorm), Magic, Item. The porter's
    pr_commands drops Magic for him (the PR's own Umaro has no Magic slot to keep), so his row gets the full list; his
    initial Umalo condition (the PR's uncontrolled Umaro) is cleared, as TedPlugin's TedUmaro also does at runtime (the
    audit's C28). Idempotent."""
    cs = MasterRows(folder, "character_status")
    row = cs.row(UMARO_ROW)
    for k, cid in enumerate(UMARO_COMMANDS, 1):
        row[f"command_id{k}"] = str(cid)
    row["initial_condition_group"] = "0"
    cs.save()
    log(f"T-Edition data rules: Umaro's commands {UMARO_COMMANDS}, no initial Umalo condition")


def set_messages(folder, texts):
    """Text keys onto the port folder's system_en.txt (key<TAB>text lines, sorted, CRLF, as port.py writes it)."""
    path = os.path.join(folder, "message", "Assets", "GameAssets", "Serial", "Data", "Message", "system_en.txt")
    lines = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8").read().splitlines():
            if "\t" in line:
                k, v = line.split("\t", 1)
                lines[k] = v
    lines.update(texts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        for k in sorted(lines):
            f.write(f"{k}\t{lines[k]}\r\n")


# T-Edition's rule abilities: a random pick among SNES spells, as Beyond Chaos's random commands (bc_commands
# .random_ability): ability_random_group rows -> a function_group (function 46 = cast one of a random group) -> an
# ability copying a random-cast template -> its content row. Fixed ids past every porter's range (idempotent).
RANDOM_ABILITIES = {   # name: (ability / function group / random group / content id, template ability, SNES spells)
    "dancing_dagger": (9901, 271, range(0x65, 0x75)),   # the 16 dance moves; template 271: the Man-Eater's proc copy
    "animal": (9902, 214, range(0x75, 0x7D)),           # Animal: one of the 8 animal summons; template 214 Bar-Bar-Bar
}


def random_ability(folder, key):
    import idmap as M
    rid, template, spells = RANDOM_ABILITIES[key]
    ab, fg, arg, ct = (MasterRows(folder, t) for t in ("ability", "function_group", "ability_random_group", "content"))
    abilities = [M.spell(s) for s in spells if M.spell(s)]
    for i in [i for i, r in arg.rows.items() if r["group_id"] == str(rid)]:
        del arg.rows[i]
    for k, a in enumerate(abilities):
        arg.add({"id": rid * 100 + k, "group_id": rid, "ability_id": a, "invocation_rate": 1, "condition_group_id": 0})
    tf = fg.rows.get(int(ab.van[template]["battle_function_group_id"])) or fg.van[int(ab.van[template]["battle_function_group_id"])]
    row = {c: "0" for c in fg.header}
    row.update(id=str(rid), function1_id="46", function1_value1=str(rid), function1_value2="1",
               function1_value3=tf.get("function1_value3", "0") if tf.get("function1_id") == "46" else "1")
    fg.add(row)
    ab.add(dict(ab.rows.get(template) or ab.van[template], id=str(rid), battle_function_group_id=str(rid)))
    src = next(r for r in ct.van if r["type_id"] == "4" and r["type_value"] == str(template))
    ct.add(dict(src, id=str(rid), type_value=str(rid)))
    for t in (ab, fg, arg, ct):
        t.save()
    return rid, abilities


def command_rule(folder, log=print):
    """T-Edition's commands (the spec's rules 31, 32): Control (SNES $0E, Umaro's) is Snowstorm, casting spell $54 on
    every enemy; the relic swaps' new commands sit in vanilla command slots: Health $1A = Pray (casts Sunbath $66; Banon's
    too, as T-Edition's handler), Possess $1C = Spirit (casts Bless $EC), Leap $11 = Animal (one of spells $75-$7C at
    random; T-Edition's Gau has no Leap). The PR rows (port.SNES_CMD: 19, 27, 29, 24) cast those abilities (idmap.spell,
    T-Edition's slots); renamed where the name changed. The relics that swap to them: profile relic_bit_funcs."""
    import idmap as M
    cm = MasterRows(folder, "command")
    animal, _ = random_ability(folder, "animal")
    plan = {19: (M.spell(0x54), "Snowstorm"), 27: (M.spell(0x66), None), 29: (M.spell(0xEC), "Spirit"), 24: (animal, "Animal")}
    texts = {}
    for rid, (ability, name) in plan.items():
        row = cm.row(rid)
        row["ability_id"] = str(ability)
        if name:
            texts[row["mes_id_name"]] = name
    cm.save()
    set_messages(folder, texts)
    log(f"T-Edition data rules: commands {', '.join(f'{r} -> ability {a}' + (f' ({n})' if n else '') for r, (a, n) in plan.items())}")


def dancing_dagger_rule(folder, log=print):
    """Dancing Dagger casts one of the 16 dance moves ($65 + random(16)) half the time (the spec): its weapon's entry in
    battle_extra_data's change_ability_by_weapon (the swing replaced by the ability, as the Man-Eater's proc) takes the
    random dance at 50%. Its weapon row from ted_items.json (the item identity step's choice)."""
    import json
    items = os.path.join(folder, "ted_items.json")
    extra = os.path.join(folder, "battleextradata", "Assets", "GameAssets", "Serial", "Data", "BattleExtraData",
                         "battle_extra_data.json")
    if not (os.path.exists(items) and os.path.exists(extra)):
        log("T-Edition data rules: Dancing Dagger skipped (no ted_items.json or battle_extra_data.json in the port)")
        return
    wid = next((int(v["id"]) for v in json.load(open(items, encoding="utf-8"))["items"].values()
                if v["name"] == "Dancing Dagger" and v["table"] == "weapon"), None)
    if wid is None:
        log("T-Edition data rules: Dancing Dagger skipped (no weapon row named so)")
        return
    aid, abilities = random_ability(folder, "dancing_dagger")
    doc = json.load(open(extra, encoding="utf-8"))
    lst = [e for e in doc["change_ability_by_weapon"] if e["weapon_id"] != wid]
    lst.append({"weapon_id": wid, "change_ability_id": aid, "ability_per": 50})
    doc["change_ability_by_weapon"] = sorted(lst, key=lambda e: e["weapon_id"])
    with open(extra, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)   # as the porter writes it
    log(f"T-Edition data rules: Dancing Dagger (weapon {wid}) casts one of abilities {abilities} at 50% (ability {aid})")


# T-Edition's consumables whose effect vanilla's item on their PR row lacks (item identity copies only the look, so the
# row kept its old effect: Power Tab opened the rename screen). Stat items: T-Edition's menu code (C3/922F -> 40/7700)
# raises a stat by 1 (to 128), max HP by 100 (to 9999), max MP by 10 (to 999) for party members 0-13: the PR's
# "persistence parameter" function (FunctionType 4, OwnedItemClient.PersistenceParameterExecute; no FF6 item uses it)
# with value1 1 = amount from the item's standard_value (as Recovery's), value2 = ParameterType (HP 2, MP 3, Power 4,
# Vitality 5, Agility 6, Magic 14). The layout is inferred, not seen: check one Tab in game; TedPlugin's
# OwnedItemClient.UseFunction postfix is the fallback. Cures: the statuses T-Edition's record removes (bytes 21-24) as a
# condition group (port_resist.PROTECT: vanilla's Antidote / Remedy groups come out the same). Fixed ids 9920 up.
STAT_ITEMS = {231: (4, 1), 241: (6, 1), 242: (5, 1), 243: (14, 1), 244: (2, 100), 246: (3, 10)}   # slot: (parameter, amount)
CURE_ITEMS = (248, 249, 253)   # Antidote (+blind, mute, seizure), Smelling Salts (berserk, muddle, sleep), Gold Needle (+imp)
REVIVE_ITEMS = {250: 433}      # Reincarnation: battle only, revive to full (vanilla Arise's function group 433)
ITEM_FG_BASE = 9920


def consumable_rule(folder, log=print):
    import json
    import port_resist as R
    import profile_tedition as T
    import ff6snes as S
    items = os.path.join(folder, "ted_items.json")
    if not os.path.exists(items):
        log("T-Edition data rules: consumables skipped (no ted_items.json in the port)")
        return
    slots = json.load(open(items, encoding="utf-8"))["items"]
    T.build()
    raw = {it.id: it.raw for it in S.items(S.Rom(T.MATO))}
    it, fg, cg = MasterRows(folder, "item"), MasterRows(folder, "function_group"), MasterRows(folder, "condition_group")
    # the stat items' raises: the PR's function 4 takes value1 as a parameter_group id and adds each of that group's rows
    # (parameter_id, vertical_id 1 up / 2 down, value) to the character (OwnedItemClient.IsPersistenceParameter /
    # PersistenceParameterExecute, decompiled by the TedPlugin session: tools/decomp/ted_use, ted_use3); FF6 PR ships
    # parameter_group empty, so each stat item gets its own group row (ted-8's teduse showed them unusable without)
    pg = MasterRows(folder, "parameter_group")
    for i in [i for i, r in pg.rows.items() if int(r["group_id"]) >= ITEM_FG_BASE]:
        del pg.rows[i]
    for i in [i for i, r in cg.rows.items() if int(r["group_id"]) >= ITEM_FG_BASE]:
        del cg.rows[i]
    done, n = [], 0

    def row_of(slot):
        v = slots.get(str(slot))
        return it.row(int(v["id"])) if v and v["table"] == "item" else None

    def group(fid, funcs):
        r = {c: "0" for c in fg.header}
        r["id"] = str(fid)
        for k, f in enumerate(funcs, 1):
            for c, x in zip(("id", "value1", "value2", "value3"), f):
                r[f"function{k}_{c}"] = str(x)
        fg.add(r)
    for slot, (param, amount) in sorted(STAT_ITEMS.items()):
        row = row_of(slot)
        if row is None:
            continue
        fid = ITEM_FG_BASE + n
        n += 1
        pg.add({"id": fid, "group_id": fid, "parameter_id": param, "vertical_id": 1, "value": amount})
        group(fid, [(4, fid, 0, 0)])
        row.update(system_id="1", menu_renge_id="7", battle_renge_id="0", battle_function_group_id="0",
                   menu_function_group_id=str(fid), standard_value=str(amount), menu_se_asset_id="585")
        done.append(f"{slot} +{amount} param {param}")
    for slot in CURE_ITEMS:
        row = row_of(slot)
        if row is None:
            continue
        r = raw[slot]
        bits = r[21] | r[22] << 8
        conds = sorted({c for b in range(16) if bits >> b & 1 for c in R.PROTECT.get(b, [])})
        fid = ITEM_FG_BASE + n
        n += 1
        for k, c in enumerate(conds):
            cg.add({"id": fid * 100 + k, "group_id": fid, "condition_id": c, "type_id": 1, "invocation_rate": 0})
        group(fid, [(12, fid, 0, 0)])
        battle_only = not r[0] & 0x40
        row.update(battle_function_group_id=str(fid), menu_function_group_id="0" if battle_only else str(fid),
                   menu_renge_id="0" if battle_only else "7", battle_renge_id="7", system_id="1")
        done.append(f"{slot} cures {conds}")
    for slot, gid in REVIVE_ITEMS.items():
        row = row_of(slot)
        if row is None:
            continue
        row.update(system_id="1", menu_function_group_id="0", menu_renge_id="0", battle_renge_id="7",
                   accuracy_rate="100", standard_value="0", battle_function_group_id=str(gid))
        done.append(f"{slot} revives (group {gid})")
    for t in (it, fg, cg, pg):
        t.save()
    log(f"T-Edition data rules: consumables: {'; '.join(done)}")


SHOP_GROUP_BASE = 900   # product groups for SNES shops the porter matched to none: 900 + shop (the PR's end at 209)


def shop_rule(folder, log=print):
    """T-Edition's shops the porter paired with no PR product group (its own: repopulated Narshe, Kohlingen WoB...): a
    product group each (SHOP_GROUP_BASE + shop; rows 90000 + 10 shop + k, the porter's coefficient 0 and no limit), from
    ted_shops.json's "unmatched" (profile extra_data). Writes "shops" {SNES shop: PR group} (matched and made) back into
    ted_shops.json for ted-events' TED:shop. Idempotent."""
    import json
    path = os.path.join(folder, "ted_shops.json")
    if not os.path.exists(path):
        log("T-Edition data rules: shops skipped (no ted_shops.json in the port)")
        return
    doc = json.load(open(path, encoding="utf-8"))
    pr = MasterRows(folder, "product")
    for rid in [i for i in pr.rows if i >= 90000]:
        del pr.rows[rid]
    shops = {s: int(g) for s, g in doc.get("pairs", {}).items()}
    for s, v in sorted(doc.get("unmatched", {}).items(), key=lambda kv: int(kv[0])):
        g = SHOP_GROUP_BASE + int(s)
        for k, cid in enumerate(v["stock"]):
            pr.add({"id": 90000 + 10 * int(s) + k, "content_id": cid, "group_id": g, "coefficient": 0, "purchase_limit": 0})
        shops[s] = g
    pr.save()
    doc["shops"] = {s: shops[s] for s in sorted(shops, key=int)}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    log(f"T-Edition data rules: shops: {len(doc.get('pairs', {}))} on the porter's PR groups, "
        f"{len(doc.get('unmatched', {}))} new groups ({SHOP_GROUP_BASE}+shop): {sorted(map(int, doc.get('unmatched', {})))}")


def relm_magic_rule(folder, log=print):
    """Relm learns magic by level (the spec's rule 5): 16 (spell, level) pairs at EC/E3A0 -> learning rows of type 1
    (learned at a level: value1 = level, as Terra's and Celes'), job of Relm's character_status row, content = the
    spell's ability (idmap.spell: T-Edition's spell slots are ported onto those abilities). Idempotent: the rows
    replace earlier ones for Relm's job."""
    import idmap as M
    import profile_tedition as T
    with open(T.MATO, "rb") as f:
        mod = f.read()
    le = MasterRows(folder, "learning")
    job = P.Table("character_status")[RELM + 1]["job_id"]
    c4 = {int(r["type_value"]): r["id"] for r in P.Table("content") if r["type_id"] == "4"}
    for rid in [i for i, r in le.rows.items() if r["type_id"] == "1" and r["job_id"] == job and i not in le.van.rows]:
        del le.rows[rid]
    nxt = max(le.ids()) + 1
    made, missing = [], []
    for k in range(16):
        spell, lv = mod[RELM_MAGIC + 2 * k], mod[RELM_MAGIC + 2 * k + 1]
        cid = c4.get(M.spell(spell))
        if spell == 0xFF or not cid:
            missing.append(spell)
            continue
        le.add({"id": nxt, "type_id": 1, "value1": lv, "value2": 0, "job_id": job, "content_id": cid})
        made.append((spell, lv))
        nxt += 1
    le.save()
    log(f"T-Edition data rules: Relm's natural magic: {len(made)} learning rows (job {job}): {made}"
        + (f"; no PR ability for spells {missing}" if missing else ""))


def _ensure_master_key(folder, table):
    import json
    kdir = os.path.join(folder, "master", "keys")
    files = sorted(f for f in os.listdir(kdir) if f.endswith(".json")) if os.path.isdir(kdir) else []
    path = os.path.join(kdir, files[0] if files else "mod_master.json")
    doc = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {"keys": [], "values": []}
    if table not in doc["keys"]:
        doc["keys"].append(table)
        doc["values"].append(f"Assets/GameAssets/Serial/Data/Master/{table}")
        os.makedirs(kdir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)


MANIFEST = OUT + ".manifest.json"   # beside mods/TEdition, never installed: each input file's fingerprint per output path
LOCK = OUT + ".building"            # one build at a time (several sessions run ted_build): an atomic mkdir


class _lock:
    """Holds LOCK (a folder with owner.txt) for one build; waits up to 10 minutes for another build, takes over a lock
    whose process is gone."""

    held = 0   # re-entrant within one process (main holds it around the build and its checks)

    def __init__(self, log=print):
        self.log = log

    def __enter__(self):
        import time
        if _lock.held:
            _lock.held += 1
            return self
        for i in range(600):
            try:
                os.mkdir(LOCK)
                with open(os.path.join(LOCK, "owner.txt"), "w", encoding="utf-8") as f:
                    f.write(f"{os.getpid()} {time.strftime('%H:%M:%S')} {' '.join(sys.argv)}\n")
                _lock.held = 1
                return self
            except FileExistsError:
                try:
                    pid = int(open(os.path.join(LOCK, "owner.txt"), encoding="utf-8").read().split()[0])
                except (OSError, ValueError, IndexError):
                    pid = None
                if pid and not _alive(pid):
                    self.log(f"ted_build: taking over the lock of process {pid}, which is gone")
                    shutil.rmtree(LOCK, ignore_errors=True)
                    continue
                if i % 30 == 0:
                    self.log(f"ted_build: waiting for another build (lock {LOCK}, process {pid})")
                time.sleep(1)
        raise SystemExit(f"ted_build: another build still holds {LOCK} after 10 minutes")

    def __exit__(self, *exc):
        _lock.held -= 1
        if not _lock.held:
            shutil.rmtree(LOCK, ignore_errors=True)


def _alive(pid):
    if sys.platform == "win32":
        r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
        return str(pid) in r.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def merge_into(out, sources, full=False, log=print, manifest=None):
    """The porter's output (STAGE) and the workstreams' folders merged into out, as magicite_merge.merge does on a fresh
    copy of STAGE, but redoing only output paths whose inputs changed since the last build (MANIFEST: each input's size,
    mtime and sha1; a file whose mtime moved but whose bytes didn't counts as unchanged). Every group's keys files are
    always rebuilt. Conflicts of unchanged paths come back from the manifest. full=True (or no usable manifest): the
    whole merge afresh. Same result either way (`ted_build.py --verify` diffs the two)."""
    import hashlib
    import json
    import magicite_merge as MM
    manifest = manifest or MANIFEST
    names = [os.path.basename(os.path.normpath(s)) for s in sources]
    with open(MM.__file__, "rb") as f:   # a changed merger redoes everything
        merger = hashlib.sha1(f.read()).hexdigest()
    old = None
    if not full and os.path.isdir(out) and os.path.exists(manifest):
        try:
            with open(manifest, encoding="utf-8") as f:
                old = json.load(f)
        except (OSError, ValueError):
            old = None
        if old and (old.get("sources") != names or old.get("merger") != merger):
            old = None
    prev = (old or {}).get("files", {})
    files = {}

    def fingerprint(origin, rel, path):
        st = os.stat(path)
        p = prev.get(f"{origin}|{rel}")
        if p and p[0] == st.st_size and p[1] == st.st_mtime_ns:
            fp = p
        else:
            with open(path, "rb") as f:
                fp = [st.st_size, st.st_mtime_ns, hashlib.sha1(f.read()).hexdigest()]
        files[f"{origin}|{rel}"] = fp
        return fp[2]

    inputs = {}   # rel -> [(origin, path)] in merge order (STAGE first)
    for origin, root in [("", STAGE)] + list(zip(names, sources)):
        for rel, path in MM._files(root):
            inputs.setdefault(rel, []).append((origin, path))
    sig = {rel: [[o, fingerprint(o, rel, p)] for o, p in ins] for rel, ins in inputs.items()}
    if old is None:
        if os.path.isdir(out):
            shutil.rmtree(out)
        shutil.copytree(STAGE, out)
        rep = MM.merge(out, sources, log=log)
        changed = set(inputs)
    else:
        old_sig = old.get("sig", {})
        changed = {rel for rel in inputs if MM._is_keys(rel) or old_sig.get(rel) != sig[rel]
                   or not os.path.exists(os.path.join(out, *rel.split("/")))}
        for rel in set(old_sig) - set(inputs):   # an input gone: its output goes too
            p = os.path.join(out, *rel.split("/"))
            if os.path.exists(p):
                os.remove(p)
        tmp = out + ".tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        keys_groups = {rel.split("/")[0] for rel in inputs if MM._is_keys(rel)}
        for g in keys_groups:   # keys are rebuilt from STAGE's and merged again, as on a fresh copy
            kdir = os.path.join(out, g, "keys")
            if os.path.isdir(kdir):
                for f in os.listdir(kdir):
                    if f.endswith(".json"):
                        os.remove(os.path.join(kdir, f))
        tmp_sources = []
        for name in names:
            os.makedirs(os.path.join(tmp, name), exist_ok=True)
            tmp_sources.append(os.path.join(tmp, name))
        for rel in sorted(changed):
            dst = os.path.join(out, *rel.split("/"))
            for origin, path in inputs[rel]:
                if origin == "":
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(path, dst)
                else:
                    t = os.path.join(tmp, origin, *rel.split("/"))
                    os.makedirs(os.path.dirname(t), exist_ok=True)
                    shutil.copy2(path, t)
            if not any(o == "" for o, _ in inputs[rel]) and os.path.exists(dst):
                os.remove(dst)   # a workstream's file only: the merge copies it afresh
        rep = MM.merge(out, tmp_sources, log=lambda *a: None)
        shutil.rmtree(tmp, ignore_errors=True)
        for rel, conflicts in old.get("conflicts", {}).items():   # unchanged paths keep their conflicts
            if rel not in changed and rel in inputs:
                rep.conflicts.extend((rel, who, what) for who, what in conflicts)
        log(f"magicite merge (incremental) -> {out}: {len(changed)} of {len(inputs)} paths redone; {rep}")
    conflicts = {}
    for rel, who, what in rep.conflicts:
        conflicts.setdefault(rel, []).append([who, what])
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump({"sources": names, "merger": merger, "files": files, "sig": sig, "conflicts": conflicts}, f)
    return rep


def verify(log=print):
    """The incremental merge against a full one: mods/TEdition vs a fresh merge in mods/TEdition.verify, file by file."""
    import filecmp
    sources = [os.path.join(P.ROOT, "mods", s) for s in MERGED if os.path.isdir(os.path.join(P.ROOT, "mods", s))]
    real_out, fresh = OUT, OUT + ".verify"
    merge_into(fresh, sources, full=True, log=lambda *a: None, manifest=fresh + ".manifest.json")
    import magicite_merge as MM
    a = {rel for rel, _ in MM._files(real_out)}
    b = {rel for rel, _ in MM._files(fresh)}
    differ = sorted(rel for rel in a & b if not filecmp.cmp(os.path.join(real_out, rel), os.path.join(fresh, rel), shallow=False))
    log(f"verify: {len(a)} files incremental, {len(b)} full; only incremental {sorted(a - b)[:10]}, "
        f"only full {sorted(b - a)[:10]}, differing {differ[:10]}")
    shutil.rmtree(fresh, ignore_errors=True)
    if os.path.exists(fresh + ".manifest.json"):
        os.remove(fresh + ".manifest.json")
    return not (a - b or b - a or differ)


def build(run_port=True, full=False, log=print, check=False):
    """Port (unless run_port is False and a port exists), the data rules, art and music, then the merge into OUT and the
    Magicite check, all under one lock (sessions build at once; the data rules write STAGE in place). check: also
    verify() the merge before the lock is let go; a failed check counts as a problem."""
    with _lock(log):
        rep, problems = _build(run_port, full, log)
        if check and not verify(log):
            problems = list(problems) + ["the incremental merge differs from a full merge (verify)"]
        return rep, problems


def _build(run_port, full, log):
    from prkit import data, magicite
    if run_port or not os.path.isdir(STAGE):
        port()
    data_rules(STAGE, log)
    import ted_art   # T-Edition's monster art (bc-sprites): monster_asset rows + the monsters pointed at them
    ted_art.apply(STAGE, log=log)
    import ted_music   # the song pack + bgm rules for BepInEx/TEdition/music (the TedPlugin session; not Magicite)
    ted_music.build(log=log)
    ted_music.install_player(STAGE, log=log)   # the Extras music player's 175 rows and their names (audit: never installed)
    sources = [os.path.join(P.ROOT, "mods", s) for s in MERGED if os.path.isdir(os.path.join(P.ROOT, "mods", s))]
    rep = merge_into(OUT, sources, full=full, log=log)
    for rel, who, what in rep.conflicts:
        log(f"  conflict: {rel} ({who}): {what}")
    problems, notes = magicite.validate(OUT, data.GameData("ff6"), ignore=())
    log(f"T-Edition build -> {OUT}: merged {', '.join(os.path.basename(s) for s in sources) or 'nothing'}; "
        f"{len(rep.conflicts)} conflicts; check: {len(problems)} problems, {len(notes)} notes")
    for p in problems[:20]:
        log(f"  problem: {p}")
    return rep, problems


def main(argv):
    with _lock():   # the build and its checks under one lock: another session's build can't change OUT between them
        ok = _main(argv)
    sys.exit(0 if ok else 1)


def _main(argv):
    rep, problems = build(run_port="--no-port" not in argv, full="--full" in argv, check="--verify" in argv)
    ok = not rep.conflicts and not problems
    if "--test" in argv:
        env = dict(os.environ, PR_MOD="TEditionPort", PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", os.path.join(P.ROOT, "tests"),
                            "-p", "test_mod.py"], env=env, cwd=P.ROOT)
        ok = ok and r.returncode == 0
        # the runner's pre-flight check on the merged folder (scripts a map doesn't list never run; QA's batches check it)
        r = subprocess.run([sys.executable, os.path.join(P.ROOT, "tools", "magicite_check.py"), OUT],
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"), cwd=P.ROOT)
        ok = ok and r.returncode == 0
    return ok


if __name__ == "__main__":
    main(sys.argv[1:])
