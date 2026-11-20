using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using TEdition.Rules;

// Tiny test runner (as BNW's Rules.Tests): each Test() prints PASS/FAIL; exit code = number of failures.
static partial class Program
{
    static int failures, passes;
    static string DataPath;

    static int Main(string[] args)
    {
        DataPath = args.Length > 0 ? args[0] : FindData();
        Console.WriteLine($"data: {DataPath ?? "(none: data tests skipped)"}");

        Test("ted_data.json shape", DataShape);
        Test("icon tags off for name checks", PlainNames);
        Test("6: one element (weak loses its x2, others as the game)", OneElement);
        Test("6: several elements split and summed", ManyElements);
        Test("6: the element view for the game's table", ElementViews);
        Test("7: weakness quarters Def/MDef", WeakDefense);
        Test("8: ignore-defense meets Safe/Shell/Defend/row/Morph", IgnoreDefense);
        Test("8: heals meet Shell", HealsMeetShell);
        Test("9: half damage on flagged monsters (ignore-defense only)", HalfFlag);
        Test("10: Defend, back row, Morph target", DefendRowMorph);
        Test("17: Atma Weapon's level from Stamina", Atma);
        Test("40: Trance attacker x1.5", TranceAttacker);
        Test("a plain hit is left alone", PlainHit);
        RunMore();

        Console.WriteLine($"\n{passes} passed, {failures} failed");
        return failures;
    }

    static partial void RunMore();

    static string FindData()
    {
        for (var dir = new DirectoryInfo(AppContext.BaseDirectory); dir != null; dir = dir.Parent)
        {
            var p = Path.Combine(dir.FullName, "build", "t-edition", "plugin", "ted_data.json");
            if (File.Exists(p)) return p;
        }
        return null;
    }

    static void Test(string name, Action body)
    {
        try
        {
            body();
            passes++;
            Console.WriteLine($"PASS  {name}");
        }
        catch (Exception e)
        {
            failures++;
            Console.WriteLine($"FAIL  {name}: {e.Message}");
        }
    }

    static void Check(bool ok, string what)
    {
        if (!ok) throw new Exception(what);
    }

    static void Near(double have, double want, string what, double tol = 1e-6)
    {
        if (Math.Abs(have - want) > tol) throw new Exception($"{what}: {have:0.######}, want {want:0.######}");
    }

    static DamageSteps.Hit Magic(params int[] elements) => new DamageSteps.Hit { Elements = elements };
    static DamageSteps.Hit Phys(params int[] elements) => new DamageSteps.Hit { Physical = true, Elements = elements };

    // --- data ------------------------------------------------------------------------------------

    static void DataShape()
    {
        if (DataPath == null) return;
        var d = TedData.Parse(File.ReadAllText(DataPath));
        Check(d.Items.Count >= 250, $"items {d.Items.Count}");
        Check(d.Items.Select(i => i.Slot).Distinct().Count() == d.Items.Count, "item slots repeat");
        Check(d.Items.All(i => i.Content > 0 && i.Row > 0 && i.Name.Length > 0), "an item without content/row/name");
        Check(d.NewWeapons.Count == 24 && d.NewWeapons.All(w => w.Row >= 92 && w.Content > 0 && w.Name.Length > 0), $"new weapons {d.NewWeapons.Count}");
        Check(d.DropRates.SequenceEqual(new[] { 68, 19, 8, 5 }), $"drop rates {string.Join("/", d.DropRates)}");
        Check(d.HalfIgnoreDefense.Count > 0 && d.HalfIgnoreDefense.All(id => (id >= 1 && id <= 384) || (id >= 1384 && id <= 1511)), "half-damage monsters");
        Check(d.HalfIgnoreDefenseNew.All(e => d.HalfIgnoreDefense.Contains(1000 + e)), "new monsters as PR 1000 + id");
        Check(d.NamedContent("orichalcum") > 0, "Orichalcum's content id");
        Console.WriteLine($"      {d.Items.Count} items ({d.Items.Count(i => i.Moved)} moved), {d.NewWeapons.Count} new weapons, " +
                          $"{d.HalfIgnoreDefense.Count}+{d.HalfIgnoreDefenseNew.Count} half-damage monsters");
    }

    static void PlainNames()
    {
        Check(TedData.Plain("<IC_TRW>Gaia's Hammer") == "Gaia's Hammer", "icon tag");
        Check(TedData.Plain("  Potion ") == "Potion", "spaces");
        Check(TedData.Plain(null) == "", "null");
    }

