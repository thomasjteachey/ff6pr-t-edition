using System;
using HarmonyLib;
using Last.Data.User;
using PrKit;

namespace TEdition.PR
{
    // Rule 35: Gogo and Umaro may equip magicite and learn its magic (T-Edition lifts vanilla's block). The PR
    // blocks them in code: StatusDetailsData.CanEquipMagicStone (its readonly GogoId / UmaroId) and the menu's
    // restriction checks (CharacterInfomationData, as WcRecruits lifts Umaro's equipment block). Magicite learning
    // rows already apply to anyone. Signatures are matched by name at run time: a character id is any int argument
    // or an OwnedCharacterData argument; the menu command by its name containing "Magic".
    static class TedMagicite
    {
        const int Gogo = 13, Umaro = 14;    // character_status ids (Terra 1 .. Umaro 14)
        internal static string State = "not hooked";

        public static void Apply(Harmony h)
        {
            int n = 0;
            var sd = typeof(Serial.FF6.Management.StatusDetailsData);
            var ci = typeof(Serial.FF6.Management.CharacterInfomationData);
            foreach (var (type, name, post) in new[] {
                         (sd, "CanEquipMagicStone", nameof(Can_Postfix)),
                         (ci, "CanOpenRestrictionMenuWindow", nameof(Can_Postfix)),
                         (ci, "GetDisplayRestrictionCharaIdList", nameof(Restricted_Postfix)) })
            {
                if (type == null) continue;
                foreach (var m in AccessTools.GetDeclaredMethods(type))
                {
                    if (m.Name != name) continue;
                    try { h.Patch(m, postfix: new HarmonyMethod(typeof(TedMagicite), post)); n++; }
                    catch (Exception e) { Plugin.L.LogWarning($"[ted] rule 35: {name}: {e.Message}"); }
                }
            }
            State = $"{n} checks hooked (CanEquipMagicStone, the menu's restrictions)";
            Plugin.L.LogInfo($"[ted] rule 35: Gogo and Umaro may equip magicite: {State}");
        }

        static bool IsMagicMenu(object[] args)
        {
            foreach (var a in args)
                if (a is Enum e) return e.ToString().IndexOf("Magic", StringComparison.OrdinalIgnoreCase) >= 0;
            return true;   // no command argument: the magicite check itself
        }

        static int CharacterOf(object[] args)
        {
            foreach (var a in args)
            {
                if (a is int i && (i == Gogo || i == Umaro)) return i;
                if (a is OwnedCharacterData c && (c.characterStatusId == Gogo || c.characterStatusId == Umaro)) return c.characterStatusId;
            }
            return 0;
        }

        public static void Can_Postfix(object[] __args, ref bool __result)
        {
            if (__result || !Plugin.TedMode || !IsMagicMenu(__args)) return;
            int who = CharacterOf(__args);
            if (who == 0) return;
            __result = true;
            TedLog.Rule(35, "", () => $"{(who == Gogo ? "Gogo" : "Umaro")} may equip magicite");
        }

        public static void Restricted_Postfix(object[] __args, ref Il2CppSystem.Collections.Generic.List<int> __result)
        {
            if (__result == null || !Plugin.TedMode || !IsMagicMenu(__args)) return;
            if (!__result.Contains(Gogo) && !__result.Contains(Umaro)) return;
            var list = new Il2CppSystem.Collections.Generic.List<int>();   // a copy: the PR's own list stays
            foreach (var id in __result) if (id != Gogo && id != Umaro) list.Add(id);
            __result = list;
            TedLog.Rule(35, "menu", () => "the magicite menu lists Gogo and Umaro");
        }
    }
}
