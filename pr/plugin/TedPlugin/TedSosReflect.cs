using System;
using System.Collections.Generic;
using Last.Battle;
using Last.Defaine;
using PrKit;

namespace TEdition.PR
{
    // Rule 57 (SOS relics): T-Edition's Lunar Curtain (item slot 224, "SOS Auto-Reflect") casts Reflect ($31) when its
    // wearer falls to Near Fatal (C2/0A62-0A7E). The PR has ShellDying / ProteusDying for the other two SOS relics
    // and no Reflect one, so this does it: once per battle per wearer, when the wearer is alive and Near Fatal
    // (ConditionType.Dying), Reflect is added (InterruptAddCondition, as the harness's tedcond).
    static class TedSosReflect
    {
        public const int LunarCurtainSlot = 224;
        static readonly HashSet<IntPtr> done = new HashSet<IntPtr>();
        static bool inBattle;
        internal static int Casts;

        public static void Update()
        {
            if (!Plugin.TedMode) return;
            var bm = BattlePlugManager.Instance();
            bool now = bm != null && bm.IsBattle();
            if (!now) { if (inBattle) done.Clear(); inBattle = false; return; }
            inBattle = true;
            int curtain = Plugin.D.BySlot(LunarCurtainSlot)?.Content ?? 0;
            if (curtain <= 0) return;
            var players = bm.GetPlayerUnits();
            if (players == null) return;
            foreach (var u in players)
            {
                if (u == null || done.Contains(u.Pointer)) continue;
                var c = u.TryCast<BattlePlayerData>()?.ownedCharacterData;
                if (c?.EquipmentData == null) continue;
                bool wears = false;
                foreach (var kv in c.EquipmentData) if (kv.Value != null && kv.Value.ContentId == curtain) wears = true;
                if (!wears) continue;
                var conds = u.BattleUnitDataInfo?.GetConfirmedConditionType();
                if (conds == null || !conds.Contains(ConditionType.Dying)) continue;
                if (c.Parameter == null || c.Parameter.CurrentHP <= 0) continue;
                done.Add(u.Pointer);
                if (conds.Contains(ConditionType.Reflex)) continue;
                bm.BattleConditionController.InterruptAddCondition(u, ConditionType.Reflex);
                Casts++;
                TedLog.Rule(57, "sos-reflect", () => "Lunar Curtain: Reflect on its Near Fatal wearer");
            }
        }
    }
}
