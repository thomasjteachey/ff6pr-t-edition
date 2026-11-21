using System;
using System.Collections.Generic;
using HarmonyLib;
using Last.Data.Master;
using Last.Data.User;
using PrKit;

namespace TEdition.PR
{
    // Audit U10: Gau's Rage list in alphabetical order (T-Edition). The PR orders a character's ability lists in
    // OwnedCharacterClient.Sort(characterId, command, list, OrderlyType), which returns {command: sorted list}; for the
    // Rage command (23) a postfix sorts that list by the abilities' names as the game shows them. (That the battle menu
    // takes its list from this sort is inferred: tedrules shows the rule when it fires.)
    static class TedRageOrder
    {
        const int RageCommand = 23;
        static Dictionary<int, string> names;

        public static void Patch(Harmony h) =>
            Hooks.Patch(h, typeof(Last.Management.OwnedCharacterClient), "Sort", typeof(TedRageOrder), postfix: nameof(Sort_Postfix));

        static string Name(int ability)
        {
            if (names == null)
            {
                names = new Dictionary<int, string>();
                var contents = Master.All<Content>();
                if (contents != null)
                    foreach (var kv in contents)
                        if (kv.Value != null && kv.Value.TypeId == 4)
                            names[kv.Value.TypeValue] = TEdition.Rules.TedData.Plain(GameText.Get(kv.Value.MesIdName) ?? "");
            }
            return names.TryGetValue(ability, out var n) ? n : "";
        }

        // The battle menu lists Gau's Rages in his stored order (the Sort above runs only when the player picks an order in
        // the field menu), so the stored list is kept sorted too: outside battle, every 2 s, his Rage entries (ted_data
        // known_bits "rage" abilities) are put in name order in the slots they already hold; other abilities stay put.
        static float next;
        static HashSet<int> rages;
        internal static int Reordered;

        public static void Update()
        {
            if (!Plugin.TedMode || UnityEngine.Time.unscaledTime < next) return;
            next = UnityEngine.Time.unscaledTime + 2f;
            try
            {
                var bm = Last.Battle.BattlePlugManager.Instance();
                if (bm != null && bm.IsBattle()) return;
                if (rages == null)
                {
                    if (!Plugin.D.KnownBits.TryGetValue("rage", out var ids)) return;
                    rages = new HashSet<int>(ids);
                }
                var owned = Last.Management.UserDataManager.Instance()?.OwnedCharacterList;
                if (owned == null) return;
                foreach (var c in owned)
                {
                    if (c == null || c.characterStatusId != 12 || c.OwnedAbilityList == null) continue;   // Gau
                    var list = c.OwnedAbilityList;
                    var slots = new List<int>();
                    var items = new List<OwnedAbility>();
                    for (int i = 0; i < list.Count; i++)
                        if (list[i]?.Ability != null && rages.Contains(list[i].Ability.Id)) { slots.Add(i); items.Add(list[i]); }
                    if (items.Count < 2) continue;
                    var sorted = new List<OwnedAbility>(items);
                    sorted.Sort((x, y) => string.Compare(Name(x.Ability.Id), Name(y.Ability.Id), StringComparison.CurrentCultureIgnoreCase));
                    bool same = true;
                    for (int k = 0; k < items.Count && same; k++) same = items[k].Pointer == sorted[k].Pointer;
                    if (same) continue;
                    for (int k = 0; k < slots.Count; k++) list[slots[k]] = sorted[k];
                    Reordered++;
                    TedLog.Rule(0, "rage-order-stored", () => $"Gau's {slots.Count} Rages stored in name order (audit U10)");
                }
            }
            catch (Exception e) { Hooks.WarnOnce("ted-rage-order-stored", e); }
        }

        public static void Sort_Postfix(Command command, ref Il2CppSystem.Collections.Generic.Dictionary<Command, Il2CppSystem.Collections.Generic.List<OwnedAbility>> __result)
        {
            try
            {
                if (!Plugin.TedMode || command == null || command.Id != RageCommand || __result == null) return;
                foreach (var kv in __result)
                {
                    var list = kv.Value;
                    if (list == null || list.Count < 2) continue;
                    var items = new List<OwnedAbility>();
                    foreach (var a in list) items.Add(a);
                    items.Sort((x, y) => string.Compare(Name(x?.Ability?.Id ?? 0), Name(y?.Ability?.Id ?? 0), StringComparison.CurrentCultureIgnoreCase));
                    list.Clear();
                    foreach (var a in items) list.Add(a);
                }
                TedLog.Rule(0, "rage-order", () => "Gau's Rage list sorted by name (audit U10)");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-rage-order", e); }
        }
    }
}
