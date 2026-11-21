using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using HarmonyLib;
using Last.Data.Master;
using PrKit;

namespace TEdition.PR
{
    // T-Edition's Coliseum and boss rewards (ted-monsters' export ted_rewards.json, beside ted_ai.json in
    // BepInEx/TEdition):
    //  "coliseum" [[wager content, 0, 0, opponent party, reward content, hidden, PR monster], ...] (T-Edition's D0/F140
    //    wagers): the PR builds its table in code (ColosseumInfomationData, by wager content id); GetMonsterId /
    //    GetRewardItemId / IsRewardNameUnknown answer from it (WcColiseum's way: a party of 0 keeps the game's party
    //    with its monster changed to the record's).
    //  "boss_rewards" {"<PR party>": content id}: the item T-Edition adds when that boss fight is won (4B/4A00,
    //    C2/FC40 -> 4E/0D30), added to the inventory at the result (empty until the second item bank has content ids).
    static class TedColiseum
    {
        static readonly Dictionary<int, int[]> matches = new Dictionary<int, int[]>();
        static readonly Dictionary<int, int> bossRewards = new Dictionary<int, int>();
        internal static string State = "not loaded", Last = "";

        public static void Apply(Harmony h, string path)
        {
            try
            {
                if (!File.Exists(path)) { State = $"no {path}"; return; }
                using var doc = JsonDocument.Parse(File.ReadAllText(path));
                var root = doc.RootElement;
                if (root.TryGetProperty("coliseum", out var c))
                    foreach (var r in c.EnumerateArray())
                    {
                        var a = r.EnumerateArray().Select(x => x.GetInt32()).ToArray();
                        if (a.Length >= 7 && a[0] > 0) matches[a[0]] = a.Skip(1).ToArray();   // m[2] party, m[3] reward, m[4] hidden, m[5] monster
                    }
                if (root.TryGetProperty("boss_rewards", out var b))
                    foreach (var p in b.EnumerateObject())
                        if (int.TryParse(p.Name, out int party)) bossRewards[party] = p.Value.GetInt32();
                var t = typeof(Serial.FF6.Management.ColosseumInfomationData);
                int n = 0;
                foreach (var (name, post) in new[] { ("GetMonsterId", nameof(Monster_Postfix)), ("GetRewardItemId", nameof(Reward_Postfix)),
                                                     ("IsRewardNameUnknown", nameof(Hidden_Postfix)) })
                {
                    var m = AccessTools.Method(t, name);
                    if (m == null) continue;
                    h.Patch(m, postfix: new HarmonyMethod(typeof(TedColiseum), post));
                    n++;
                }
                Hooks.Patch(h, typeof(Last.Systems.BattleResultProvider), "Genelate", typeof(TedColiseum), prefix: nameof(Result_Prefix));
                State = $"{matches.Count} Coliseum wagers ({n} of 3 lookups hooked), {bossRewards.Count} boss rewards";
                Plugin.L.LogInfo($"[ted] coliseum: {State}");
            }
            catch (Exception e) { State = "not loaded: " + e.Message; Plugin.L.LogError($"[ted] coliseum: {e.Message}"); }
        }

        static int[] Match(int wager) => Plugin.TedMode && matches.TryGetValue(wager, out var m) ? m : null;

        static readonly Dictionary<int, (int Slot, int Monster)> retargeted = new Dictionary<int, (int, int)>();

        static int Get(MonsterParty p, int slot) => slot switch
        {
            1 => p.Monster1, 2 => p.Monster2, 3 => p.Monster3, 4 => p.Monster4, 5 => p.Monster5, 6 => p.Monster6, _ => 0,
        };

        static void Set(MonsterParty p, int slot, int monster)
        {
            switch (slot)
            {
                case 1: p.Monster1 = monster; break;
                case 2: p.Monster2 = monster; break;
                case 3: p.Monster3 = monster; break;
                case 4: p.Monster4 = monster; break;
                case 5: p.Monster5 = monster; break;
                case 6: p.Monster6 = monster; break;
            }
        }

        static void Retarget(int partyId, int monster)
        {
            var p = MasterManager.Instance.GetData<MonsterParty>(partyId);
            if (p == null) return;
            if (!retargeted.TryGetValue(partyId, out var orig))
            {
                int slot = Enumerable.Range(1, 6).FirstOrDefault(i => Get(p, i) > 0);
                if (slot == 0) return;
                orig = (slot, Get(p, slot));
                retargeted[partyId] = orig;
            }
            Set(p, orig.Slot, monster);
        }

        static void Restore(int partyId)
        {
            if (!retargeted.TryGetValue(partyId, out var orig)) return;
            var p = MasterManager.Instance.GetData<MonsterParty>(partyId);
            if (p != null) Set(p, orig.Slot, orig.Monster);
            retargeted.Remove(partyId);
        }

        public static void Monster_Postfix(int selectItemContentId, ref int __result)
        {
            try
            {
                var m = Match(selectItemContentId);
                if (m == null) return;
                if (m[2] > 0)
                {
                    Restore(m[2]);
                    Last = $"wager {selectItemContentId}: party {__result} -> {m[2]}";
                    __result = m[2];
                }
                else if (m[5] > 0)
                {
                    Retarget(__result, m[5]);
                    Last = $"wager {selectItemContentId}: party {__result} keeps, monster -> {m[5]}";
                }
                TedLog.Rule(56, "wager", () => $"Coliseum: T-Edition's opponents ({Last})");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-coliseum-monster", e); }
        }

        public static void Reward_Postfix(int selectItemContentId, ref int __result)
        {
            try
            {
                var m = Match(selectItemContentId);
                if (m == null) return;
                Last += $"; reward {__result} -> {m[3]}";
                __result = m[3];
            }
            catch (Exception e) { Hooks.WarnOnce("ted-coliseum-reward", e); }
        }

        public static void Hidden_Postfix(int selectItemContentId, ref bool __result)
        {
            try
            {
                var m = Match(selectItemContentId);
                if (m != null) __result = m[4] != 0;
            }
            catch (Exception e) { Hooks.WarnOnce("ted-coliseum-hidden", e); }
        }

        // a won battle: T-Edition's boss item (to the inventory; the result screen doesn't list it yet)
        public static void Result_Prefix()
        {
            try
            {
                if (!Plugin.TedMode || bossRewards.Count == 0) return;
                int party = TedVictory.BattleParty;
                if (!bossRewards.TryGetValue(party, out int content) || content <= 0) return;
                new Last.Management.OwnedItemClient().AddOwnedItem(content, 1);
                Plugin.L.LogInfo($"[ted] boss reward: party {party} gives content {content}");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-boss-reward", e); }
        }

        public static string Summary() => $"{State}; last: {Last}";
    }
}
