using System;
using System.Collections.Generic;
using HarmonyLib;
using Last.Battle;
using Last.Data;
using Last.Data.User;
using Last.Defaine;
using Last.Systems;
using PrKit;
using TEdition.Rules;

namespace TEdition.PR
{
    // T-Edition's character commands (BATTLE_SPEC 27, 28, 36, 38, 43; numbers in TedRules/CommandMath.cs):
    //  27 Steal (CalcControllerProvider.GetStealStatus postfix, BNW's CommandRules hook): Lv + 70 - target Lv
    //     out of 100, x2 with Enhanced Steal (Thief's Bracer, Orichalcum), the rare slot 64/256, an empty
    //     picked slot fails; the PR's own: (Lv + 50 - target Lv)/99, rare 12%. A character's steals count.
    //  43 the success counters ($1E70 Steal, $1E72 Twin Fang, ...) live in the save (TedCounters).
    //  28 Orichalcum: battle power min(steals / 2, 255) (PlayerCharacterParameter.GetArmConfirmedAttack /
    //     ConfirmedAttack postfix for a hand holding it).
    //  38 Interceptor blocks 171/256 (WildFangConditionFunction.CheckDefendInvoke rolls CommonUtility
    //     .GetRand(100) < 50; while it runs that roll answers with T-Edition's odds).
    //  36 Umaro's attack odds: the kit's SNES table (SnesUmaro; T-Edition's C2/5251 weights are vanilla's and
    //     its Berserker Ring is the PR's Rage Ring row). Power Belt -> Rampage: deferred (notes).
    sealed class TedCommands : Feature
    {
        public TedCommands() : base("Battle", "Commands", true,
            "T-Edition's commands: Steal (Lv+70-target Lv, rare 1/4), its saved success counter, Orichalcum's power from it, " +
            "Interceptor blocking 2 in 3, Umaro's SNES attack odds.") { }

        static bool On => Plugin.TedMode;
        static readonly Random Rng = new Random();
        internal static int Steals, Blocks, Rolls;
        internal static bool? ForceSteal;           // tests
        internal static bool Testing;               // self-tests: no counting
        internal static int LastStealChance;        // tests: the chance (percent) the last steal rolled against
        internal static bool LastStealSure;

        public override void Apply(Harmony h)
        {
            Hooks.Patch(h, typeof(CalcControllerProvider), "GetStealStatus", typeof(TedCommands), postfix: nameof(Steal_Postfix));
            var pcp = typeof(PlayerCharacterParameter);
            Hooks.Patch(h, pcp, "GetArmConfirmedAttack", typeof(TedCommands), postfix: nameof(ArmAttack_Postfix));
            Hooks.Patch(h, pcp, "ConfirmedAttack", typeof(TedCommands), postfix: nameof(Attack_Postfix));
            Hooks.Patch(h, typeof(WildFangConditionFunction), "CheckDefendInvoke", typeof(TedCommands),
                prefix: nameof(Defend_Prefix), postfix: nameof(Defend_Postfix));
            Hooks.Patch(h, typeof(global::CommonUtility), "GetRand", typeof(TedCommands), prefix: nameof(GetRand_Prefix), args: new[] { typeof(int) });
            PrKit.Ff6.SnesUmaro.Apply(h, new PrKit.Ff6.SnesUmaroMod { Name = "T-Edition", On = () => On });
        }

        public override string Check()
        {
            if (!On) return "off (no T-Edition data)";
            return $"on: Orichalcum row {Plugin.D.NamedRow("orichalcum")}, Enhanced Steal items {string.Join("/", EnhancedSteal())}; {TedCounters.State}";
        }

        // --- 27: Steal --------------------------------------------------------------------------------

        static int[] EnhancedSteal() => new[] { Plugin.D.BySlot(0xCF)?.Content ?? 0, Plugin.D.NamedContent("orichalcum") };   // Thief's Bracer, Orichalcum

