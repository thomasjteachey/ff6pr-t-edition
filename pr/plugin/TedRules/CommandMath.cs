using System;

namespace TEdition.Rules
{
    // T-Edition's character-command numbers (pr/ted/BATTLE_SPEC.md 27-29, 38, 43; battle_commands.md).
    public static class CommandMath
    {
        // 27 Steal (C2/398E): C = attacker Lv + 70 - target Lv (vanilla +50), x2 with Enhanced Steal;
        // C < 0 fails, Lv + 70 >= 256 or C >= 128 always succeeds, else success when random(0..99) < C
        public static int StealChance(int level, int targetLevel, bool enhanced)
        {
            int c = level + 70 - targetLevel;
            if (enhanced) c *= 2;
            return c;
        }

        public static bool StealSucceeds(int level, int targetLevel, bool enhanced, int roll100)
        {
            if (level + 70 >= 256) return true;
            int c = StealChance(level, targetLevel, enhanced);
            if (c < 0) return false;
            if (c >= 128) return true;
            return roll100 < c;
        }

        // the rare slot with 64/256 (vanilla 32/256), else the common one; an empty picked slot fails
        public const int RareOdds = 64;
        public static bool PicksRare(int roll256) => roll256 < RareOdds;

        // 43: the success counters ($1E70...), 16-bit, capped at 510 ($1FE); Twin Fang's at 255
        public const int CounterCap = 510, TwinFangCap = 255;
        public static int Bump(int value, int cap = CounterCap) => Math.Min(cap, Math.Max(0, value) + 1);

        // 28 Orichalcum (CE/0140): battle power = min(steals / 2, 255)
        public static int OrichalcumPower(int steals) => Math.Min(Math.Max(0, steals) / 2, 255);

        // 29 Gil Toss (47/3F9F): cost Lv x 180; a character deals cost / 2 to every target, not split;
        // a monster pays from its own gil (capped at what it has) and deals paid / 2 / targets
        public static int GilTossCost(int level) => Math.Max(0, level) * 180;
        public static int GilTossDamage(int level) => GilTossCost(level) / 2;
        public static int MonsterGilToss(int paid, int targets) => paid / 2 / Math.Max(1, targets);

        // 38 Interceptor (C2/2283): blocks when random(256) >= $55: 171/256 (the code's reversed branch;
        // the docs say 33%). The PR rolls GetRand(100) < 50.
        public const int InterceptorBlocks = 171;
        public static bool InterceptorBlock(int roll256) => roll256 >= 0x55;
        // the PR's own roll (GetRand(100) < 50) answered so the block comes with T-Edition's odds
        public static int InterceptorAnswer(bool block) => block ? 0 : 99;
    }
}
