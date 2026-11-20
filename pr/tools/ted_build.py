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
SIBLINGS = ["TEditionMaps", "TEditionEvents", "TEditionEX"]   # ted-maps' new maps, ted-events' events, EX's boss room


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
