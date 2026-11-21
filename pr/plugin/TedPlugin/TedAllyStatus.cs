using System;
using System.Collections.Generic;
using Last.Battle;
using Last.Defaine;
using PrKit;
using UnityEngine;

namespace TEdition.PR
{
    // Audit U7 (change.html §2 "Information Display of Status Ailments of Allies"): holding Select in battle shows the
    // allies' statuses the battle doesn't draw: Reraise, Defend, Runic (readying) and Bushido Sky's counter stance (the
    // PR's ConditionType 602, 1, 612 and 626). T-Edition draws them as icons (feather, shield, knight sword,
    // katana); here they are a box of words in the top-left corner while the button is held (IMGUI, painted after
    // the battle's canvases). Charm, Love Token and Cloudy Heaven (its other three icons) are T-Edition's own
    // mechanics the PR has no status for: not shown. `tedallies` prints the same lines.
    sealed class TedAllyStatus : Feature
    {
        static readonly (ConditionType Type, string Label)[] Shown =
        {
            ((ConditionType)602, "Reraise"), (ConditionType.Defend, "Defend"), ((ConditionType)612, "Runic"), ((ConditionType)626, "Sky"),
        };
        static readonly List<string> lines = new List<string>();
        static bool held;
        static GUIStyle style;

        public override void Update()
        {
            held = false;
            if (!Plugin.TedMode) return;
            try
            {
                var bm = BattlePlugManager.Instance();
                if (bm == null || !bm.IsBattle()) return;
                held = SelectHeld();
                if (held && Time.frameCount % 6 == 0) Refresh(bm);
            }
            catch (Exception e) { Hooks.WarnOnce("ted-ally-status", e); }
        }

        // the game's Select (its key config: keyboard and pad) or the pad's own Select button (on the Steam Deck the
        // game's check can miss the pad: PrKit/Seeds/PadInput's note)
        static bool SelectHeld()
        {
            bool on = false;
            try { on = global::Il2CppSystem.Input.InputListener.Instance?.GetKey(global::Il2CppSystem.Input.Key.Select, global::Il2CppSystem.Input.KeyConfig.KeyValue.InputDeviceType.None, true) == true; }
            catch (Exception) { }
            if (on) return true;
            try { return UnityEngine.InputSystem.Gamepad.current?.selectButton?.isPressed == true; }
            catch (Exception) { return false; }
        }

        // a line per ally: "Name: Reraise, Defend" ("Name: -" when none)
        public static List<string> Refresh(BattlePlugManager bm)
        {
            lines.Clear();
            var players = bm?.GetPlayerUnits();
            if (players == null) return lines;
            foreach (var u in players)
            {
                var p = u?.TryCast<global::BattlePlayerData>();
                if (p == null) continue;
                var conds = u.BattleUnitDataInfo?.GetConfirmedConditionType();
                var on = new List<string>();
                foreach (var (type, label) in Shown) if (conds != null && conds.Contains(type)) on.Add(label);
                lines.Add($"{p.ownedCharacterData?.Name ?? "?"}: {(on.Count == 0 ? "-" : string.Join(", ", on))}");
            }
            return lines;
        }

        public override void OnGUI()
        {
            if (!held || lines.Count == 0) return;
            try
            {
                if (style == null)
                {
                    style = new GUIStyle();
                    style.alignment = TextAnchor.UpperLeft;
                    style.wordWrap = false;
                    style.normal.textColor = Color.white;
                }
                style.fontSize = Math.Max(14, Screen.height / 40);
                var text = string.Join("\n", lines);
                float w = Screen.width * 0.32f, h = (lines.Count + 0.8f) * style.fontSize * 1.35f;
                var box = new Rect(Screen.width * 0.02f, Screen.height * 0.03f, w, h);
                GUI.Box(box, "");
                GUI.Box(box, "");   // twice: the default box is half transparent
                GUI.Label(new Rect(box.x + style.fontSize * 0.6f, box.y + style.fontSize * 0.4f, w, h), text, style);
                Hooks.NoteOnce("ted-ally-status-shown", () => $"[ted] ally statuses shown (Select held): {text.Replace("\n", " | ")} (audit U7)");
            }
            catch (Exception e) { Hooks.WarnOnce("ted-ally-status-gui", e); }
        }
    }
}
