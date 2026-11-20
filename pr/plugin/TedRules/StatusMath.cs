using System;

namespace TEdition.Rules
{
    // T-Edition's status numbers (pr/ted/BATTLE_SPEC.md rules 41, 45, 46, 50, 51; battle_status.md 2, 3, 7).
    public static class StatusMath
    {
        public const int TickCap = 999;

        // 50: periodic ticks, power / 16 of the max (C2/500A + 40/3030): Poison 2 (max HP / 8), Regen 2 on
        // the party (1/8) and 1 on monsters (1/16), Disease (the PR's Sap) and MP Slip 1 of max MP (1/16);
        // no Stamina, no Poison growth, capped at 999, no minimum (a max under 16/power gives 0)
        public static int Poison(int maxHp) => Math.Min(TickCap, Math.Max(0, maxHp) * 2 / 16);
        public static int Regen(int maxHp, bool party) => Math.Min(TickCap, Math.Max(0, maxHp) * (party ? 2 : 1) / 16);
        public static int Disease(int maxMp) => Math.Min(TickCap, Math.Max(0, maxMp) / 16);

        // 45 / 51: the status clock's constants (C2/09DA: Haste $3ADD 96, vanilla 84; C2/4668: Stop 9 steps,
        // vanilla 18) and the ATB's (Haste x144 = 96 x 1.5; monsters (Speed + 20) x (255 - 4 x battle speed))
        public const int AddHaste = 96, StopSteps = 9, AtbHasteK = 144, MonsterSpeedTerm = 4;

        // 46: command wait times (C2/067B), by the PR's command id (tools/port.py SNES_CMD): $30 for Magic,
        // Throw, Tools, Snowstorm (Control), Rage, Animal (Leap), Mimic, Dance, X-Magic, Spirit (Possess);
        // $40 for Bushido, Blitz, Lore; $20 for Sketch, Slot, Gil Toss; the rest as vanilla
        public static readonly (int Command, int Wait)[] CommandWaits =
        {
            (7, 0x30), (13, 0x30), (14, 0x30), (19, 0x30), (23, 0x30), (24, 0x30), (25, 0x30), (22, 0x30), (31, 0x30), (29, 0x30),
            (12, 0x40), (15, 0x40), (17, 0x40),
            (18, 0x20), (20, 0x20), (21, 0x20),
        };

        // 41: Dice (weapon effect 9, C2/4140): the level used is Lv with 2 dice, ((Lv+1)>>1 + Lv + carry)>>1
        // (about 3/4 Lv) with 3 (C2/67C0)
        public static int DiceLevel(int level, int dice)
        {
            if (dice < 3) return level;
            int a = (level + 1) >> 1;
            int sum = a + level;
            return sum >> 1;
        }

        // T-Edition's dice damage from the faces: product x 2 x DiceLevel, all three equal x the face again
        // (the PR's own: product x 2 x Lv, all equal face^(n+1) x 2 x Lv); /16 against $3C95 bit 1 monsters
        public static int Dice(int[] faces, int level, bool halfFlag)
        {
            if (faces == null || faces.Length == 0) return 0;
            long p = 1;
            foreach (var f in faces) p *= f;
            long v = p * 2 * DiceLevel(level, faces.Length);
            bool same = true;
            foreach (var f in faces) same &= f == faces[0];
            if (same && faces.Length >= 2) v *= faces[0];
            if (halfFlag) v >>= 4;
            return (int)Math.Min(int.MaxValue, v);
        }
    }
}