    // --- damage ----------------------------------------------------------------------------------

    static void OneElement()
    {
        Near(DamageSteps.Apply(Magic(DamageSteps.Weak)).Factor, 0.5, "weak: the game's x2 undone");
        Near(DamageSteps.Apply(Magic(DamageSteps.Half)).Factor, 1, "resist: the game's 1/2 is T-Edition's");
        Near(DamageSteps.Apply(Magic(DamageSteps.Normal)).Factor, 1, "neutral");
        Near(DamageSteps.Apply(Magic(DamageSteps.Absorb)).Factor, 1, "absorb heals as the game");
        Check(DamageSteps.Apply(Magic(DamageSteps.Absorb)).View == DamageSteps.View.None, "one element: no view");
    }

    static void ManyElements()
    {
        // change.txt's example: weak water + immune ice = half damage (MDef quartered: tested below)
        var r = DamageSteps.Apply(Magic(DamageSteps.Weak, DamageSteps.Null));
        Check(r.View == DamageSteps.View.AllNormal, "view all neutral");
        Near(r.Factor, 0.5 * (255.0 - 0) / (255 - 0), "weak + immune = 1/2 (MDef 0)");
        Near(DamageSteps.Apply(Magic(DamageSteps.Half, DamageSteps.Normal)).Factor, 0.75, "resist + neutral");
        Near(DamageSteps.Apply(Magic(DamageSteps.Half, DamageSteps.Half, DamageSteps.Normal)).Factor, 2.0 / 3, "resist x2 + neutral");
        var zero = DamageSteps.Apply(Magic(DamageSteps.Absorb, DamageSteps.Normal));
        Check(zero.ZeroDamage && zero.View == DamageSteps.View.OneNull, "absorb + neutral: 0");
        var heal = DamageSteps.Apply(Magic(DamageSteps.Absorb, DamageSteps.Absorb, DamageSteps.Half));
        Check(heal.HealsByElement && heal.View == DamageSteps.View.OneAbsorb, "absorb x2 + resist heals");
        Near(heal.Factor, 1.5 / 3, "heal share (-2 + 0.5) / 3");
        Near(DamageSteps.Apply(Magic(DamageSteps.Null, DamageSteps.Null)).Factor, 1, "immune x2: the view's 0");
        Check(DamageSteps.Apply(Magic(DamageSteps.Null, DamageSteps.Null)).ZeroDamage, "immune x2: zero");
    }

    static void ElementViews()
    {
        var table = new Dictionary<int, int> { [1] = DamageSteps.Weak, [2] = DamageSteps.Null, [5] = DamageSteps.Absorb };
        var all = DamageSteps.ViewTable(table, new[] { 1, 2 }, DamageSteps.View.AllNormal);
        Check(!all.ContainsKey(1) && !all.ContainsKey(2) && all[5] == DamageSteps.Absorb, "attack elements neutral, others kept");
        var n = DamageSteps.ViewTable(table, new[] { 1, 2 }, DamageSteps.View.OneNull);
        Check(n[1] == DamageSteps.Null && !n.ContainsKey(2), "one immune");
        var a = DamageSteps.ViewTable(table, new[] { 2, 1 }, DamageSteps.View.OneAbsorb);
        Check(a[2] == DamageSteps.Absorb && !a.ContainsKey(1), "one absorbing");
        Check(DamageSteps.ViewTable(table, new[] { 1 }, DamageSteps.View.None) == null, "no view");
    }

    static void WeakDefense()
    {
        var h = Magic(DamageSteps.Weak);
        h.Defense = 100;
        var r = DamageSteps.Apply(h);
        Near(r.Factor, 0.5 * (255 - 25) / (255.0 - 100), "MDef 100 weak: x1/2 for the x2, MDef/4");
        Check(r.Fired.Any(f => f.Rule == 7) && r.Fired.Any(f => f.Rule == 6), "rules 6 and 7 fired");
        var p = Phys(DamageSteps.Weak, DamageSteps.Normal);
        p.Defense = 200;
        Near(DamageSteps.Apply(p).Factor, 1.0 * (255 - 50) / (255.0 - 200), "two elements, one weak: share 1, Def/4");
        var ign = Magic(DamageSteps.Weak);
        ign.Defense = 100; ign.IgnoreDefense = ign.GameSkippedDefense = true;
        Near(DamageSteps.Apply(ign).Factor, 0.5 * 255 / 256.0, "ignore-defense: Def 0 either way");
    }

