using System;
using System.Collections.Generic;
using HarmonyLib;
using Last.Battle;
using Last.Battle.Function;
using Last.Data.Master;
using Last.Systems;
using PrKit;

namespace TEdition.PR
{
    // Audit M17 (change.html §2 "Critical Health"; spec 48): T-Edition's percent spells (Gravity, Graviga, Tornado ...:
    // spell byte 4 bit 7) inflict only Near Fatal, and vanilla's "miss when the target is immune to all its statuses"
    // stays, so a monster immune to Near Fatal (its status immunity byte $15 bit 1: 229 of 512) dodges them; death
    // immunity no longer matters. The PR has no Near Fatal status (it is HP-based), so that immunity didn't reach its
    // data: ted_data "near_fatal_immune" / "percent_abilities" (tools/ted_plugin_data.py) carry it, and a hit of one
    // of those abilities on such a monster becomes a miss in the act's hit calculation (BattleFunction2.HitCalc
    // postfix, as the kit's SnesSuplex makes its misses).
    static class TedNearFatal
    {
        internal static int Misses;

        public static void Patch(Harmony h) =>
            Hooks.Patch(h, typeof(BattleFunction2), "HitCalc", typeof(TedNearFatal), postfix: nameof(HitCalc_Postfix));

        public static void HitCalc_Postfix(BattleFunction2 __instance)
        {
            if (!Plugin.TedMode || __instance == null || Plugin.D == null || Plugin.D.PercentAbilities.Count == 0) return;
            try
            {
                var abilities = __instance.battleActData?.abilityList;
                if (abilities == null || abilities.Count == 0 || abilities[0] == null || !Plugin.D.PercentAbilities.Contains(abilities[0].Id)) return;
                var dic = __instance.ICalcResultDic;
                if (dic == null) return;
                var keys = new List<BattleUnitData>();
                foreach (var k in dic.Keys) keys.Add(k);
                int aid = abilities[0].Id;
                foreach (var unit in keys)
                {
                    int monster = unit?.TryCast<BattleEnemyData>()?.GetMonster()?.Id ?? 0;
                    if (monster == 0 || !Plugin.D.NearFatalImmune.Contains(monster)) continue;
                    var r = dic[unit];
                    var hit = r.GetHitType();
                    if (hit != HitType.Hit && hit != HitType.Critical) continue;
                    r.SetStatus(0, HitType.Miss, r.GetHitCount(), new Il2CppSystem.Collections.Generic.List<Condition>(), false);
                    Misses++;
                    TedLog.Rule(48, $"nf-{monster}", () => $"percent spell (ability {aid}) misses monster {monster}: immune to Near Fatal (audit M17)");
                }
            }
            catch (Exception e) { Hooks.WarnOnce("ted-near-fatal", e); }
        }
    }
}
