using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using Last.Interpreter;
using PrKit;

namespace TEdition.PR
{
    // ted-events' ted_flags.json (BepInEx/TEdition; tools/ted_events.py ted_flags): named PR flags as
    // [category, index], the category a DataStorage name ("ScenarioFlag2", "TreasureFlag3") or a number:
    //   "wor", "humbaba_scared_off", "humbaba_returns", "humbaba" (I18), "engine_story_bits" (a list),
    //   "ngplus_clear" / "ngplus_set" (lists: New Game+'s story-bit reset, N1-N3).
    static class TedFlags
    {
        static readonly Dictionary<string, List<(DataStorage.Category Cat, int Idx)>> flags =
            new Dictionary<string, List<(DataStorage.Category, int)>>();
        internal static string State = "no ted_flags.json";

        public static void Load(string path)
        {
            if (!File.Exists(path)) return;
            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(path));
                foreach (var p in doc.RootElement.EnumerateObject())
                {
                    var list = new List<(DataStorage.Category, int)>();
                    if (p.Value.ValueKind == JsonValueKind.Object)   // {"1BC": [cat, idx], ...}: the whole set, and each by name
                    {
                        foreach (var q in p.Value.EnumerateObject())
                        {
                            if (q.Value.ValueKind != JsonValueKind.Array) continue;
                            var one = new List<(DataStorage.Category, int)>();
                            Add(one, q.Value);
                            flags[p.Name + "." + q.Name] = one;
                            list.AddRange(one);
                        }
                        flags[p.Name] = list;
                        continue;
                    }
                    if (p.Value.ValueKind != JsonValueKind.Array) continue;
                    if (p.Value.GetArrayLength() == 2 && p.Value[0].ValueKind != JsonValueKind.Array)
                        Add(list, p.Value);
                    else
                        foreach (var e in p.Value.EnumerateArray()) if (e.ValueKind == JsonValueKind.Array) Add(list, e);
                    flags[p.Name] = list;
                }
                State = $"{flags.Count} named flags";
                Plugin.L.LogInfo($"[ted] ted_flags.json: {State}");
            }
            catch (Exception e) { State = "unreadable: " + e.Message; Plugin.L.LogWarning($"[ted] {path}: {e.Message}"); }
        }

        static void Add(List<(DataStorage.Category, int)> list, JsonElement pair)
        {
            if (pair.GetArrayLength() != 2) return;
            var c = pair[0];
            DataStorage.Category cat;
            if (c.ValueKind == JsonValueKind.Number) cat = (DataStorage.Category)c.GetInt32();
            else if (!Enum.TryParse("k" + c.GetString(), out cat) && !Enum.TryParse(c.GetString(), out cat)) return;
            list.Add((cat, pair[1].GetInt32()));
        }

        public static bool Has(string name) => flags.TryGetValue(name, out var l) && l.Count > 0;
        public static IReadOnlyList<(DataStorage.Category Cat, int Idx)> List(string name) =>
            flags.TryGetValue(name, out var l) ? l : (IReadOnlyList<(DataStorage.Category, int)>)Array.Empty<(DataStorage.Category, int)>();

        public static bool IsSet(string name)
        {
            if (!flags.TryGetValue(name, out var l) || l.Count == 0) return false;
            var (cat, idx) = l[0];
            return (DataStorage.Instance?.Get(cat, idx) ?? 0) != 0;
        }

        public static void SetAll(string name, int value)
        {
            var ds = DataStorage.Instance;
            if (ds == null) return;
            foreach (var (cat, idx) in List(name)) ds.Set(cat, idx, value);
        }
    }
}
