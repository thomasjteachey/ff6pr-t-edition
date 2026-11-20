"""Put T-Edition on this PC's game for a test run, and take it off again exactly.

  .venv/Scripts/python tools/ted_testinstall.py install   # the game closed
  .venv/Scripts/python tools/ted_testinstall.py restore   # back as it was; T-Edition to the shelf
  .venv/Scripts/python tools/ted_testinstall.py status

Like tools/bc_testinstall.py: tools/deploy.sh switches Brave New World and Worlds Collide and knows no
other game-data mod, so a T-Edition install left in place would load beside whichever mod is installed
next. This sets the active game-data mods (BNW, WC, Beyond Chaos) aside in a holding folder of its own
(BepInEx/ted-test-held, recorded in BepInEx/ted_testinstall.json) and installs T-Edition:
  BepInEx/plugins/TEdition/TEdition.PR.dll     the plugin (plugin/TedPlugin, Release build); nothing else there
  BepInEx/TEdition/ted_data.json               its data (tools/ted_plugin_data.py): out of the plugins folder
  BepInEx/TEdition/ted_ai.json                 the monsters' SNES AI (mods/TEdition/ted_ai.json, the porter's), if made
  <Magicite>/TEdition                          T-Edition's Magicite folder (mods/TEdition: tools/port.py tedition)
`restore` moves T-Edition's plugin and Magicite folders to the shelf in deploy.sh's layout
(BepInEx/mod-shelf/TEdition, mod-shelf/magicite/TEdition: nothing loads there) and the held mods back.
BepInEx/TEdition (data) stays; its saves are its own files (ModSaves "TEdition") and a test run writes none.

Build first:  cd plugin/TedPlugin && dotnet build -c Release;  .venv/Scripts/python tools/ted_plugin_data.py
"""
import json
import os
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
DLL = os.path.join(PR, "plugin", "TedPlugin", "bin", "Release", "net6.0", "TEdition.PR.dll")
DATA = os.path.join(PR, "build", "t-edition", "plugin", "ted_data.json")
AI = os.path.join(PR, "mods", "TEdition", "ted_ai.json")   # the porter's SNES AI scripts (profile_tedition), when made
MAGICITE = os.path.join(PR, "mods", MOD)


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


def mirror(src, dst):
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)


def install():
    for path, what in ((DLL, "the plugin (cd plugin/TedPlugin && dotnet build -c Release)"),
                       (DATA, "ted_data.json (tools/ted_plugin_data.py)"),
                       (os.path.join(MAGICITE, "master"), "the port (tools/port.py tedition)")):
        if not os.path.exists(path):
            raise SystemExit(f"missing {path}: build {what} first")
    g = game()
    if g.running():
        raise SystemExit("the game is running: close it (or wait for the other session's run)")
    state_path = os.path.join(g.bepinex, STATE)
    if os.path.exists(state_path):
        raise SystemExit(f"already installed for a test ({state_path}): restore first")
    held = os.path.join(g.bepinex, HELD)
    state = {"held": []}
    for name in OTHERS:
        for kind, path in (("plugin", os.path.join(g.plugins_dir, name)), ("magicite", os.path.join(g.magicite_dir, name))):
            if os.path.isdir(path):
                dst = os.path.join(held, kind, name)
                move(path, dst)
                state["held"].append([path, dst])
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)
    plugin = os.path.join(g.plugins_dir, MOD)
    shelved = os.path.join(g.shelf_dir, MOD)
    if not os.path.isdir(plugin) and os.path.isdir(shelved):
        move(shelved, plugin)
    os.makedirs(plugin, exist_ok=True)
    shutil.copy2(DLL, plugin)
    data = os.path.join(g.bepinex, MOD)
    os.makedirs(data, exist_ok=True)
    shutil.copy2(DATA, data)
    if os.path.exists(AI):
        shutil.copy2(AI, data)
    elif os.path.exists(os.path.join(data, "ted_ai.json")):
        os.remove(os.path.join(data, "ted_ai.json"))       # an older run's: the port no longer makes it
    shelved_mg = os.path.join(g.shelf_dir, "magicite", MOD)
    if os.path.isdir(shelved_mg):
        shutil.rmtree(shelved_mg)
    mirror(MAGICITE, os.path.join(g.magicite_dir, MOD))
    print(f"installed {MOD} for a test; {len(state['held'])} folders held in {held}")


def restore():
    g = game()
    if g.running():
        raise SystemExit("the game is running: wait for it to close")
    state_path = os.path.join(g.bepinex, STATE)
    if not os.path.exists(state_path):
        raise SystemExit("not installed for a test (no state file)")
    with open(state_path, encoding="utf-8") as f:
        state = json.load(f)
    plugin = os.path.join(g.plugins_dir, MOD)
    if os.path.isdir(plugin):
        dst = os.path.join(g.shelf_dir, MOD)
        shutil.rmtree(dst, ignore_errors=True)
        move(plugin, dst)
    mg = os.path.join(g.magicite_dir, MOD)
    if os.path.isdir(mg):
        dst = os.path.join(g.shelf_dir, "magicite", MOD)
        shutil.rmtree(dst, ignore_errors=True)
        move(mg, dst)
    for original, held in state["held"]:
        move(held, original)
    os.remove(state_path)
    print(f"restored: {MOD} on the shelf, {len(state['held'])} folders back")


def status():
    g = game()
    print(f"game running: {g.running()}")
    print(f"T-Edition plugin: {os.path.isdir(os.path.join(g.plugins_dir, MOD))}; Magicite: {os.path.isdir(os.path.join(g.magicite_dir, MOD))}; "
          f"data: {os.path.exists(os.path.join(g.bepinex, MOD, 'ted_data.json'))}")
    for name in OTHERS:
        print(f"{name}: plugin {os.path.isdir(os.path.join(g.plugins_dir, name))}, Magicite {os.path.isdir(os.path.join(g.magicite_dir, name))}")
    print(f"test install state: {os.path.exists(os.path.join(g.bepinex, STATE))}")


if __name__ == "__main__":
    {"install": install, "restore": restore, "status": status}.get(sys.argv[1] if len(sys.argv) > 1 else "status", status)()
