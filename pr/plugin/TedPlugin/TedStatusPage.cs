using System;
using System.Collections.Generic;
using HarmonyLib;
using Last.Data.User;
using PrKit;
using UnityEngine;
using UnityEngine.UI;
using Object = UnityEngine.Object;
using StatusController = Serial.FF6.UI.KeyInput.StatusDetailsController;

namespace TEdition.PR
{
    // Audit U4 (T-Edition's status screen pages: attributes, conditions, abilities), first part: the character's element
    // responses and status immunities on the PR's status screen. The PR's screen has no pages (StatusDetailsController:
    // one view per character; decompiled tools/decomp/ted_ui1). T-Edition gives no esper level-up bonus (rule 4), so the
    // "Level Up Bonus" row is free: it shows the element line, and a copy of its text below it (BnwPlugin's
    // EsperLevelDisplay way: a child of the game's own text, same font) lists the rest. Element names are the game's
    // (MSG_SYSTEM_373-380); `tedstatus` prints the same lines for a party member.
    static class TedStatusPage
    {
        // attribute id -> its name's message key (Fire 1, Ice 2, Lightning 3, Poison 4, Water 5 from the ported
        // scrolls; 6-8 unverified: tedstatus prints the ids)
        static readonly Dictionary<int, string> ElementKey = new Dictionary<int, string>
        {
            [1] = "MSG_SYSTEM_380", [2] = "MSG_SYSTEM_379", [3] = "MSG_SYSTEM_378", [4] = "MSG_SYSTEM_377",
            [5] = "MSG_SYSTEM_373", [6] = "MSG_SYSTEM_376", [7] = "MSG_SYSTEM_375", [8] = "MSG_SYSTEM_374",
        };
        static Text extra;

        public static void Patch(Harmony h)
        {
            Hooks.Patch(h, typeof(StatusController), "SetParameter", typeof(TedStatusPage), postfix: nameof(Status_Postfix));
            Hooks.Patch(h, typeof(StatusController), "SetMagicStoneBouns", typeof(TedStatusPage), postfix: nameof(Status_Postfix));
        }

        static string Name(int id) => ElementKey.TryGetValue(id, out var k) ? (GameText.Get(k) ?? $"#{id}") : $"#{id}";

        public static string[] Lines(OwnedCharacterData c, bool ids = false)
        {
            var groups = new SortedDictionary<int, List<string>>();
            var p = c?.Parameter;
            var map = p?.ConfirmedResistanceAttributeList();
            if (map != null)
                foreach (var kv in map)
                {
                    int t = kv.Value switch { 1 => 1, 401 => 1, 2 => 2, 402 => 2, 3 => 3, 4 => 4, _ => 0 };
                    if (t == 0) continue;
                    if (!groups.TryGetValue(t, out var l)) groups[t] = l = new List<string>();
                    l.Add(Name(kv.Key) + (ids ? $"({kv.Key})" : ""));
                }
            string Part(int t, string label) => groups.TryGetValue(t, out var l) ? $"{label} {string.Join(", ", l)}" : null;
            var elems = new List<string>();
            foreach (var s in new[] { Part(1, "Weak:"), Part(2, "Resist:"), Part(3, "Immune:"), Part(4, "Absorb:") }) if (s != null) elems.Add(s);
            int immune = p?.ConfirmedResistanceCondtionList()?.Count ?? 0;
            return new[]
            {
                elems.Count == 0 ? "Elements: none" : string.Join("  ", elems),
                $"Status immunities: {immune}",
            };
        }

        public static void Status_Postfix(StatusController __instance)
        {
            if (!Plugin.TedMode || !Hooks.IsA<StatusController>(__instance)) return;
            try
            {
                var v = __instance.view;
                var c = __instance.statusController?.targetData;
                var name = v?.FixedLevelUpBonusText;
                var value = v?.LevelUpBonusText;
                if (name == null || value == null || c == null) return;
                var lines = Lines(c);
                name.text = "";
                value.text = "";
                if (extra == null || extra.gameObject == null)
                {
                    var go = Object.Instantiate(name.gameObject);
                    go.name = "TedStatusExtra";
                    go.transform.SetParent(name.transform, false);
                    extra = go.GetComponent<Text>();
                    var rt = go.GetComponent<RectTransform>();
                    rt.anchorMin = new Vector2(0f, 1f);
                    rt.anchorMax = new Vector2(0f, 1f);
                    rt.pivot = new Vector2(0f, 1f);
                    rt.anchoredPosition = Vector2.zero;
                    rt.sizeDelta = new Vector2(900f, 80f);
                    extra.alignment = TextAnchor.UpperLeft;
                    extra.horizontalOverflow = HorizontalWrapMode.Overflow;
                    extra.verticalOverflow = VerticalWrapMode.Overflow;
                }
                extra.text = string.Join("\n", lines);
                TedLog.Rule(0, "status-page", () => $"status screen: {string.Join(" | ", lines)} (audit U4)");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-status-page", e); }
        }
    }
}
