using System;
using HarmonyLib;
using PrKit;
using UnityEngine;
using Object = UnityEngine.Object;
using View = Last.Battle.ViewDamageEntity;

namespace TEdition.PR
{
    // Audit M30 (change.html §2 "Damage/Recovery Limit Increase"): T-Edition hits up to 32000 (the porter's
    // MAX_HIT_VALUE), so a number can have 5 digits. The PR draws a number into its damage prefab's children, one digit
    // per child (ViewDamageEntity.CreateDamageValue: the value's digits reversed, Transform.GetChild(i) for digit i;
    // decompiled tools/decomp/ted_m30), and the prefab is made for the PR's 9999: four children. For 10000 and up the
    // prefab gets more children here (CreateDamagePrefab postfix): copies of the last one, each placed one digit step
    // further on (the step between the last two), so the game's own loop fills them like the others.
    static class TedDamageDigits
    {
        internal static int Grown;

        public static void Patch(Harmony h) =>
            Hooks.Patch(h, typeof(View), "CreateDamagePrefab", typeof(TedDamageDigits), postfix: nameof(Prefab_Postfix));

        public static void Prefab_Postfix(View __instance)
        {
            if (!Plugin.TedMode || __instance == null) return;
            try
            {
                int value = Math.Abs(__instance.damageValue_);
                int digits = value.ToString().Length;
                var t = __instance.prefab != null ? __instance.prefab.transform : null;
                if (t == null || digits <= t.childCount || t.childCount < 2) return;
                while (t.childCount < digits)
                {
                    var last = t.GetChild(t.childCount - 1);
                    var prev = t.GetChild(t.childCount - 2);
                    var step = last.localPosition - prev.localPosition;
                    var copy = Object.Instantiate(last.gameObject, t, false);
                    copy.transform.localPosition = last.localPosition + step;
                    Grown++;
                }
                Hooks.NoteOnce("ted-damage-digits", () => $"[ted] damage {value}: {digits} digits drawn (the PR's prefab holds 4; audit M30)");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-damage-digits", e); }
        }
    }
}
