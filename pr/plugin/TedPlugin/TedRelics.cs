using System;
using System.Collections.Generic;
using Last.Data;
using Last.Data.User;
using Last.Management;
using PrKit;

namespace TEdition.PR
{
    // Audit I5: T-Edition gives vanilla relic effects to more items (its relic bits, decoded in ted_data "relic_bits":
    // byte.bit -> its item slots). The PR keys most of those effects on its own items' ids (in code: Gale Hairpin and
    // Alarm Earring by content, Atlas Armlet / Hero Ring by CalcExecuteCorrection's PhysicalType, Earrings by
    // MagicType, Hyper Wrist in its strength), so T-Edition's relics on the same rows work and its other items (Gram,
    // Gigas Glove, Brave Ring, Wizard Rod, Earthbreaker, Behemoth Suit, Masamune, Earth Greaves, ...) need these hooks:
    //   9.0 physical damage +25% (an Atlas-type answer from GetAccessoryPhysicalCorrectionValue, BasketsOfGiants)
    //   9.1 magic damage +25% (an Earring answer from GetAccessoryMagicCorrectionValue)
    //   11.7 strength +50% (PlayerCharacterParameter.ConfirmedPower); 11.2 Sketch up, 12.2 Blade Grasp (evasion +20),
    //   12.7 multi-jump: Patch()'s hooks (decompiled: UniqueUpdateParameterProvider.HitCalc's Beret check,
    //   the Beads' evasion_rate, SerialBattleUtility.CanContiniusJumpAttack's Dragon Horn)
    //   11.0 Steal up, 12.0 Offering-type, 13.2 SOS Reflect, 13.5 pre-emptive up, 13.6 Alarm: read by TedCommands,
    //   TedDesperation, TedSosReflect, TedEncounters through Wears().
    // The data-only ones (9.2 HP +25%, 9.3 HP +50%, 12.0's four hits: the PR's passive abilities 286 / 288 / 253) are the
    // porter's relic_bit_funcs.
    static class TedRelics
    {
        static readonly Dictionary<string, HashSet<int>> contents = new Dictionary<string, HashSet<int>>();

        // the content ids of the items that set a relic bit ("9.0" ...)
        public static HashSet<int> Contents(string bit)
        {
            if (contents.TryGetValue(bit, out var set)) return set;
            set = new HashSet<int>();
            foreach (var slot in Plugin.D.RelicSlots(bit))
            {
                int c = Plugin.D.BySlot(slot)?.Content ?? 0;
                if (c > 0) set.Add(c);
            }
            if (Plugin.D.RelicSlots(bit).Length > 0) contents[bit] = set;
            return set;
        }

        public static bool Wears(OwnedCharacterData c, string bit)
        {
            var eq = c?.EquipmentData;
            if (eq == null) return false;
            var set = Contents(bit);
            if (set.Count == 0) return false;
            foreach (var kv in eq) if (kv.Value != null && set.Contains(kv.Value.ContentId)) return true;
            return false;
        }

        public static bool AnyWears(OwnedCharacterData[] party, string bit)
        {
            if (party == null) return false;
            foreach (var c in party) if (Wears(c, bit)) return true;
            return false;
        }

        public static void Patch(HarmonyLib.Harmony h)
        {
            Hooks.Patch(h, typeof(PlayerCharacterParameter), "ConfirmedPower", typeof(TedRelics), postfix: nameof(Power_Postfix));
            // 11.2 Sketch up (the Beret's x2 threshold, inline in UniqueUpdateParameterProvider.HitCalc's ff6_ability_sketch
            // branch: its EquipmentData[Slot4] item 23 check): IsResistanceSketch (called just before the roll) arms, the
            // roll GetRandPlus(100) answers half
            Hooks.Patch(h, typeof(Serial.FF6.Calc.UniqueUpdateParameterProvider), "IsResistanceSketch", typeof(TedRelics), postfix: nameof(Sketch_Postfix));
            Hooks.Patch(h, typeof(global::CommonUtility), "GetRandPlus", typeof(TedRelics), postfix: nameof(RandPlus_Postfix), args: new[] { typeof(int) });
            // 12.2 Blade Grasp: the PR's Beads are evasion 20 in data (armor row 115): T-Edition's other items add the same
            Hooks.Patch(h, typeof(PlayerCharacterParameter), "ConfirmedEvasionRate", typeof(TedRelics), postfix: nameof(Evasion_Postfix));
            // 12.7 multi-jump: SerialBattleUtility.CanContiniusJumpAttack keys on the Dragon Horn (armor row 120)
            Hooks.Patch(h, typeof(Serial.FF6.Management.SerialBattleUtility), "CanContiniusJumpAttack", typeof(TedRelics), postfix: nameof(Jump_Postfix));
        }

