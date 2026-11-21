using System;
using System.Collections.Generic;
using System.Linq;
using HarmonyLib;
using Last.Battle;
using Last.Data;
using Last.Data.Master;
using Last.Defaine;
using Last.Systems;
using PrKit;
using TEdition.Rules;
using Il2CppIntMap = Il2CppSystem.Collections.Generic.Dictionary<int, int>;

namespace TEdition.PR
{
    // T-Edition's damage steps (BATTLE_SPEC rules 6-10, 17, 40; TedRules/DamageSteps.cs) on the game's
    // results. CalcControllerProvider.GetFightStatus / GetMagicStatus / GetRecoveryStatus: the prefix reads
    // what the game will use (the ability's elements and the target's responses, Def/MDef, Safe/Shell,
    // Defend, row, Morph, the ignore-defense flag) and works out T-Edition's steps over the game's; a
    // multi-element attack's target table reads with T-Edition's outcome while the game computes it
    // (ConfirmedResistanceAttributeList postfix: the game's own "one response" rule then gives 0 or a heal
    // where T-Edition's sum does); the postfix multiplies the game's value by the factor.
    sealed class TedDamage : Feature
    {
        public TedDamage() : base("Battle", "Damage", true,
            "T-Edition's damage rules: elements split over an attack's elements, weakness quarters the target's defense instead of x2, " +
            "attacks that ignore defense (and heals) still meet Safe/Shell/Defend/row/Morph, half damage from them on T-Edition's flagged monsters, " +
            "magic on a defending or Morphed target and physical on the back row x170/256, Trance x1.5, Atma Weapon by Stamina.") { }

        internal static bool On => Plugin.TedMode && !Bypass;
        internal static bool Bypass;                 // tests: the game's own value
        internal static DamageSteps.Result LastResult;     // tests: the last result worked out
        internal static string LastInputs = "";
        internal static int Applied;
        internal static bool NoSplitTest;            // tests: rule 37 off (the game's own split)
        static int cap = 9999;

        public override void Apply(Harmony h)
        {
            var calc = typeof(CalcControllerProvider);
            Hooks.Patch(h, calc, "GetFightStatus", typeof(TedDamage), prefix: nameof(Fight_Prefix), postfix: nameof(Calc_Postfix));
            Hooks.Patch(h, calc, "GetMagicStatus", typeof(TedDamage), prefix: nameof(Magic_Prefix), postfix: nameof(Calc_Postfix));
            Hooks.Patch(h, calc, "GetRecoveryStatus", typeof(TedDamage), prefix: nameof(Heal_Prefix), postfix: nameof(Calc_Postfix));
            Hooks.Patch(h, typeof(PlayerCharacterParameter), "ConfirmedResistanceAttributeList", typeof(TedDamage), postfix: nameof(Resist_Postfix));
            Hooks.Patch(h, typeof(EnemyCharacterParameter), "ConfirmedResistanceAttributeList", typeof(TedDamage), postfix: nameof(Resist_Postfix));
            Hooks.Patch(h, typeof(CalcExecuteCorrection), "GetAccessoryPhysicalCorrectionValue", typeof(TedDamage), postfix: nameof(Physical_Postfix));
            Hooks.Patch(h, typeof(CalcExecuteCorrection), "GetAccessoryMagicCorrectionValue", typeof(TedDamage), postfix: nameof(MagicBoost_Postfix));
            Hooks.Patch(h, typeof(CalcExecuteCorrection), "GetHawkEyeCorrectionValue", typeof(TedDamage), postfix: nameof(HawkEye_Postfix));
        }

