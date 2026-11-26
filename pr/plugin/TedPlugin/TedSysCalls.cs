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
            __result = Run(name, mc);
            return false;
        }

        // one TED:/BNW: call (mc: the script's interpreter; null from the harness's `tedcall`, where shops don't open)
        internal static int Run(string name, MainCore mc)
        {
            int __result = 0;
            try
            {
                var parts = name.Substring(4).Split(' ');
                if (parts.Length == 2 && parts[0] == "shop" && mc != null && int.TryParse(parts[1], out int group))
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
                else if ((parts.Length == 4 || parts.Length == 5) && parts[0] == "cmp") TedRam.Cmp(parts[1..]);   // T-Edition's word compares (TedRam.cs)
                else if (parts.Length == 4 && parts[0] == "set") TedRam.Set(parts[1..]);
                else if (parts.Length >= 1 && parts[0] == "ngplus")
                {
                    // audit N1-N3: New Game+ from the Beginner's House clerk (T-Edition's C0/DB58 -> DA9C): every story bit
                    // cleared (costume/dream bits included: costumes re-lock), the new-game bits set; items, characters,
                    // espers, gil, chests, play time and T-Edition's counters stay (its handler doesn't touch them). The
                    // PR flags are ted-events' (ted_flags.json "ngplus_clear" / "ngplus_set"); the clerk's translated
                    // script does the rest (the NPC show bits, the warp).
                    var clear = TedFlags.List("ngplus_clear");
                    var set = TedFlags.List("ngplus_set");
                    TedFlags.SetAll("ngplus_clear", 0);
                    TedFlags.SetAll("ngplus_set", 1);
                    Kit.Info($"[ted] New Game+: {clear.Count} story flags cleared, {set.Count} set");
                    TedLog.Rule(0, "ngplus", () => $"New Game+: {clear.Count} story flags cleared, {set.Count} set (audit N1-N3)");
                }
                else if (parts.Length >= 1 && parts[0] == "falconsong")
                    TedCostumes.FalconSong(parts.Length > 1 && int.TryParse(parts[1], out int fv) ? fv : 0);   // audit D6
                else if (parts.Length >= 1 && parts[0] == "song")
                {
                    // audit S7: the song playing (T-Edition's own: its pack slot, C5 song n = n, bank-43 song n = $100 + n;
                    // 0 when the game plays one of its own tracks) into map-local variable <var> (default 0), for the
                    // Developer's Room patrons who comment on the song
                    int var = parts.Length > 1 && int.TryParse(parts[1], out int sv) ? sv : 0;
                    int slot = TedRam.SongPlaying();
                    DataStorage.Instance?.Set(DataStorage.Category.kMapLocalVariable, var, slot);
                    Hooks.NoteOnce("ted-song", () => $"[ted] {name}: song {slot} -> map-local {var}");
                }
                else if (parts.Length >= 2 && parts[0] == "tiles")
                {
                    var line = TedTiles.Apply(parts[1..]);   // T-Edition's 73/74 tile changes (TedTiles.cs)
                    Hooks.NoteOnce($"ted-tiles-{TedTiles.Calls % 20}", () => $"[ted tiles] {name.Length} chars: {line}");
                }
                else if (parts.Length == 4 && parts[0] == "roster" && int.TryParse(parts[1], out int rc) && int.TryParse(parts[2], out int rbit)
                         && int.TryParse(parts[3], out int rvar))
                    TedRoster.Call(rc, rbit, rvar);   // T-Edition's $1850+c bit tests (TedRoster.cs)
                else if (parts.Length == 3 && parts[0] == "costume" && int.TryParse(parts[1], out int costumeOf) && int.TryParse(parts[2], out int k))
                    TedCostumes.Wear(costumeOf, k);   // the dressing room (TedCostumes.cs)
                else if (parts[0] == "timer_start")   // TedTimers.cs (a line per timer number: NPC-step timers restart often)
                {
                    var line = TedTimers.Start(parts[1..]);
                    Hooks.NoteOnce($"ted-timer-start-{(parts.Length > 1 ? parts[1] : "")}", () => $"[ted] {name}: {line}");
                }
                else if (parts[0] == "timer_reset") TedTimers.Reset(parts[1..]);
                else if (parts.Length == 2 && parts[0] == "gil" && int.TryParse(parts[1], out int gil) && gil > 0)
                {
                    // T-Edition's event command 84 (add gil; the PR's scripts only remove it): the game's own AddGil
                    new global::Last.Management.OwnedItemClient().AddGil(gil);
                    int now = global::Last.Management.UserDataManager.Instance()?.OwendGil ?? 0;
                    Hooks.NoteOnce($"ted-gil-{gil}", () => $"[ted] {name}: +{gil} gil (now {now})");
                }
                else if (parts.Length == 4 && parts[0] == "status" && (parts[1] == "add" || parts[1] == "remove"))
                {
                    // event commands 89 / 88 (status add / remove: char, 16-bit mask; audit E10): TED:status add|remove
                    // <char hex> <mask hex>; char 00-0F a character, 31-34 the party's member 1-4; mask: status bytes 1-2
                    var line = SetStatus(parts[1] == "add", Convert.ToInt32(parts[2], 16), Convert.ToInt32(parts[3], 16));
                    Hooks.NoteOnce($"ted-status-{parts[1]}-{parts[3]}", () => $"[ted] {name}: {line}");
                }
                else if (parts.Length >= 2 && parts[0] == "leadstatus")
                {
                    // T-Edition's event command EC (audit E10, Q20): "if the party lead has any status of <mask> (status
                    // byte 1: 01 Dark, 02 Zombie, 04 Poison, 08 Magitek, 10 Clear, 20 Imp, 40 Petrify, 80 Wound)":
                    // 1 / 0 into map-local variable <var> (default 0)
                    int mask = Convert.ToInt32(parts[1].StartsWith("0x", StringComparison.OrdinalIgnoreCase) ? parts[1].Substring(2) : parts[1], 16);
                    int var = parts.Length > 2 && int.TryParse(parts[2], out int lv) ? lv : 0;
                    bool has = LeadHas(mask);
                    DataStorage.Instance?.Set(DataStorage.Category.kMapLocalVariable, var, has ? 1 : 0);
                    Hooks.NoteOnce($"ted-leadstatus-{mask:X2}", () => $"[ted] {name}: lead has status {mask:X2}: {has} -> map-local {var}");
                }
                else if (parts.Length >= 2 && parts[0] == "timer_left" && int.TryParse(parts[1], out int tn))
                    DataStorage.Instance?.Set(DataStorage.Category.kMapLocalVariable, parts.Length > 2 && int.TryParse(parts[2], out int tv) ? tv : 0, TedTimers.SecondsLeft(tn));
                else Kit.Warn($"[ted] unknown call {name}");
            }
            catch (Exception e) { __result = 0; Hooks.WarnOnce("TedSysCalls", e); }
            return __result;
        }

        // status byte 1 bit -> the PR's ConditionType (as the kit's SnesAiHost maps SNES statuses); Wound also by 0 HP
        static readonly int[] Status1 = { 9, 34, 10, 607, 604, 601, 11, 5 };
        // status byte 2 bit: Condemned, Near Fatal (HP-based: none), Image, Mute, Berserk, Muddle, Sap, Sleep
        static readonly int[] Status2 = { 404, -1, 14, 6, 410, 12, 407, 7 };

        // TED:status: the character (00-0F) or party member (31-34) gets / loses the statuses of a 16-bit mask, through the
        // game's own OwnedCharacterClient.AddCondition / RemoveCondition (condition rows found by their ConditionType)
        internal static string SetStatus(bool add, int who, int mask)
        {
            var udm = global::Last.Management.UserDataManager.Instance();
            if (udm == null) return "no game";
            global::Last.Data.User.OwnedCharacterData oc = null;
            if (who >= 0x31 && who <= 0x34)
            {
                var corps = udm.GetCorpsListClone();
                int i = who - 0x31;
                int id = corps != null && i < corps.Count && corps[i] != null ? corps[i].CharacterId : 0;
                foreach (var o in udm.OwnedCharacterList) if (o != null && id != 0 && o.Id == id) oc = o;
            }
            else if (who < 0x10)
                foreach (var o in udm.OwnedCharacterList) if (o != null && o.characterStatusId == who + 1) oc = o;
            if (oc == null) return $"no character {who:X2}";
            var rows = global::PrKit.Master.All<global::Last.Data.Master.Condition>();
            var client = new global::Last.Management.OwnedCharacterClient();
            var done = new System.Collections.Generic.List<int>();
            for (int b = 0; b < 16; b++)
            {
                if ((mask & (1 << b)) == 0) continue;
                int type = b < 8 ? Status1[b] : Status2[b - 8];
                if (type < 0 || rows == null) continue;
                int row = 0;
                foreach (var kv in rows) if (kv.Value != null && kv.Value.ConditionType == type) { row = kv.Value.Id; break; }
                if (row == 0) continue;
                if (add) client.AddCondition(oc.Id, row);
                else client.RemoveCondition(oc.Id, row, true);
                done.Add(type);
            }
            return $"{(add ? "added" : "removed")} conditions [{string.Join(",", done)}] on {oc.Name}";
        }

        // TED:leadstatus: the party's top member (the field leader) has any status of status-byte-1 mask
        internal static bool LeadHas(int mask)
        {
            var udm = global::Last.Management.UserDataManager.Instance();
            var corps = udm?.GetCorpsListClone();
            if (corps == null || corps.Count == 0 || corps[0] == null || corps[0].CharacterId == 0) return false;
            global::Last.Data.User.OwnedCharacterData lead = null;
            foreach (var o in udm.OwnedCharacterList) if (o != null && o.Id == corps[0].CharacterId) { lead = o; break; }
            var p = lead?.Parameter;
            if (p == null) return false;
            if ((mask & 0x80) != 0 && p.currentHP <= 0) return true;
            var conds = p.ConfirmedConditionList();
            if (conds == null) return false;
            for (int b = 0; b < 8; b++)
            {
                if ((mask & (1 << b)) == 0) continue;
                foreach (var c in conds) if (c != null && c.ConditionType == Status1[b]) return true;
            }
            return false;
        }
    }
}
