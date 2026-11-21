using System;
using HarmonyLib;
using PrKit;
using Treasure = Last.Map.EventActionTreasure;

namespace TEdition.PR
{
    // Audit U9 (change.html §1 "Treasure Chest Message"): a chest's item line is the party lead's own (T-Edition's EE
    // dialogues 657-670: "Locke: Wow, what a find! <item>!"); an empty top slot, Banon, Ghost or Leo get the generic
    // one. The PR's chest (EventActionTreasure.GetMessage, decompiled tools/decomp/ted_u9) shows its entity's
    // PropertyTresureBox.MessageKey ("T0001_01_01": "Obtained (ITEM_N)!") with the item's name set as ITEM_N; for the
    // call, that key becomes TED_CHEST_<lead 00-13> (tools/ted_plugin_data.chest_rule writes them into system_en),
    // then goes back. Gil, "learned", count-over and empty chests keep the PR's own lines; so does a language
    // without the keys.
    static class TedChestLines
    {
        const string ItemKey = "T0001_01_01";
        internal static string Last = "";   // tests: the key the last chest used

        public static void Patch(Harmony h) =>
            Hooks.Patch(h, typeof(Treasure), "GetMessage", typeof(TedChestLines),
                prefix: nameof(GetMessage_Prefix), postfix: nameof(GetMessage_Postfix));

        // the party lead's character 0-13 (Terra..Umaro), -1 for an empty top slot or anyone else
        public static int Lead()
        {
            var udm = global::Last.Management.UserDataManager.Instance();
            var corps = udm?.GetCorpsListClone();
            if (corps == null || corps.Count == 0 || corps[0] == null || corps[0].CharacterId == 0) return -1;
            foreach (var o in udm.OwnedCharacterList)
                if (o != null && o.Id == corps[0].CharacterId)
                    return o.characterStatusId >= 1 && o.characterStatusId <= 14 ? o.characterStatusId - 1 : -1;
            return -1;
        }

        public static void GetMessage_Prefix(global::Last.Map.PropertyTresureBox propertyTresureBox, bool isCountOver, out string __state)
        {
            __state = null;
            if (!Plugin.TedMode || isCountOver || propertyTresureBox == null) return;
            try
            {
                if (propertyTresureBox.MessageKey != ItemKey) return;
                int lead = Lead();
                var key = lead >= 0 ? $"TED_CHEST_{lead:00}" : null;
                if (key == null || !GameText.Has(key)) { Last = ItemKey; return; }
                __state = propertyTresureBox.MessageKey;
                propertyTresureBox.MessageKey = key;
                Last = key;
                TedLog.Rule(0, "chest-" + lead, () => $"chest line of the party lead (character {lead}): {key} (audit U9)");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-chest-lines", e); }
        }

        public static void GetMessage_Postfix(global::Last.Map.PropertyTresureBox propertyTresureBox, string __state)
        {
            if (__state != null && propertyTresureBox != null) propertyTresureBox.MessageKey = __state;
        }
    }
}
