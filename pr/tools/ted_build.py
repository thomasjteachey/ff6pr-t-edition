"""T-Edition's Magicite folder, pr/mods/TEdition: the porter's output with every workstream's folder merged in.

    .venv/Scripts/python tools/ted_build.py [--no-port] [--test]

1. The porter (`port.py tedition`) into mods/TEditionPort (it wipes its output folder each run), unless
   --no-port reuses the last one.
2. mods/TEdition made afresh from it, then each workstream's Magicite folder merged in (SIBLINGS, in
   order; those that exist) by the kit's three-way merge (tools/magicite_merge.py): the game reads one
   copy of each map package, entity file and master table, so T-Edition ships one folder.
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
    for rule in (growth_rule, relm_magic_rule, command_rule, dancing_dagger_rule):
        rule(folder, log)


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


def build(run_port=True, log=print):
    import magicite_merge as MM
    from prkit import data, magicite
    if run_port or not os.path.isdir(STAGE):
        port()
    data_rules(STAGE, log)
    import ted_art   # T-Edition's monster art (bc-sprites): monster_asset rows + the monsters pointed at them
    ted_art.apply(STAGE, log=log)
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(STAGE, OUT)
    sources = [os.path.join(P.ROOT, "mods", s) for s in SIBLINGS if os.path.isdir(os.path.join(P.ROOT, "mods", s))]
    rep = MM.merge(OUT, sources, log=log)
    for rel, who, what in rep.conflicts:
        log(f"  conflict: {rel} ({who}): {what}")
    problems, notes = magicite.validate(OUT, data.GameData("ff6"), ignore=())
    log(f"T-Edition build -> {OUT}: merged {', '.join(os.path.basename(s) for s in sources) or 'nothing'}; "
        f"{len(rep.conflicts)} conflicts; check: {len(problems)} problems, {len(notes)} notes")
    for p in problems[:20]:
        log(f"  problem: {p}")
    return rep, problems


def main(argv):
    rep, problems = build(run_port="--no-port" not in argv)
    ok = not rep.conflicts and not problems
    if "--test" in argv:
        env = dict(os.environ, PR_MOD="TEditionPort", PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", os.path.join(P.ROOT, "tests"),
                            "-p", "test_mod.py"], env=env, cwd=P.ROOT)
        ok = ok and r.returncode == 0
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
