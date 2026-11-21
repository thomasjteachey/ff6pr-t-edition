using System;
using System.IO;
using HarmonyLib;
using PrKit;
using PrKit.Snes;

namespace TEdition.PR
{
    // T-Edition's own songs (~250 of its new music, much of it arranged from other Square games) on the kit's SNES
    // music player (PrKit/Snes), as Beyond Chaos's BcMusic does: the pack BepInEx/TEdition/music (songs.json +
    // songs.bin, tools/ted_music.py: C5 songs at their number, bank-43 fanfares/jingles at $100 + n) and what plays
    // where (ted_music.json, the kit's BgmRules: a new song's PR bgm id is 1000 + its slot, which T-Edition's maps,
    // scripts and battles name). Vanilla's songs stay the game's own tracks. No pack: the game's music, logged.
    // Harness: tedmusic [play SLOT | stop | suspend | resume | jump | log | state] (the kit's).
    static class TedMusic
    {
        internal static string State = "not loaded";

        internal static void Patch(Harmony h)
        {
            SnesBgm.Tag = "[ted music]";
            SnesBgm.Name = "ted music";
            SnesBgm.On = () => Plugin.TedMode && loaded;
            SnesBgm.Patch(h);
            SnesBgm.RegisterHarness("tedmusic");
        }

        static bool loaded;

        internal static void Load(string dir)
        {
            try
            {
                if (!File.Exists(Path.Combine(dir, "songs.json")) || !File.Exists(Path.Combine(dir, "ted_music.json")))
                {
                    State = $"no song pack in {dir}: the game's own music";
                    Kit.Info($"[ted music] {State}");
                    return;
                }
                var pack = SongPack.Load(dir);
                var rules = BgmRules.Load(File.ReadAllText(Path.Combine(dir, "ted_music.json")));
                SnesBgm.SetMusic(pack, rules);
                loaded = true;
                State = $"{pack.Songs.Count} songs, {pack.SampleCount} samples, {rules.Tracks.Count} tracks, {rules.Maps.Count} area songs, " +
                        $"{rules.Battles.Count} formations";
                Kit.Info($"[ted music] {State} from {dir}");
            }
            catch (Exception e)
            {
                loaded = false;
                SnesBgm.SetMusic(null, null);
                State = $"{dir}: {e.GetType().Name}: {e.Message}; the game's own music";
                Kit.Warn($"[ted music] {State}");
            }
        }

        internal static void Update()
        {
            if (loaded) SnesBgm.Update();
        }
    }
}
