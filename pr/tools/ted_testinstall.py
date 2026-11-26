"""Put T-Edition on this PC's game for a test run, and take it off again exactly.

  .venv/Scripts/python tools/ted_testinstall.py install   # the game closed
  .venv/Scripts/python tools/ted_testinstall.py restore   # back exactly as it was
  .venv/Scripts/python tools/ted_testinstall.py status

Like tools/bc_testinstall.py: deploy.sh switches Brave New World and Worlds Collide and knows no other
game-data mod, so a T-Edition install left in place would load beside whichever mod is installed next.
`install` sets aside, in a holding folder of its own (BepInEx/ted-test-held, recorded in
BepInEx/ted_testinstall.json), the active game-data mods (BNW, WC, Beyond Chaos: plugin and Magicite folders)
and anything of T-Edition's already on the PC (a player install's plugin, Magicite, data folder and config,
active or shelved), then installs the test build:
  BepInEx/plugins/TEdition/TEdition.PR.dll   the plugin (plugin/TedPlugin, Release build); nothing else there
  BepInEx/TEdition/                          the files the plugin reads: build/t-edition/plugin/*.json
                                             (tools/ted_plugin_data.py: ted_data.json), the top-level *.json
                                             of mods/TEdition (ted_ai.json, ted_items.json: the porter's), EX's
                                             build/t-edition/ex/ted_ex_ai.json when made, data/ted_monster_images.json
                                             (bc-sprites' monster image recipe); music/: the song pack
                                             (build/t-edition/music, tools/ted_music.py) when made; costumes/:
                                             ff6-mod/build/t-edition/art/costumes (tools/ted_art.py) when made
  <Magicite>/TEdition                        the group folders of mods/TEdition (tools/ted_build.py: the port
                                             merged with ted-maps' and ted-events' folders); its top-level files stay out
It never writes BepInEx/TEdition/build.json: that file marks a player install (T-Edition's real installer
writes it last; deck_push.sh and the PC's T-Edition shortcut act only when it exists).
`restore` deletes everything the test put there (plugin, Magicite, data folder, and the config
BepInEx/config/ff6mod.tedition.cfg BepInEx writes on the first load) and puts every held folder back where it
was. A test run writes no save (ModSaves "TEdition" makes no first-start copy in test runs).

Build first:  cd plugin/TedPlugin && dotnet build -c Release;  .venv/Scripts/python tools/ted_build.py --no-port;
              .venv/Scripts/python tools/ted_plugin_data.py
"""
import glob
import json
import os
import time
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PR = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kitpath  # noqa: E402,F401
from prkit import games  # noqa: E402

MOD = "TEdition"
OTHERS = ["BraveNewWorld", "WorldsCollide", "BeyondChaos"]   # the other game-data mods
STATE = "ted_testinstall.json"
HELD = "ted-test-held"
CONFIG = "ff6mod.tedition.cfg"
DLL = os.path.join(PR, "plugin", "TedPlugin", "bin", "Release", "net6.0", "TEdition.PR.dll")
MAGICITE = os.path.join(PR, "mods", MOD)     # tools/ted_build.py's merged folder
MUSIC = os.path.join(PR, "build", "t-edition", "music")   # tools/ted_music.py's song pack (songs.json, songs.bin, ted_music.json)
COSTUMES = os.path.join(os.path.dirname(PR), "build", "t-edition", "art", "costumes")   # tools/ted_art.py costumes (ArtSwap folders)


def data_files():
    """The files the plugin reads, from the builds that make them (never build.json)."""
    out = sorted(glob.glob(os.path.join(PR, "build", "t-edition", "plugin", "*.json")))
    out += sorted(f for f in glob.glob(os.path.join(MAGICITE, "*.json")))
    for extra in (os.path.join(PR, "build", "t-edition", "ex", "ted_ex_ai.json"),
                  os.path.join(PR, "data", "ted_monster_images.json"),       # bc-sprites' recipe (TedArt.cs)
                  os.path.join(PR, "data", "ted_costumes.json")):            # costume titles (TedCostumes, audit D7)
        if os.path.exists(extra):
            out.append(extra)
    return [f for f in out if os.path.basename(f).lower() != "build.json"]


def game():
    g = games.get("ff6")
    if not g.installed:
        raise SystemExit("FF6 PR isn't installed")
    return g


