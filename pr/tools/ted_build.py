"""T-Edition's Magicite folder, pr/mods/TEdition: the porter's output with every workstream's folder merged in.

    .venv/Scripts/python tools/ted_build.py [--no-port] [--test]

1. The porter (`port.py tedition`) into mods/TEditionPort (it wipes its output folder each run), unless
   --no-port reuses the last one.
2. mods/TEdition made afresh from it, then each workstream's Magicite folder merged in (SIBLINGS, in
   order; those that exist) by the kit's three-way merge (tools/magicite_merge.py): the game reads one
   copy of each map package, entity file and master table, so T-Edition ships one folder.
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
SIBLINGS = ["TEditionMaps", "TEditionEvents"]   # ted-maps' new maps, ted-events' translated events


def port():
    import port as PORT
    import profile_tedition as T
    base = T.PROFILE
    Cls = type("TEditionStaged", (type(base),), {"out": property(lambda self: STAGE)})
    prof = Cls()
    prof.__dict__.update(base.__dict__)
    PORT.main(prof)


def build(run_port=True, log=print):
    import magicite_merge as MM
    from prkit import data, magicite
    if run_port or not os.path.isdir(STAGE):
        port()
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
