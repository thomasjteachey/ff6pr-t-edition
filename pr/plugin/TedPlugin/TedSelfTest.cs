using System;
using System.Collections.Generic;
using System.Linq;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using Last.Battle;
using Last.Battle.Function;
using Last.Data.Master;
using Last.Defaine;
using Last.Systems;
using PrKit;

namespace TEdition.PR
{
    // In-battle checks of T-Edition's rules through the game's own functions (harness `teddamage`): each case
    // runs an act's functions (nothing applied, as PrKit's SnesRelicPenalties.SelfTest) n times with the rules
    // off (the game's value) and on, and compares the mean ratio with the factor the rules worked out from
    // what the game read. Statuses a case needs (Shell, Defend, Trance) are put on for the case and taken off.
    static class TedSelfTest
    {
        sealed class Case
        {
            public string Name;
            public Func<BattleUnitData> Attacker, Target;
            public string Ability, Command;
            public ConditionType[] TargetStatus = Array.Empty<ConditionType>(), AttackerStatus = Array.Empty<ConditionType>();
            public int[] Rules = Array.Empty<int>();   // rules expected to fire (any of them)
        }

        internal static string Damage(string[] args)
        {
            var battle = BattlePlugManager.Instance();
            if (battle == null || !battle.IsBattle()) return "error: not in a battle";
            var players = battle.GetPlayerUnits()?.Where(p => p?.BattleUnitDataInfo?.Parameter?.CurrentHP > 0).ToList();
            var enemies = battle.GetEnemyUnits()?.Where(e => e?.BattleUnitDataInfo?.Parameter?.CurrentHP > 0).ToList();
            if (players == null || players.Count == 0 || enemies == null || enemies.Count == 0) return "error: no living fighters";
            BattleUnitData p0 = players[0], e0 = enemies[0];
            int n = args.Length > 0 && int.TryParse(args[0], out var v) ? Math.Clamp(v, 4, 200) : 24;
            var cases = new List<Case>
            {
                new Case { Name = "Fight on a monster", Attacker = () => p0, Target = () => e0, Ability = "#1", Command = "#1" },
                new Case { Name = "Fire on a monster", Attacker = () => p0, Target = () => e0, Ability = "Fire", Command = "Magic", Rules = new[] { 6, 7 } },
                new Case { Name = "Ice on a monster", Attacker = () => p0, Target = () => e0, Ability = "Blizzard|Ice", Command = "Magic", Rules = new[] { 6, 7 } },
                new Case { Name = "Bolt on a monster", Attacker = () => p0, Target = () => e0, Ability = "Thunder|Bolt", Command = "Magic", Rules = new[] { 6, 7 } },
                new Case { Name = "a multi-element spell on a monster", Attacker = () => p0, Target = () => e0, Ability = "*multi", Command = "Magic", Rules = new[] { 6 } },
                new Case { Name = "Cure on a Shelled character", Attacker = () => p0, Target = () => p0, Ability = "Cure", Command = "Magic",
                           TargetStatus = new[] { ConditionType.Shell }, Rules = new[] { 8 } },
                new Case { Name = "monster Fire on a defending character", Attacker = () => e0, Target = () => p0, Ability = "Fire", Command = "Magic",
                           TargetStatus = new[] { ConditionType.Defend }, Rules = new[] { 10 } },
                new Case { Name = "monster Fire on a Morphed character", Attacker = () => e0, Target = () => p0, Ability = "Fire", Command = "Magic",
                           TargetStatus = new[] { ConditionType.Trance }, Rules = new[] { 10 } },
                new Case { Name = "Fight by a Morphed character", Attacker = () => p0, Target = () => e0, Ability = "#1", Command = "#1",
                           AttackerStatus = new[] { ConditionType.Trance }, Rules = new[] { 40 } },
                new Case { Name = "an ignore-defense spell on a Shelled character", Attacker = () => e0, Target = () => p0, Ability = "*ignore", Command = "Magic",
                           TargetStatus = new[] { ConditionType.Shell }, Rules = new[] { 8 } },
            };
            var lines = new List<string>();
            int ok = 0, failed = 0, skipped = 0;
            foreach (var c in cases)
            {
                string line;
                try { line = Run(c, n, out bool? pass); if (pass == true) ok++; else if (pass == false) failed++; else skipped++; }
                catch (Exception e) { line = $"{c.Name}: error {e.GetType().Name}: {e.Message}"; failed++; }
                lines.Add(line);
                Kit.Info($"[ted] damage self-test: {line}");
            }
            return $"teddamage: {ok} ok, {failed} failed, {skipped} skipped ({n} samples each) | " + string.Join(" | ", lines);
        }

