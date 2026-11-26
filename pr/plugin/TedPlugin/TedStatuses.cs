using System;
using System.Collections.Generic;
using HarmonyLib;
using Last.Battle;
using Last.Battle.Function;
using Last.Systems;
using PrKit;
using TEdition.Rules;
using UnityEngine;
using PrKit.Ff6;

namespace TEdition.PR
{
    // T-Edition's status rules (BATTLE_SPEC 44, 50, 54, 55; numbers in TedRules/StatusMath.cs):
    //  50 ticks: Poison max HP/8, Regen max HP/8 (party) or /16 (monsters), Disease (the PR's Sap) max MP/16
    //     instead of HP, all capped at 999, no Stamina, no growth (BattleConditionFunction.GetRateValue for
    //     Poison/Sap, RegenerationConditionFunction.healValue before GenerateRegeneHeal). The cadence is the
    //     kit's SNES status clock (SnesStatusTicks, on for T-Edition in Plugin.cs).
    //  54 drains uncapped: the drainer gets the whole computed damage (BattleFunction13.GetAbsorptionValues,
    //     the PR's caps at the victim's HP and the drainer's missing HP, answers each target's full value).
    //  55 espers summonable again in a battle (BattlePlugManager.MemorizeUsedMagicStoneAbility skipped,
    //     IsUsedMagicStoneAbilityInBattle false).
    //  44 time stops while an action plays (Active and Wait): ATB gauges and chanting
    //     (BattleProgressATB.UpdateGaugeIncrease / UpdateChantTime skipped while the act executor prepares,
    //     plays or finishes an act or a counter: BNW's NatbRules idea) and the kit's status clock (the
    //     AppDomain "pr.battle.timeHeldFrame" channel SnesStatusTicks reads). Never more than 15 s in a row.
    sealed class TedStatuses : Feature
    {
        public TedStatuses() : base("Battle", "Statuses", true,
            "T-Edition's status rules: Poison/Regen/Disease ticks from max HP/MP (Disease drains MP), drains uncapped, " +
            "espers summonable again, time stops while an action plays.") { }

        static bool On => Plugin.TedMode;
        internal static int Ticks, Drains, Summons;

        internal static bool ColiseumControl;    // config [Battle] ColiseumControl (rule 56), off until seen in game

        public override void Apply(Harmony h)
        {
            if (ColiseumControl)
            {
                // 56: the Colosseum fighter takes commands (C2/0126, 092A): the PR's ActSelectQuick.CheckAutoMode
                // turns to ActSelectColosseum.CreateActDataAuto while BattlePlugManager.IsColosseumBattle; inside
                // that one check the battle reads as an ordinary one
                Hooks.Patch(h, typeof(ActSelectQuick), "CheckAutoMode", typeof(TedStatuses), prefix: nameof(AutoMode_Prefix), postfix: nameof(AutoMode_Postfix));
                Hooks.Patch(h, typeof(BattlePlugManager), "IsColosseumBattle", typeof(TedStatuses), postfix: nameof(Colosseum_Postfix));
            }
            Hooks.Patch(h, typeof(BattleConditionFunction), "GetRateValue", typeof(TedStatuses), postfix: nameof(Rate_Postfix));
            Hooks.Patch(h, typeof(RegenerationConditionFunction), "GenerateRegeneHeal", typeof(TedStatuses), prefix: nameof(Regen_Prefix));
            Hooks.Patch(h, typeof(SlipConditionFunction), "GenerateSlipDamageTo", typeof(TedStatuses), postfix: nameof(Sap_Postfix));
            Hooks.Patch(h, typeof(BattleFunction13), "GetAbsorptionValues", typeof(TedStatuses), postfix: nameof(Absorb_Postfix));
            Hooks.Patch(h, typeof(BattlePlugManager), "MemorizeUsedMagicStoneAbility", typeof(TedStatuses), prefix: nameof(Memorize_Prefix));
            Hooks.Patch(h, typeof(BattlePlugManager), "IsUsedMagicStoneAbilityInBattle", typeof(TedStatuses), postfix: nameof(IsUsed_Postfix));
            // 44 on the kit's action freeze (BNW's nATB: the gauge, chants, the status timers and the status clock;
            // ted-gate-1, 2026-11-25: TED's own hooks never held: the FF6 update doesn't call UpdateGaugeIncrease and
            // the game never writes BattleActExection.nowState)
            SnesActionFreeze.Tag = "[ted]";
            SnesActionFreeze.On = () => On;
            SnesActionFreeze.WhileTurnUp = () => false;
            SnesActionFreeze.Patch(h);
            Hooks.Patch(h, typeof(BattleConditionController), "Update", typeof(TedStatuses), prefix: nameof(Clock_Prefix));
        }

        public override string Check() => On ? "on" : "off (no T-Edition data)";

        // --- 50: ticks ----------------------------------------------------------------------------------

        static bool Unit(BattleUnitData u, out Last.Data.CharacterParameterBase p, out bool party)
        {
            p = u?.BattleUnitDataInfo?.Parameter;
            party = p != null && u.TryCast<BattlePlayerData>() != null;
            return p != null;
        }