        // 16: Hawk-eye weapons (Cards, Darts, Tarot of Ben, Antares: weapon process HAWK_EYE). The PR rolls an
        // attack type per act (FunctionProvider.CheckAndSetHawkEyeAttackType) and answers x1.5 ("to land") or
        // x3 ("to sky", a floating target) here; vanilla's 50% +1 $BC, +3 more vs Float. T-Edition (C2/38EE):
        // no roll, x2 against a target with Float when the command is Fight, nothing otherwise.
        public static void HawkEye_Postfix(BattleActData battleActData, ref float __result)
        {
            if (!On || battleActData == null) return;
            try
            {
                var type = battleActData.GetHawkEyeAttackType();
                if (type == BattleActData.HawkEyeAttackType.None) return;   // not a Hawk-eye weapon's act
                var targets = battleActData.TargetUnitDatas;
                var t = targets != null && targets.Length > 0 ? targets[0] : null;
                bool floating = t?.BattleUnitDataInfo?.GetConfirmedConditionType()?.Contains(ConditionType.Leviteto) == true;
                bool fight = battleActData.Command?.Id == 1;
                float was = __result, now = fight && floating ? 2f : 1f;
                __result = now;
                TedLog.Rule(16, "", () => $"Hawk-eye ({type}, {(fight ? "Fight" : "not Fight")}, target {(floating ? "floating" : "on the ground")}): x{now} (the game's x{was})");
            }
            catch (Exception e) { Hooks.WarnOnce("TedDamage.HawkEye", e); }
        }

        // 15: the Atlas-type physical boost (CalcExecuteCorrection.PhysicalType 2, "BasketsOfGiants") +25% once,
        // however many are worn (T-Edition NOPs the double-boost branch at C2/0D62)
        public static void Physical_Postfix(CalcExecuteCorrection.PhysicalType physicalType, Last.Data.User.OwnedCharacterData ownedCharacterData, ref float __result)
        {
            if (!On || (int)physicalType != 2) return;
            // audit I5: T-Edition's other "physical attack up" items (relic bit 9.0: Gram, Gigas Glove, Brave Ring ...)
            if (__result == 1f && TedRelics.Wears(ownedCharacterData, "9.0"))
            {
                __result = 1.25f;
                TedLog.Rule(15, "relic-9.0", () => "a T-Edition physical-boost item: +25% (bit 9.0, audit I5)");
            }
            float was = __result;
            if (was > 1.25f) __result = 1.25f;                 // a multiplier
            else if (was > 0.25f && was < 1f) __result = 0.25f; // a fraction
            if (__result != was)
            {
                float now = __result;
                TedLog.Rule(15, "phys", () => $"Atlas-type boost {was} -> {now} (one +25%, no stacking)");
            }
        }

        public override string Check()
        {
            if (!Plugin.TedMode) return "off (no T-Edition data)";
            var c = TedHarness.Constants("MAX_HIT_VALUE");
            if (c.TryGetValue("MAX_HIT_VALUE", out int v) && v > 0) cap = v;
            return $"on: damage cap {cap} (MAX_HIT_VALUE), {Plugin.D.HalfIgnoreDefense.Count} half-damage monsters, " +
                   $"Valiant Knife row {Plugin.D.NamedRow("valiant_knife")}, Atma Weapon row {Plugin.D.NamedRow("atma_weapon")}";
        }

        // --- the calculation in progress (one per thread; the game's calc runs on the main thread) ------

        public sealed class Calc
        {
            public DamageSteps.Result R;
            public IntPtr Target;
            public int[] Elements;
            public int ViewsServed;
            public int HealEarrings = -1;      // rule 15 on a heal: the relics worn (-1: not a heal or none)
            public bool GameBoostedHeal;       // the game asked for the Earring boost during this heal
        }

        internal const int GilTossAbility = 15, GameGilTossPerLevel = 30;   // rule 29 (ted-7: 90 at Lv 3)
        internal static bool GameSplits = false;   // rule 37: the game splits effect $2A spells over targets (it doesn't)
        [ThreadStatic] static Calc healCalc;
        [ThreadStatic] static bool ownAsk;

