using System;
using System.Collections.Generic;
using System.IO;
using BepInEx;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using PrKit;
using TEdition.Rules;
using UnityEngine;

namespace TEdition.PR
{
    // FF6 T-Edition (Tsushiy; Mato's English 3.0.7 A7 r1, with EX) for the Pixel Remaster: T-Edition's
    // battle rules on the game's engine (pr/ted/BATTLE_SPEC.md), on the port's data (its Magicite folder
    // TEdition, from tools/port.py tedition). A mod of its own: Brave New World, Worlds Collide and
    // Beyond Chaos are separate mods, one active per install. PORTING.md "T-Edition port" is the plan.
    [BepInPlugin(Guid, "FF6 T-Edition (Pixel Remaster)", Version)]
    public partial class Plugin : BasePlugin
    {
        public const string Guid = "ff6mod.tedition";
        public const string Version = "0.1.2";
        public const string ModFolder = "TEdition";   // its Magicite folder, its data folder (BepInEx/TEdition), its saves
        internal static ManualLogSource L;
        internal static bool TedMode;                 // T-Edition's data is installed: the rules are on
        internal static TedData D;
        internal static string DataDir, DataFile, DataError;
        internal static FeatureHost Features;
        internal static Harmony H;

        public override void Load()
        {
            L = Log;
            var clock = System.Diagnostics.Stopwatch.StartNew();
            Kit.Init(Log, "T-Edition");
            // plugin data stays out of the plugins folder (BepInEx scans it on every assembly lookup)
            DataDir = Path.Combine(Paths.BepInExRootPath, ModFolder);
            DataFile = Path.Combine(DataDir, "ted_data.json");
            TedMode = MagiciteDir.Has(ModFolder);
            if (TedMode) L.LogInfo($"T-Edition's data: {MagiciteDir.FolderPath(ModFolder)}");
            else L.LogWarning($"T-Edition's data isn't installed (no {ModFolder} folder in {MagiciteDir.ImportDir}): its rules are off");
            try
            {
                D = File.Exists(DataFile) ? TedData.Parse(File.ReadAllText(DataFile)) : null;
                if (D == null) DataError = $"no {DataFile}";
            }
            catch (Exception e) { DataError = $"{DataFile}: {e.Message}"; }
            if (DataError != null) L.LogWarning($"[ted] {DataError}: rules that need the port's lists are off");
            D ??= new TedData();
            H = new Harmony(Guid);
            // T-Edition's own saves, apart from vanilla's and the other mods' (PrKit/ModSaves.cs), synced by Steam Cloud
            if (TedMode) ModSaves.Apply(H, ModFolder);
            if (TedMode) TedArt.MonsterImagesAtLoad(DataDir);   // before Magicite's first Update scans its folder
            if (TedMode) TedArt.BaseLooks(H, DataDir);
            if (TedMode)
            {
                TedCostumes.Init(DataDir);
                TedCostumes.SetLayer = (n, f) => ArtSwap.SetLayer(n, f);   // the kit's ArtSwap layers
            }
            Features = new FeatureHost(Config, H);
            Features.Add(new SingleGamepad());   // one controller, one input on the Steam Deck
            Features.Add(new TedDamage());
            TedStatuses.ColiseumControl = Config.Bind("Battle", "ColiseumControl", false,
                "T-Edition's Colosseum: the fighter takes your commands instead of acting on its own (rule 56). Off until it has been seen working in game.").Value;
            Features.Add(new TedStatuses());     // its BattleConditionController.Update prefix before the kit's (below)
            Features.Add(new TedCommands());
            Features.Add(new TedVictory());
            Features.Add(new TedAllyStatus());   // audit U7: Select in battle shows the allies' hidden statuses
            Features.ApplyAll();                 // also starts a test run (harness) when one is requested
            TedHarness.Register();
            if (TedMode) TedSysCalls.Apply(H);
            if (TedMode) TedMagicite.Apply(H);   // rule 35
            if (TedMode) TedStatusPage.Patch(H);   // audit U4: elements and immunities on the status screen
            if (TedMode) TedChestLines.Patch(H);   // audit U9: the chest line by party lead
            if (TedMode) TedEquipDetails.Patch(H);   // audit U5: weapons' effects in the equip menu's description
            if (TedMode) TedDamageDigits.Patch(H);   // audit M30: 5-digit damage numbers (cap 32000)
            if (TedMode) TedNearFatal.Patch(H);   // audit M17: percent spells miss monsters immune to Near Fatal
            if (TedMode) TedBlocker.Patch(H);   // audit M38: Golem / Interceptor blocks against defense 119
            if (TedMode) TedUltima.Patch(H);   // audit I12: the Ultima Weapon's blade at T-Edition's damage thresholds
            if (TedMode) TedBarrage.Patch(H);   // audit M34: the Offering's hits at normal accuracy
            if (TedMode) TedRibbon.Patch(H);   // audit M15: equipment statuses beat immunity (Cursed Shield + Ribbon)
            // audit G12: MP damage pink, MP healing blue (the kit's SnesMpNumbers)
            if (TedMode) PrKit.Ff6.SnesMpNumbers.Apply(H, new PrKit.Ff6.SnesMpNumbersMod
            {
                Name = "T-Edition", MpDamage = new UnityEngine.Color(1f, 0.55f, 0.8f), MpHeal = new UnityEngine.Color(0.45f, 0.7f, 1f),
                Enabled = () => TedMode,
            });
            if (TedMode) TedRageOrder.Patch(H);   // audit U10: Rages alphabetical
            if (TedMode) TedRelics.Patch(H);   // audit I5: relic effects on T-Edition's other items
            if (TedMode) TedDesperation.Patch(H);
            if (TedMode) TedUmaro.Patch(H);   // audit C28: Umaro takes commands; his Fight by T-Edition's table   // rule 39: desperation attacks
            if (TedMode) TedEncounters.Patch(H);   // rule 24: openings (pre-emptive relic x4, no enemy first strike)
            if (TedMode) TedFlags.Load(Path.Combine(DataDir, "ted_flags.json"));   // ted-events' named PR flags
            if (TedMode) TedRam.LoadSongs(Path.Combine(DataDir, "music", "ted_music.json"));   // TED:cmp 1300 / TED:song: vanilla tracks as SNES songs
            if (TedMode) TedShop.Apply(H);   // audit I18: WoR prices x2 until Humbaba
            if (TedMode)
            {
                TedTiles.LoadCells(Path.Combine(DataDir, "ted_tile_cells.json"));   // T-Edition's tile changes: walkability
                TedTiles.Patch(H);
            }
            if (TedMode) TedColiseum.Apply(H, Path.Combine(DataDir, "ted_rewards.json"));
            if (TedMode)
            {
                // T-Edition's own songs on the kit's SNES music player (TedMusic; the pack from tools/ted_music.py)
                try
                {
                    TedMusic.Patch(H);
                    TedMusic.Load(Path.Combine(DataDir, "music"));
                }
                catch (Exception e) { L.LogError($"[ted music] {e.GetType().Name}: {e.Message}"); }
            }   // SysCall "TED:shop <group>" / "BNW:shop <group>" (the mod's merchants)
            if (TedMode) KitRules();
            if (TedMode) TedEnemyAi.Apply(H, Path.Combine(DataDir, "ted_ai.json"), Path.Combine(DataDir, "ted_ex_ai.json"),
                Config.Bind("Battle", "ScriptStatusEffects", false,
                    "Monster scripts may set/clear statuses on themselves and end the battle (SNES AI FB 0B/0C/02; T-Edition's boss deaths). " +
                    "On anyway when ted_ai.json was built for them (its \"status_effects\": the bosses on their T-Edition scripts, audit B5).").Value);
            L.LogInfo($"T-Edition {Version}: data {(TedMode ? "installed" : "missing")}, " +
                      $"{(DataError == null ? $"ted_data {D.Version} ({D.Items.Count} items, {D.NewWeapons.Count} new weapon rows, {D.HalfIgnoreDefense.Count} half-damage monsters)" : DataError)}; " +
                      $"load {clock.Elapsed.TotalSeconds:0.00} s");
            AddComponent<TedRunner>();
        }
    }

