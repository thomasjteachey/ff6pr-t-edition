using System;
using System.Collections.Generic;
using System.Linq;

namespace TEdition.Rules
{
    // T-Edition's damage steps (pr/ted/BATTLE_SPEC.md rules 6-10, 17, 40) as a factor on the game's
    // result. The Pixel Remaster computes vanilla FF6's formulas (BNW's formula probe, PORTING.md); its
    // steps, read from the decompiled CalcExecuteFF6.PhysicalExecution / MagicExecution:
    //   * defense: x(255 - Def)/256 + 1 (MDef for magic), then Safe (physical) / Shell (magic) x170/256 + 1,
    //     physical: a character in the back row x1/2 (unless the attack ignores row), Defend x1/2;
    //     magic: a Morphed target x1/2. All skipped for heals and for attacks that ignore defense
    //     (content flag 5, and Valiant Knife by weapon);
    //   * elements: one response for the attack (weak x2, resist x1/2, immune 0, absorb heals);
    //   * a Morphed attacker x2 (heals too).
    // T-Edition:
    //   6  elements: the damage split over the attack's n elements, per element absorb -1, immune 0,
    //      resist 1/2, weak or neutral 1; the sum below 0 heals (C2/FAD0);
    //   7  no x2 for a weakness: the target's Def/MDef is quartered when any element is a weakness (C2/6560);
    //   8  ignore-defense attacks (and heals) go through the defense step with Def 0, so Safe/Shell,
    //      Defend, row and Morph now apply to them (40/0140);
    //   9  half damage from ignore-defense attacks on monsters with byte $12 bit 1 (C0/D854);
    //   10 physical Defend 1/2 (as vanilla), magic Defend x170/256 (new), back row x170/256 (was 1/2),
    //      magic on a Morphed target x170/256 (was 1/2) (47/0CE4-0D1C);
    //   17 Atma Weapon: Level -> 2 x min(Stamina, 127) in its formula (40/78A0);
    //   40 a Morphed attacker x1.5, not x2 ($BC +1, C2/335F).
    // The game's +1 after each step is left to its own rounding: the factor is T-Edition's product over
    // the game's (within 1 of the SNES's integer steps for typical values).
    public static class DamageSteps
    {
        // the game's element responses (Last.Defaine ResistanceAttributeType): 401/402 = double weak/resist
        public const int Normal = 0, Weak = 1, Half = 2, Null = 3, Absorb = 4;
        public const double Quarter170 = 170.0 / 256.0;

        public enum View
        {
            None,       // the target's table as it is (no element, or one: the game's own response kept)
            AllNormal,  // every attack element reads neutral (the factor carries T-Edition's share)
            OneNull,    // the attack's elements sum to 0: one reads immune (no damage)
            OneAbsorb,  // the sum is below 0: one reads absorb (the game heals; the factor scales the heal)
        }

        public sealed class Hit
        {
            public bool Physical;          // Fight-type (Def, Safe, row, Defend) vs magic (MDef, Shell, Morph)
            public bool Heal;              // a recovery result (GetRecoveryStatus)
            public bool IgnoreDefense;     // the ability's "ignore defense" (content flag 5): T-Edition's rule 8/9 key
            public bool GameSkippedDefense; // the game skipped its defense block (flag 5, or Valiant Knife by weapon)
            public int Defense;            // the target's Def (physical) or MDef (magic)
            public bool Guard;             // Safe (physical) / Shell (magic) on the target
            public bool Defending;
            public bool BackRow;           // a character target in the back row, the attack respecting row
            public bool TargetMorph, AttackerMorph;
            public bool HalfFlag;          // a monster with T-Edition's byte $12 bit 1
            public IReadOnlyList<int> Elements = Array.Empty<int>();   // the target's response to each attack element
            public bool Atma;              // a strike with the Atma Weapon (the game's own formula runs)
            public int Level, Stamina;     // the attacker's (Atma)
        }

        public sealed class Result
        {
            public double Factor = 1.0;
            public View View = View.None;
            public bool ZeroDamage;        // T-Edition's elements sum to 0 (the view makes the game's 0)
            public bool HealsByElement;    // T-Edition's elements sum below 0 (the view makes the game's heal)
            public readonly List<(int Rule, string Text)> Fired = new List<(int, string)>();

            internal void Rule(int rule, string text) => Fired.Add((rule, text));
        }

        public static double ElementShare(int type) => type switch
        {
            Absorb => -1.0,
            Null => 0.0,
            Half or 402 => 0.5,
            _ => 1.0,                      // weak (1, 401) or neutral
        };

        // the game's single response to a one-element attack (factor on the damage, absorb as -1)
        public static double GameElement(int type) => type switch
        {
            Absorb => -1.0,
            Null => 0.0,
            Half => 0.5,
            402 => 0.25,
            Weak => 2.0,
            401 => 4.0,
            _ => 1.0,
        };

        public static bool IsWeak(int type) => type == Weak || type == 401;

