using System;
using System.Collections.Generic;
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
    // EX's bosses (SNES 512-539, PR 1512-1539: the ted-ex workstream, tools/ted_ex_ai.py) come in a file of
    // their own, ted_ex_ai.json in the same schema, merged in at load (no id overlaps), plus
    // "attack_overrides" {SNES attack: PR ability}: EX wrote its bosses' own attacks over 3.0.7's enemy
    // attacks 166-237, so the same attack byte means another ability for a monster 512 and up.
    static class TedEnemyAi
    {
        sealed class Ted : SnesAiMod
        {
            public SnesAiData D;
            public Dictionary<int, int> ExAttacks = new Dictionary<int, int>();
            public override SnesAiData Data => D;
            public override bool Active => Plugin.TedMode && D != null;
            public override string Tag => "ted";
            // the host's FB 0B/0C/02 (a boss dying by its own script, the battle's end): on once T-Edition's
            // fights are tested with them (as Worlds Collide); the porter's snes_ai_status decides the data
            public override bool ScriptStatusEffects => Status;

            public override int AbilityFor(int snesMonster, int attack) =>
                snesMonster >= ExFirst && ExAttacks.TryGetValue(attack, out int ab) && ab > 0 ? ab : SnesAiHost.BaseAbility(D, snesMonster, attack);
        }

        public const int ExFirst = 512;
        internal static SnesAiData Data;
        internal static bool Status;
        internal static string State = "not loaded";
        internal static int ExMonsters, ExOverrides;

        public static void Apply(Harmony h, string path, string exPath, bool statusEffects)
        {
            Status = statusEffects;
            var mod = new Ted();
            Data = Load(path, null);
            var ex = Load(exPath, mod.ExAttacks);
            if (ex != null)
            {
                ExMonsters = ex.Scripts.Count;
                ExOverrides = mod.ExAttacks.Count;
                Data = Data == null ? ex : Merge(Data, ex);
            }
            if (Data == null)
            {
                State = $"no {Path.GetFileName(path)}: monsters keep their compiled scripts";
                Kit.Info($"[ted] enemy AI: {State}");
                return;
            }
            mod.D = Data;
            SnesAiHost.Patch(h, mod);
            State = $"{Data.Plugin.Count} monsters on their T-Edition scripts ({ExMonsters} EX scripts, {ExOverrides} EX attack overrides), " +
                    $"{Data.BossDeath.Count} bosses die by script";
            Kit.Info($"[ted] enemy AI: {State}");
        }

        // a {"snes_ai": ...} file (null when there's none or it can't be read); EX's attack_overrides into `overrides`
        static SnesAiData Load(string path, Dictionary<int, int> overrides)
        {
            if (string.IsNullOrEmpty(path) || !File.Exists(path)) return null;
            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(path));
                if (!doc.RootElement.TryGetProperty("snes_ai", out var sai) || sai.ValueKind != JsonValueKind.Object)
                {
                    Kit.Warn($"[ted] enemy AI: {Path.GetFileName(path)} has no snes_ai");
                    return null;
                }
                var d = SnesAiData.Parse(sai);
                if (overrides != null && sai.TryGetProperty("attack_overrides", out var ao) && ao.ValueKind == JsonValueKind.Object)
                    foreach (var p in ao.EnumerateObject()) overrides[int.Parse(p.Name)] = p.Value.GetInt32();
                return d;
            }
            catch (Exception e)
            {
                Kit.Warn($"[ted] enemy AI: can't read {path}: {e.Message}");
                return null;
            }
        }

        // EX's data into T-Edition's: every table's union (EX's ids are its own: 512+, parties 30768+); the
        // engine rules and the attack table stay T-Edition's
        static SnesAiData Merge(SnesAiData a, SnesAiData b)
        {
            void Dict<TV>(Dictionary<int, TV> into, Dictionary<int, TV> from)
            {
                foreach (var kv in from) if (!into.ContainsKey(kv.Key)) into[kv.Key] = kv.Value;
            }
            Dict(a.Scripts, b.Scripts);
            Dict(a.Battle, b.Battle);
            Dict(a.Special, b.Special);
            Dict(a.Messages, b.Messages);
            Dict(a.MessageKeys, b.MessageKeys);
            Dict(a.PartySlots, b.PartySlots);
            Dict(a.Copies, b.Copies);
            Dict(a.ItemUse, b.ItemUse);
            Dict(a.Throws, b.Throws);
            Dict(a.Commands, b.Commands);
            Dict(a.PartyMembers, b.PartyMembers);
            Dict(a.Weak, b.Weak);
            Dict(a.Formations, b.Formations);
            Dict(a.EventModes, b.EventModes);
            foreach (var (into, from) in new[] { (a.Plugin, b.Plugin), (a.BossDeath, b.BossDeath), (a.PrEnds, b.PrEnds), (a.ZeroWait, b.ZeroWait),
                                                 (a.StartShows, b.StartShows), (a.PrEntrances, b.PrEntrances) })
                into.UnionWith(from);
            a.EventBits.AddRange(b.EventBits);
            return a;
        }

        public static void Update()
        {
            if (Data != null && Plugin.TedMode) SnesAiHost.Update();
        }

        internal static string Summary() => $"enemy AI: {State}; turns {SnesAiHost.Turns}; last {SnesAiHost.LastTurn}";
    }
}
