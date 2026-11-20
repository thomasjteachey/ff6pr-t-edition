using System;
using System.Collections.Generic;
using System.Linq;
using Last.Data.Master;
using Last.Management;
using PrKit;
using TEdition.Rules;

namespace TEdition.PR
{
    // T-Edition's commands for the kit's headless harness (the PC test runner; tools/game_harness.py):
    //   ted                   version, data found (Magicite folder, ted_data.json), rules on
    //   tedcheck              the port as the game has it: new weapon rows and their names, T-Edition's
    //                         items by slot (names on moved rows), 4 drop slots, the drop-rate constants
    //   tedgive ID [n]        content ID (or sSLOT: T-Edition's item slot) into the inventory (test runs never save)
    //   tedkeep on|off [manual]   a headless battle keeps moving (Active mode, auto, party HP 9999)
    //   enemyhp N             every living monster's HP to N
    //   tedrules              which T-Edition rules have fired, how often
    //   teddamage [n]         in a battle: the damage rules case by case against the game's own value (TedSelfTest)
    //   tedsteal [n]          in a battle: Steal's success rate through the game's functions against T-Edition's chance
    //   tedcounters [steal N] the success counters in the loaded game (Orichalcum's power comes from Steal's)
    static class TedHarness
    {
        internal static void Register()
        {
            Harness.Register("ted", _ => Status(), "ted: T-Edition's version, data and rules");
            Harness.Register("tedcheck", _ => Check(), "tedcheck: the port's rows as the game has them (new weapons, item names, drops)");
            Harness.Register("tedgive", Give, "tedgive ID|sSLOT [n]: a content id (or T-Edition's item slot) into the inventory");
            Harness.Register("tedrules", _ => TedLog.Summary(), "tedrules: the T-Edition rules that have fired");
            Harness.Register("tedsteal", TedSelfTest.Steal, "tedsteal [n]: in a battle, n Steals by the first party member through the game's functions (nothing applied): rate vs T-Edition's chance");
            Harness.Register("tedcounters", a =>
            {
                if (a.Length >= 2 && a[0] == "steal" && int.TryParse(a[1], out int v)) TedCounters.Set(TedCounters.Steal, Math.Clamp(v, 0, 510));
                return "counters: " + TedCounters.Summary();
            }, "tedcounters [steal N]: T-Edition's success counters in the loaded game (set the Steal count, for Orichalcum tests; test runs never save)");
            Harness.Register("teddamage", TedSelfTest.Damage, "teddamage [n]: in a battle, T-Edition's damage rules against the game's own value, case by case (nothing applied)");
            Harness.Register("tedkeep", a =>
            {
                Keep = a.Length == 0 || a[0] != "off";
                Auto = !(a.Length > 1 && a[1] == "manual");
                return $"keep battles moving: {(Keep ? $"on (Active mode, {(Auto ? "auto" : "no auto")}, party HP 9999)" : "off")}";
            }, "tedkeep on|off [manual]: a headless battle keeps moving (Active mode, auto battle unless manual, the party's HP at 9999)");
            Harness.Register("enemyhp", a =>
            {
                int hp = a.Length > 0 && int.TryParse(a[0], out var v) ? v : 9999;
                var bm = Last.Battle.BattlePlugManager.Instance();
                if (bm == null || !bm.IsBattle()) return "error: not in a battle";
                int n = 0;
                foreach (var e in bm.GetEnemyUnits())
                {
                    var p = e?.BattleUnitDataInfo?.Parameter;
                    if (p == null || p.CurrentHP <= 0) continue;
                    if (p.BaseMaxHp < hp) p.BaseMaxHp = hp;
                    p.CurrentHP = hp;
                    n++;
                }
                return $"{n} monsters at {hp} HP";
            }, "enemyhp N: every living monster's HP to N (default 9999)");
            Harness.StateParts.Add(() => $"ted {(Plugin.TedMode ? "on" : "off")}; {TedLog.Summary()}");
            Harness.Register("teddrops", _ => $"battles won {Wins}; last result: {LastResult}", "teddrops: the last battle result's EXP, gil and drops");
            Hooks.Patch(Plugin.H, typeof(Last.Systems.BattleResultProvider), "Genelate", typeof(TedHarness), prefix: nameof(Result_Prefix));
            Kit.Info("[ted] harness commands: ted, tedcheck, tedgive, tedkeep, enemyhp, tedrules, teddamage, tedsteal, tedcounters, teddrops");
        }

