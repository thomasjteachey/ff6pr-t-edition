using System;
using Last.Battle;
using Last.Data.User;
using PrKit;

namespace TEdition.PR
{
    // Rule 24 / audit M9-M10: a battle's opening as T-Edition has it (C2/522F; 47/2E30, 47/2EA5). The PR rolls it in
    // BattlePopPlug.Calculation from six weights (game_constant_int's *_WALKING_* constants by the party's battle_pattern
    // flags: Normal 68, PreeMptive 13, BackAttack 13, EnemyPreeMptive ?, EnemySideAttack = pincer 3, SideAttack 3), each
    // passed through PassiveContentProvider.GetPreeMptiveWeight (decompiled tools/decomp/ted_enc1), which knows two relics
    // by the equipped item's ability: Alarm Earring (324: no back attack, no pincer) and Gale Hairpin (325: Normal -13,
    // PreeMptive +13, about 1 in 4). T-Edition's are the same items (its slots 218 / 219 sit on those rows) with:
    //   * the pre-emptive relic x4 (vanilla x2): 128/256 = one in two; the base 32/256 is vanilla's (the PR's 13 of ~100);
    //   * Back Guard as vanilla (no back attack, no pincer: the PR's own);
    //   * no enemy first strike (the PR's EnemyPreeMptive has no SNES counterpart): weight 0.
    // So: EnemyPreeMptive 0; with the Gale Hairpin worn, Normal keeps its weight and PreeMptive equals the sum of the others
    // (an even split), instead of the PR's +/-13.
    static class TedEncounters
    {
        internal static string Last = "";

        public static void Patch(HarmonyLib.Harmony h)
        {
            Hooks.Patch(h, typeof(Serial.FF6.Management.PassiveContentProvider), "GetPreeMptiveWeight", typeof(TedEncounters),
                postfix: nameof(Weight_Postfix));
        }

        static bool Wears(OwnedCharacterData[] party, int slot)   // T-Edition's 219 Gale Hairpin, 218 Alarm Earring
        {
            if (party == null) return false;
            int content = Plugin.D.BySlot(slot)?.Content ?? 0;
            foreach (var c in party)
            {
                var eq = c?.EquipmentData;
                if (eq == null) continue;
                foreach (var kv in eq)
                    if (kv.Value != null && content > 0 && kv.Value.ContentId == content) return true;
            }
            return false;
        }

        // the PR's other weights (game_constant_int *_WALKING_*: Normal 68, BackAttack 13, pincer 3, SideAttack 3), each
        // only when the party's battle_pattern allows it
        static int Others(int[] flags, bool alarm)
        {
            int[] w = { 68, 0, 13, 0, 3, 3 };
            int sum = 0;
            for (int i = 0; i < 6; i++)
            {
                if (i == 1 || flags == null || i >= flags.Length || flags[i] == 0) continue;
                if (alarm && (i == 2 || i == 4)) continue;
                sum += w[i];
            }
            return sum;
        }

        public static void Weight_Postfix(OwnedCharacterData[] targetDatum, BattlePopPlug.PreeMptiveState preeMptiveState,
                                          int baseValue, int[] preeMptiveFlags, bool isExceptAlarmEarrings, ref int __result)
        {
            try
            {
                if (!Plugin.TedMode) return;
                int state = (int)preeMptiveState;
                int was = __result;
                if (state == 3) __result = 0;                                     // no enemy first strike in T-Edition
                else if ((state == 0 || state == 1) && (Wears(targetDatum, 219) || TedRelics.AnyWears(targetDatum, "13.5")))
                {
                    if (state == 0) __result = baseValue;                          // the PR's -13: not T-Edition's
                    else if (baseValue > 0)
                    {
                        bool alarm = !isExceptAlarmEarrings && (Wears(targetDatum, 218) || TedRelics.AnyWears(targetDatum, "13.6"));   // back attack and pincer gone
                        __result = Others(preeMptiveFlags, alarm);                 // x4 of 32/256: one in two
                    }
                }
                if (__result != was)
                {
                    int now = __result;
                    Last = $"opening weight {preeMptiveState}: {was} -> {now}";
                    TedLog.Rule(24, $"w{state}", () => $"opening odds: {preeMptiveState} {was} -> {now} (T-Edition's pre-emptive relic x4, no enemy first strike)");
                }
            }
            catch (Exception e) { Hooks.WarnOnce("ted-encounters", e); }
        }
    }
}