    // The kit's SNES battle modules T-Edition runs on (PrKit/Ff6): the SNES's ATB fill and command waits
    // (rules 45-46: T-Edition's wait table, Haste x144, monster speed term 4), the SNES status clock (cadence
    // of rule 50; rule 51's Stop 9 steps and rule 45's Haste add 96), no hit-rate change from target statuses
    // (rule 21: both lists emptied), no esper level-up bonuses (rule 4: every esper answers "none"). Each
    // plugin compiles its own copy of the kit, so these values never reach another mod.
    public partial class Plugin
    {
        static void KitRules()
        {
            System.Func<bool> on = () => TedMode;
            try
            {
                foreach (var (cmd, wait) in StatusMath.CommandWaits) PrKit.Ff6.SnesAtb.SnesCommandWait[cmd] = wait;
                // rule 45: Haste x144 (= $3ADD 96 x 1.5) and monsters (Speed + 20) x (255 - 4 x battle speed)
                PrKit.Ff6.SnesAtb.HasteK = StatusMath.AtbHasteK;
                PrKit.Ff6.SnesAtb.MonsterSpeedTerm = StatusMath.MonsterSpeedTerm;
                TedLog.Rule(45, "", () => $"ATB: Haste x{StatusMath.AtbHasteK}, monster speed term {StatusMath.MonsterSpeedTerm} (C2/2482, C2/09DA)");
                PrKit.Ff6.SnesAtb.On = on;
                PrKit.Ff6.SnesAtb.Tag = "[ted]";
                PrKit.Ff6.SnesAtb.Patch(H);
            }
            catch (Exception e) { L.LogError($"[ted] kit ATB: {e.Message}"); }
            try
            {
                // rules 45 / 51: the status clock's Haste add 96 (vanilla 84), Stop 9 steps (vanilla 18)
                PrKit.Ff6.SnesStatusClock.AddHaste = StatusMath.AddHaste;
                PrKit.Ff6.SnesStatusClock.StopSteps = StatusMath.StopSteps;
                TedLog.Rule(51, "", () => $"status clock: Stop {StatusMath.StopSteps} steps, Haste add {StatusMath.AddHaste}");
                PrKit.Ff6.SnesStatusTicks.On = on;
                PrKit.Ff6.SnesStatusTicks.Tag = "[ted]";
                PrKit.Ff6.SnesStatusTicks.Patch(H);
            }
            catch (Exception e) { L.LogError($"[ted] kit status clock: {e.Message}"); }
            try
            {
                var none = new Dictionary<int, int>();
                foreach (var id in D.EsperBonusVanilla.Keys) none[id] = 0xFF;
                IReadOnlyDictionary<int, int> vanilla = D.EsperBonusVanilla;
                PrKit.Ff6.SnesEsperBonus.Seed = () => TedMode && none.Count > 0 ? none : null;
                PrKit.Ff6.SnesEsperBonus.Vanilla = () => TedMode && vanilla.Count > 0 ? vanilla : null;
                PrKit.Ff6.SnesEsperBonus.Tag = "[ted]";
                PrKit.Ff6.SnesEsperBonus.Patch(H);
                TedLog.Rule(4, "", () => $"espers give no level-up bonus ({none.Count} espers answer none)");
            }
            catch (Exception e) { L.LogError($"[ted] kit esper bonuses: {e.Message}"); }
            RelicPenalties();
        }

