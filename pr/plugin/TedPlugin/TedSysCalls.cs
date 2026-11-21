using System;
using HarmonyLib;
using Last.Interpreter;
using Last.Interpreter.Instructions;
using PrKit;

namespace TEdition.PR
{
    // SysCall "TED:<name>" lines in T-Edition's scripts (ted-ex's boss room, tools/ted_ex*.py), and "BNW:<name>"
    // ones, which the shared porter writes for a mod's added merchants (tools/port_merchants.shop_script) and
    // sellers (port_bnw_mechanics): answered while T-Edition's data is installed (its mods never load beside
    // Brave New World), as BnwPlugin/ShopCalls.cs answers them for BNW:
    //   shop <group>       a shop for that product group through the game's own opener
    //                      SystemCall.Current.OpenShopCommon(group, isFirstClock): 1 while the shop is open
    //                      (the script engine repeats the call), 0 once it's closed
    //   pay <gil>          map-local 0 = 1 and the gil taken if the party has it, else 0
    //   unequip <id> / optimize <id>   a character's equipment back to the bag / its best equipment
    //   veldt_open <party>...           Veldt entries opened as if those parties were fought
    //   counter <n> [var]  T-Edition's success counter n (word n of 7E/1E70) into map-local variable var (0)
    //   bump <n>           counter n + 1 (capped as the battle code caps it)
    // Every other call is the game's.
    static class TedSysCalls
    {
        internal static int Opened;   // tests: shops opened

        public static void Apply(Harmony h)
        {
            var m = AccessTools.Method(typeof(External.Misc), "SystemCall");
            if (m == null) { Kit.Warn("[ted] no External.Misc.SystemCall: T-Edition's merchants are off"); return; }
            h.Patch(m, prefix: new HarmonyMethod(typeof(TedSysCalls), nameof(SystemCall_Prefix)));
        }

        public static bool SystemCall_Prefix(MainCore mc, ref int __result)
        {
            if (!Plugin.TedMode) return true;
            string name;
            try
            {
                var sv = mc?.op?.sValues;
                name = sv != null && sv.Length > 0 ? sv[0] : null;
            }
            catch { return true; }
            if (name == null || !(name.StartsWith("TED:") || name.StartsWith("BNW:"))) return true;
            __result = 0;
            try
            {
                var parts = name.Substring(4).Split(' ');
                if (parts.Length == 2 && parts[0] == "shop" && int.TryParse(parts[1], out int group))
                {
                    bool first = mc.IsFirstClock();
                    __result = global::Last.Interpreter.Instructions.SystemCall.Current.OpenShopCommon(group, first);
                    if (first)
                    {
                        Opened++;
                        Hooks.NoteOnce("ted-shop-" + group, () => $"[ted] shop {group} opened ({name})");
                    }
                }
                else if (parts.Length == 2 && parts[0] == "pay" && int.TryParse(parts[1], out int price))
                {
                    var udm = global::Last.Management.UserDataManager.Instance();
                    bool paid = udm != null && udm.OwendGil >= price;
                    if (paid) new global::Last.Management.OwnedItemClient().RemoveGil(price);
                    DataStorage.Instance?.Set(DataStorage.Category.kMapLocalVariable, 0, paid ? 1 : 0);
                    Kit.Info($"[ted] pay {price}: {(paid ? "paid" : "not enough gil")} (now {udm?.OwendGil})");
                }
                else if (parts.Length == 2 && (parts[0] == "unequip" || parts[0] == "optimize") && int.TryParse(parts[1], out int who))
                {
                    var udm = global::Last.Management.UserDataManager.Instance();
                    global::Last.Data.User.OwnedCharacterData oc = null;
                    if (udm?.OwnedCharacterList != null) foreach (var x in udm.OwnedCharacterList) if (x?.characterStatusId == who) oc = x;
                    if (oc == null) Kit.Info($"[ted] {parts[0]} {who}: no such character yet");
                    else if (parts[0] == "unequip") new global::Last.Management.OwnedCharacterClient().RemoveAllEquip(oc.Id);
                    else global::Last.Interpreter.Instructions.SystemCall.Current.SetStrongestEquipCommon(who);
                }
                else if (parts.Length >= 2 && parts[0] == "veldt_open")
                {
                    var beast = global::Last.Map.Encount.BeastFieldEncount.Instance();
                    if (beast == null) Kit.Warn("[ted] veldt_open: no BeastFieldEncount");
                    else
                        for (int i = 1; i < parts.Length; i++)
                            if (int.TryParse(parts[i], out int party)) beast.EncounterMonsterParty(party);
                }
                else if (parts.Length >= 2 && parts[0] == "counter" && int.TryParse(parts[1], out int which))
                {
                    // T-Edition's success counters (word n of 7E/1E70: 0 Steal, 1 Twin Fang, 2 Runic, 3 Sketch, 5 Slot,
                    // 6 Snowstorm, 7 Mimic) for its events' compares (commands 67.. on 1E70; the Achievement Room's
                    // NPCs): into map-local variable <var> (default 0), where the translated script branches on it
                    int var = parts.Length > 2 && int.TryParse(parts[2], out int v) ? v : 0;
                    int value = which >= 0 && which < TedCounters.Count ? TedCounters.Get(which) : 0;
                    DataStorage.Instance?.Set(DataStorage.Category.kMapLocalVariable, var, value);
                    Hooks.NoteOnce($"ted-counter-{which}", () => $"[ted] {name}: counter {which} = {value} -> map-local {var}");
                }
                else if (parts.Length == 2 && parts[0] == "bump" && int.TryParse(parts[1], out int bump) && bump >= 0 && bump < TedCounters.Count)
                    TedCounters.Bump(bump);
                else if (parts.Length == 3 && parts[0] == "costume" && int.TryParse(parts[1], out int costumeOf) && int.TryParse(parts[2], out int k))
                    TedCostumes.Wear(costumeOf, k);   // the dressing room (TedCostumes.cs)
                else Kit.Warn($"[ted] unknown call {name}");
            }
            catch (Exception e) { __result = 0; Hooks.WarnOnce("TedSysCalls", e); }
            return false;
        }
    }
}
