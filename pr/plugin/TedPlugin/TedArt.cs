using System;
using System.Diagnostics;
using System.IO;
using HarmonyLib;
using PrKit;

namespace TEdition.PR
{
    // T-Edition's art (bc-sprites' tools/ted_art.py): its 226 monster images and their bestiary thumbnails, made
    // once from the player's own game into T-Edition's Magicite folder (the kit's MonsterImages, as BnwMonsterImages:
    // before Magicite scans its folder on its first Update, so they load on the same start; later starts only check
    // the marker), and its redrawn base character looks served by the kit's ArtSwap from BepInEx/TEdition/costumes/
    // default (each <Name>_<k> folder there: a dressing-room costume, put on as an ArtSwap layer once the kit has
    // layers).
    static class TedArt
    {
        internal static string MonsterLine = "not made", ArtLine = "none";

        public static void MonsterImagesAtLoad(string dataDir)
        {
            var path = Path.Combine(dataDir, "ted_monster_images.json");
            if (!File.Exists(path)) { MonsterLine = $"no {path}"; return; }
            var sw = Stopwatch.StartNew();
            try
            {
                var recipe = MonsterImageRecipe.FromJson(File.ReadAllText(path), "monster_images");
                if (recipe == null) { MonsterLine = "no recipe"; return; }
                MonsterLine = MonsterImages.Ensure(BepInEx.Paths.GameRootPath, MagiciteDir.FolderPath(Plugin.ModFolder), recipe,
                    w => Plugin.L.LogWarning("[ted] " + w));
                Plugin.L.LogInfo($"[ted] {MonsterLine} ({sw.ElapsedMilliseconds} ms)");
            }
            catch (Exception e)
            {
                MonsterLine = "not made: " + e.Message;
                Plugin.L.LogError("[ted] monster images not made: " + e.Message);
            }
        }

        public static void BaseLooks(Harmony h, string dataDir)
        {
            var dir = Path.Combine(dataDir, "costumes", "default");
            if (!File.Exists(Path.Combine(dir, "art.json"))) { ArtLine = $"no {dir}"; return; }
            try
            {
                ArtSwap.Tag = "[ted art]";
                ArtSwap.Install(h);
                ArtLine = ArtSwap.Load(dir);
                Plugin.L.LogInfo($"[ted art] base looks: {ArtLine}");
            }
            catch (Exception e)
            {
                ArtLine = "not loaded: " + e.Message;
                Plugin.L.LogError("[ted art] base looks not loaded: " + e.Message);
            }
        }
    }
}