        // rule 15 (heals): notes whether the game itself asks for the Earring boost while computing a heal
        public static void MagicBoost_Postfix(CalcExecuteCorrection.MagicType magicType, Last.Data.User.OwnedCharacterData ownedCharacterData,
                                              ref int equipNum, ref float __result)
        {
            // audit I5: T-Edition's other "magic attack up" items (relic bit 9.1: Wizard Rod, Brave Ring ...) count as one Earring
            if ((int)magicType == 0 && equipNum == 0 && TedRelics.Wears(ownedCharacterData, "9.1"))
            {
                equipNum = 1;
                __result = 1.25f;
                TedLog.Rule(15, "relic-9.1", () => "a T-Edition magic-boost item: +25% (bit 9.1, audit I5)");
            }
            if (!ownAsk && healCalc != null) healCalc.GameBoostedHeal = true;
        }

        [ThreadStatic] static Calc current;

        public static void Fight_Prefix(CalcControllerProvider __instance, ref Calc __state) => Enter(__instance, ref __state, true, false);
        public static void Magic_Prefix(CalcControllerProvider __instance, ref Calc __state) => Enter(__instance, ref __state, false, false);
        public static void Heal_Prefix(CalcControllerProvider __instance, ref Calc __state) => Enter(__instance, ref __state, false, true);