        public static void Steal_Postfix(CalcControllerProvider __instance, ICalcResult __result)
        {
            if (!On || __result == null || !Hooks.IsA<CalcControllerProvider>(__instance)) return;
            try
            {
                if (__instance.userCharaData == null || __instance.attack == null) return;   // monsters steal gil as in vanilla
                var monster = __instance.calcInfo?.targetMonster;
                var res = __result.TryCast<CalcResult>();
                if (monster == null || res == null) return;
                int common = monster.StealContentId1, rare = monster.StealContentId2;
                if (common == 0 && rare == 0) return;                                    // nothing to steal: the game's own message
                int lv = __instance.attack.ConfirmedLevel(), tlv = __instance.target?.ConfirmedLevel() ?? 0;
                bool enhanced = Wears(__instance.userCharaData, EnhancedSteal());
                int roll = Rng.Next(100);
                bool success = ForceSteal ?? CommandMath.StealSucceeds(lv, tlv, enhanced, roll);
                int slot = CommandMath.PicksRare(Rng.Next(256)) ? 2 : 1;
                if ((slot == 2 ? rare : common) == 0) success = false;
                var gameHit = __result.GetHitType();
                int gameSlot = res.GetStealContentId();
                __result.SetStatus(__result.GetValue(false), success ? HitType.Hit : HitType.Non, __result.GetHitCount(), __result.GetConditions(), false);
                res.SetStealContentId(success ? slot : 0);
                Steals++;
                if (success && !Testing) TedCounters.Bump(TedCounters.Steal);
                int c = CommandMath.StealChance(lv, tlv, enhanced);
                LastStealSure = lv + 70 >= 256 || c >= 128;
                LastStealChance = LastStealSure ? 100 : Math.Clamp(c, 0, 100);
                TedLog.Rule(27, "", () => $"Steal (Lv {lv} vs {tlv}{(enhanced ? ", Enhanced Steal" : "")}): chance {Math.Clamp(c, 0, 100)}%, " +
                                          $"{(success ? (slot == 2 ? "rare" : "common") : "failed")} (the game's {gameHit}/slot {gameSlot}); steals {TedCounters.Get(TedCounters.Steal)}");
            }
            catch (Exception e) { Hooks.WarnOnce("TedCommands.Steal", e); }
        }

        static bool Wears(OwnedCharacterData c, int[] contentIds)
        {
            var eq = c?.EquipmentData;
            if (eq == null) return false;
            foreach (var kv in eq)
            {
                var it = kv.Value;
                if (it == null) continue;
                foreach (var id in contentIds) if (id > 0 && it.ContentId == id) return true;
            }
            return false;
        }

        // --- 28: Orichalcum ---------------------------------------------------------------------------

        static readonly Dictionary<IntPtr, OwnedCharacterData> owners = new Dictionary<IntPtr, OwnedCharacterData>();
        static int ownersAt = -1000;

        static OwnedCharacterData Owner(PlayerCharacterParameter p)
        {
            lock (owners)
            {
                int f = UnityEngine.Time.frameCount;
                if (!owners.TryGetValue(p.Pointer, out var c) && f - ownersAt > 30)
                {
                    ownersAt = f;
                    owners.Clear();
                    var all = Last.Management.UserDataManager.Instance()?.GetOwnedCharactersClone(false);
                    if (all != null)
                        foreach (var o in all)
                            if (o?.Parameter != null) owners[o.Parameter.Pointer] = o;
                    owners.TryGetValue(p.Pointer, out c);
                }
                return c;
            }
        }

        static bool Holds(OwnedCharacterData c, EquipSlotType slot, int contentId)
        {
            var eq = c?.EquipmentData;
            return eq != null && contentId > 0 && eq.ContainsKey(slot) && eq[slot]?.ContentId == contentId;
        }

        static int OrichalcumBonus(PlayerCharacterParameter p, BattleActData.ArmType? arm)
        {
            int ori = Plugin.D.NamedContent("orichalcum");
            if (ori <= 0) return 0;
            var c = Owner(p);
            if (c == null) return 0;
            bool right = Holds(c, EquipSlotType.Slot1, ori), left = Holds(c, EquipSlotType.Slot2, ori);
            bool held = arm == null ? right || left : arm == BattleActData.ArmType.Right ? right : left;
            return held ? CommandMath.OrichalcumPower(TedCounters.Get(TedCounters.Steal)) : 0;
        }

        public static void ArmAttack_Postfix(PlayerCharacterParameter __instance, BattleActData.ArmType armType, ref int __result)
        {
            if (!On || __instance == null) return;
            try
            {
                int add = OrichalcumBonus(__instance, armType);
                if (add <= 0) return;
                int was = __result;
                __result += add;
                int now = __result;
                TedLog.Rule(28, "", () => $"Orichalcum: battle power +{add} from {TedCounters.Get(TedCounters.Steal)} steals ({was} -> {now})");
            }
            catch (Exception e) { Hooks.WarnOnce("TedCommands.Orichalcum", e); }
        }

