using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using Last.Interpreter;
using PrKit;

namespace TEdition.PR
{
    // T-Edition's own word compares and sets (ted-events' SysCalls for event commands 67 68 69 6D 6E 6F A4 FC / 83 ED):
    //   TED:cmp <area> <word> <value>  the 16-bit word at 7E/<area> + 2 x word (or a ROM table) against value:
    //                                  MapLocalVariable 5 = equal, 6 = greater, 7 = less (1 / 0)
    //   TED:set <area> <word> <value>
    // Areas (hex): 1E70 the success counters (TedCounters: the PR's global variables); 1DD0 and 1E40 T-Edition's own words
    // (kept in a "TED2" block of OwnedKeyWaordList, in the save); 1300 word 0 = the song playing << 8 (the Developer's
    // Room patrons; T-Edition's own songs by number, a game track reads 0); 58E4CC / 58E52A: ROM tables from
    // BepInEx/TEdition/ted_tables.json {"58E4CC": [words], ...}; anything else reads 0 (logged once per area).
    static class TedRam
    {
        const int Marker = 0x54454432;   // "TED2": then n, then n (key, value) pairs; key = area << 16 | word
        static Dictionary<int, int[]> tables = new Dictionary<int, int[]>();
        internal static string Last = "";

        public static void LoadTables(string path)
        {
            if (!File.Exists(path)) return;
            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(path));
                foreach (var p in doc.RootElement.EnumerateObject())
                {
                    if (p.Value.ValueKind != JsonValueKind.Array) continue;
                    int area = Convert.ToInt32(p.Name, 16);
                    var words = new List<int>();
                    foreach (var w in p.Value.EnumerateArray()) words.Add(w.GetInt32());
                    tables[area] = words.ToArray();
                }
                Plugin.L.LogInfo($"[ted] ted_tables.json: {tables.Count} ROM tables");
            }
            catch (Exception e) { Plugin.L.LogWarning($"[ted] {path}: {e.Message}"); }
        }

        static Il2CppSystem.Collections.Generic.List<int> List() => global::Last.Management.UserDataManager.Instance()?.OwnedKeyWaordList;

        static int Find(Il2CppSystem.Collections.Generic.List<int> l)
        {
            for (int i = 0; i + 1 < l.Count; i++)
                if (l[i] == Marker && i + 2 + 2 * l[i + 1] <= l.Count) return i;
            return -1;
        }

        static bool Stored(int area) => area == 0x1DD0 || area == 0x1E40;

        public static int Read(int area, int word)
        {
            if (area == 0x1E70) return TedCounters.Get(word);
            if (area == 0x1300 && word == 0)
            {
                int slot = PrKit.Snes.SnesBgm.Player?.CurrentSlot ?? -1;
                return slot < 0 ? 0 : (slot & 0xFF) << 8;
            }
            if (tables.TryGetValue(area, out var t)) return word >= 0 && word < t.Length ? t[word] : 0;
            if (Stored(area))
            {
                var l = List();
                if (l == null) return 0;
                int at = Find(l), key = area << 16 | word;
                if (at < 0) return 0;
                for (int k = 0; k < l[at + 1]; k++) if (l[at + 2 + 2 * k] == key) return l[at + 3 + 2 * k];
                return 0;
            }
            Hooks.NoteOnce($"ted-ram-{area:X}", () => $"[ted] T-Edition word area {area:X4} isn't known to TedPlugin: reads 0");
            return 0;
        }

        public static void Write(int area, int word, int value)
        {
            if (area == 0x1E70) { TedCounters.Set(word, value); return; }
            if (!Stored(area)) { Hooks.NoteOnce($"ted-ram-set-{area:X}", () => $"[ted] TED:set on area {area:X4}: not stored"); return; }
            var l = List();
            if (l == null) return;
            int at = Find(l), key = area << 16 | word;
            if (at < 0) { at = l.Count; l.Add(Marker); l.Add(0); }
            for (int k = 0; k < l[at + 1]; k++)
                if (l[at + 2 + 2 * k] == key) { l[at + 3 + 2 * k] = value; return; }
            int end = at + 2 + 2 * l[at + 1];
            l.Insert(end, key);
            l.Insert(end + 1, value);
            l[at + 1] = l[at + 1] + 1;
        }

        static int Hex(string s) => Convert.ToInt32(s, 16);
        static int Num(string s) => s.StartsWith("0x", StringComparison.OrdinalIgnoreCase) ? Convert.ToInt32(s.Substring(2), 16) : int.Parse(s);

        // SysCall parts after "cmp" / "set"
        public static void Cmp(string[] a)
        {
            int area = Hex(a[0]), word = Num(a[1]), value = Num(a[2]);
            int now = Read(area, word);
            var ds = DataStorage.Instance;
            ds?.Set(DataStorage.Category.kMapLocalVariable, 5, now == value ? 1 : 0);
            ds?.Set(DataStorage.Category.kMapLocalVariable, 6, now > value ? 1 : 0);
            ds?.Set(DataStorage.Category.kMapLocalVariable, 7, now < value ? 1 : 0);
            Last = $"cmp {area:X4}[{word}] = {now} vs {value}";
        }

        public static void Set(string[] a)
        {
            Write(Hex(a[0]), Num(a[1]), Num(a[2]));
            Last = $"set {a[0]}[{a[1]}] = {a[2]}";
        }
    }
}
