"""Rule 49 (percent damage) on a copy of T-Edition's staged port (tools/ted_plugin_data.percent_damage; TedPlugin
session).

    .venv/Scripts/python -m unittest tests/test_ted_percent_damage.py

Copies mods/TEdition's ability / function_group / item CSVs to a temporary folder (skipped without the ROM or the
port), runs the rule twice and checks what the game will read: the ten listed spells on current HP at T-Edition's
power, the others on max HP (the end state, whether or not the build already applied the rule), spells that are no percent spells in T-Edition back on plain damage, revives at
T-Edition's power, and nothing more to do on the second run.
"""
import csv
import glob
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PR = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PR, "tools"))
import ted_plugin_data as X  # noqa: E402

MASTER = os.path.join("master", "Assets", "GameAssets", "Serial", "Data", "Master")
SRC = os.path.join(PR, "mods", "TEdition")
MATO = os.path.join(os.path.dirname(PR), "build", "t-edition", "T-Edition 3.0.7 (Mato).sfc")


def table(folder, name):
    rows = {}
    for root in (os.path.join(PR, "vanilla"), folder):
        path = os.path.join(root, MASTER, name + ".csv")
        if os.path.exists(path):
            with open(path, encoding="utf-8", newline="") as f:
                for r in csv.DictReader(f):
                    rows[int(r["id"])] = r
    return rows


@unittest.skipUnless(os.path.exists(MATO) and os.path.exists(os.path.join(SRC, MASTER, "ability.csv")), "no ROM or port")
class PercentDamage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="ted_rule49_")
        os.makedirs(os.path.join(cls.dir, MASTER))
        for name in ("ability", "function_group", "item"):
            path = os.path.join(SRC, MASTER, name + ".csv")
            if os.path.exists(path):
                shutil.copy2(path, os.path.join(cls.dir, MASTER))
        keys = glob.glob(os.path.join(SRC, "master", "keys", "*.json"))
        if keys:
            os.makedirs(os.path.join(cls.dir, "master", "keys"))
            shutil.copy2(keys[0], os.path.join(cls.dir, "master", "keys"))
        cls.first = X.percent_damage(cls.dir, log=lambda *_: None)
        cls.second = X.percent_damage(cls.dir, log=lambda *_: None)
        cls.ab, cls.fg = table(cls.dir, "ability"), table(cls.dir, "function_group")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def funcs(self, ability):
        g = self.fg[int(self.ab[ability]["battle_function_group_id"])]
        return [tuple(int(g[f"function{k}_{c}"]) for c in ("id", "value1", "value2", "value3")) for k in (1, 2, 3)]

    def fraction(self, ability, fid=X.FRACTION):
        return next((f[2], f[3]) for f in self.funcs(ability) if f[0] == fid)

    def test_listed_spells_keep_current_hp(self):
        self.assertIn(self.fraction(70), ((2, 50), (3, 2)))          # Gravity, power 8
        self.assertEqual(self.fraction(315), (2, 63))                # Whirlwind, power 10 (the porter's template: 94%)
        self.assertEqual(self.fraction(342), (3, 4))                 # Launcher, power 4
        self.assertEqual(self.fraction(358), (3, 2))                 # Missile, power 8

    def test_others_take_max_hp(self):
        self.assertEqual(self.fraction(109), (4, 75))                # Diabolos, power 12 (the port: plain magic)
        self.assertEqual(self.fraction(320), (4, 56))                # Wave Cannon, power 9
        self.assertEqual(self.fraction(110, X.REVIVE), (4, 63))      # Phoenix revives with 10/16 of max HP
        self.assertEqual(self.fraction(31, X.REVIVE), (5, 4))        # Raise, power 4

    def test_reraise_revives_as_raise(self):
        self.assertEqual(self.fraction(X.RERAISE_ABILITY, X.REVIVE), (5, 4))   # rule 57: T-Edition's Raise, power 4

    def test_not_percent_in_tedition(self):
        self.assertFalse(any(f[0] == X.FRACTION for f in self.funcs(186)))   # Snowball: power 58 magic
        self.assertIn((3, 1, 0, 0), self.funcs(186))

    def test_idempotent(self):
        # the port may already carry the rule (ted_build applies it): the end state is checked above, and a
        # second run finds nothing left to do
        self.assertEqual((self.second["edited"], self.second["cloned"], self.second["moved"]), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
