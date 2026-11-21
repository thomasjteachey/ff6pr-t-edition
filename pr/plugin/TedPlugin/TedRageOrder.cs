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