        public static void Rate_Postfix(BattleConditionFunction __instance, int typeIndex, ref int __result)
        {
            if (!On || __instance == null) return;
            try
            {
                bool poison = typeIndex == 1 && Hooks.IsA<PoisonConditionFunction>(__instance);
                bool sap = typeIndex == 4 && Hooks.IsA<SlipConditionFunction>(__instance);
                if (!poison && !sap) return;
                if (!Unit(__instance.BattleUnitData, out var v, out bool party)) return;
                int was = __result;
                if (poison)
                {
                    int now = StatusMath.Poison(v.ConfirmedMaxHp());
                    __result = now;
                    Ticks++;
                    TedLog.Rule(50, "poison", () => $"Poison tick on a {(party ? "character" : "monster")}: max HP/8 = {now} (the game's {was})");
                }
                else
                {
                    __result = 0;   // Disease drains MP instead (Sap_Postfix)
                    TedLog.Rule(50, "sap", () => $"Disease (Sap) tick: no HP damage (the game's {was}); MP/16 instead");
                }
            }
            catch (Exception e) { Hooks.WarnOnce("TedStatuses.Rate", e); }
        }

        public static void Regen_Prefix(RegenerationConditionFunction __instance)
        {
            if (!On || __instance == null) return;
            try
            {
                if (!Unit(__instance.BattleUnitData, out var v, out bool party)) return;
                int was = __instance.healValue, now = StatusMath.Regen(v.ConfirmedMaxHp(), party);
                __instance.healValue = now;
                Ticks++;
                TedLog.Rule(50, "regen" + party, () => $"Regen tick on a {(party ? "character: max HP/8" : "monster: max HP/16")} = {now} (the game's {was})");
            }
            catch (Exception e) { Hooks.WarnOnce("TedStatuses.Regen", e); }
        }

        public static void Sap_Postfix(SlipConditionFunction __instance, BattleUnitData battleUnitData)
        {
            if (!On || __instance == null) return;
            try
            {
                var p = battleUnitData?.BattleUnitDataInfo?.Parameter;
                if (p == null || p.CurrentHP <= 0) return;
                int loss = StatusMath.Disease(p.ConfirmedMaxMp());
                int was = p.CurrentMP, now = Math.Max(0, was - loss);
                p.CurrentMP = now;
                Ticks++;
                TedLog.Rule(50, "disease", () => $"Disease tick: MP {was} -> {now} (max MP/16 = {loss})");
            }
            catch (Exception e) { Hooks.WarnOnce("TedStatuses.Sap", e); }
        }

        // --- 56: the Colosseum fighter takes commands ---------------------------------------------------

        [ThreadStatic] static int autoCheck;

        public static void AutoMode_Prefix() => autoCheck++;
        public static void AutoMode_Postfix() { if (autoCheck > 0) autoCheck--; }

        public static void Colosseum_Postfix(ref bool __result)
        {
            if (!On || autoCheck <= 0 || !__result) return;
            __result = false;
            TedLog.Rule(56, "", () => "Colosseum fight: the fighter takes commands (no auto act)");
        }

        // --- 54: drains -----------------------------------------------------------------------------------

        public static void Absorb_Postfix(BattleFunction13 __instance, Il2CppSystem.Collections.Generic.Dictionary<BattleUnitData, int> __result)
        {
            if (!On || __instance == null || __result == null) return;
            try
            {
                var dic = __instance.ICalcResultDic;
                if (dic == null) return;
                var keys = new List<BattleUnitData>();
                foreach (var k in __result.Keys) keys.Add(k);
                foreach (var unit in keys)
                {
                    if (unit == null || !dic.ContainsKey(unit)) continue;
                    var r = dic[unit];
                    var hit = r.GetHitType();
                    if (hit != HitType.HpAbs && hit != HitType.MpAbs && hit != HitType.Hit && hit != HitType.Critical) continue;
                    int full = r.GetValue(false), was = __result[unit];
                    if (full <= was) continue;
                    __result[unit] = full;
                    Drains++;
                    TedLog.Rule(54, "", () => $"drain uncapped: {was} -> {full} (the whole damage)");
                }
            }
            catch (Exception e) { Hooks.WarnOnce("TedStatuses.Absorb", e); }
        }

        // --- 55: espers again ---------------------------------------------------------------------------

        public static bool Memorize_Prefix(BattlePlugManager __instance, int characterStatusId)
        {
            if (!On) return true;
            Summons++;
            TedLog.Rule(55, "", () => $"esper summoned by character {characterStatusId}: not marked, espers stay available (T-Edition)");
            return false;
        }

        public static void IsUsed_Postfix(ref bool __result)
        {
            if (On && __result) __result = false;
        }

        // --- 44: time stops while an action plays -------------------------------------------------------------
        // The holding itself is the kit's SnesActionFreeze (patched in Apply); this logs the rule and counts.

        internal static int FrozenFrames;
        static int lastFrame = -1;

        static bool Frozen()
        {
            int f = Time.frameCount;
            if (f == lastFrame || !On) return false;
            lastFrame = f;
            try
            {
                if (!SnesActionFreeze.Held()) return false;
                if (FrozenFrames++ == 0)
                    TedLog.Rule(44, "", () => "time stops while an action plays (ATB, chanting, the status clock)");
                return true;
            }
            catch (Exception e)
            {
                Hooks.WarnOnce("TedStatuses.Freeze", e);
                return false;
            }
        }

        public static void Clock_Prefix() => Frozen();
    }
}
