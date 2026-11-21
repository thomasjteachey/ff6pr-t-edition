using System;
using HarmonyLib;
using PrKit;

namespace TEdition.PR
{
    // Audit I12 (change.html §5 "Ultima Weapon"; spec 17): the Ultima Weapon's blade shows the hit's damage: dagger under
    // 2000, sword under 5000, great sword from 5000. The PR already picks its blade by the act's damage
    // (DoEffectActFunction.ChangeUltimaWeaponSprite, decompiled tools/decomp/ted_i12: the first target's
    // CalcResult.GetValue: under 500 sprite "Default_02", under 1000 "Default_01", else "Default_00" with the max-power
    // after-images; a miss shows the small one), only at its own thresholds. While that method runs, the value it reads
    // goes through a monotonic map that puts T-Edition's 2000 / 5000 on the PR's 500 / 1000; nothing else reads it.
    static class TedUltima
    {
        [ThreadStatic] static bool inside;
        internal static string Last = "";

        public static void Patch(Harmony h)
        {
            Hooks.Patch(h, typeof(Last.Battle.DoEffectActFunction), "ChangeUltimaWeaponSprite", typeof(TedUltima),
                prefix: nameof(Change_Prefix), postfix: nameof(Change_Postfix));
            Hooks.Patch(h, typeof(Last.Systems.CalcResult), "GetValue", typeof(TedUltima), postfix: nameof(Value_Postfix));
        }

        public static void Change_Prefix() => inside = Plugin.TedMode;
        public static void Change_Postfix() => inside = false;

        // T-Edition's thresholds onto the PR's: [0, 2000) -> [0, 500), [2000, 5000) -> [500, 1000), 5000+ -> 1000+
        public static int Map(int v) => v < 2000 ? v / 4 : v < 5000 ? 500 + (v - 2000) / 6 : 1000 + (v - 5000);

        public static void Value_Postfix(ref int __result)
        {
            if (!inside) return;
            int was = __result;
            __result = Map(was);
            Last = $"{was} -> {__result}";
            TedLog.Rule(17, "ultima", () => $"Ultima Weapon blade by damage {was} (T-Edition's 2000 / 5000; the PR reads {Map(was)}) (audit I12)");
        }
    }
}
