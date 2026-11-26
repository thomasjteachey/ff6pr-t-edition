using System;
using System.Collections.Generic;
using HarmonyLib;
using Last.Battle;
using Last.Data.User;
using Last.Management;
using PrKit;

namespace TEdition.PR
{
    // T-Edition's end-of-battle rules (BATTLE_SPEC 34, 58):
    //  34 Gau learns the Rage of every monster of the formation with an id below $100 (PR monsters 1-256)
    //     on any victory with Gau in the battle party, alive or not (C2/5ECD -> C2/49EF LearnRages); the PR's
    //     Rage abilities are 799 + the PR monster id (as Worlds Collide's -rnl teaches them), learned by
    //     whoever holds Rage (command 23). On BattleResultProvider.Genelate (a won battle's rewards).
    //  58 Shadow never leaves at random after a battle (C2/486F NOPed): the PR's draw
    //     (SystemCall Current.LotSecedeShadow, decompiled tools/decomp/shadow_leave) takes its "stays" path
    //     (Worlds Collide's WcEvents.LotSecedeShadow_Prefix).
    sealed class TedVictory : Feature
    {
        public TedVictory() : base("Battle", "Victory", true,
            "T-Edition's battle ends: Gau learns the Rages of every won formation he fought in; Shadow never leaves at random.") { }

        const int GauStatusId = 12, RageCommand = 23, RageBase = 799;
        static bool On => Plugin.TedMode;
        internal static string LastRages = "";
        internal static bool Testing;      // tests: count, don't teach

        public override void Apply(Harmony h)
        {
            Hooks.Patch(h, typeof(Last.Systems.BattleResultProvider), "Genelate", typeof(TedVictory), prefix: nameof(Result_Prefix));
            var lot = AccessTools.Method(typeof(Last.Interpreter.Instructions.SystemCall.Current), "LotSecedeShadow");
            if (lot != null) h.Patch(lot, prefix: new HarmonyMethod(typeof(TedVictory), nameof(LotSecedeShadow_Prefix)));
            else Kit.Warn("[ted] no Current.LotSecedeShadow: Shadow may leave after a battle");
            // the party a battle is made from (InstantiateManager.Create's first argument, as the kit's AI host reads
            // it): a battle an event or the harness starts (EncountBoss) has MonsterParty.Id -1 all through
            var create = AccessTools.Method(typeof(InstantiateManager), "Create");
            if (create != null) h.Patch(create, postfix: new HarmonyMethod(typeof(TedVictory), nameof(Create_Postfix)));
        }

        public static void Create_Postfix(int __0)
        {
            if (__0 >= 0) BattleParty = __0;
        }

        // the battle under way (the formation is gone by the time the result is built: BNW's BattleRewards)
        internal static int BattleParty = -1;
        internal static int LastParty = -1;     // the battle that just ended (BattleParty is reset at its result)
        internal static bool GauFought;

        public override void Update()
        {
            if (!On) return;
            var battle = BattlePlugManager.Instance();
            if (battle == null || !battle.IsBattle()) return;
            // (ted-gate-1, 2026-11-25: the party's Id reads -1 once the battle is won, so the rages and the result
            //  line lost the party: keep the last real one)
            int id = battle.MonsterParty?.Id ?? -1;
            if (id >= 0) BattleParty = id;
            var players = battle.GetPlayerUnits();
            bool gau = false;
            if (players != null)
                foreach (var p in players)
                    if (p?.TryCast<BattlePlayerData>()?.ownedCharacterData?.characterStatusId == GauStatusId) gau = true;
            GauFought = gau;
        }

        public static void Result_Prefix(Last.Systems.BattleResultProvider __instance)
        {
            if (!On || !Hooks.IsA<Last.Systems.BattleResultProvider>(__instance)) return;
            try { LastRages = LearnRages(BattleParty, GauFought); }
            catch (Exception e) { Hooks.WarnOnce("TedVictory.Rages", e); }
            LastParty = BattleParty;
            BattleParty = -1;
            GauFought = false;
        }

        // the formation's rages to the Rage holders when Gau fought in it
        internal static string LearnRages(int partyId, bool gau)
        {
            var party = Master.Get<Last.Data.Master.MonsterParty>(partyId);
            if (party == null || !gau) return "";
            var rages = new List<int>();
            foreach (var m in new[] { party.Monster1, party.Monster2, party.Monster3, party.Monster4, party.Monster5,
                                      party.Monster6, party.Monster7, party.Monster8, party.Monster9 })
                if (m >= 1 && m <= 256 && !rages.Contains(RageBase + m) && Master.Get<Last.Data.Master.Ability>(RageBase + m) != null)
                    rages.Add(RageBase + m);
            int taught = 0;
            if (!Testing)
                foreach (var c in Holders())
                    foreach (var id in rages)
                        if (!Knows(c, id) && Teach(c, id)) taught++;
            string line = $"party {party.Id}: rages {string.Join(",", rages)} ({taught} newly learned)";
            if (rages.Count > 0) TedLog.Rule(34, "", () => $"Gau fought and won: {line}");
            return line;
        }

        static List<OwnedCharacterData> Holders()
        {
            var list = new List<OwnedCharacterData>();
            var owned = UserDataManager.Instance()?.OwnedCharacterList;
            if (owned == null) return list;
            foreach (var c in owned)
            {
                if (c == null || c.characterStatusId < 1 || c.characterStatusId > 14 || c.CommandList == null) continue;
                foreach (var x in c.CommandList) if (x != null && x.Id == RageCommand) { list.Add(c); break; }
            }
            return list;
        }

        // learned = skill level 100 (the PR gives Gau an entry for every rage, the unknown ones at 0)
        static bool Knows(OwnedCharacterData c, int id)
        {
            var list = c.OwnedAbilityList;
            if (list == null) return false;
            foreach (var a in list)
                if (a?.Ability != null && a.Ability.Id == id) return a.SkillLevel >= 100;
            return false;
        }

        static bool Teach(OwnedCharacterData c, int id)
        {
            OwnedAbility owned = null;
            foreach (var a in c.OwnedAbilityList)
                if (a?.Ability != null && a.Ability.Id == id) owned = a;
            owned ??= new OwnedCharacterClient().AddAbility(c.Id, id);
            if (owned == null) return false;
            owned.SkillLevel = 100;
            return true;
        }

        public static bool LotSecedeShadow_Prefix(ref int __result)
        {
            if (!On) return true;
            try
            {
                Last.Interpreter.DataStorage.Instance?.Set(Last.Interpreter.DataStorage.Category.kScriptLocalVariable, 3, 0);
                __result = 0;
                TedLog.Rule(58, "", () => "Shadow's after-battle draw: he stays (T-Edition)");
                return false;
            }
            catch (Exception e) { Hooks.WarnOnce("TedVictory.Shadow", e); return true; }
        }
    }
}