        static void Enter(CalcControllerProvider c, ref Calc state, bool physical, bool heal)
        {
            state = null;
            if (!On || current != null || c == null || !Hooks.IsA<CalcControllerProvider>(c)) return;
            try
            {
                var target = c.target;
                var attacker = c.attack;
                if (target == null || attacker == null) return;
                var ability = c.ability;
                var tUnit = c.GetUnitData(target);
                var aUnit = c.GetUnitData(attacker);
                var tCond = tUnit?.BattleUnitDataInfo?.GetConfirmedConditionType();
                var aCond = aUnit?.BattleUnitDataInfo?.GetConfirmedConditionType();
                bool Has(Il2CppSystem.Collections.Generic.List<ConditionType> l, ConditionType t) => l != null && l.Contains(t);
                var ci = c.calcInfo;
                var weapon = physical ? ci?.userWeapon : null;
                bool flag5 = IgnoresDefense(ability);
                int vkRow = Plugin.D.NamedRow("valiant_knife"), atmaRow = Plugin.D.NamedRow("atma_weapon");
                bool valiant = physical && weapon != null && vkRow > 0 && weapon.Id == vkRow;
                var tool = c.item?.Item;
                bool machineIgnores = physical && tool != null && (tool.Id == 33 || tool.Id == 35);   // CalcExecuteCorrection.IgnoreDefenseItemIds
                bool targetIsCharacter = c.targetCharaData != null;
                int abilityType = ability?.TypeId ?? 0;
                bool jump = abilityType == 15 || abilityType == 16;
                // 41: Dice / Fixed Dice (weapon process DICE / CHEAT_DICE; the game's own roll in
                // CalcExecuteCorrection.IsDiceWeapon: faces product x 2 x Lv, all equal face^(n+1) x 2 x Lv)
                var prog = physical ? weapon?.ProcessProg : null;
                if (prog == "DICE" || prog == "CHEAT_DICE")
                {
                    int dice = prog == "CHEAT_DICE" ? 3 : 2, lv = attacker.ConfirmedLevel();
                    int dm = targetIsCharacter ? 0 : tUnit?.TryCast<BattleEnemyData>()?.GetMonster()?.Id ?? 0;
                    bool half = dm > 0 && Plugin.D.HalfIgnoreDefense.Contains(dm);
                    var dr = new DamageSteps.Result();
                    if (lv > 0 && dice == 3) dr.Factor *= (double)StatusMath.DiceLevel(lv, 3) / lv;
                    if (half) dr.Factor /= 16.0;
                    dr.Rule(41, $"{(dice == 3 ? "Fixed Dice: level " + lv + " -> " + StatusMath.DiceLevel(lv, 3) : "Dice")}" +
                                $"{(half ? ", /16 on a half-damage monster" : "")}");
                    LastResult = dr;
                    LastInputs = $"dice ({dice}) by Lv {lv} on {(targetIsCharacter ? c.targetCharaData.Name : $"monster {dm}")}";
                    if (Math.Abs(dr.Factor - 1.0) < 1e-9) return;
                    state = new Calc { R = dr, Target = target.Pointer, Elements = Array.Empty<int>() };
                    return;
                }
                var elems = Elements(c, ability, physical);
                var types = new int[elems.Length];
                if (elems.Length > 0 && !heal)
                {
                    var table = target.ConfirmedResistanceAttributeList();
                    for (int i = 0; i < elems.Length; i++)
                        types[i] = table != null && table.ContainsKey(elems[i]) ? table[elems[i]] : 0;
                }
                int monsterId = targetIsCharacter ? 0 : tUnit?.TryCast<BattleEnemyData>()?.GetMonster()?.Id ?? 0;
                var hit = new DamageSteps.Hit
                {
                    Physical = physical,
                    Heal = heal,
                    IgnoreDefense = flag5 || machineIgnores,
                    GameSkippedDefense = flag5 || machineIgnores || valiant,
                    Defense = physical ? target.ConfirmedDefense() : target.ConfirmedAbilityDefense(),
                    Guard = Has(tCond, physical ? ConditionType.Proteus : ConditionType.Shell),
                    Defending = Has(tCond, ConditionType.Defend),
                    BackRow = physical && targetIsCharacter && c.targetCorpsId == Last.Defaine.User.CorpsId.Back && tool == null && !jump,
                    TargetMorph = Has(tCond, ConditionType.Trance),
                    AttackerMorph = Has(aCond, ConditionType.Trance),
                    HalfFlag = monsterId > 0 && Plugin.D.HalfIgnoreDefense.Contains(monsterId),
                    Elements = elems.Length == 0 || heal ? Array.Empty<int>() : types,
                    Atma = physical && c.userCharaData != null && weapon != null && atmaRow > 0 && weapon.Id == atmaRow,
                    Level = attacker.ConfirmedLevel(),
                    Stamina = attacker.ConfirmedVitality(),
                };
                var r = DamageSteps.Apply(hit);
                // 37: effect $2A (Mysidian Rabbit, Heal Force, Flare Star) no longer divided by the targets
                // (C2/4115 NOPed): the game's per-target value x the number of targets
                int aid = ability?.Id ?? 0;
                if (aid > 0 && (aid == Plugin.D.Ability("mysidian_rabbit") || aid == Plugin.D.Ability("heal_force") ||
                                aid == Plugin.D.Ability("flare_star")) && !NoSplitTest)
                {
                    // ted-7 (2026-11-21): the game doesn't split these either (Mysidian Rabbit 76 on 1 target, 73 each
                    // on 3), so T-Edition's rule holds as the game has it: no factor (GameSplits for a game that would)
                    int n = c.numTarget;
                    if (n > 1 && GameSplits)
                    {
                        r.Factor *= n;
                        r.Rule(37, $"ability {aid} not split over its {n} targets (x{n})");
                    }
                    else if (n > 1) r.Rule(37, $"ability {aid} on {n} targets: not split (the game's own way)");
                }
                // 15: one +25% magic boost however many Earrings (the game: 1 + 0.25 x the number worn, in
                // MagicExecution); heals: T-Edition boosts them too (whether the game does: unchecked)
                if (!physical && !heal && c.userCharaData != null)
                {
                    int n = 0;
                    try { CalcExecuteCorrection.GetAccessoryMagicCorrectionValue(CalcExecuteCorrection.MagicType.Earring, c.userCharaData, out n); }
                    catch (Exception) { n = 0; }
                    if (n >= 2)
                    {
                        r.Factor *= 1.25 / (1 + 0.25 * n);
                        r.Rule(15, $"{n} magic boost relics: +25% once (the game's +{25 * n}%)");
                    }
                }
                // 29: a character's Gil Toss deals Lv x 90 to every target (the game's Lv x 30, unsplit: ted-7's tedgil,
                // 90 at Lv 3 on one and on two monsters); the cost (Lv x 180) is TedCommands'
                if (ability != null && ability.Id == GilTossAbility && c.userCharaData != null)
                {
                    r.Factor *= CommandMath.GilTossDamage(1) / (double)GameGilTossPerLevel;
                    r.Rule(29, $"Gil Toss: Lv x {CommandMath.GilTossDamage(1)} to each target (the game's Lv x {GameGilTossPerLevel})");
                }
                if (valiant) r.Rule(60, "Valiant Knife meets the target's defense (T-Edition NOPs its ignore-defense)");
                LastResult = r;
                LastInputs = $"{(physical ? "physical" : heal ? "heal" : "magic")} ability {ability?.Id} (type {abilityType}) on " +
                             $"{(targetIsCharacter ? c.targetCharaData.Name : $"monster {monsterId}")}: elements [{string.Join(",", elems)}] " +
                             $"responses [{string.Join(",", hit.Elements)}], {(physical ? "Def" : "MDef")} {hit.Defense}" +
                             $"{(hit.IgnoreDefense ? ", ignores defense" : "")}{(hit.Guard ? (physical ? ", Safe" : ", Shell") : "")}" +
                             $"{(hit.Defending ? ", defending" : "")}{(hit.BackRow ? ", back row" : "")}{(hit.TargetMorph ? ", Morphed" : "")}" +
                             $"{(hit.AttackerMorph ? ", Morphed attacker" : "")}{(hit.HalfFlag ? ", half-damage monster" : "")}" +
                             $"{(hit.Atma ? $", Atma (Lv {hit.Level}, Sta {hit.Stamina})" : "")}";
                // 15 (heals): T-Edition's Earring boost covers healing magic too (C2/0D47); how many are worn
                int healEarrings = -1;
                if (heal && c.userCharaData != null)
                {
                    int n = 0;
                    ownAsk = true;
                    try { CalcExecuteCorrection.GetAccessoryMagicCorrectionValue(CalcExecuteCorrection.MagicType.Earring, c.userCharaData, out n); }
                    catch (Exception) { n = 0; }
                    finally { ownAsk = false; }
                    if (n >= 1) healEarrings = n;
                }
                if (Math.Abs(r.Factor - 1.0) < 1e-9 && r.View == DamageSteps.View.None && r.Fired.Count == 0 && healEarrings < 0) return;
                state = new Calc { R = r, Target = target.Pointer, Elements = elems, HealEarrings = healEarrings };
                if (r.View != DamageSteps.View.None) current = state;
                if (healEarrings > 0) healCalc = state;
            }
            catch (Exception e) { Hooks.WarnOnce("TedDamage.Enter", e); }
        }

