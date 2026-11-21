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
    //   11.7 strength +50% (PlayerCharacterParameter.ConfirmedPower)
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

        public static void Patch(HarmonyLib.Harmony h) =>
            Hooks.Patch(h, typeof(PlayerCharacterParameter), "ConfirmedPower", typeof(TedRelics), postfix: nameof(Power_Postfix));

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
