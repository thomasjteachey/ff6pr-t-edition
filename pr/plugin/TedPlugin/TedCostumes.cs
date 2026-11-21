using System;
using System.Collections.Generic;
using System.IO;
using Last.Battle;
using Last.Data.User;
using PrKit;

namespace TEdition.PR
{
    // T-Edition's costumes (bc-sprites' art: BepInEx/TEdition/costumes, tools/ted_art.py costumes; data/ted_costumes.json):
    //  * one costume per character (k 0 = the default, 1-4 the dressing room's), picked by the dressing room's
    //    SysCall "TED:costume <char 0-13> <k>" (ted-events translates the SNES event's graphic slot command 37 into
    //    it), kept in T-Edition's save (a "TEC1" marker block in OwnedKeyWaordList, ModSaves "TEdition"), put on as
    //    the ArtSwap layer "costume:<Name>" = costumes/<Name>_<k> (none for 0) and again whenever a save is loaded;
    //  * battle only: Gogo in the Chameleon Robe (his costume 1) takes one of 10 forms each battle
    //    ("costume:Gogo-battle" = costumes/Gogo_chameleon_<0-9>); a wearer of Kappa's Favor (item $115) or Piggy's
    //    Badge ($116) is drawn as a kappa / pig ("relic:<Name>" = costumes/<Name>_kappa / _pig); cleared at the end.
    // The layers need the kit's ArtSwap.SetLayer (staged as PrKit/ArtSwap.layers.cs.wip until WC's kit freeze ends):
    // SetLayer stays null until then and the choices are only stored and logged. Characters already on the map keep
    // their frames until the map reloads (the SNES dressing room reloads it).
    static class TedCostumes
    {
        public static readonly string[] Names = { "Terra", "Locke", "Cyan", "Shadow", "Edgar", "Sabin", "Celes", "Strago",
                                                  "Relm", "Setzer", "Mog", "Gau", "Gogo", "Umaro" };
        public const int Count = 14, GogoIndex = 12, ChameleonCostume = 1, ChameleonForms = 10;
        public const int KappaSlot = 0x115, PigSlot = 0x116;
        const int Marker = 0x54454331;   // "TEC1"
        public static Func<string, string, string> SetLayer;   // = ArtSwap.SetLayer once the kit has layers (returns a log line)
        public static string Dir, State = "nothing applied yet";
        static readonly int[] applied = new int[Count];
        static readonly List<string> battleLayers = new List<string>();
        static bool inBattle;
        static int frames;
        static readonly Random Rng = new Random();

        public static void Init(string dataDir)
        {
            Dir = Path.Combine(dataDir, "costumes");
            for (int i = 0; i < Count; i++) applied[i] = -1;
        }

        static Il2CppSystem.Collections.Generic.List<int> List() => Last.Management.UserDataManager.Instance()?.OwnedKeyWaordList;

        static int Find(Il2CppSystem.Collections.Generic.List<int> list)
        {
            for (int i = 0; i + 1 + Count <= list.Count; i++)
                if (list[i] == Marker) return i;
            return -1;
        }

        public static int Get(int c)
        {
            var list = List();
            if (list == null || c < 0 || c >= Count) return 0;
            int at = Find(list);
            return at < 0 ? 0 : list[at + 1 + c];
        }

        // the dressing room's SysCall
        public static void Wear(int c, int k)
        {
            if (c < 0 || c >= Count || k < 0 || k > 4) { Kit.Warn($"[ted] costume {c} {k}: out of range"); return; }
            var list = List();
            if (list == null) return;
            int at = Find(list);
            if (at < 0)
            {
                at = list.Count;
                list.Add(Marker);
                for (int i = 0; i < Count; i++) list.Add(0);
            }
            list[at + 1 + c] = k;
            Apply(c, k);
        }

        static void Layer(string name, string folder)
        {
            if (folder != null && !Directory.Exists(folder)) { Kit.Warn($"[ted art] {folder} missing"); folder = null; }
            if (SetLayer == null)
            {
                Hooks.NoteOnce($"ted-costume-nolayers-{name}", () => $"[ted art] {name} -> {(folder == null ? "default" : Path.GetFileName(folder))} (stored; the kit's ArtSwap layers aren't in yet)");
                return;
            }
            var line = SetLayer(name, folder);
            if (!string.IsNullOrEmpty(line)) Plugin.L.LogInfo($"[ted art] {line}");
        }

        static void Apply(int c, int k)
        {
            applied[c] = k;
            Layer("costume:" + Names[c], k == 0 ? null : Path.Combine(Dir, $"{Names[c]}_{k}"));
            State = $"{Names[c]} costume {k}";
        }

        // every frame (TedRunner): the save's choices (a loaded save) and the battle-only looks
        public static void Update()
        {
            if (!Plugin.TedMode || Dir == null) return;
            if (++frames % 30 == 0 && List() != null)
                for (int c = 0; c < Count; c++)
                {
                    int k = Get(c);
                    if (k != applied[c]) Apply(c, k);
                }
            var battle = BattlePlugManager.Instance();
            bool now = battle != null && battle.IsBattle();
            if (now && !inBattle) BattleStart(battle);
            else if (!now && inBattle) BattleEnd();
            inBattle = now;
        }

        static void BattleStart(BattlePlugManager battle)
        {
            var players = battle.GetPlayerUnits();
            if (players == null) return;
            int kappa = Plugin.D.BySlot(KappaSlot)?.Content ?? 0, pig = Plugin.D.BySlot(PigSlot)?.Content ?? 0;
            foreach (var p in players)
            {
                var c = p?.TryCast<BattlePlayerData>()?.ownedCharacterData;
                if (c == null || c.characterStatusId < 1 || c.characterStatusId > Count) continue;
                int i = c.characterStatusId - 1;
                if (i == GogoIndex && Get(i) == ChameleonCostume)
                    BattleLayer("costume:Gogo-battle", Path.Combine(Dir, $"Gogo_chameleon_{Rng.Next(ChameleonForms)}"));
                string relic = Wears(c, kappa) ? "kappa" : Wears(c, pig) ? "pig" : null;
                if (relic != null) BattleLayer("relic:" + Names[i], Path.Combine(Dir, $"{Names[i]}_{relic}"));
            }
        }

        static void BattleLayer(string name, string folder)
        {
            battleLayers.Add(name);
            Layer(name, folder);
        }

        static void BattleEnd()
        {
            foreach (var name in battleLayers) Layer(name, null);
            battleLayers.Clear();
        }

        static bool Wears(OwnedCharacterData c, int content)
        {
            if (content <= 0 || c?.EquipmentData == null) return false;
            foreach (var kv in c.EquipmentData)
                if (kv.Value != null && kv.Value.ContentId == content) return true;
            return false;
        }

        public static string Summary()
        {
            var parts = new List<string>();
            for (int c = 0; c < Count; c++) if (Get(c) != 0) parts.Add($"{Names[c]} {Get(c)}");
            return $"costumes: {(parts.Count == 0 ? "all default" : string.Join(", ", parts))}; layers {(SetLayer == null ? "not in the kit yet" : "on")}; {State}";
        }
    }
}
