using System;
using Last.Data.User;
using Last.Management;
using PrKit;

namespace TEdition.PR
{
    // Rule 61 / audit C29: Magitek for everyone, T-Edition's six spells $85-$8A (Magitek Beam, Bio Blaster, Heal Force,
    // Confuser, Banisher, Magitek Missile; ted/battle_commands.md §14) = PR abilities 220-225. The PR's Magitek command
    // (26, shown in the armor) lists each character's owned abilities of ability group 7 (218-225; decompiled: no per-
    // character list to hook): vanilla gives everyone 218-220 + 222 and Terra all eight. So every party character
    // (status 1-14) owns 220-225 at skill 100 and not 218 / 219 (vanilla's Fire / Thunder Beam, not T-Edition's), kept
    // so on every save load and join (checked twice a second while the game runs). WcObjectives' MagitekUpgrade pattern.
    static class TedMagitek
    {
        static readonly int[] Six = { 220, 221, 222, 223, 224, 225 };
        static readonly int[] Gone = { 218, 219 };
        static int frames;
        internal static int Taught, Removed;

        public static void Update()
        {
            if (!Plugin.TedMode || ++frames % 30 != 0) return;
            try
            {
                var udm = UserDataManager.Instance();
                var list = udm?.OwnedCharacterList;
                if (list == null) return;
                var client = new OwnedCharacterClient();
                foreach (var c in list)
                {
                    if (c == null || c.characterStatusId < 1 || c.characterStatusId > 14 || c.OwnedAbilityList == null) continue;
                    foreach (var id in Six)
                    {
                        OwnedAbility owned = null;
                        foreach (var a in c.OwnedAbilityList) if (a?.Ability != null && a.Ability.Id == id) owned = a;
                        if (owned != null && owned.SkillLevel >= 100) continue;
                        owned ??= client.AddAbility(c.Id, id);
                        if (owned == null) continue;
                        owned.SkillLevel = 100;
                        Taught++;
                    }
                    foreach (var id in Gone)
                    {
                        bool has = false;
                        foreach (var a in c.OwnedAbilityList) if (a?.Ability != null && a.Ability.Id == id) has = true;
                        if (!has) continue;
                        client.RemoveAbility(c.Id, id);
                        Removed++;
                    }
                }
                if (Taught + Removed > 0)
                    TedLog.Rule(61, "", () => $"Magitek for everyone: T-Edition's six (220-225) taught {Taught}, Fire/Thunder Beam removed {Removed}");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-magitek", e); }
        }
    }
}