        static string Status() =>
            $"ted {Plugin.Version}: mode {Plugin.TedMode}; Magicite {(Plugin.TedMode ? MagiciteDir.FolderPath(Plugin.ModFolder) : "missing")}; " +
            $"data {(Plugin.DataError ?? $"{Plugin.DataFile} ({Plugin.D.Version}, made {Plugin.D.Made}: {Plugin.D.Items.Count} items, " +
                                            $"{Plugin.D.NewWeapons.Count} new weapon rows, {Plugin.D.HalfIgnoreDefense.Count} half-damage monsters)")}; " +
            $"saves {(ModSaves.Tag ?? "shared")}; features {string.Join(", ", Plugin.Features.All.Where(f => f.Enabled).Select(f => f.Name))}; " +
            $"game data {(Master.Ready ? "loaded" : "not loaded yet")}; {TedEnemyAi.Summary()}; counters: {TedCounters.Summary()}";

        // --- the battle result (what dropped: T-Edition's four slots, rule 1) --------------------------
        internal static int Wins;
        internal static string LastResult = "none";

        public static void Result_Prefix(Last.Systems.BattleResultProvider __instance, int expValue, int gilValue,
                                         Il2CppSystem.Collections.Generic.List<Last.Data.DropItemData> dropItems)
        {
            if (!Hooks.IsA<Last.Systems.BattleResultProvider>(__instance)) return;
            try
            {
                var parts = new List<string>();
                if (dropItems != null)
                    foreach (var d in dropItems)
                    {
                        if (d == null) continue;
                        var c = Master.Get<Content>(d.ContentId);
                        parts.Add($"{(c == null ? "?" : TedData.Plain(GameText.Get(c.MesIdName)))} (content {d.ContentId}) x{d.DropValue}");
                    }
                var party = Last.Battle.BattlePlugManager.Instance()?.MonsterParty?.Id ?? TedVictory.BattleParty;
                Wins++;
                LastResult = $"party {party}: EXP {expValue}, gil {gilValue}, drops {(parts.Count == 0 ? "none" : string.Join(", ", parts))}";
                Kit.Info($"[ted] battle result: {LastResult}");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-result", e); }
        }

        // --- tedcheck --------------------------------------------------------------------------------

        internal static string Check()
        {
            if (!Master.Ready) return "error: the game's data isn't loaded yet";
            var bad = new List<string>();
            int checks = 0;
            void Expect(bool ok, string what)
            {
                checks++;
                if (!ok) bad.Add(what);
            }

            // the port's new weapon rows (92-115): the row, its content row, the name
            int weaponsOk = 0;
            foreach (var w in Plugin.D.NewWeapons)
            {
                var row = Master.Get<Weapon>(w.Row);
                var c = Master.Get<Content>(w.Content);
                string name = c == null ? null : GameText.Get(c.MesIdName);
                bool ok = row != null && row.Attack == w.Attack && c != null && c.TypeId == 2 && c.TypeValue == w.Row &&
                          TedData.Plain(name) == TedData.Plain(w.Name);
                Expect(ok, $"weapon row {w.Row}: {(row == null ? "missing" : $"attack {row.Attack}/{w.Attack}")}, content {w.Content} " +
                           $"{(c == null ? "missing" : $"type {c.TypeId}/{c.TypeValue}")}, name '{TedData.Plain(name)}' vs '{TedData.Plain(w.Name)}'");
                if (ok) weaponsOk++;
            }
            // T-Edition's items by slot: each slot's content row resolves with the slot's name (the moved rows too)
            int itemsOk = 0, moved = 0, movedOk = 0;
            foreach (var it in Plugin.D.Items)
            {
                var c = Master.Get<Content>(it.Content);
                string name = c == null ? null : GameText.Get(c.MesIdName);
                bool rowOk = c != null && c.TypeValue == it.Row && c.TypeId == (it.Table == "item" ? 1 : it.Table == "weapon" ? 2 : 3);
                bool ok = rowOk && TedData.Plain(name) == TedData.Plain(it.Name);
                Expect(ok, $"item slot {it.Slot} ({it.Table} {it.Row}, content {it.Content}): {(c == null ? "no content row" : $"'{TedData.Plain(name)}' vs '{TedData.Plain(it.Name)}'{(rowOk ? "" : $", row {c.TypeId}/{c.TypeValue}")}")}");
                if (ok) itemsOk++;
                if (it.Moved)
                {
                    moved++;
                    if (ok) movedOk++;
                }
            }
            // drops: T-Edition's four slots per monster, the drop-rate constants 68/19/8/5 (the rest 0)
            int four = 0, three = 0, rate100 = 0, monsters = 0;
            var all = Master.All<Monster>();
            if (all != null)
                foreach (var kv in all)
                {
                    var m = kv.Value;
                    if (m == null) continue;
                    monsters++;
                    if (m.DropContentId4 != 0) four++;
                    else if (m.DropContentId3 != 0) three++;
                    if (m.DropRate == 100) rate100++;
                }
            Expect(four + three > 0, "no monster has a third or fourth drop slot");
            Expect(Plugin.D.DropMonsters == 0 || four + three == Plugin.D.DropMonsters,
                   $"monsters with 3-4 drop slots: game {four + three}, port {Plugin.D.DropMonsters}");
            var consts = Constants("MONSTER_DROP_RATE_");
            var want = Plugin.D.DropRates;
            for (int k = 1; k <= 8; k++)
            {
                int expected = k <= want.Length ? want[k - 1] : 0;
                consts.TryGetValue($"MONSTER_DROP_RATE_{k}", out int have);
                Expect(have == expected, $"MONSTER_DROP_RATE_{k} {have}, want {expected}");
            }
            string rates = string.Join("/", Enumerable.Range(1, 4).Select(k => consts.TryGetValue($"MONSTER_DROP_RATE_{k}", out int v) ? v : -1));
            var head = $"tedcheck: {checks - bad.Count}/{checks} ok; new weapon rows {weaponsOk}/{Plugin.D.NewWeapons.Count}; " +
                       $"items {itemsOk}/{Plugin.D.Items.Count} (moved rows {movedOk}/{moved}); monsters {monsters}: {four} with 4 drop slots, " +
                       $"{three} with 3, {rate100} at drop rate 100; MONSTER_DROP_RATE {rates}";
            if (Plugin.DataError != null) return $"{head}; tedcheck FAILED: {Plugin.DataError}";
            return bad.Count == 0 ? $"{head}; tedcheck passed"
                                  : $"{head}; tedcheck FAILED ({bad.Count}): {string.Join("; ", bad.Take(6))}";
        }

        internal static Dictionary<string, int> Constants(string prefix)
        {
            var d = new Dictionary<string, int>();
            var all = Master.All<GameConstantInt>();
            if (all == null) return d;
            foreach (var kv in all)
            {
                var c = kv.Value;
                if (c?.KeyName != null && c.KeyName.StartsWith(prefix)) d[c.KeyName] = c.Value1;
            }
            return d;
        }

        // --- tedgive ---------------------------------------------------------------------------------

        static string Give(string[] a)
        {
            if (a.Length < 1) return "error: tedgive ID|sSLOT [n]";
            int id;
            if (a[0].StartsWith("s", StringComparison.OrdinalIgnoreCase))
            {
                if (!int.TryParse(a[0].Substring(1), out int slot)) return "error: tedgive sSLOT";
                var it = Plugin.D.BySlot(slot);
                if (it == null) return $"error: no T-Edition item slot {slot} in ted_data.json";
                id = it.Content;
            }
            else if (!int.TryParse(a[0], out id)) return "error: tedgive ID [n]";
            int n = a.Length > 1 && int.TryParse(a[1], out var v) ? Math.Clamp(v, 1, 99) : 1;
            var c = Master.Get<Content>(id);
            if (c == null) return $"error: no content {id}";
            var udm = UserDataManager.Instance();
            if (udm == null) return "error: no game loaded";
            var client = new OwnedItemClient();
            client.AddOwnedItem(id, n);
            return $"gave {n} x {GameText.Get(c.MesIdName)} (content {id}, type {c.TypeId} row {c.TypeValue}); has it: {client.HasItem(id)}" +
                   (TestRun.Running ? " (a test run: saves are blocked)" : "");
        }

        // --- battles (the PC test runner's recipe, as Beyond Chaos's bckeep) -------------------------
        internal static bool Keep, Auto = true;

        // every frame while on: Wait mode freezes a headless battle on command menus nobody answers
        internal static void Update()
        {
            if (!Keep) return;
            try
            {
                var udm = UserDataManager.Instance();
                if (udm?.Config != null && udm.Config.BattleModeIndex != 0) udm.Config.BattleModeIndex = 0;
                var bm = Last.Battle.BattlePlugManager.Instance();
                if (bm == null || !bm.IsBattle()) return;
                Last.UI.BattleUIManager.Instance?.SetIsAuto(Auto);
                foreach (var p in bm.GetPlayerUnits())
                {
                    var prm = p?.BattleUnitDataInfo?.Parameter;
                    if (prm == null || prm.CurrentHP <= 0) continue;
                    if (prm.BaseMaxHp < 9999) prm.BaseMaxHp = 9999;
                    if (prm.CurrentHP < 9999) prm.CurrentHP = 9999;
                }
            }
            catch (Exception e) { Hooks.WarnOnce("ted-keep", e); }
        }
    }
}