        public static Result Apply(Hit h)
        {
            var r = new Result();
            var el = h.Elements ?? Array.Empty<int>();
            bool anyWeak = !h.Heal && el.Any(IsWeak);

            // --- 6: elements -------------------------------------------------------------------------
            if (!h.Heal && el.Count == 1)
            {
                int t = el[0];
                double gameEl = GameElement(t), tedEl = ElementShare(t);
                if (gameEl != 0 && Math.Abs(gameEl - tedEl) > 1e-9 && Math.Sign(gameEl) == Math.Sign(tedEl))
                {
                    r.Factor *= tedEl / gameEl;
                    r.Rule(6, $"one element ({TypeName(t)}): x{tedEl:0.##} instead of the game's x{gameEl:0.##}");
                }
            }
            else if (!h.Heal && el.Count >= 2)
            {
                double sum = el.Sum(ElementShare), share = sum / el.Count;
                string list = string.Join("+", el.Select(TypeName));
                if (sum > 0)
                {
                    r.View = View.AllNormal;
                    r.Factor *= share;
                    r.Rule(6, $"{el.Count} elements ({list}): damage x{share:0.###} (split, summed)");
                }
                else if (sum == 0)
                {
                    r.View = View.OneNull;
                    r.ZeroDamage = true;
                    r.Rule(6, $"{el.Count} elements ({list}): sum 0, no damage");
                }
                else
                {
                    r.View = View.OneAbsorb;
                    r.HealsByElement = true;
                    r.Factor *= -share;
                    r.Rule(6, $"{el.Count} elements ({list}): sum {sum:0.##}, heals x{-share:0.###}");
                }
            }

            // --- 7-10: the defense block -----------------------------------------------------------------
            bool tedDefense = !h.IgnoreDefense && !h.Heal;     // T-Edition's Def/MDef step (else Def 0)
            double game = 1.0, ted = 1.0;
            int def = Math.Clamp(h.Defense, 0, 255);
            bool gameBlock = !h.Heal && !h.GameSkippedDefense;
            if (gameBlock)
            {
                game *= (255 - def) / 256.0;
                if (h.Guard) game *= Quarter170;
                if (h.Physical)
                {
                    if (h.BackRow) game *= 0.5;
                    if (h.Defending) game *= 0.5;
                }
                else if (h.TargetMorph) game *= 0.5;
            }
            int tedDef = tedDefense ? (anyWeak ? def / 4 : def) : 0;
            ted *= (255 - tedDef) / 256.0;
            if (tedDefense && anyWeak && def > 0 && !r.ZeroDamage)
                r.Rule(7, $"weakness: {(h.Physical ? "Def" : "MDef")} {def} -> {tedDef} (no x2)");
            if (!tedDefense && !h.Heal && (h.Guard || h.Defending || h.BackRow || (h.TargetMorph && !h.Physical)))
                r.Rule(8, "ignore-defense attack meets Safe/Shell/Defend/row/Morph");
            if (h.Heal && (h.Guard || h.Defending || h.TargetMorph))
                r.Rule(8, "a heal meets Shell/Defend/Morph (x170/256 each)");
            if (h.Guard) ted *= Quarter170;
            if (h.Physical)
            {
                if (h.BackRow)
                {
                    ted *= Quarter170;
                    r.Rule(10, "back row x170/256 (not 1/2)");
                }
                if (h.Defending) ted *= 0.5;
            }
            else
            {
                if (h.Defending)
                {
                    ted *= Quarter170;
                    r.Rule(10, "magic on a defending target x170/256");
                }
                if (h.TargetMorph)
                {
                    ted *= Quarter170;
                    r.Rule(10, "magic on a Morphed target x170/256 (not 1/2)");
                }
            }
            if (h.HalfFlag && h.IgnoreDefense && !h.Heal)
            {
                ted *= 0.5;
                r.Rule(9, "ignore-defense attack on a half-damage monster: x1/2");
            }
            if (game > 1e-9) r.Factor *= ted / game;
            else if (ted > 1e-9) r.Factor *= ted * 256.0;   // the game's step left only its +1: an estimate

            // --- 17: Atma Weapon --------------------------------------------------------------------------
            if (h.Atma && h.Physical && !h.Heal && h.Level > 0)
            {
                int lv = 2 * Math.Min(Math.Max(h.Stamina, 0), 127);
                r.Factor *= (double)lv / h.Level;
                r.Rule(17, $"Atma Weapon: level {h.Level} -> 2 x Stamina {lv}");
            }

            // --- 40: Trance (Morph) attacker x1.5 ----------------------------------------------------------
            if (h.AttackerMorph)
            {
                r.Factor *= 0.75;
                r.Rule(40, "Morphed attacker x1.5 (the game's x2)");
            }
            return r;
        }

        // The target's element table as the game should read it for this attack (View): attack
        // elements neutral, or one of them immune / absorbing. Null: leave the table.
        public static Dictionary<int, int> ViewTable(IReadOnlyDictionary<int, int> table, IReadOnlyList<int> attack, View view)
        {
            if (view == View.None || attack == null) return null;
            var elems = attack.Where(a => a > 0).Distinct().ToList();
            if (elems.Count == 0) return null;
            var t = table == null ? new Dictionary<int, int>() : table.ToDictionary(kv => kv.Key, kv => kv.Value);
            foreach (var a in elems) t.Remove(a);
            if (view == View.OneNull) t[elems[0]] = Null;
            else if (view == View.OneAbsorb) t[elems[0]] = Absorb;
            return t;
        }

        public static string TypeName(int t) => t switch
        {
            Absorb => "absorb", Null => "immune", Half => "resist", 402 => "resist x2", Weak => "weak", 401 => "weak x2", _ => "neutral",
        };

        // the result as the game holds it: 1..cap (T-Edition's cap 32000 is the port's MAX_HIT_VALUE)
        public static int Scale(int value, double factor, int cap) =>
            Math.Clamp((int)Math.Round(value * factor), value > 0 ? 1 : 0, Math.Max(1, cap));
    }
}