def move(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        raise SystemExit(f"{dst} is already there: not moving {src} over it")
    shutil.move(src, dst)
    print(f"  {src} -> {dst}")


def remove(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
        print(f"  removed {path}")
    elif os.path.exists(path):
        os.remove(path)
        print(f"  removed {path}")


def install():
    for path, what in ((DLL, "the plugin (cd plugin/TedPlugin && dotnet build -c Release)"),
                       (os.path.join(PR, "build", "t-edition", "plugin", "ted_data.json"), "ted_data.json (tools/ted_plugin_data.py)"),
                       (os.path.join(MAGICITE, "master"), "the merged Magicite folder (tools/ted_build.py)")):
        if not os.path.exists(path):
            raise SystemExit(f"missing {path}: build {what} first")
    g = game()
    if g.running():
        raise SystemExit("the game is running: close it (or wait for the other session's run)")
    state_path = os.path.join(g.bepinex, STATE)
    if os.path.exists(state_path):
        raise SystemExit(f"already installed for a test ({state_path}): restore first")
    held = os.path.join(g.bepinex, HELD)
    if os.path.exists(held) and os.listdir(held):
        raise SystemExit(f"{held} isn't empty (an earlier test's?): look at it before installing")
    plugin = os.path.join(g.plugins_dir, MOD)
    magicite = os.path.join(g.magicite_dir, MOD)
    data = os.path.join(g.bepinex, MOD)
    config = os.path.join(g.bepinex, "config", CONFIG)
    # set aside: the other game-data mods, and every T-Edition file already here (a player install, shelved or not)
    aside = []
    for name in OTHERS:
        aside += [("plugin", name, os.path.join(g.plugins_dir, name)), ("magicite", name, os.path.join(g.magicite_dir, name))]
    aside += [("plugin", MOD, plugin), ("magicite", MOD, magicite), ("data", MOD, data), ("config", CONFIG, config),
              ("shelf", MOD, os.path.join(g.shelf_dir, MOD)), ("shelf-magicite", MOD, os.path.join(g.shelf_dir, "magicite", MOD))]
    state = {"held": []}
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)
    for kind, name, path in aside:
        if os.path.exists(path):
            dst = os.path.join(held, kind, name)
            move(path, dst)
            state["held"].append([path, dst])
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=1)
    # the test build
    os.makedirs(plugin)
    shutil.copy2(DLL, plugin)
    os.makedirs(data)
    files = data_files()
    for f in files:
        shutil.copy2(f, data)
    if os.path.exists(os.path.join(MUSIC, "songs.json")):
        shutil.copytree(MUSIC, os.path.join(data, "music"))
    if os.path.isdir(COSTUMES):
        shutil.copytree(COSTUMES, os.path.join(data, "costumes"))
    os.makedirs(magicite)
    groups = [d for d in sorted(os.listdir(MAGICITE)) if os.path.isdir(os.path.join(MAGICITE, d))]
    for d in groups:
        shutil.copytree(os.path.join(MAGICITE, d), os.path.join(magicite, d))
    print(f"installed {MOD} for a test: {len(groups)} Magicite groups, data {', '.join(os.path.basename(f) for f in files)}"
          f"{', music pack' if os.path.isdir(os.path.join(data, 'music')) else ''}; "
          f"{len(state['held'])} folders held in {held}")


def restore():
    g = game()
    # a test's game that just quit (or crashed) takes a few seconds to go (ted-gate-1, 2026-11-25: the run's undo
    # came while it closed, and the test install stayed): wait up to 30 s
    for _ in range(30):
        if not g.running():
            break
        time.sleep(1)
    if g.running():
        raise SystemExit("the game is running: wait for it to close")
    state_path = os.path.join(g.bepinex, STATE)
    if not os.path.exists(state_path):
        raise SystemExit("not installed for a test (no state file)")
    with open(state_path, encoding="utf-8") as f:
        state = json.load(f)
    # the test's own files, all of them (the held ones come back below)
    for path in (os.path.join(g.plugins_dir, MOD), os.path.join(g.magicite_dir, MOD), os.path.join(g.bepinex, MOD),
                 os.path.join(g.bepinex, "config", CONFIG)):
        remove(path)
    for original, held in state["held"]:
        move(held, original)
    os.remove(state_path)
    held_root = os.path.join(g.bepinex, HELD)
    for root, dirs, files in os.walk(held_root, topdown=False):
        if not files and not os.listdir(root):
            os.rmdir(root)
    print(f"restored: the test's T-Edition files gone, {len(state['held'])} folders back")


def status():
    g = game()
    print(f"game running: {g.running()}")
    data = os.path.join(g.bepinex, MOD)
    print(f"T-Edition plugin: {os.path.isdir(os.path.join(g.plugins_dir, MOD))}; Magicite: {os.path.isdir(os.path.join(g.magicite_dir, MOD))}; "
          f"data: {sorted(os.listdir(data)) if os.path.isdir(data) else 'none'}; "
          f"player install (build.json): {os.path.exists(os.path.join(data, 'build.json'))}")
    for name in OTHERS:
        print(f"{name}: plugin {os.path.isdir(os.path.join(g.plugins_dir, name))}, Magicite {os.path.isdir(os.path.join(g.magicite_dir, name))}")
    print(f"test install state: {os.path.exists(os.path.join(g.bepinex, STATE))}; data files a test would install: "
          f"{[os.path.relpath(f, PR) for f in data_files()]}")


if __name__ == "__main__":
    {"install": install, "restore": restore, "status": status}.get(sys.argv[1] if len(sys.argv) > 1 else "status", status)()
