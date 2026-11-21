using System;
using System.Collections.Generic;
using Last.Battle;
using Last.Data.Master;
using Last.Defaine;
using PrKit;

namespace TEdition.PR
{
    // Rule 39 / audit M31: desperation attacks as T-Edition has them (ted/battle_commands.md §18; 40/3700, C2/15C3): a
    // character's Fight while Near Fatal turns into its desperation attack with 1 chance in 32 (vanilla 1 in 16), with no
    // 768-frame timer, any number of times, for all fourteen (Gau $FB, Gogo $FC, Umaro $FD too: spell $F0 + character),
    // and never with Elven Darts in hand or the Master's Scroll / Offering worn. The PR decides it in
    // BattleProgressATBFF6.CheckAndChangeDyingSpecialAbility(act) (decompiled: Fight ability 1, the per-character 25.6 s
    // timer, HP <= max / RATE_HAVE_NEAR_DEATH, GetRand(16), a native table of abilities 228-239 without Gau and Umaro):
    // a prefix replaces it whole. The spells' PR abilities come from ted_data "abilities" desperation_<index>.
    static class TedDesperation
    {
        const int MastersScrollSlot = 0x107;   // T-Edition's Offering-type relic (its second item bank)
        static readonly Random Rng = new Random();
        internal static int Rolls, Fired;

        public static void Patch(HarmonyLib.Harmony h) =>
            Hooks.Patch(h, typeof(BattleProgressATBFF6), "CheckAndChangeDyingSpecialAbility", typeof(TedDesperation), prefix: nameof(Check_Prefix));

        static bool Holds(Last.Data.User.OwnedCharacterData c, int content)
        {
            if (content <= 0 || c?.EquipmentData == null) return false;
            foreach (var kv in c.EquipmentData) if (kv.Value != null && kv.Value.ContentId == content) return true;
            return false;
        }

        static bool Fires(BattleActData act, BattlePlayerData unit, Last.Data.User.OwnedCharacterData c)
        {
            if (TedRelics.Wears(c, "12.0") || Holds(c, Plugin.D.NamedContent("elven_darts")) || Holds(c, Plugin.D.BySlot(MastersScrollSlot)?.Content ?? 0)) return false;
            var conds = unit.BattleUnitDataInfo?.GetConfirmedConditionType();
            if (conds == null || !conds.Contains(ConditionType.Dying)) return false;            // Near Fatal
            var blocked = BattleProgressATBFF6.CantUseDyingSpecialAbilityConditions;
            if (blocked != null) foreach (var b in blocked) if (conds.Contains(b)) return false;
            Rolls++;
            return Rng.Next(32) == 0;
        }

        public static bool Check_Prefix(BattleActData battleActData)
        {
            if (!Plugin.TedMode) return true;
            try
            {
                var unit = battleActData?.AttackUnitData?.TryCast<BattlePlayerData>();
                var c = unit?.ownedCharacterData;
                if (c == null || c.characterStatusId < 1 || c.characterStatusId > 14) return false;
                var list = battleActData.abilityList;
                if (list == null || list.Count == 0 || list[0] == null || list[0].Id != 1) return false;   // Fight only
                if (!Fires(battleActData, unit, c)) { TedUmaro.Pick(battleActData, unit); return false; }   // C2/1636
                int id = Plugin.D.Ability($"desperation_{c.characterStatusId - 1}");
                var ab = id > 0 ? MasterManager.Instance.GetData<Ability>(id) : null;
                if (ab == null) return false;
                var nl = new Il2CppSystem.Collections.Generic.List<Ability>();
                nl.Add(ab);
                battleActData.abilityList = nl;
                Fired++;
                TedLog.Rule(39, $"c{c.characterStatusId}", () => $"desperation attack: {c.Name} uses ability {id} (1 in 32 per Fight while Near Fatal, no timer)");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-desperation", e); }
            return false;
        }
    }
}
