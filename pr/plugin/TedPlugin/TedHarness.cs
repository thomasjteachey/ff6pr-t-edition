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
            Harness.Register("tedtalk", (Harness.Handler)TedTalk, "tedtalk <script id> [now]: start the event of the field entity that runs that script, " +
                "as talking to it or stepping on it does (EventProcedure.RequestEntityAction; T-Edition's wired scripts " +
                "aren't startable by name: the field loads only what its entities name). Waits (30 s at most) until the player " +
                "has the field (state Player, no script, no request pending), as a player can only talk then. A request whose " +
                "script hasn't started 6 s later has its task ended by a watchdog: see tedtalkstate");
            Harness.Register("tedtalkstate", _ => $"tedtalkstate: {TalkLast}", "tedtalkstate: what became of the last tedtalk request (ran, ended, or ended by the watchdog and why)");
            // a headless run can't close the PR's shop with "press cancel" (ted-deny-2, 2026-11-26: map 77's merchant opened
            // shop 997, then 150 s of cancel presses left it open): ShopUIManager.Close, as the shop's own close button does
            Harness.Register("tedshopclose", (Harness.Handler)((a, tick) =>
            {
                var shop = Last.Management.ShopUIManager.Instance;
                if (tick == 0)
                {
                    if (shop == null || !shop.IsOpen) return "tedshopclose: no shop open";
                    shop.Close();
                    return null;
                }
                if (shop != null && (shop.IsOpen || shop.IsClosing) && tick < 600) return null;
                return $"tedshopclose: shop {(shop != null && shop.IsOpen ? "still open" : "closed")} after {tick} frames";
            }), "tedshopclose: close the open shop (ShopUIManager.Close, the shop's close button) and wait for it to close");
            Harness.Register("tedtile", TedTiles.Harness, "tedtile [#LAYER CELL [TILEID]]: field map layers / a cell's tile / write a tile at runtime (timed; T-Edition's tile changes)");
            Harness.Register("tedequip", Equip, "tedequip <party index 0-3 | character status id 1-14 as c1..c14> <T-Edition item slot> [equip slot 1-6, default 5 (relic 1)]: give it if needed and equip it (memory only)");
            Harness.Register("teduse", Use, "teduse <T-Edition item slot> <party index 0-3>: give it if needed and use it from the menu on that member (the game's OwnedItemClient.UseFunction); stats before/after");
            Harness.Register("tedcoliseum", _ => TedColiseum.Summary(), "tedcoliseum: T-Edition's Coliseum wagers and boss rewards loaded, the last match's choice");
            Harness.Register("tedstatus", a =>
            {
                var m = Member(a.Length > 0 ? a[0] : "0");
                return m == null ? "error: tedstatus <party 0-3|cN>" : $"{m.Name}: {string.Join(" | ", TedStatusPage.Lines(m, true))}";
            }, "tedstatus [party 0-3|cN]: the element and immunity lines the status screen shows (audit U4), with element ids");
            Harness.Register("tedcall", a =>
            {
                if (a.Length == 0) return "error: tedcall <call> (e.g. leadstatus 20 3 | timer_start 0 600 0x50 sc_x | status add 31 0020 | cmp 1E70 0 5)";
                string call = "TED:" + string.Join(" ", a);
                int r = TedSysCalls.Run(call, null);
                var ds = Last.Interpreter.DataStorage.Instance;
                string vars = ds == null ? "" : string.Join(" ", System.Linq.Enumerable.Range(0, 8).Select(i => $"{i}={ds.Get(Last.Interpreter.DataStorage.Category.kMapLocalVariable, i)}"));
                return $"tedcall {call}: result {r}; map-local {vars}; timers: {TedTimers.Last}; cmp: {TedRam.Last}";
            }, "tedcall <call>: runs a TED: SysCall as a script would (no shops), then the map-local variables 0-7");
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

        // --- tedtalk: an entity's own event, as the player triggers it (first-release plan task 5) --------
        // tedtalk waits for state Player held 0.2 s, no script running and no request pending, as a player can only talk
        // then: the gates sent their talks as soon as "scene field; map N" matched, which is also true while the map's
        // arrival still runs (ted-art-1: talk 11003 at "FieldReady"; ted-deny-1's merchant talk at "ChangeMap" ran a second
        // and never reached its shop).
        // The "harness artifact" of 2026-11-26 00:2x (a failing talk, then the next map load never finishing) was a SHOP:
        // the entity of script 11003 is map 9's weapon-shop keeper ("weapon shop: initial", action_id 8), so the game's action is
        // the PR's shop (EventProcedure.RequestEntityAction -> RequestActionTask(entity, PropertyEvent.ActionName)), T-Edition's
        // script there never runs (in a player's game neither: the PR's keepers switch stock by story layer), and the test
        // warped away with the shop still open (ted-art-1/2/3 at 11:2x). 11 of the 143 wired T-Edition NPC scripts sit on
        // such keepers. So a talk whose entity runs anything but a script is answered here, not requested.
        static float talkAsked, talkSettled = -1f;
        const int ShopAction = 8;   // action_id of the PR's shop keepers (map entity files)

        static string TalkBusy()
        {
            var mg = UnityEngine.Object.FindObjectOfType<global::MainGame>();
            if (mg?.eventProcedure == null || UnityEngine.Object.FindObjectOfType<global::FieldMap>()?.fieldController?.entityList == null)
                return "not on the field";
            var st = mg.CurrentState<Last.Management.SubSceneManagerMainGame.State>();
            if (st != Last.Management.SubSceneManagerMainGame.State.Player) return $"field state {st}";
            if (MapScripts.Busy) return $"a script runs or waits ({MapScripts.Current})";
            if (mg.eventProcedure.runAction != null) return $"an event request is pending ({TalkLast})";
            return null;
        }

        static string TedTalk(string[] a, int tick)
        {
            if (a.Length < 1 || !int.TryParse(a[0], out int id)) return "error: tedtalk <script id>";
            float now = UnityEngine.Time.realtimeSinceStartup;
            if (tick == 0) { talkAsked = now; talkSettled = -1f; }
            bool atOnce = a.Length > 1 && a[1] == "now";   // the old behaviour, for the watchdog's own test (ted-art-3)
            var busy = TalkBusy();
            if (atOnce && UnityEngine.Object.FindObjectOfType<global::FieldMap>()?.fieldController?.entityList != null &&
                UnityEngine.Object.FindObjectOfType<global::MainGame>()?.eventProcedure?.runAction == null) busy = null;
            else if (atOnce) return "error: not on the field, or a request is pending";
            if (atOnce) talkSettled = now - 1f;
            if (busy != null)
            {
                talkSettled = -1f;
                return now - talkAsked < 30f ? null : $"error: the player didn't have the field in 30 s ({busy}): script {id} not requested";
            }
            if (talkSettled < 0) talkSettled = now;
            if (now - talkSettled < 0.2f) return null;
            var fc = UnityEngine.Object.FindObjectOfType<global::FieldMap>().fieldController;
            var ep = UnityEngine.Object.FindObjectOfType<global::MainGame>().eventProcedure;
            float waited = now - talkAsked;
            var mine = new List<int>();
            foreach (var e in fc.entityList)
            {
                var pe = e?.Property?.TryCast<Last.Map.PropertyEvent>();
                if (pe == null) continue;
                if (pe.ScriptId != id)
                {
                    if (pe.ScriptId >= 9000 && !mine.Contains(pe.ScriptId)) mine.Add(pe.ScriptId);
                    continue;
                }
                if (pe.ActionId == ShopAction || (pe.ActionName ?? "").IndexOf("Shop", StringComparison.OrdinalIgnoreCase) >= 0)
                    return $"tedtalk: script {id} not requested: its entity ({e.gameObject.name}) runs the PR's shop (action {pe.ActionId} " +
                           $"'{pe.ActionName}'), so T-Edition's script there never runs in game (map {MapScripts.MapId})";
                var act = ep.RequestEntityAction(e);     // what the game calls when the player talks to it / steps on it
                if (act == null) return $"error: script {id}'s entity gave no action (map {MapScripts.MapId})";
                Watch(ep.runAction, id);
                return $"tedtalk: script {id} requested (entity {(e.gameObject.activeInHierarchy ? "shown" : "hidden")}, action {pe.ActionId} " +
                       $"'{pe.ActionName}', map {MapScripts.MapId}" + (waited > 0.5f ? $", after {waited:0.0} s for the player to have the field)" : ")");
            }
            return $"error: no entity runs script {id} on map {MapScripts.MapId} (mod scripts here: {string.Join(" ", mine)})";
        }

        // --- tedtalk's watchdog (2026-11-26; decompiled in tools/decomp/ted_talk*, patterns pr/tools/ghidra/ted_talk*.txt) --
        // The game keeps a requested event in EventProcedure.runAction until the action's task ends (UpdateController:
        // Task.CheckCompleted, i.e. TaskBase.Status == End -> action.Destroy(), runAction = null), and IsRunningAction
        // (= runAction != null) means an event is under way. EventActionScript's task (EventRunScript) first waits while
        // IMapAccessor.IsMovingCompanion, then runs the Master Script row's ProcessProg through EventProcedure.EventRunScript
        // and waits for the interpreter's End callback (ScriptFinished). When the player has the field, no script runs and
        // the request is still pending TalkTimeout seconds after it was made (or after its script ended), the watchdog logs
        // where the request sits and ends its task (Status = End); the game's own UpdateController then destroys the action
        // and clears runAction. A request still pending a second later is destroyed and cleared here. Test runs only: in a
        // player's game nothing calls tedtalk.
        const float TalkTimeout = 6f;
        static Last.Map.EventAction talkAction;
        static int talkScript;
        static float talkSince, talkCancelledAt = -1f;
        static bool talkStarted;
        internal static string TalkLast = "none";

        static void Watch(Last.Map.EventAction action, int id)
        {
            talkAction = action;
            talkScript = id;
            talkSince = UnityEngine.Time.realtimeSinceStartup;
            talkCancelledAt = -1f;
            talkStarted = false;
            TalkLast = action == null ? $"script {id}: no action to watch" : $"script {id} requested";
        }

        static void WatchTalk()
        {
            if (talkAction == null) return;
            var ep = UnityEngine.Object.FindObjectOfType<global::MainGame>()?.eventProcedure;
            var now = UnityEngine.Time.realtimeSinceStartup;
            bool pending = ep?.runAction != null && ep.runAction.Pointer == talkAction.Pointer;
            if (!pending)
            {
                // a short script can start and end between two frames here: its End callback set ScriptFinished
                try { if (talkAction.TryCast<Last.Map.EventActionScript>()?.ScriptFinished == true) talkStarted = true; }
                catch (Exception) { }
                // ended without its script: another action ran (EventAction by the entity's ActionName), or the
                // interpreter refused the script (EventActionScript.RunScript false)
                TalkLast = talkCancelledAt >= 0 ? $"script {talkScript}: request ended after the watchdog ended its task"
                         : talkStarted ? $"script {talkScript} ran and its request ended"
                         : $"script {talkScript}: request ended without its script running";
                if (talkCancelledAt >= 0 || !talkStarted) Kit.Info($"[ted] tedtalk: {TalkLast}");
                talkAction = null;
                return;
            }
            if (talkCancelledAt >= 0)
            {
                if (now - talkCancelledAt < 1f) return;
                try { talkAction.Destroy(); } catch (Exception e) { Hooks.WarnOnce("ted-talk-destroy", e); }
                ep.runAction = null;
                TalkLast = $"script {talkScript}: request destroyed and cleared by the watchdog (its task didn't end)";
                Kit.Info($"[ted] tedtalk: {TalkLast}");
                talkAction = null;
                return;
            }
            if (MapScripts.Busy) { talkStarted = true; talkSince = now; return; }   // a script runs: its End ends the request
            var st = UnityEngine.Object.FindObjectOfType<global::MainGame>()?.CurrentState<Last.Management.SubSceneManagerMainGame.State>();
            if (st != Last.Management.SubSceneManagerMainGame.State.Player) { talkSince = now; return; }   // a battle, a menu, a shop...
            if (now - talkSince < TalkTimeout) return;
            string where = TalkWhere(talkAction);
            try
            {
                var task = talkAction.Task?.TryCast<Last.Management.TaskBase>();
                if (task != null) task.Status = Last.Management.TaskBase.State.End;
            }
            catch (Exception e) { Hooks.WarnOnce("ted-talk-end", e); }
            talkCancelledAt = now;
            TalkLast = $"script {talkScript} {(talkStarted ? "ran, but its request stayed pending" : "never started")} {TalkTimeout:0} s with the player on the field ({where}): watchdog ended its task";
            Kit.Info($"[ted] tedtalk: {TalkLast}");
        }

        // where a pending request sits: its task's status, EventRunScript's coroutine state (0 not started, 1 waiting for
        // the companion to stop, 2 waiting for the script's End, -1 inside MoveNext), the companion wait's inputs
        static string TalkWhere(Last.Map.EventAction action)
        {
            var parts = new List<string> { $"action {action.GetIl2CppType()?.Name}" };
            try
            {
                var task = action.Task?.TryCast<Last.Management.TaskBase>();
                parts.Add(task == null ? "no task" : $"task {task.GetIl2CppType()?.Name} status {task.Status}");
                if (task != null)
                {
                    IntPtr handler = System.Runtime.InteropServices.Marshal.ReadIntPtr(task.Pointer + 0x18);   // EnumeratorTaskProcess.handler
                    if (handler != IntPtr.Zero)
                        parts.Add($"coroutine state {System.Runtime.InteropServices.Marshal.ReadInt32(handler + 0x10)}");
                }
                var script = action.TryCast<Last.Map.EventActionScript>();
                if (script != null) parts.Add($"script finished {script.ScriptFinished}, name '{script.scriptName}'");
                var fm = UnityEngine.Object.FindObjectOfType<global::FieldMap>();
                var fc = fm?.fieldController;
                if (fc != null)
                {
                    parts.Add($"companion moving {fc.TryCast<Last.Map.IMapAccessor>()?.IsMovingCompanion}");
                    parts.Add($"companion entity {(fc.companionEntity == null ? "none" : "set")}");
                }
                parts.Add($"companion asset {Last.Map.SaveMapManager.Instance?.CompanionEntity?.fieldCharacterAssetId}");
                parts.Add($"player state {fm?.playerStateMachine?.Current}");
            }
            catch (Exception e) { parts.Add($"? {e.GetType().Name}"); }
            return string.Join(", ", parts);
        }

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
                int party = Last.Battle.BattlePlugManager.Instance()?.MonsterParty?.Id ?? -1;
                if (party < 0) party = TedVictory.BattleParty >= 0 ? TedVictory.BattleParty : TedVictory.LastParty;
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
            // like for like (ted-8: the game's 281 rows include the PR's own copies, the port's 220 only changed rows):
            // each monster T-Edition gives a 3rd or 4th drop (ted_data drop_monster_ids, from its ROM) has one in game
            int listed = 0, missing = 0, extra = 0;
            var missingIds = new List<int>();
            if (all != null)
                foreach (var kv in all)
                {
                    var m = kv.Value;
                    if (m == null) continue;
                    bool has = m.DropContentId3 != 0 || m.DropContentId4 != 0;
                    if (Plugin.D.DropMonsterIds.Contains(m.Id))
                    {
                        listed++;
                        if (!has) { missing++; if (missingIds.Count < 8) missingIds.Add(m.Id); }
                    }
                    else if (has) extra++;
                }
            Expect(Plugin.D.DropMonsterIds.Count == 0 || missing == 0,
                   $"monsters T-Edition gives a 3rd/4th drop: {missing} of {listed} without one in game ({string.Join(",", missingIds)})");
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
                       $"{three} with 3 ({listed} of T-Edition's {Plugin.D.DropMonsterIds.Count} 3-4-slot monsters in game, {extra} other rows), {rate100} at drop rate 100; MONSTER_DROP_RATE {rates}";
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
            try { WatchTalk(); }
            catch (Exception e) { Hooks.WarnOnce("ted-talk-watch", e); }
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