        // 27: Steal by the first party member on the first monster through the game's functions (nothing applied,
        // no counting): the success rate against T-Edition's chance; the rare share against 1/4
        internal static string Steal(string[] args)
        {
            var battle = BattlePlugManager.Instance();
            if (battle == null || !battle.IsBattle()) return "error: not in a battle";
            var p0 = battle.GetPlayerUnits()?.FirstOrDefault(p => p?.BattleUnitDataInfo?.Parameter?.CurrentHP > 0);
            var e0 = battle.GetEnemyUnits()?.FirstOrDefault(e => e?.BattleUnitDataInfo?.Parameter?.CurrentHP > 0);
            if (p0 == null || e0 == null) return "error: no living fighters";
            var cmd = Master.Get<Command>(10);
            var ab = cmd == null ? null : Master.Get<Ability>(cmd.AbilityId);
            if (ab == null) return "error: no Steal command/ability";
            var mon = e0.TryCast<BattleEnemyData>()?.GetMonster();
            if (mon == null || (mon.StealContentId1 == 0 && mon.StealContentId2 == 0)) return $"tedsteal: monster {mon?.Id} has nothing to steal (n/a)";
            int n = args.Length > 0 && int.TryParse(args[0], out var v) ? Math.Clamp(v, 10, 2000) : 400;
            int ok = 0, rare = 0, other = 0;
            TedCommands.Testing = true;
            try
            {
                for (int i = 0; i < n; i++)
                {
                    var (hit, _, slot) = StealOnce(p0, e0, cmd, ab);
                    if (hit == HitType.Hit) { ok++; if (slot == 2) rare++; }
                    else if (hit != HitType.Non && hit != HitType.Miss) other++;
                }
            }
            finally { TedCommands.Testing = false; }
            int chance = TedCommands.LastStealChance;
            // the empty slot fails too: expected success = chance x (filled share of the slot pick)
            double fill = (mon.StealContentId1 != 0 ? 0.75 : 0) + (mon.StealContentId2 != 0 ? 0.25 : 0);
            double want = chance / 100.0 * fill, got = (double)ok / n;
            double sd = Math.Sqrt(Math.Max(want * (1 - want), 0.0025) / n);
            bool pass = Math.Abs(got - want) <= 4 * sd + 0.01;
            double rareShare = ok == 0 ? 0 : (double)rare / ok;
            string line = $"tedsteal: {ok}/{n} stolen ({got:P1}), T-Edition's chance {chance}% x slots {fill:0.##} = {want:P1} " +
                          $"{(pass ? "ok" : "MISMATCH")}; rare {rare} ({rareShare:P0} of steals; 1/4 when both slots hold items); " +
                          $"monster {mon.Id} (Lv {e0.BattleUnitDataInfo.Parameter.ConfirmedLevel()}) items {mon.StealContentId1}/{mon.StealContentId2}; " +
                          $"thief Lv {p0.BattleUnitDataInfo.Parameter.ConfirmedLevel()}{(other > 0 ? $"; {other} other results" : "")}";
            Kit.Info("[ted] " + line);
            return line;
        }

        static (HitType, int, int) StealOnce(BattleUnitData attacker, BattleUnitData target, Command cmd, Ability ab)
        {
            var abilities = new Il2CppSystem.Collections.Generic.List<Ability>();
            abilities.Add(ab);
            var targets = new Il2CppReferenceArray<BattleUnitData>(1);
            targets[0] = target;
            var act = new BattleActData(attacker, targets, cmd, abilities, BattleActData.ActType.Normal,
                (BattleActData.TargetType)0, BattleActData.ArmType.Right, (BattleActData.ActAbilityType)0, 1, false);
            var fns = ParameterActFunctionManagment.GetFunction(ab);
            if (fns == null) return (HitType.Non, 0, 0);
            var results = new Il2CppSystem.Collections.Generic.Dictionary<BattleUnitData, ICalcResult>();
            var attacks = new Il2CppSystem.Collections.Generic.Dictionary<BattleUnitData, ICalcResult>();
            HitType hitType = HitType.Non;
            int value = 0, slot = 0;
            foreach (var f in fns)
            {
                if (f == null) continue;
                f.Init(act, results, attacks);
                f.FixedTarget();
                f.HitCalc();
                var dic = f.ICalcResultDic ?? results;
                if (dic != null && dic.ContainsKey(target))
                {
                    var r = dic[target];
                    hitType = r.GetHitType();
                    value = r.GetValue(false);
                    slot = r.TryCast<CalcResult>()?.GetStealContentId() ?? 0;
                }
            }
            return (hitType, value, slot);
        }