    static void IgnoreDefense()
    {
        var shell = new DamageSteps.Hit { IgnoreDefense = true, GameSkippedDefense = true, Guard = true };
        Near(DamageSteps.Apply(shell).Factor, 255 / 256.0 * 170 / 256.0, "Shell now cuts ignore-defense magic");
        var safe = new DamageSteps.Hit { Physical = true, IgnoreDefense = true, GameSkippedDefense = true, Guard = true, Defending = true, BackRow = true };
        Near(DamageSteps.Apply(safe).Factor, 255 / 256.0 * 170 / 256.0 * 170 / 256.0 * 0.5, "Safe, row and Defend now apply");
        // Valiant Knife: the game skips defense by weapon, T-Edition doesn't (rule 60)
        var vk = new DamageSteps.Hit { Physical = true, GameSkippedDefense = true, Defense = 60 };
        Near(DamageSteps.Apply(vk).Factor, (255 - 60) / 256.0, "Valiant Knife meets Defense");
    }

    static void HealsMeetShell()
    {
        Near(DamageSteps.Apply(new DamageSteps.Hit { Heal = true, Guard = true }).Factor, 255 / 256.0 * 170 / 256.0, "Cure on a Shell target");
        Near(DamageSteps.Apply(new DamageSteps.Hit { Heal = true }).Factor, 255 / 256.0, "plain heal ~ as the game");
        Near(DamageSteps.Apply(new DamageSteps.Hit { Heal = true, Elements = new[] { DamageSteps.Weak } }).Factor, 255 / 256.0, "no elements on heals");
    }

    static void HalfFlag()
    {
        Near(DamageSteps.Apply(new DamageSteps.Hit { IgnoreDefense = true, GameSkippedDefense = true, HalfFlag = true }).Factor,
             255 / 256.0 * 0.5, "flagged + ignore-defense");
        var plain = new DamageSteps.Hit { HalfFlag = true, Defense = 50 };
        Near(DamageSteps.Apply(plain).Factor, 1, "flagged, defense met: no half");
    }

    static void DefendRowMorph()
    {
        Near(DamageSteps.Apply(new DamageSteps.Hit { Physical = true, BackRow = true, Defense = 10 }).Factor, (170 / 256.0) / 0.5, "back row 170/256 over 1/2");
        Near(DamageSteps.Apply(new DamageSteps.Hit { Physical = true, Defending = true, Defense = 10 }).Factor, 1, "physical Defend as the game");
        Near(DamageSteps.Apply(new DamageSteps.Hit { Defending = true, Defense = 10 }).Factor, 170 / 256.0, "magic Defend new");
        Near(DamageSteps.Apply(new DamageSteps.Hit { TargetMorph = true, Defense = 10 }).Factor, (170 / 256.0) / 0.5, "magic on Morph 170/256 over 1/2");
        Near(DamageSteps.Apply(new DamageSteps.Hit { Physical = true, TargetMorph = true }).Factor, 1, "physical on Morph unchanged");
    }

    static void Atma()
    {
        var h = new DamageSteps.Hit { Physical = true, Atma = true, Level = 40, Stamina = 50 };
        Near(DamageSteps.Apply(h).Factor, 100.0 / 40, "Stamina 50 at level 40");
        h.Stamina = 200;
        Near(DamageSteps.Apply(h).Factor, 254.0 / 40, "Stamina capped at 127");
    }

    static void TranceAttacker()
    {
        Near(DamageSteps.Apply(new DamageSteps.Hit { AttackerMorph = true }).Factor, 0.75, "damage");
        Near(DamageSteps.Apply(new DamageSteps.Hit { Heal = true, AttackerMorph = true }).Factor, 255 / 256.0 * 0.75, "heals too");
    }

    static void PlainHit()
    {
        var r = DamageSteps.Apply(new DamageSteps.Hit { Physical = true, Defense = 120, Guard = true, Defending = true });
        Near(r.Factor, 1, "Def, Safe, Defend as the game");
        Check(r.Fired.Count == 0, "nothing fired");
        Check(DamageSteps.Scale(9000, 4.0, 32000) == 32000 - 0 * 1 || DamageSteps.Scale(9000, 4.0, 32000) == 32000, "cap");
        Check(DamageSteps.Scale(3, 0.01, 32000) == 1, "at least 1");
    }
}
