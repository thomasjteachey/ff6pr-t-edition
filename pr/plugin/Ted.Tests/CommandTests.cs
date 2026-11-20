using System;
using TEdition.Rules;

static partial class Program
{
    static partial void MoreCommands()
    {
        Test("27: Steal chance (Lv + 70 - target Lv, x2 enhanced)", StealRule);
        Test("27: rare slot 64/256", RareRule);
        Test("28/43: Orichalcum power and the counters' caps", OrichalcumRule);
        Test("29: Gil Toss cost and damage", GilTossRule);
        Test("38: Interceptor 171/256", InterceptorRule);
    }

    static void StealRule()
    {
        Check(CommandMath.StealChance(20, 30, false) == 60, "20 + 70 - 30");
        Check(CommandMath.StealChance(20, 30, true) == 120, "enhanced x2");
        Check(!CommandMath.StealSucceeds(10, 90, false, 0), "C < 0 fails");
        Check(CommandMath.StealSucceeds(60, 0, false, 99), "C >= 128 sure");
        Check(CommandMath.StealSucceeds(190, 255, false, 99), "Lv + 70 >= 256 sure");
        Check(CommandMath.StealSucceeds(20, 30, false, 59) && !CommandMath.StealSucceeds(20, 30, false, 60), "roll 0..99 < C");
        int ok = 0;
        for (int r = 0; r < 100; r++) if (CommandMath.StealSucceeds(20, 30, false, r)) ok++;
        Check(ok == 60, $"60% at C 60 ({ok})");
    }

    static void RareRule()
    {
        int rare = 0;
        for (int r = 0; r < 256; r++) if (CommandMath.PicksRare(r)) rare++;
        Check(rare == 64, $"rare {rare}/256");
    }

    static void OrichalcumRule()
    {
        Check(CommandMath.OrichalcumPower(0) == 0 && CommandMath.OrichalcumPower(101) == 50, "steals / 2");
        Check(CommandMath.OrichalcumPower(510) == 255 && CommandMath.OrichalcumPower(9999) == 255, "255 at 510");
        Check(CommandMath.Bump(509) == 510 && CommandMath.Bump(510) == 510, "counter cap 510");
        Check(CommandMath.Bump(255, CommandMath.TwinFangCap) == 255, "Twin Fang's cap 255");
    }

    static void GilTossRule()
    {
        Check(CommandMath.GilTossCost(50) == 9000 && CommandMath.GilTossDamage(50) == 4500, "Lv 50: 9000 gil, 4500 each (change.txt)");
        Check(CommandMath.MonsterGilToss(900, 3) == 150, "monster: paid / 2 / targets");
    }

    static void InterceptorRule()
    {
        int blocks = 0;
        for (int r = 0; r < 256; r++) if (CommandMath.InterceptorBlock(r)) blocks++;
        Check(blocks == CommandMath.InterceptorBlocks, $"blocks {blocks}/256");
        Check(CommandMath.InterceptorAnswer(true) < 50 && CommandMath.InterceptorAnswer(false) >= 50, "the PR's roll answered");
    }
}