        public static void Calc_Postfix(CalcControllerProvider __instance, ICalcResult __result, Calc __state)
        {
            if (__state == null) return;
            if (current == __state) current = null;
            if (healCalc == __state) healCalc = null;
            if (__state.HealEarrings > 0)
            {
                // the game boosted the heal (1 + 0.25 n): capped at one +25%; it didn't: T-Edition's +25% added
                int n = __state.HealEarrings;
                if (__state.GameBoostedHeal && n >= 2) { __state.R.Factor *= 1.25 / (1 + 0.25 * n); __state.R.Rule(15, $"heal: {n} boost relics, +25% once (the game's +{25 * n}%)"); }
                else if (!__state.GameBoostedHeal) { __state.R.Factor *= 1.25; __state.R.Rule(15, $"heal: +25% from {n} boost relic(s) (the game gives heals none)"); }
                __state.HealEarrings = 0;
            }
            try
            {
                if (__result == null) return;
                var r = __state.R;
                var hit = __result.GetHitType();
                int value = __result.GetValue(false);
                bool damage = hit == HitType.Hit || hit == HitType.Critical;
                bool heal = hit == HitType.Recovery;
                int now = value;
                if ((damage || heal) && value > 0 && Math.Abs(r.Factor - 1.0) > 1e-9)
                {
                    if (value >= cap && r.Factor > 1) now = value;    // the game's cap already: left as it is
                    else now = DamageSteps.Scale(value, r.Factor, cap);
                    if (now != value)
                    {
                        __result.SetValue(now);
                        Applied++;
                    }
                }
                var inputs = LastInputs;
                foreach (var (rule, text) in r.Fired)
                {
                    int was = value, after = now;
                    TedLog.Rule(rule, "", () => $"{text}; {inputs}; the game's {was} -> {after}" +
                                               (__state.ViewsServed > 0 ? " (element view read)" : ""));
                }
            }
            catch (Exception e) { Hooks.WarnOnce("TedDamage.Result", e); }
        }

