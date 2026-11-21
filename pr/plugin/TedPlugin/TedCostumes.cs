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
    //    ("costume:Gogo-battle" = costumes/Gogo_chameleon_<0-9>); a wearer of Imp Token (slot 277, the kappa amulet) or
    //    Piggy Patch (278) is drawn as a kappa / pig ("relic:<Name>" = costumes/<Name>_kappa / _pig); cleared at the end.
    // The layers need the kit's ArtSwap.SetLayer (staged as PrKit/ArtSwap.layers.cs.wip until WC's kit freeze ends):
    // SetLayer stays null until then and the choices are only stored and logged. Characters already on the map keep
    // their frames until the map reloads (the SNES dressing room reloads it).
    static class TedCostumes
    {
        public static readonly string[] Names = { "Terra", "Locke", "Cyan", "Shadow", "Edgar", "Sabin", "Celes", "Strago",
                                                  "Relm", "Setzer", "Mog", "Gau", "Gogo", "Umaro" };
        public const int Count = 14, GogoIndex = 12, ChameleonCostume = 1, ChameleonForms = 10;
        // the costume relics, by T-Edition item slot (ted_items.json / ted_data "items"; the second bank: armor.html's
        // relics 115 / 116, Mato's "Imp Token" and "Piggy Patch"): rows and names may move, slots don't
        public const int KappaSlot = 277, PigSlot = 278;
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
            LoadTitles(Path.Combine(dataDir, "ted_costumes.json"));
        }

        // audit D7: the job title follows the worn costume: the part of its name after the colon ("Silk Dress: Hybrid" ->
        // "Hybrid"; data/ted_costumes.json, installed beside the plugin's data). The character's job name text
        // (MSG_JOB_NAME_<job>, one job per character) is set at runtime; costume 0 puts the game's own back.
        static readonly string[][] titles = new string[Count][];
        static readonly int[][] falconSongs = new int[Count][];

        // audit D6: SysCall "TED:falconsong [var]" from the Falcon's entrance event (SNES map 12, EB/0EA0): the party
        // leader's worn costume picks the Falcon's song (data/ted_costumes.json falcon_bgm: a vanilla song's own PR track, a T-Edition song's PR
        // bgm 1000 + song, which TedMusic plays). Map-local <var> (default 0) = 1 when a costume song started, 0 when the
        // leader wears no costume (the event then plays its own per-character song).
        public static void FalconSong(int var)
        {
            int played = 0;
            try
            {
                var udm = Last.Management.UserDataManager.Instance();
                var corps = udm?.GetCorpsListClone();
                int leader = -1;
                if (corps != null)
                    foreach (var e in corps)
                    {
                        if (e == null || e.CharacterId == 0) continue;
                        foreach (var o in udm.OwnedCharacterList) if (o != null && o.Id == e.CharacterId) { leader = o.characterStatusId - 1; break; }
                        break;
                    }
                if (leader >= 0 && leader < Count)
                {
                    int k = Get(leader);
                    int song = k > 0 && falconSongs[leader] != null && k < falconSongs[leader].Length ? falconSongs[leader][k] : 0;
                    if (song > 0)
                    {
                        Last.Management.AudioManager.Instance?.PlayBgm(song);
                        played = 1;
                        TedLog.Rule(0, "falcon", () => $"the Falcon plays {Names[leader]}'s costume song {song:X2} (audit D6)");
                    }
                }
            }
            catch (Exception e) { Hooks.WarnOnce("ted-falcon-song", e); }
            Last.Interpreter.DataStorage.Instance?.Set(Last.Interpreter.DataStorage.Category.kMapLocalVariable, var, played);
        }
        static readonly Dictionary<string, string> originalTitle = new Dictionary<string, string>();

        static void LoadTitles(string path)
        {
            if (!File.Exists(path)) return;
            try
            {
                using var doc = System.Text.Json.JsonDocument.Parse(File.ReadAllText(path));
                var chars = doc.RootElement.GetProperty("characters");
                int i = 0;
                foreach (var ch in chars.EnumerateArray())
                {
                    if (i >= Count) break;
                    var list = new List<string> { null };
                    var songs = new List<int> { 0 };
                    foreach (var co in ch.GetProperty("costumes").EnumerateArray())
                    {
                        songs.Add(co.TryGetProperty("falcon_bgm", out var fs) && fs.ValueKind == System.Text.Json.JsonValueKind.Number ? fs.GetInt32() : 0);
                        var name = co.TryGetProperty("name", out var n) ? n.GetString() ?? "" : "";
                        int colon = name.LastIndexOf(':');
                        list.Add(colon >= 0 ? name.Substring(colon + 1).Trim() : null);
                    }
                    falconSongs[i] = songs.ToArray();
                    titles[i++] = list.ToArray();
                }
            }
            catch (Exception e) { Plugin.L.LogWarning($"[ted] costume titles: {e.Message}"); }
        }

        static void Title(int c, int k)
        {
            try
            {
                var owned = Last.Management.UserDataManager.Instance()?.OwnedCharacterList;
                if (owned == null) return;
                int job = 0;
                foreach (var o in owned) if (o != null && o.characterStatusId == c + 1) { job = o.JobId; break; }
                if (job <= 0) return;
                string key = $"MSG_JOB_NAME_{job:D2}";
                if (!originalTitle.ContainsKey(key)) originalTitle[key] = GameText.Get(key);
                string want = k > 0 && titles[c] != null && k < titles[c].Length && !string.IsNullOrEmpty(titles[c][k]) ? titles[c][k] : originalTitle[key];
                if (want != null && GameText.Get(key) != want)
                {
                    GameText.Set(key, want);
                    TedLog.Rule(0, $"title-{c}", () => $"{Names[c]}'s title follows the costume: '{want}' (audit D7)");
                }
            }
            catch (Exception e) { Hooks.WarnOnce("ted-costume-title", e); }
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
            Title(c, k);
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