        static string Run(Case c, int n, out bool? pass)
        {
            pass = null;
            var attacker = c.Attacker();
            var target = c.Target();
            var ab = FindAbility(c.Ability, attacker, target);
            var cmd = FindCommand(c.Command);
            if (ab == null || cmd == null) return $"{c.Name}: skipped (no {(ab == null ? $"ability '{c.Ability}'" : $"command '{c.Command}'")})";
            var cc = BattlePlugManager.Instance().BattleConditionController;
            var added = new List<(BattleUnitData, ConditionType)>();
            void Put(BattleUnitData u, ConditionType t)
            {
                var l = u.BattleUnitDataInfo?.GetConfirmedConditionType();
                if (l != null && l.Contains(t)) return;
                cc.InterruptAddCondition(u, t);
                added.Add((u, t));
            }
            try
            {
                foreach (var t in c.TargetStatus) Put(target, t);
                foreach (var t in c.AttackerStatus) Put(attacker, t);
                var missing = c.TargetStatus.Where(t => !Has(target, t)).Concat(c.AttackerStatus.Where(t => !Has(attacker, t))).ToList();
                if (missing.Count > 0) return $"{c.Name}: skipped (status {string.Join(",", missing)} didn't stay on)";
                TedDamage.Bypass = true;
                var (gameMean, gameN, gameHit) = Mean(attacker, target, cmd, ab, n);
                TedDamage.Bypass = false;
                TedDamage.LastResult = null;
                var (tedMean, tedN, tedHit) = Mean(attacker, target, cmd, ab, n);
                var r = TedDamage.LastResult;
                double want = r?.Factor ?? 1.0;
                string fired = r == null ? "none" : string.Join(",", r.Fired.Select(f => f.Rule).Distinct());
                string inputs = TedDamage.LastInputs;
                if (gameN == 0 && tedN == 0)
                    return $"{c.Name} ({AbilityName(ab)}): no hit either way ({gameHit}/{tedHit}); {inputs}";
                double ratio = gameMean > 0 ? tedMean / gameMean : 0;
                bool zeroOk = r != null && r.ZeroDamage && tedMean == 0;
                pass = zeroOk || (gameMean > 0 && Math.Abs(ratio - want) <= 0.06 * Math.Max(want, 0.2) + 1.0 / Math.Max(1, gameMean));
                if (c.Rules.Length > 0 && r != null && !r.Fired.Any(f => c.Rules.Contains(f.Rule)) && Math.Abs(want - 1) < 1e-9)
                    pass = pass == true ? (bool?)null : pass;   // the rule didn't apply to this monster/party (no weakness...): not a failure
                return $"{c.Name} ({AbilityName(ab)}): game {gameMean:0.#} ({gameHit}), T-Edition {tedMean:0.#} ({tedHit}): x{ratio:0.###}, " +
                       $"rules' factor x{want:0.###} [{fired}] {(pass == true ? "ok" : pass == false ? "MISMATCH" : "n/a")}; {inputs}";
            }
            finally
            {
                TedDamage.Bypass = false;
                foreach (var (u, t) in added)
                    try { cc.InterruptRemoveCondition(u, t); } catch { }
            }
        }

        static bool Has(BattleUnitData u, ConditionType t) => u.BattleUnitDataInfo?.GetConfirmedConditionType()?.Contains(t) == true;

        static (double Mean, int N, string Hit) Mean(BattleUnitData attacker, BattleUnitData target, Command cmd, Ability ab, int n)
        {
            double sum = 0;
            int k = 0;
            var kinds = new Dictionary<HitType, int>();
            for (int i = 0; i < n; i++)
            {
                var (hit, value) = Hit(attacker, target, cmd, ab);
                kinds[hit] = kinds.TryGetValue(hit, out var c) ? c + 1 : 1;
                if (hit == HitType.Hit || hit == HitType.Recovery || hit == HitType.Zero) { sum += value; k++; }
            }
            return (k == 0 ? 0 : sum / k, k, string.Join(" ", kinds.Select(kv => $"{kv.Key} {kv.Value}")));
        }

