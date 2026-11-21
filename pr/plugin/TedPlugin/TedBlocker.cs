using System;
using HarmonyLib;
using Last.Data;
using PrKit;

namespace TEdition.PR
{
    // Audit M38 (spec 11): T-Edition figures a hit that Golem or the Interceptor blocks against defense 119 (C2/0CD0-0CD8:
    // either block flag, $3A82 / $3A83, gives LDA #$78 in place of the target's defense; vanilla #$C0 = 192). The PR's
    // physical calc (CalcExecuteFF6.PhysicalExecution, decompiled tools/decomp/physical: isDefendInvoked /
    // isDefencedGolem) only logs a 192 and uses the target's own ConfirmedDefense, then moves a Golem block's damage
    // into Golem's pool inside the method. So for that one calculation the target's defense reads 119: the prefix
    // notes the blocked target, PlayerCharacterParameter.ConfirmedDefense answers 119 for it, the postfix clears it.
    static class TedBlocker
    {
        const int BlockerDefense = 119;
        [ThreadStatic] static IntPtr blocked;
        internal static int Applied;

        public static void Patch(Harmony h)
        {
            Hooks.Patch(h, typeof(Last.Battle.CalcExecuteFF6), "PhysicalExecution", typeof(TedBlocker),
                prefix: nameof(Physical_Prefix), postfix: nameof(Physical_Postfix));
            Hooks.Patch(h, typeof(PlayerCharacterParameter), "ConfirmedDefense", typeof(TedBlocker), postfix: nameof(Defense_Postfix));
        }

        public static void Physical_Prefix(CharacterParameterBase target, bool isDefendInvoked, bool isDefencedGolem)
        {
            blocked = IntPtr.Zero;
            if (!Plugin.TedMode || target == null || !(isDefendInvoked || isDefencedGolem)) return;
            blocked = target.Pointer;
            bool golem = isDefencedGolem;
            TedLog.Rule(11, golem ? "golem" : "interceptor",
                () => $"{(golem ? "Golem" : "Interceptor")} block: the hit is figured against defense {BlockerDefense} (vanilla 192; audit M38)");
        }

        public static void Physical_Postfix() => blocked = IntPtr.Zero;

        public static void Defense_Postfix(PlayerCharacterParameter __instance, ref int __result)
        {
            if (blocked == IntPtr.Zero || __instance == null || __instance.Pointer != blocked) return;
            __result = BlockerDefense;
            Applied++;
        }
    }
}
