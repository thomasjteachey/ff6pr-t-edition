using System;
using Last.Battle;
using Last.Data.Master;
using PrKit;

namespace TEdition.PR
{
    // Audit C28 / battle_commands.md §11: Umaro takes the player's commands (C2/091E: the uncontrollable test never
    // matches) and his Fight becomes a weighted pick (C2/1636 over C2/5251, vanilla's table; each set option weighs its
    // table value + 1):
    //   none            Fight 159, Charge 96
    //   Berserker Ring  Fight 95, Charge 64, Throw Ally 96   (with a throwable ally)
    //   Power Belt      Fight 95, Charge 64, Rampage 96
    //   both            Fight 63, Charge 64, Rampage 64, Throw Ally 64
    // The PR makes him act alone through his permanent Umalo status: PassiveContentProvider.GetActSelectByCondition
    // returns ActSelectUmalo while he has condition type 622 (decompiled tools/decomp/ted_umaro1). A postfix answers null
    // for him (the player's own input). His Fight acts pass TedDesperation's prefix first; when no desperation attack
    // fires, Pick() swaps the act's ability by the table. Charge = the PR's Tackle (201), Throw Ally = 200 (the kit's
    // SnesUmaro still makes a thrown Mog critical), Rampage = ted_data "rampage" (spell $EF; else the PR's 199).
    static class TedUmaro
    {
        const int UmaroStatus = 14, BerserkerRingSlot = 227, PowerBeltSlot = 226;
        const int Charge = 201, ThrowAlly = 200, StormFallback = 199;
        static readonly Random Rng = new Random();
        internal static int Picks;

        public static void Patch(HarmonyLib.Harmony h) =>
            Hooks.Patch(h, typeof(Serial.FF6.Management.PassiveContentProvider), "GetActSelectByCondition", typeof(TedUmaro),
                postfix: nameof(Select_Postfix));

        public static void Select_Postfix(BattleUnitData targetData, ref ActSelect __result)
        {
            try
            {
                if (!Plugin.TedMode || __result == null) return;
                var c = targetData?.TryCast<BattlePlayerData>()?.ownedCharacterData;
                if (c == null || c.characterStatusId != UmaroStatus || __result.TryCast<ActSelectUmalo>() == null) return;
                __result = null;   // the player's own command input
                TedLog.Rule(36, "control", () => "Umaro takes the player's commands (T-Edition)");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-umaro-select", e); }
        }

        static bool Wears(Last.Data.User.OwnedCharacterData c, int slot)
        {
            int content = Plugin.D.BySlot(slot)?.Content ?? 0;
            if (content <= 0 || c?.EquipmentData == null) return false;
            foreach (var kv in c.EquipmentData) if (kv.Value != null && kv.Value.ContentId == content) return true;
            return false;
        }

        // Umaro's Fight with no desperation attack: the weighted pick (TedDesperation calls it)
        public static void Pick(BattleActData act, BattlePlayerData unit)
        {
            try
            {
                var c = unit?.ownedCharacterData;
                if (c == null || c.characterStatusId != UmaroStatus) return;
                bool ring = Wears(c, BerserkerRingSlot), belt = Wears(c, PowerBeltSlot);
                if (ring)
                {
                    bool ally = false;
                    var party = BattlePlugManager.Instance()?.GetPlayerUnits();
                    if (party != null)
                        foreach (var p in party)
                            if (p != null && p.Pointer != unit.Pointer && (p.BattleUnitDataInfo?.Parameter?.CurrentHP ?? 0) > 0) ally = true;
                    ring = ally;
                }
                // weights: Fight, Charge, Rampage, Throw Ally (vanilla's table + 1; 0 = not offered)
                int[] w = TEdition.Rules.CommandMath.UmaroWeights(ring, belt);
                int pick = TEdition.Rules.CommandMath.UmaroPick(w, Rng.Next(w[0] + w[1] + w[2] + w[3]));
                if (pick == 0) return;   // a plain Fight
                int id = pick == 1 ? Charge : pick == 3 ? ThrowAlly : (Plugin.D.Ability("rampage") is int r && r > 0 ? r : StormFallback);
                var ab = MasterManager.Instance.GetData<Ability>(id);
                if (ab == null) return;
                var nl = new Il2CppSystem.Collections.Generic.List<Ability>();
                nl.Add(ab);
                act.abilityList = nl;
                Picks++;
                TedLog.Rule(36, "fight", () => $"Umaro's Fight: {(pick == 1 ? "Charge" : pick == 2 ? "Rampage" : "Throw Ally")} (ability {id}; Berserker Ring {ring}, Power Belt {belt})");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-umaro-pick", e); }
        }
    }
}
