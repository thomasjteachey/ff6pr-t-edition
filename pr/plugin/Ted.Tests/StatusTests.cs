using System;
using TEdition.Rules;

static partial class Program
{
    static partial void RunMore()
    {
        Test("50: tick amounts (max-HP/MP fractions, cap 999, no minimum)", Ticks);
        Test("41: Dice level and damage", DiceRule);
        Test("45/46/51: clock constants and command waits", ClockConstants);
        MoreCommands();
    }

    static partial void MoreCommands();

    static void Ticks()
    {
        Check(StatusMath.Poison(800) == 100, "Poison 1/8");
        Check(StatusMath.Poison(9999) == 999, "Poison capped");
        Check(StatusMath.Poison(7) == 0, "no minimum");
        Check(StatusMath.Regen(800, true) == 100 && StatusMath.Regen(800, false) == 50, "Regen 1/8 party, 1/16 monsters");
        Check(StatusMath.Regen(30000, false) == 999, "Regen capped");
        Check(StatusMath.Disease(320) == 20, "Disease 1/16 MP");
    }

    static void DiceRule()
    {
        Check(StatusMath.DiceLevel(40, 2) == 40, "2 dice: level");
        Check(StatusMath.DiceLevel(40, 3) == 30, "3 dice: (20 + 40) / 2 = 30");
        Check(StatusMath.DiceLevel(41, 3) == 31, "3 dice: (21 + 41) / 2 = 31");
        Check(StatusMath.Dice(new[] { 2, 5 }, 40, false) == 2 * 5 * 2 * 40, "2 dice product");
        Check(StatusMath.Dice(new[] { 3, 3 }, 40, false) == 3 * 3 * 2 * 40 * 3, "a pair x face");
        Check(StatusMath.Dice(new[] { 2, 4, 6 }, 40, false) == 48 * 2 * 30, "3 dice");
        Check(StatusMath.Dice(new[] { 6, 6, 6 }, 40, false) == 216 * 2 * 30 * 6, "triple x face");
        Check(StatusMath.Dice(new[] { 2, 5 }, 40, true) == (2 * 5 * 2 * 40) >> 4, "/16 on flagged monsters");
    }

    static void ClockConstants()
    {
        Check(StatusMath.AddHaste == 96 && StatusMath.StopSteps == 9 && StatusMath.AtbHasteK == 144 && StatusMath.MonsterSpeedTerm == 4, "constants");
        int magic = Array.Find(StatusMath.CommandWaits, c => c.Command == 7).Wait;
        int bushido = Array.Find(StatusMath.CommandWaits, c => c.Command == 12).Wait;
        Check(magic == 48 && bushido == 64, "Magic $30, Bushido $40");
        Check(Array.FindAll(StatusMath.CommandWaits, c => c.Command == 1).Length == 0, "Fight as vanilla");
    }
}
