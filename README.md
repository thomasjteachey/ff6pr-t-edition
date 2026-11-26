# T-Edition for FINAL FANTASY VI Pixel Remaster

FF6 T-Edition, Tsushiy's expansion of Final Fantasy VI (new events, pub quests, dungeons, bosses,
costumes and a reworked battle system), with Mato's English translation, ported to the Steam Pixel
Remaster as a mod of its own; the EX patch's super-bosses are reached in the same game.

**Preview builds are on the [Releases](https://github.com/thomasjteachey/ff6pr-t-edition/releases)
page.** 0.1.0 is an "Act 1 preview": the first act (Narshe to the Returners) is the part checked in
game so far. Later parts are in the build but untested; expect rough edges there.

## Playing it

No ROM is needed: the zip carries the mod's own data, art and songs, never the game's files.

1. Install BepInEx 6 for Unity IL2CPP games, x64 (a bleeding-edge build from builds.bepinex.dev;
   made with 6.0.0-be.697), and Magicite, the Pixel Remaster mod loader.
2. Download `TEdition-PR-<version>.zip` from the latest release and extract it into the game folder
   (next to `FINAL FANTASY VI.exe`), keeping its folders.
3. Start a new game. T-Edition keeps its own save files (`TEdition_*.sav` beside the game's), so
   your other saves stay as they are.

Don't install it beside Brave New World, Worlds Collide or Beyond Chaos: each changes the same game
data. Remove it by deleting `BepInEx/plugins/TEdition`, `BepInEx/TEdition` and
`FINAL FANTASY VI_Data/StreamingAssets/Magicite/TEdition`.

Steam Deck / Linux (Proton): BepInEx only starts with `WINEDLLOVERRIDES="winhttp=n,b" %command%` in
the game's Steam launch options.

What 0.1.0 has: T-Edition's items (all 279, re-slotted as T-Edition has them), shops, monsters and
formations (its new monsters too, with its art), drops (four slots), steals, Mato's English names and
descriptions, the reworked battle rules, its songs, costumes, and its events on the maps (run in
game for the first act). Not yet: New Game+, T-Edition's recoloured battle backgrounds, and a full
playthrough past the first act; the release notes list what is known.

## How it works

- `kit/`: the [modding kit](https://github.com/thomasjteachey/ff6pr-kit) (a submodule). Its porter
  turns a modded FF6 ROM into Pixel Remaster data; `kit/pr/tools/jp_layout.py` reads a mod on the
  Japanese ROM.
- `pr/docs/tedition.md`: T-Edition's development log (its plan, decisions and "Live progress");
  `pr/docs/tedition-audit.md`: every feature T-Edition's documents name, with its state in the port.
- `pr/tools/profile_tedition.py`: where T-Edition keeps its tables in its 6 MB ROM, its records in the
  US layout the porter reads, Mato's full names, its item list and drop slots.
- `pr/tools/ted_*.py`: T-Edition's maps, events, art, music and battle data; `ted_build.py` builds it.
- `pr/plugin/TedPlugin`: the BepInEx plugin for T-Edition's battle rules, items, music, costumes and
  events; `pr/plugin/TedRules`: its game-free rules, with offline tests (`Ted.Tests`).

## Build

Needs Windows, FF6 PR with BepInEx 6 and Magicite installed, .NET 6 SDK, Python 3.12, the US v1.0 and
Japanese v1.0 SNES ROMs (`rom/vanilla/`), and T-Edition 3.0.7 with Mato's translation patched onto the
Japanese ROM at `build/t-edition/T-Edition 3.0.7 (Mato).sfc`. None of these are in this repository.

    git clone --recurse-submodules <this repo>
    cd pr && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
    .venv/Scripts/python ../kit/pr/tools/extract.py --game "<your FF6 PR folder>"   # pr/vanilla
    .venv/Scripts/python tools/ted_build.py --test                                 # pr/mods/TEdition + port checks
    .venv/Scripts/python ../kit/pr/tools/package_mod.py tedition                    # the player zip

## Credits

FF6 T-Edition and T-Edition EX by Tsushiy. English translation by Mato; the earlier English
translation (Lua) and its guides by its translators. BepInEx, Il2CppInterop, HarmonyX, Magicite by
Silvris. FINAL FANTASY VI is Square Enix's; this is an unofficial fan mod.
