using HarmonyLib;
using PrKit;

namespace TEdition.PR
{
    // Audit M34 (change.html §4 "Barrage (Master's Scroll Effect)": "The accuracy has been changed to normal accuracy").
    // The PR halves the hit rate of a fighter wearing its Offering (CalcExecuteFF6.PhysicalExecution's mikiriBracelet,
    // decompiled tools/decomp/physical: hit rate / 2, so 255 "never misses" becomes 127), vanilla's penalty; that is the
    // flag's only use there, so T-Edition's hits come with it off. Desperation attacks are already blocked with the
    // Master's Scroll (TedDesperation); the "no procs" half is the PR's own (unchecked).
    static class TedBarrage
    {
        internal static int Cleared;

        public static void Patch(Harmony h) =>
            Hooks.Patch(h, typeof(Last.Battle.CalcExecuteFF6), "PhysicalExecution", typeof(TedBarrage), prefix: nameof(Physical_Prefix));

        public static void Physical_Prefix(ref bool mikiriBracelet)
        {
            if (!mikiriBracelet || !Plugin.TedMode) return;
            mikiriBracelet = false;
            Cleared++;
            TedLog.Rule(0, "barrage", () => "Barrage (Offering / Master's Scroll): normal accuracy, the PR's halved hit rate off (audit M34)");
        }
    }
}
