using System;
using PrKit;
using UnityEngine;

namespace TEdition.PR
{
    // T-Edition's field timers (SNES event commands A0 "start timer" / A1 "reset timer"; audit Q18 Imitation's Secret,
    // Q19 Night Patrol, the stubs ted-events' translator wrote as "SNES:timer_start/_reset"), as SysCalls:
    //   TED:timer_start <n> <frames> <flags> <script>   timer n (0-3) runs <frames> SNES frames (60 a second); when it
    //                                                    runs out, <script> (the translated expiry event, one of the
    //                                                    current map's scripts) starts as soon as no script runs
    //   TED:timer_reset <n>                              timer n stops without its script (A1 n)
    //   TED:timer_left <n> [var]                         seconds left (0 = stopped) into map-local variable var (0)
    // A0's last byte (zz in A0 tt tt yy yy zz): bits 0-1 the event's bank offset, 2-3 the timer, 4-6 flags; a timer
    // with any flag bit shows its time left on screen (the long, timed ones: Night Patrol's 12 minutes have 0x50;
    // the short NPC-step ones 0x00). Timers run on the game's clock (Time.deltaTime: pause stops them), not saved.
    static class TedTimers
    {
        const int Count = 4;
        static readonly double[] left = new double[Count];   // seconds; <= 0 off
        static readonly string[] script = new string[Count];
        static readonly bool[] shown = new bool[Count];
        static readonly bool[] due = new bool[Count];
        static GUIStyle style;
        internal static string Last = "";

        public static string Start(string[] a)
        {
            if (a.Length < 4 || !int.TryParse(a[0], out int n) || n < 0 || n >= Count || !int.TryParse(a[1], out int frames))
                return Last = $"bad timer_start {string.Join(" ", a)}";
            int flags = Num(a[2]);
            left[n] = Math.Max(frames, 1) / 60.0;
            script[n] = a[3];
            shown[n] = (flags & 0x70) != 0;
            due[n] = false;
            return Last = $"timer {n}: {left[n]:0.0} s, then {script[n]}{(shown[n] ? " (on screen)" : "")}";
        }

        public static string Reset(string[] a)
        {
            if (a.Length < 1 || !int.TryParse(a[0], out int n) || n < 0 || n >= Count) return Last = "bad timer_reset";
            left[n] = 0;
            due[n] = false;
            return Last = $"timer {n} reset";
        }

        public static int SecondsLeft(int n) => n >= 0 && n < Count && left[n] > 0 ? (int)Math.Ceiling(left[n]) : 0;

        static int Num(string s) =>
            s.StartsWith("0x", StringComparison.OrdinalIgnoreCase) ? Convert.ToInt32(s.Substring(2), 16)
            : int.TryParse(s, out int v) ? v : Convert.ToInt32(s, 16);

        public static void Update()
        {
            if (!Plugin.TedMode) return;
            for (int n = 0; n < Count; n++)
            {
                if (left[n] > 0)
                {
                    left[n] -= Time.deltaTime;
                    if (left[n] <= 0) { left[n] = 0; due[n] = true; }
                }
                if (!due[n] || MapScripts.Busy) continue;
                due[n] = false;
                var why = MapScripts.Start(script[n]);
                int k = n;
                if (why == null) Kit.Info($"[ted] timer {k} ran out: {script[k]} started");
                else Kit.Warn($"[ted] timer {k} ran out: {why}");
                Last = $"timer {n} ran out: {why ?? script[n] + " started"}";
            }
        }

        public static void OnGUI()
        {
            if (!Plugin.TedMode) return;
            for (int n = 0; n < Count; n++)
            {
                if (left[n] <= 0 || !shown[n]) continue;
                if (style == null)
                {
                    style = new GUIStyle();
                    style.alignment = TextAnchor.UpperRight;
                    style.normal.textColor = Color.white;
                }
                style.fontSize = Math.Max(16, Screen.height / 28);
                int s = (int)Math.Ceiling(left[n]);
                var text = $"{s / 60:00}:{s % 60:00}";
                var r = new Rect(Screen.width * 0.70f, Screen.height * 0.03f, Screen.width * 0.27f, style.fontSize * 1.5f);
                GUI.Box(r, "");
                GUI.Label(new Rect(r.x, r.y + style.fontSize * 0.2f, r.width - style.fontSize * 0.4f, r.height), text, style);
                break;   // one on screen, as the SNES shows one
            }
        }
    }
}
