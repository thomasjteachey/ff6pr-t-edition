"""The public T-Edition repository (ff6pr-t-edition): this project's T-Edition parts, copied into their own
git tree, with the modding kit as its kit/ submodule.

    .venv/Scripts/python tools/ted_publish.py [OUT]     (default: ../../ff6pr-t-edition)

Copies T-Edition's plugin (once it exists), its tools (the porter profile, its map/event/battle tools,
this script) and its checks into OUT with the project's layout (pr/...), writes its README, .gitignore,
requirements and manifest, and records the kit (ff6pr-kit, kit/) at the kit repository's current
commit: publish and commit the kit first (tools/kit_publish.py). Nothing of the other mods'. No
T-Edition files either (its ROMs, patches, readmes or SPOILERS dumps): a build uses the developer's own.
OUT's .git is left alone: commit and push from there. The checks are tools/repo_publish.py's.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitpath  # noqa: E402,F401  (the modding kit's tools, when it's this repository's kit/ submodule)
import repo_publish as R  # noqa: E402

DEFAULT_OUT = os.path.join(os.path.dirname(R.PROJECT), "ff6pr-t-edition")
# T-Edition's tools that are published: listed one by one, so a workstream's files join once reviewed
TOOLS = ["profile_tedition.py", "ted_rooms.py", "ted_publish.py", "kitpath.py",
         "ted_events.py", "ted_dialog.py"]      # 2026-11-20: ted-events' first milestone, reviewed


def parts():
    out = [("pr/tools", TOOLS)]
    for folder in ("pr/plugin/TedPlugin", "pr/plugin/TedRules", "pr/plugin/Ted.Tests"):
        if os.path.isdir(os.path.join(R.PROJECT, *folder.split("/"))):
            out.append((folder, ["**"]))
    tests = [f for f in os.listdir(os.path.join(R.PR, "tests")) if f.startswith("test_ted")]
    if tests:
        out.append(("pr/tests", tests))
    return out


README = """# T-Edition for FINAL FANTASY VI Pixel Remaster

FF6 T-Edition, Tsushiy's expansion of Final Fantasy VI (new events, pub quests, dungeons, bosses,
costumes and a reworked battle system), with Mato's English translation, ported to the Steam Pixel
Remaster as a mod of its own; the EX patch's super-bosses are reached in the same game. **In
development: there is no release yet.**

## How it works

- `kit/`: the [modding kit](https://github.com/thomasjteachey/ff6pr-kit) (a submodule). Its porter
  turns a modded FF6 ROM into Pixel Remaster data; `kit/pr/tools/jp_layout.py` reads a mod on the
  Japanese ROM, and `kit/pr/PORTING.md` is the project's development log ("T-Edition" sections).
- `pr/tools/profile_tedition.py`: where T-Edition keeps its tables in its 6 MB ROM, its records in the
  US layout the porter reads, Mato's full names, its item list and drop slots.
- `pr/tools/ted_*.py`: T-Edition's maps, events and battle rules (in progress).

## Build

Needs Windows, FF6 PR with BepInEx 6 and Magicite installed, .NET 6 SDK, Python 3.12, the US v1.0 and
Japanese v1.0 SNES ROMs (`rom/vanilla/`), and T-Edition 3.0.7 with Mato's translation patched onto the
Japanese ROM at `build/t-edition/T-Edition 3.0.7 (Mato).sfc`. None of these are in this repository.

    git clone --recurse-submodules <this repo>
    cd pr && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
    .venv/Scripts/python ../kit/pr/tools/extract.py --game "<your FF6 PR folder>"   # pr/vanilla
    .venv/Scripts/python ../kit/pr/tools/port.py tedition                          # pr/mods/TEdition
    PR_MOD=TEdition .venv/Scripts/python -m unittest tests.test_mod                # port checks

## Credits

FF6 T-Edition and T-Edition EX by Tsushiy. English translation by Mato; the earlier English
translation (Lua) and its guides by its translators. BepInEx, Il2CppInterop, HarmonyX, Magicite by
Silvris. FINAL FANTASY VI is Square Enix's; this is an unofficial fan mod.
"""


def main():
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT)
    entries = list(R.collect(parts()))
    texts = {"README.md": README, ".gitignore": R.GITIGNORE_COMMON + "mods/\n",
             "pr/requirements.txt": R.REQUIREMENTS, "pr/modkit.json": R.manifest(keep=("tedition",))}
    done = R.write(out, entries, texts, submodules=[("kit", R.KIT_URL, R.head(R.KIT_REPO))])
    print(f"T-Edition publish: {done} -> {out}")


if __name__ == "__main__":
    main()