        const int BeretContent = 219, BeadsContent = 311;
        [ThreadStatic] static bool sketchArmed;
        internal static int SketchBoosts, Jumps;

        public static void Sketch_Postfix(Last.Battle.BattleUnitData unitData)
        {
            try
            {
                sketchArmed = false;
                if (!Plugin.TedMode) return;
                var c = unitData?.TryCast<global::BattlePlayerData>()?.ownedCharacterData;
                if (c == null || !Wears(c, "11.2")) return;
                foreach (var kv in c.EquipmentData) if (kv.Value != null && kv.Value.ContentId == BeretContent) return;   // the game's own x2
                sketchArmed = true;
            }
            catch (Exception e) { Hooks.WarnOnce("ted-relic-sketch", e); }
        }

        public static void RandPlus_Postfix(int max, ref int __result)
        {
            if (!sketchArmed || max != 100) return;
            sketchArmed = false;
            __result /= 2;   // floor(r / 2) < t  ==  r < 2t: the Beret's doubled threshold
            SketchBoosts++;
            TedLog.Rule(0, "relic-11.2", () => "Sketch chance up from a T-Edition item (bit 11.2, audit I5)");
        }

        public static void Evasion_Postfix(PlayerCharacterParameter __instance, bool isNatunalValue, ref int __result)
        {
            if (isNatunalValue || inPower || !Plugin.TedMode) return;
            inPower = true;
            try
            {
                var c = Owner(__instance);
                if (c == null || !Wears(c, "12.2")) return;
                foreach (var kv in c.EquipmentData) if (kv.Value != null && kv.Value.ContentId == BeadsContent) return;   // the Beads' own 20
                __result += 20;
                TedLog.Rule(0, "relic-12.2", () => "Blade Grasp: evasion +20 from a T-Edition item (bit 12.2, audit I5)");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-relic-evade", e); }
            finally { inPower = false; }
        }

        public static void Jump_Postfix(Last.Battle.BattleUnitData battleUnitData, ref bool __result)
        {
            try
            {
                if (__result || !Plugin.TedMode) return;
                var c = battleUnitData?.TryCast<global::BattlePlayerData>()?.ownedCharacterData;
                if (c == null || !Wears(c, "12.7")) return;
                __result = true;
                Jumps++;
                TedLog.Rule(0, "relic-12.7", () => "multi-jump from a T-Edition item (Gungnir; bit 12.7, audit I5)");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-relic-jump", e); }
        }

        // the parameter's owner (the PR's parameter has no back reference)
        static OwnedCharacterData Owner(PlayerCharacterParameter p)
        {
            var list = UserDataManager.Instance()?.OwnedCharacterList;
            if (list == null || p == null) return null;
            foreach (var c in list) if (c?.Parameter != null && c.Parameter.Pointer == p.Pointer) return c;
            return null;
        }

        const int HyperWristContent = 309;   // the PR's own Hyper Wrist row (T-Edition's 212 sits on it): the PR's +50%

        [ThreadStatic] static bool inPower;

        public static void Power_Postfix(PlayerCharacterParameter __instance, ref int __result)
        {
            if (inPower || !Plugin.TedMode) return;
            inPower = true;
            try
            {
                var c = Owner(__instance);
                if (c == null || !Wears(c, "11.7")) return;
                foreach (var kv in c.EquipmentData) if (kv.Value != null && kv.Value.ContentId == HyperWristContent) return;
                int was = __result;
                __result = Math.Min(255, was + was / 2);
                TedLog.Rule(0, "relic-11.7", () => $"strength +50% from a T-Edition item ({c.Name}: {was} -> {Math.Min(255, was + was / 2)}; audit I5)");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-relic-power", e); }
            finally { inPower = false; }
        }
    }
}