        // rule 14: the Offering halves every physical hit by a character (the SNES's, unchanged in T-Edition); the
        // Genji Glove's vanilla -25% (a wearer NOT dual wielding) only on a plain Fight (C2/2C06 -> C2/65E0)
        static void RelicPenalties()
        {
            try
            {
                PrKit.Ff6.SnesRelicPenalties.Apply(H, new PrKit.Ff6.SnesRelicPenaltiesMod
                {
                    Name = "T-Edition", Offering = true, Genji = PrKit.Ff6.GenjiRule.SnesBugPlainFight, Enabled = () => TedMode,
                });
            }
            catch (Exception e) { L.LogError($"[ted] kit relic penalties: {e.Message}"); }
        }

        // first frames: the game's static lists exist (their static constructors have run)
        internal static void FirstFrames()
        {
            if (!TedMode || hitRatesDone) return;
            hitRatesDone = true;
            try
            {
                var plus = new List<Last.Defaine.ConditionType>();
                var minus = new List<Last.Defaine.ConditionType>();
                var p = Last.Battle.CalcExecuteFF6.HitRatePlusConditions;
                var m = Last.Battle.CalcExecuteFF6.HitRateMinusConditions;
                if (p != null) foreach (var c in p) plus.Add(c);
                if (m != null) foreach (var c in m) minus.Add(c);
                var line = PrKit.Ff6.SnesHitRates.Fix("T-Edition", plus, minus);
                if (line != null) L.LogInfo(line);
                TedLog.Rule(21, "", () => "no hit-rate change from the target's statuses (both lists emptied)");
            }
            catch (Exception e) { L.LogError($"[ted] hit-rate lists: {e.Message}"); }
        }
        static bool hitRatesDone;
    }

