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
            Harness.Register("tedtile", TedTiles.Harness, "tedtile [#LAYER CELL [TILEID]]: field map layers / a cell's tile / write a tile at runtime (timed; T-Edition's tile changes)");
            Harness.Register("tedequip", Equip, "tedequip <party index 0-3 | character status id 1-14 as c1..c14> <T-Edition item slot> [equip slot 1-6, default 5 (relic 1)]: give it if needed and equip it (memory only)");
            Harness.Register("teduse", Use, "teduse <T-Edition item slot> <party index 0-3>: give it if needed and use it from the menu on that member (the game's OwnedItemClient.UseFunction); stats before/after");
            Harness.Register("tedcoliseum", _ => TedColiseum.Summary(), "tedcoliseum: T-Edition's Coliseum wagers and boss rewards loaded, the last match's choice");
            Harness.Register("tedstatus", a =>
            {
                var m = Member(a.Length > 0 ? a[0] : "0");
                return m == null ? "error: tedstatus <party 0-3|cN>" : $"{m.Name}: {string.Join(" | ", TedStatusPage.Lines(m, true))}";
            }, "tedstatus [party 0-3|cN]: the element and immunity lines the status screen shows (audit U4), with element ids");
            Harness.Register("tedcostume", a =>
            {
                if (a.Length == 2 && int.TryParse(a[0], out int c) && int.TryParse(a[1], out int k)) TedCostumes.Wear(c, k);
                return $"{TedCostumes.Summary()}; magicite (rule 35): {TedMagicite.State}; art: {TedArt.ArtLine}; monster images: {TedArt.MonsterLine}";
            }, "tedcostume [CHAR 0-13 K 0-4]: put a costume on (as the dressing room's SysCall does), then the costumes, art and rule 35 state");
            Battle("tedallies", a => string.Join(" | ", TedAllyStatus.Refresh(Last.Battle.BattlePlugManager.Instance())),
                "tedallies: in a battle, the ally statuses holding Select shows (audit U7: Reraise, Defend, Runic, Sky)");
            Battle("teddigits", a =>
            {
                var bm = Last.Battle.BattlePlugManager.Instance();
                Last.Battle.BattleUnitData target = null;
                foreach (var e in bm.GetEnemyUnits()) if (e != null && e.BattleUnitDataInfo?.Parameter?.CurrentHP > 0) { target = e; break; }
                if (target == null) return "error: no living monster";
                int value = a.Length > 0 && int.TryParse(a[0], out int v) ? v : 12345;
                int before = TedDamageDigits.Grown;
                var view = Last.Battle.BattleUtility.CreateDamageView(target, value, false, false);
                int children = view?.prefab != null ? view.prefab.transform.childCount : -1;
                return $"teddigits: {value} drawn on the first monster: prefab children {children}, {TedDamageDigits.Grown - before} added (audit M30)";
            }, "teddigits [value]: in a battle, a damage number (default 12345) on the first monster: the prefab's digit slots (audit M30)");
            Battle("tedsteal", TedSelfTest.Steal, "tedsteal [n]: in a battle, n Steals by the first party member through the game's functions (nothing applied): rate vs T-Edition's chance");
            Battle("tedprobe", TedSelfTest.Probe, "tedprobe blind [n]: in a battle, the game's Fight hit rate clear vs blinded (audit M5; nothing applied)");
            Battle("tedgil", TedSelfTest.GilToss, "tedgil: in a battle, the game's Gil Toss value and gil cost (information for rule 29; test runs never save)");
            Battle("tedcast", TedSelfTest.Cast, "tedcast SLOT ABILITY p0..p3|e0..e5|allies|foes [COMMAND]: a party member's act, queued as the game queues the player's (log shows its damage)");
            Battle("tedcond", a =>
            {
                if (a.Length < 2 || !int.TryParse(a[0], out int slot)) return "error: tedcond SLOT CONDITION [off]";
                if (!Enum.TryParse<Last.Defaine.ConditionType>(a[1], true, out var type)) return $"error: no condition {a[1]}";
                var bm = Last.Battle.BattlePlugManager.Instance();
                if (bm == null || !bm.IsBattle()) return "error: not in a battle";
                var players = bm.GetPlayerUnits();
                if (players == null || slot < 0 || slot >= players.Length || players[slot] == null) return $"error: no party member {slot}";
                var u = players[slot];
                bool off = a.Length > 2 && a[2] == "off";
                if (off) bm.BattleConditionController.InterruptRemoveCondition(u, type);
                else bm.BattleConditionController.InterruptAddCondition(u, type);
                bool has = u.BattleUnitDataInfo?.GetConfirmedConditionType()?.Contains(type) == true;
                return $"party {slot}: {type} {(has ? "on" : "off")}";
            }, "tedcond SLOT CONDITION [off]: a status on/off a party member in battle (Poison, Regeneration, Shell, Trance...)");
            Harness.Register("tedcounters", a =>
            {
                if (a.Length >= 2 && a[0] == "steal" && int.TryParse(a[1], out int v)) TedCounters.Set(TedCounters.Steal, Math.Clamp(v, 0, 510));
                return "counters: " + TedCounters.Summary();
            }, "tedcounters [steal N]: T-Edition's success counters in the loaded game (set the Steal count, for Orichalcum tests; test runs never save)");
            Battle("teddamage", TedSelfTest.Damage, "teddamage [n]: in a battle, T-Edition's damage rules against the game's own value, case by case (nothing applied)");
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

        // A battle command waits for the battle's Play phase (up to the harness's two minutes): run during its opening
        // (CreateObj, the pre-emptive message), ted-7's self-tests saw the map's script take the battle script's place
        // (sc_map_20160 over sc_b_0239) and the opening never ended.
        static void Battle(string name, Func<string[], string> run, string help) =>
            Harness.Register(name, (Harness.Handler)((args, tick) => InOpening() && tick < 3600 ? null : run(args) ?? ""), help);

        static bool InOpening()
        {
            try
            {
                var bm = Last.Battle.BattlePlugManager.Instance();
                if (bm == null || !bm.IsBattle()) return false;          // not in a battle: the command answers itself
                var bc = UnityEngine.Object.FindObjectOfType<Last.Battle.BattleController>();
                var phase = bc?.stateMachine?.Current.ToString();
                return phase != null && phase != "Play";
            }
            catch (Exception) { return false; }
        }

        static Last.Data.User.OwnedCharacterData Member(string who)
        {
            var udm = UserDataManager.Instance();
            if (udm == null) return null;
            int charId = -1;
            if (who.StartsWith("c") && int.TryParse(who.Substring(1), out int status))
            {
                foreach (var o in udm.OwnedCharacterList) if (o != null && o.characterStatusId == status) { charId = o.Id; break; }
            }
            else if (int.TryParse(who, out int idx))
            {
                var party = udm.GetPartyMemberData();
                if (party != null && idx >= 0 && idx < party.Count && party[idx] != null) charId = party[idx].Id;
            }
            if (charId < 0) return null;
            foreach (var o in udm.OwnedCharacterList) if (o != null && o.Id == charId) return o;
            return null;
        }

        static Last.Data.User.OwnedItemData Held(int content)
        {
            var udm = UserDataManager.Instance();
            var item = udm.SearchOwnedItem(content);
            if (item == null) { new OwnedItemClient().AddOwnedItem(content, 1); item = udm.SearchOwnedItem(content); }
            return item;
        }

        static string Equip(string[] a)
        {
            if (a.Length < 2 || !int.TryParse(a[1].TrimStart('s'), out int slot)) return "error: tedequip <party 0-3|cN> <T-Edition slot> [equip slot 1-6]";
            int es = a.Length > 2 && int.TryParse(a[2], out int e) && e >= 1 && e <= 6 ? e : 5;
            var m = Member(a[0]);
            if (m == null) return $"error: no character {a[0]}";
            int content = Plugin.D.BySlot(slot)?.Content ?? 0;
            if (content <= 0) return $"error: T-Edition slot {slot} has no content id in ted_data";
            var item = Held(content);
            if (item == null) return $"error: content {content} not in the inventory after giving it";
            m.EquipmentData[(Last.Defaine.EquipSlotType)es] = item;
            return $"tedequip: {m.Name} (status {m.characterStatusId}) wears T-Edition slot {slot} (content {content}, {Plugin.D.BySlot(slot)?.Name}) in equip slot {es}";
        }

        static string Stats(Last.Data.User.OwnedCharacterData m)
        {
            var p = m.Parameter;
            return $"Power +{p.AddtionalPower}, Speed +{p.AddtionalAgility}, Stamina +{p.AddtionalVitality}, Magic +{p.AddtionalMagic}, max HP {p.ConfirmedMaxHp()} (+{p.AddtionalMaxHp}), max MP +{p.AddtionalMaxMp}, HP {p.CurrentHP}";
        }

        static string Use(string[] a)
        {
            if (a.Length < 2 || !int.TryParse(a[0].TrimStart('s'), out int slot)) return "error: teduse <T-Edition slot> <party 0-3|cN>";
            var m = Member(a[1]);
            if (m == null) return $"error: no character {a[1]}";
            int content = Plugin.D.BySlot(slot)?.Content ?? 0;
            if (content <= 0) return $"error: T-Edition slot {slot} has no content id in ted_data";
            if (Held(content) == null) return $"error: content {content} not in the inventory";
            var client = new OwnedItemClient();
            string before = Stats(m);
            bool can = client.IsUseFunction(content, m.Id);
            if (can)
            {
                var ids = new Il2CppInterop.Runtime.InteropTypes.Arrays.Il2CppStructArray<int>(1);
                ids[0] = m.Id;
                client.UseFunction(content, ids);
            }
            return $"teduse: {Plugin.D.BySlot(slot)?.Name} (content {content}) on {m.Name}: usable {can}; before [{before}]; after [{Stats(m)}]";
        }
    }
}
