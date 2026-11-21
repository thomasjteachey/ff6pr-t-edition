using System;
using System.Collections.Generic;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using PrKit;
using Correction = Last.Battle.CalcExecuteCorrection;

namespace TEdition.PR
{
    // Audit I3 (MP Critical): the PR decides which weapons spend MP for a critical hit from a fixed list,
    // CalcExecuteCorrection.UseMpCriticalWeaponIds (weapon rows; IsUseMpCriticalOccurrence reads it). T-Edition's MP
    // Critical weapons are the ones with special effect 7 (ted_data weapon_details "MP Critical": Rune Blade, Rune Bell,
    // Mjolnir): the list becomes their PR weapon rows. The array exists once the class's static constructor has run:
    // tried every second until it reads, then set once (the game never rebuilds it).
    static class TedMpCritical
    {
        static bool done;
        static float next;
        internal static string State = "not set";

        public static void Update()
        {
            if (done || !Plugin.TedMode || Plugin.D == null || UnityEngine.Time.unscaledTime < next) return;
            next = UnityEngine.Time.unscaledTime + 1f;
            try
            {
                var was = Correction.UseMpCriticalWeaponIds;
                if (was == null) return;
                var rows = new List<int>();
                foreach (var it in Plugin.D.Items)
                    if (it.Table == "weapon" && it.Row > 0 && Plugin.D.WeaponDetails.TryGetValue(it.Slot, out var l) && Array.IndexOf(l, "MP Critical") >= 0
                        && !rows.Contains(it.Row))
                        rows.Add(it.Row);
                done = true;
                if (rows.Count == 0) { State = "no MP Critical weapons in ted_data: the PR's list kept"; return; }
                var old = new List<int>();
                foreach (var v in was) old.Add(v);
                var arr = new Il2CppStructArray<int>(rows.Count);
                for (int i = 0; i < rows.Count; i++) arr[i] = rows[i];
                Correction.UseMpCriticalWeaponIds = arr;
                State = $"MP Critical weapons: rows [{string.Join(",", rows)}] (the PR's [{string.Join(",", old)}])";
                Kit.Info($"[ted] {State} (audit I3)");
            }
            catch (Exception e) { done = true; State = "failed: " + e.Message; Hooks.WarnOnce("ted-mp-critical", e); }
        }
    }
}