    // A rule's first use goes to the log once ("[ted] rule 6 ..."); `tedrules` lists what has fired
    static class TedLog
    {
        static readonly Dictionary<int, int> fired = new Dictionary<int, int>();
        static readonly object Lock = new object();

        internal static void Rule(int rule, string key, Func<string> text)
        {
            lock (Lock) fired[rule] = fired.TryGetValue(rule, out var n) ? n + 1 : 1;
            Hooks.NoteOnce($"ted-rule-{rule}-{key}", () => $"[ted] rule {rule}: {text()}");
        }

        internal static int Count(int rule)
        {
            lock (Lock) return fired.TryGetValue(rule, out var n) ? n : 0;
        }

        internal static string Summary()
        {
            lock (Lock)
            {
                if (fired.Count == 0) return "no rule has fired yet";
                var parts = new List<string>();
                var keys = new List<int>(fired.Keys);
                keys.Sort();
                foreach (var k in keys) parts.Add($"{k} x{fired[k]}");
                return "rules fired: " + string.Join(", ", parts);
            }
        }
    }

    // per-frame driver (its own class name: IL2CPP registers runners by name)
    public class TedRunner : MonoBehaviour
    {
        public TedRunner(IntPtr ptr) : base(ptr) { }

        void Update()
        {
            try
            {
                Plugin.FirstFrames();
                Plugin.Features?.Update();
                if (Plugin.TedMode) PrKit.Ff6.SnesStatusTicks.Track();
                TedEnemyAi.Update();
                TedMusic.Update();
                TedCostumes.Update();
                TedSosReflect.Update();
                TedMagitek.Update();
                TedTimers.Update();   // T-Edition's field timers (TED:timer_start)
                TedMpCritical.Update();   // audit I3: the PR's MP Critical weapon list -> T-Edition's
                TedRageOrder.Update();   // audit U10: Gau's stored Rages in name order
                PrKit.Ff6.SnesMpNumbers.Update();
                TedHarness.Update();
            }
            catch (Exception e) { Hooks.WarnOnce("ted-update", e); }
        }

        void OnGUI()
        {
            try { Plugin.Features?.OnGUI(); TedTimers.OnGUI(); }
            catch (Exception e) { Hooks.WarnOnce("ted-gui", e); }
        }
    }
}
