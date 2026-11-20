using System;
using System.IO;
using System.Text.Json;
using HarmonyLib;
using PrKit;
using PrKit.Ff6;   // SnesAi: the kit's FF6 AI interpreter; SnesAiHost: the battle it runs in

namespace TEdition.PR
{
    // T-Edition's monsters run their own SNES AI scripts on the kit's interpreter (PrKit/Ff6/SnesAi*), as
    // Brave New World's do (BnwEnemyAi.cs). The scripts come from the porter (tools/port_ai.py snes_ai_data,
    // with profile_tedition's snes_ai settings) as BepInEx/TEdition/ted_ai.json {"snes_ai": {...}}; monsters
    // the porter couldn't shim keep their compiled or the PR's own script. No file: AI off (logged).
    static class TedEnemyAi
    {
        sealed class Ted : SnesAiMod
        {
            public SnesAiData D;
            public override SnesAiData Data => D;
            public override bool Active => Plugin.TedMode && D != null;
            public override string Tag => "ted";
            // the host's FB 0B/0C/02 (a boss dying by its own script, the battle's end): on once T-Edition's
            // fights are tested with them (as Worlds Collide); the porter's snes_ai_status decides the data
            public override bool ScriptStatusEffects => Status;
        }

        internal static SnesAiData Data;
        internal static bool Status;
        internal static string State = "not loaded";

        public static void Apply(Harmony h, string path, bool statusEffects)
        {
            Status = statusEffects;
            if (!File.Exists(path))
            {
                State = $"no {Path.GetFileName(path)}: monsters keep their compiled scripts";
                Kit.Info($"[ted] enemy AI: {State}");
                return;
            }
            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(path));
                if (!doc.RootElement.TryGetProperty("snes_ai", out var sai) || sai.ValueKind != JsonValueKind.Object)
                {
                    State = "ted_ai.json has no snes_ai: monsters keep their compiled scripts";
                    Kit.Info($"[ted] enemy AI: {State}");
                    return;
                }
                Data = SnesAiData.Parse(sai);
            }
            catch (Exception e)
            {
                State = $"can't read {path}: {e.Message}";
                Kit.Warn($"[ted] enemy AI: {State}");
                return;
            }
            SnesAiHost.Patch(h, new Ted { D = Data });
            State = $"{Data.Plugin.Count} monsters on their T-Edition scripts, {Data.BossDeath.Count} bosses die by script";
            Kit.Info($"[ted] enemy AI: {State}");
        }

        public static void Update()
        {
            if (Data != null && Plugin.TedMode) SnesAiHost.Update();
        }

        internal static string Summary() => $"enemy AI: {State}; turns {SnesAiHost.Turns}; last {SnesAiHost.LastTurn}";
    }
}