        // the target's element table while a multi-element attack is worked out (T-Edition's outcome)
        public static void Resist_Postfix(CharacterParameterBase __instance, ref Il2CppIntMap __result)
        {
            var calc = current;
            if (calc == null || __instance == null || __instance.Pointer != calc.Target) return;
            try
            {
                var table = new Dictionary<int, int>();
                if (__result != null)
                    foreach (var kv in __result) table[kv.Key] = kv.Value;
                var view = DamageSteps.ViewTable(table, calc.Elements, calc.R.View);
                if (view == null) return;
                var m = new Il2CppIntMap();
                foreach (var kv in view) m.Add(kv.Key, kv.Value);
                __result = m;
                calc.ViewsServed++;
            }
            catch (Exception e) { Hooks.WarnOnce("TedDamage.Resist", e); }
        }

        // --- what the game reads -------------------------------------------------------------------------

        // the attack's elements as the game takes them: the ability's (its attribute group or id) and, for a
        // character's physical strike, the striking hand's weapon (GetArmConfirmedActiveAttributeList)
        static int[] Elements(CalcControllerProvider c, Ability ability, bool physical)
        {
            var set = new SortedSet<int>();
            if (ability != null)
            {
                var arr = c.GetAbilityAttributeArray(ability);
                if (arr != null)
                    foreach (var a in arr) if (a > 0) set.Add(a);
            }
            if (physical && c.userCharaData != null)
            {
                var pp = c.attack?.TryCast<PlayerCharacterParameter>();
                var ci = c.calcInfo;
                if (pp != null && ci != null)
                {
                    var arm = ci.userWeapon != null && ci.userLeftWeapon != null && ci.userRightWeapon != null &&
                              ci.userWeapon.Id == ci.userLeftWeapon.Id && ci.userWeapon.Id != ci.userRightWeapon.Id
                        ? BattleActData.ArmType.Left : BattleActData.ArmType.Right;
                    var list = pp.GetArmConfirmedActiveAttributeList(arm);
                    if (list != null)
                        foreach (var a in list) if (a > 0) set.Add(a);
                }
            }
            return set.ToArray();
        }

        static readonly Dictionary<int, bool> ignoreDefense = new Dictionary<int, bool>();

        // content flag 5 = ignore defense (BNW's formula probe, 2026-11-05)
        internal static bool IgnoresDefense(Ability a)
        {
            if (a == null) return false;
            int g = a.ContentFlagGroupId;
            if (g == 0) return false;
            lock (ignoreDefense)
            {
                if (ignoreDefense.TryGetValue(g, out bool known)) return known;
                bool found = false;
                var list = Master.All<ContentFlagGroup>();
                if (list != null)
                    foreach (var kv in list)
                        if (kv.Value != null && kv.Value.GroupId == g && kv.Value.ContentFlagId == 5) { found = true; break; }
                ignoreDefense[g] = found;
                return found;
            }
        }
    }
}