        // one act through every function of the ability (nothing applied): the target's result
        static (HitType, int) Hit(BattleUnitData attacker, BattleUnitData target, Command cmd, Ability ab)
        {
            var abilities = new Il2CppSystem.Collections.Generic.List<Ability>();
            abilities.Add(ab);
            var targets = new Il2CppReferenceArray<BattleUnitData>(1);
            targets[0] = target;
            var act = new BattleActData(attacker, targets, cmd, abilities, BattleActData.ActType.Normal,
                (BattleActData.TargetType)0, BattleActData.ArmType.Right, (BattleActData.ActAbilityType)0, 1, false);
            var fns = ParameterActFunctionManagment.GetFunction(ab);
            if (fns == null) return (HitType.Non, 0);
            var results = new Il2CppSystem.Collections.Generic.Dictionary<BattleUnitData, ICalcResult>();
            var attacks = new Il2CppSystem.Collections.Generic.Dictionary<BattleUnitData, ICalcResult>();
            HitType hitType = HitType.Non;
            int value = 0;
            foreach (var f in fns)
            {
                if (f == null) continue;
                f.Init(act, results, attacks);
                f.FixedTarget();
                f.HitCalc();
                var dic = f.ICalcResultDic ?? results;
                if (dic != null && dic.ContainsKey(target))
                {
                    var r = dic[target];
                    hitType = r.GetHitType();
                    value = r.GetValue(false);
                }
            }
            return (hitType, value);
        }

        // "#id", a name ("Fire", "A|B": the first found), "*multi" (an attack spell with 2+ elements), "*ignore"
        // (a damaging spell with the ignore-defense flag)
        static Ability FindAbility(string spec, BattleUnitData attacker, BattleUnitData target)
        {
            var calc = Last.Management.BattleControllerManagement.Instance()?.GetCurrentProvider()?.TryCast<CalcControllerProvider>();
            if (spec.StartsWith("#")) return Master.Get<Ability>(int.Parse(spec.Substring(1)));
            var all = Master.All<Ability>();
            if (all == null) return null;
            if (spec == "*multi" && calc != null)
            {
                foreach (var kv in all)
                {
                    var a = kv.Value;
                    if (a == null || a.StandardValue <= 0 || a.TypeId != 1) continue;
                    var arr = calc.GetAbilityAttributeArray(a);
                    if (arr != null && arr.Count(x => x > 0) >= 2) return a;
                }
                return null;
            }
            if (spec == "*ignore")
            {
                foreach (var kv in all)
                {
                    var a = kv.Value;
                    if (a != null && a.TypeId == 1 && a.StandardValue > 20 && TedDamage.IgnoresDefense(a)) return a;
                }
                return null;
            }
            var names = spec.Split('|');
            var contents = Master.All<Content>();
            if (contents == null) return null;
            foreach (var name in names)
                foreach (var kv in contents)
                {
                    var c = kv.Value;
                    if (c == null || c.TypeId != 4) continue;
                    if (string.Equals(TEdition.Rules.TedData.Plain(GameText.Get(c.MesIdName)), name, StringComparison.OrdinalIgnoreCase))
                    {
                        var a = Master.Get<Ability>(c.TypeValue);
                        if (a != null) return a;
                    }
                }
            return null;
        }

        static Command FindCommand(string spec)
        {
            if (spec.StartsWith("#")) return Master.Get<Command>(int.Parse(spec.Substring(1)));
            var all = Master.All<Command>();
            if (all == null) return null;
            foreach (var kv in all)
                if (kv.Value != null && string.Equals(TEdition.Rules.TedData.Plain(GameText.Get(kv.Value.MesIdName)), spec, StringComparison.OrdinalIgnoreCase))
                    return kv.Value;
            return null;
        }

        static string AbilityName(Ability a)
        {
            var contents = Master.All<Content>();
            if (contents != null)
                foreach (var kv in contents)
                    if (kv.Value != null && kv.Value.TypeId == 4 && kv.Value.TypeValue == a.Id)
                        return $"{TEdition.Rules.TedData.Plain(GameText.Get(kv.Value.MesIdName))} #{a.Id}";
            return $"#{a.Id}";
        }
    }
}
