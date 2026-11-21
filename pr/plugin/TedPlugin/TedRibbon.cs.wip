using System;
using System.Collections.Generic;
using Last.Data;
using PrKit;

namespace TEdition.PR
{
    // Audit M15 (spec rule 52's $6434 gate): T-Edition's equipment statuses win over immunity: a Cursed Shield keeps its
    // curse statuses on a Ribbon wearer. The PR merges worn-equipment conditions in PlayerCharacterParameter.
    // ConfirmedConditionList (GetEquipmentConfirmedConditionList) and checks immunity (ConfirmedResistanceCondtionList)
    // in the ability-applied paths (AddConditionFunction; decompiled tools/decomp/ted_ui1, ted_ui2). Whether its battle-
    // start merge already ignores immunity is unchecked: this guard drops, from a character's immunities, every status
    // its own equipment grants, so nothing can refuse them. (Immunity to statuses the equipment doesn't grant is kept.)
    static class TedRibbon
    {
        internal static int Dropped;

        public static void Patch(HarmonyLib.Harmony h) =>
            Hooks.Patch(h, typeof(PlayerCharacterParameter), "ConfirmedResistanceCondtionList", typeof(TedRibbon), postfix: nameof(Resist_Postfix));

        [ThreadStatic] static bool inside;

        public static void Resist_Postfix(PlayerCharacterParameter __instance, ref Il2CppSystem.Collections.Generic.Dictionary<int, int> __result)
        {
            if (inside || !Plugin.TedMode || __instance == null || __result == null || __result.Count == 0) return;
            inside = true;
            try
            {
                var worn = __instance.GetEquipmentConfirmedConditionList();
                if (worn == null || worn.Count == 0) return;
                var drop = new HashSet<int>();
                foreach (var c in worn) if (c != null && __result.ContainsKey(c.Id)) drop.Add(c.Id);
                if (drop.Count == 0) return;
                var dst = new Il2CppSystem.Collections.Generic.Dictionary<int, int>();
                foreach (var kv in __result) if (!drop.Contains(kv.Key)) dst[kv.Key] = kv.Value;
                __result = dst;
                Dropped++;
                TedLog.Rule(52, "ribbon", () => $"equipment statuses beat immunity: conditions [{string.Join(",", drop)}] stay on the wearer");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-ribbon", e); }
            finally { inside = false; }
        }
    }
}
