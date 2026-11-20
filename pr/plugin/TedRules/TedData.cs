using System;
using System.Collections.Generic;
using System.Text.Json;

namespace TEdition.Rules
{
    // What the plugin reads from the port (BepInEx/TEdition/ted_data.json, written by
    // tools/ted_plugin_data.py from T-Edition's ROM and the porter's output). No game types: the
    // offline tests (plugin/Ted.Tests) load the same file.
    public sealed class TedData
    {
        public sealed class Item
        {
            public int Slot;          // T-Edition's item slot (SNES id)
            public int Content;       // the PR content id the slot became
            public string Table = ""; // weapon | armor | item
            public int Row;           // its row in that table
            public string Name = "";  // the name the game should show (message text, icon tags included)
            public string How = "";   // item identity: pr, snes, close, new row, free row, own row
            public bool Moved;        // on another row than idmap's default for its slot
        }

        public sealed class Weapon
        {
            public int Row, Content, Attack;
            public string Name = "";
        }

        public string Version = "";
        public string Made = "";
        public int[] DropRates = { 68, 19, 8, 5 };
        public int DropMonsters;            // monsters the port gave 3 or 4 drop slots
        public readonly List<Item> Items = new List<Item>();
        public readonly List<Weapon> NewWeapons = new List<Weapon>();
        // PR monster ids with T-Edition's monster byte $12 bit 1 ($3C95 bit 1): half damage from
        // attacks that ignore defense (rule 9)
        public readonly HashSet<int> HalfIgnoreDefense = new HashSet<int>();
        public readonly List<int> HalfIgnoreDefenseNew = new List<int>();   // SNES ids 384+ (no PR row yet)
        // content ids by role (orichalcum, elven_darts, offering, ...): what the rules test for
        public readonly Dictionary<string, int> Named = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        // their rows in their table (weapon rows: the game keys Atma Weapon and Valiant Knife on them)
        public readonly Dictionary<string, int> Rows = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

        public Item BySlot(int slot)
        {
            foreach (var it in Items) if (it.Slot == slot) return it;
            return null;
        }

        // PR ability ids of the SNES spells the rules name (mysidian_rabbit, heal_force, flare_star)
        public readonly Dictionary<string, int> Abilities = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        public int Ability(string role) => Abilities.TryGetValue(role, out var id) ? id : 0;

        // vanilla's esper level-up bonus code (0-16, 0xFF none) by magicite content id (rule 4)
        public readonly Dictionary<int, int> EsperBonusVanilla = new Dictionary<int, int>();

        public int NamedContent(string role) => Named.TryGetValue(role, out var id) ? id : 0;
        public int NamedRow(string role) => Rows.TryGetValue(role, out var id) ? id : 0;

        public static TedData Parse(string json)
        {
            var d = new TedData();
            using var doc = JsonDocument.Parse(json);
            var r = doc.RootElement;
            d.Version = Str(r, "version");
            d.Made = Str(r, "made");
            if (r.TryGetProperty("drop_rates", out var dr) && dr.ValueKind == JsonValueKind.Array)
            {
                var list = new List<int>();
                foreach (var v in dr.EnumerateArray()) list.Add(v.GetInt32());
                d.DropRates = list.ToArray();
            }
            d.DropMonsters = Int(r, "drop_monsters");
            if (r.TryGetProperty("items", out var items))
                foreach (var e in items.EnumerateArray())
                    d.Items.Add(new Item
                    {
                        Slot = Int(e, "slot"), Content = Int(e, "content"), Table = Str(e, "table"), Row = Int(e, "row"),
                        Name = Str(e, "name"), How = Str(e, "how"), Moved = Bool(e, "moved"),
                    });
            if (r.TryGetProperty("new_weapons", out var weapons))
                foreach (var e in weapons.EnumerateArray())
                    d.NewWeapons.Add(new Weapon { Row = Int(e, "row"), Content = Int(e, "content"), Attack = Int(e, "attack"), Name = Str(e, "name") });
            if (r.TryGetProperty("half_ignore_defense", out var half))
            {
                if (half.TryGetProperty("pr", out var pr))
                    foreach (var v in pr.EnumerateArray()) d.HalfIgnoreDefense.Add(v.GetInt32());
                if (half.TryGetProperty("snes_new", out var nw))
                    foreach (var v in nw.EnumerateArray()) d.HalfIgnoreDefenseNew.Add(v.GetInt32());
            }
            if (r.TryGetProperty("named", out var named))
                foreach (var p in named.EnumerateObject())
                    if (p.Value.ValueKind == JsonValueKind.Number) d.Named[p.Name] = p.Value.GetInt32();
            if (r.TryGetProperty("abilities", out var abl))
                foreach (var p in abl.EnumerateObject())
                    if (p.Value.ValueKind == JsonValueKind.Number) d.Abilities[p.Name] = p.Value.GetInt32();
            if (r.TryGetProperty("esper_bonus_vanilla", out var eb))
                foreach (var pair in eb.EnumerateArray())
                    if (pair.GetArrayLength() == 2 && pair[0].ValueKind == JsonValueKind.Number)
                        d.EsperBonusVanilla[pair[0].GetInt32()] = pair[1].GetInt32();
            if (r.TryGetProperty("rows", out var rows))
                foreach (var p in rows.EnumerateObject())
                    if (p.Value.ValueKind == JsonValueKind.Number) d.Rows[p.Name] = p.Value.GetInt32();
            return d;
        }

        static string Str(JsonElement e, string key) =>
            e.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : "";

        static bool Bool(JsonElement e, string key) =>
            e.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.True;

        static int Int(JsonElement e, string key) =>
            e.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.Number ? v.GetInt32() : 0;

        // a name as the game draws it: icon tags (<IC_SWD>) and surrounding space off, for comparing
        public static string Plain(string text)
        {
            if (string.IsNullOrEmpty(text)) return "";
            var sb = new System.Text.StringBuilder(text.Length);
            int depth = 0;
            foreach (var ch in text)
            {
                if (ch == '<') { depth++; continue; }
                if (ch == '>' && depth > 0) { depth--; continue; }
                if (depth == 0) sb.Append(ch);
            }
            return sb.ToString().Trim();
        }
    }
}
