using System;
using System.Collections.Generic;
using HarmonyLib;
using PrKit;
using DescriptionWindow = Last.UI.KeyInput.EquipmentDescriptionWindowController;

namespace TEdition.PR
{
    // Audit U5 (change.html §1 "Equipment Details Menu"): the equip menu tells what a weapon does beyond its numbers, as
    // T-Edition's details page does: MP Critical, HP / MP Absorb, Row OK, Throw OK, bonus damage vs humans, flying,
    // magical or dragons (ted_data "weapon_details", tools/ted_plugin_data.weapon_details: T-Edition's weapon special
    // effect and flags). The PR's equip menu shows a description line (EquipmentDescriptionWindowController.
    // SetDescriptionText(text, isParameter), no item given): a weapon is known by its description text (each weapon's
    // content row MesIdDescription, looked up once the text has loaded) and the labels go on a line under it.
    static class TedEquipDetails
    {
        static Dictionary<string, string> byText;   // description text -> its labels line
        internal static string Last = "";

        public static void Patch(Harmony h) =>
            Hooks.Patch(h, typeof(DescriptionWindow), "SetDescriptionText", typeof(TedEquipDetails), prefix: nameof(SetText_Prefix));

        static void Build()
        {
            var map = new Dictionary<string, string>();
            var mm = global::Last.Data.Master.MasterManager.Instance;
            if (mm == null || Plugin.D?.WeaponDetails == null) return;
            foreach (var it in Plugin.D.Items)
            {
                if (!Plugin.D.WeaponDetails.TryGetValue(it.Slot, out var labels) || labels.Length == 0) continue;
                var key = mm.GetData<global::Last.Data.Master.Content>(it.Content)?.MesIdDescription;
                var text = string.IsNullOrEmpty(key) || key == "None" ? null : GameText.Get(key);
                if (string.IsNullOrEmpty(text) || map.ContainsKey(text)) continue;   // two weapons sharing a text: the first's
                map[text] = string.Join(", ", labels);
            }
            if (map.Count > 0) byText = map;
            Hooks.NoteOnce("ted-equip-details", () => $"[ted] equipment details: {map.Count} weapons' effects under their description (audit U5)");
        }

        public static void SetText_Prefix(ref string text)
        {
            if (!Plugin.TedMode || string.IsNullOrEmpty(text)) return;
            try
            {
                if (byText == null) Build();
                if (byText == null || !byText.TryGetValue(text, out var line)) return;
                text = text.TrimEnd() + "\n" + line;
                Last = line;
            }
            catch (Exception e) { Hooks.WarnOnce("ted-equip-details", e); }
        }
    }
}