        public static void Attack_Postfix(PlayerCharacterParameter __instance, ref int __result)
        {
            if (!On || __instance == null) return;
            try { __result += OrichalcumBonus(__instance, null); }
            catch (Exception e) { Hooks.WarnOnce("TedCommands.OrichalcumMenu", e); }
        }

        // --- 38: Interceptor ----------------------------------------------------------------------------

        [ThreadStatic] static bool interceptorRoll, interceptorAnswered;

        public static void Defend_Prefix()
        {
            if (!On) return;
            interceptorRoll = true;
            interceptorAnswered = false;
        }

        public static void Defend_Postfix(bool __result)
        {
            if (!interceptorRoll) return;
            interceptorRoll = false;
            if (!interceptorAnswered) return;   // not a physical hit it could block: no roll
            bool r = __result;
            if (r) Blocks++;
            TedLog.Rule(38, "", () => $"Interceptor rolled with T-Edition's odds (171/256): {(r ? "blocks" : "doesn't")}");
        }

        // the one GetRand(100) inside CheckDefendInvoke (its "< 50"): answered with T-Edition's odds
        public static bool GetRand_Prefix(int max, ref int __result)
        {
            if (!interceptorRoll || interceptorAnswered || max != 100) return true;
            interceptorAnswered = true;
            __result = CommandMath.InterceptorAnswer(CommandMath.InterceptorBlock(Rng.Next(256)));
            Rolls++;
            return false;
        }
    }

    // T-Edition's success counters ($1E70 Steal, $1E72 Twin Fang, $1E74 Runic, $1E76 Sketch, $1E78 unused,
    // $1E7A Slot, $1E7C Snowstorm, $1E7E Mimic; rule 43), kept in the save: the PR games share one save format
    // and FF6 never uses FF2's keyword list (UserDataManager.OwnedKeyWaordList, saved as "ownedKeyWaordList"),
    // so the block is a marker "TED1" and 8 words there (BNW keeps its esper data the same way, marker "BNW1").
    // T-Edition's saves are its own files (ModSaves "TEdition"); test runs never save.
    static class TedCounters
    {
        public const int Steal = 0, TwinFang = 1, Runic = 2, Sketch = 3, Slot = 5, Snowstorm = 6, Mimic = 7, Count = 8;
        const int Marker = 0x54454431;   // "TED1"
        static readonly object Sync = new object();
        public static string State = "counters not read yet";

        static Il2CppSystem.Collections.Generic.List<int> List() => Last.Management.UserDataManager.Instance()?.OwnedKeyWaordList;

        static int Find(Il2CppSystem.Collections.Generic.List<int> list)
        {
            int n = list.Count;
            for (int i = 0; i + 1 + Count <= n; i++)
                if (list[i] == Marker) return i;
            return -1;
        }

        public static int Get(int which)
        {
            lock (Sync)
            {
                var list = List();
                if (list == null) { State = "no save data"; return 0; }
                int at = Find(list);
                State = at < 0 ? "no counters in this save yet" : "counters in the save";
                return at < 0 ? 0 : list[at + 1 + which];
            }
        }

        public static void Set(int which, int value)
        {
            lock (Sync)
            {
                var list = List();
                if (list == null) return;
                int at = Find(list);
                if (at < 0)
                {
                    at = list.Count;
                    list.Add(Marker);
                    for (int i = 0; i < Count; i++) list.Add(0);
                    Kit.Info("[ted] started T-Edition's success counters in this save");
                }
                list[at + 1 + which] = value;
                State = "counters in the save";
            }
        }

        public static void Bump(int which) => Set(which, CommandMath.Bump(Get(which), which == TwinFang ? CommandMath.TwinFangCap : CommandMath.CounterCap));

        public static string Summary() =>
            $"steals {Get(Steal)}, Twin Fang {Get(TwinFang)}, Runic {Get(Runic)}, Sketch {Get(Sketch)}, Slot {Get(Slot)}, Snowstorm {Get(Snowstorm)}, Mimic {Get(Mimic)} ({State})";
    }
}
