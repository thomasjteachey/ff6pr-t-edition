# T-Edition for FINAL FANTASY VI Pixel Remaster

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
    .venv/Scripts/python tools/ted_build.py --test                                 # pr/mods/TEdition + port checks

## Credits

FF6 T-Edition and T-Edition EX by Tsushiy. English translation by Mato; the earlier English
translation (Lua) and its guides by its translators. BepInEx, Il2CppInterop, HarmonyX, Magicite by
Silvris. FINAL FANTASY VI is Square Enix's; this is an unofficial fan mod.
