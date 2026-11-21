"""Offline checks of T-Edition's song pack (tools/ted_music.py; TedPlugin session).

    .venv/Scripts/python -m unittest tests/test_ted_music.py

Builds the pack from Mato's ROM into a temporary folder (skipped without the ROM) and checks what the plugin's
SNES player (PrKit/Snes) will read: the songs.json shape, T-Edition's own songs at their slots, bank-43 songs at
$100 + n, the PR bgm ids (1000 + slot), the map rules. How the songs sound is plugin/Snes.Tests' (render) and
tools/snes_song_ref.py's (against Snes9x) job.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PR = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PR, "tools"))
import ted_music as T  # noqa: E402


@unittest.skipUnless(os.path.exists(T.MATO), "no T-Edition ROM")
class TedMusicPack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="ted_music_test_")
        T.build(cls.dir, log=lambda *_: None)
        with open(os.path.join(cls.dir, "songs.json"), encoding="utf-8") as f:
            cls.pack = json.load(f)
        with open(os.path.join(cls.dir, "ted_music.json"), encoding="utf-8") as f:
            cls.rules = json.load(f)
        cls.slots = {s["slot"] for s in cls.pack["songs"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_pack_shape(self):
        self.assertEqual(self.pack["format"], "prkit-snes-songs/1")
        blob = os.path.getsize(os.path.join(self.dir, "songs.bin"))
        for s in self.pack["songs"] + self.pack["samples"]:
            self.assertLessEqual(s["offset"] + s["length"], blob)
        ids = {s["id"] for s in self.pack["samples"]}
        for s in self.pack["songs"]:
            self.assertEqual(len(s["instruments"]), 16)
            self.assertTrue(all(i == 0 or i in ids for i in s["instruments"]), f"song {s['slot']:X}: a sample missing")

    def test_own_songs(self):
        own = [s for s in self.slots if s < T.SECOND_SLOT]
        self.assertEqual(len(own), 175)                      # 0x55-0xFE and 5 in vanilla slots
        self.assertTrue({0x25, 0x38, 0x3F, 0x49, 0x51} <= self.slots)
        self.assertNotIn(0x2F, self.slots)                   # no song there (T-Edition plays fanfares via bank 43)
        self.assertNotIn(0x02, self.slots)                   # vanilla's songs stay the PR's tracks
        self.assertTrue(all(T.SECOND_SLOT <= s < 2 * T.SECOND_SLOT for s in self.slots if s >= T.SECOND_SLOT))

    def test_tracks(self):
        tracks = {int(k): v for k, v in self.rules["tracks"].items()}
        for s in self.slots:
            self.assertEqual(tracks.get(T.BGM_BASE + s), s, f"slot {s:X}")
        for k, v in tracks.items():                          # every track plays a song the pack has, or the game's own
            self.assertTrue(v in self.slots or self.rules["songs"].get("%X" % v, {}).get("pr_bgm"), f"track {k} -> {v:X}")

    def test_maps(self):
        maps = self.rules["maps"]
        self.assertGreater(len(maps), 100)
        for pr_id, m in maps.items():
            self.assertIn(m["slot"], self.slots)
            self.assertIn(T.BGM_BASE + m["slot"], m["from"])


    def test_battles(self):
        for key in ("battles", "fanfares"):
            self.assertGreater(len(self.rules[key]), 300, key)
            for party, b in self.rules[key].items():
                s = b["slot"]
                self.assertTrue(s == -1 or s in self.slots or self.rules["songs"].get("%X" % s, {}).get("pr_bgm"),
                                f"{key} {party} -> {s:X}")
        self.assertEqual(T.formation_music(self._rom(), 63)[0], 0x77)          # SF1 Battle #1 (CF/2F70)
        self.assertEqual(T.formation_music(self._rom(), 520)[1], 0xCF)         # its own victory fanfare (CF/B500)
        self.assertEqual(self.rules["pause_songs"], [0x24, 0x38, 0x14, 0x33])

    @staticmethod
    def _rom():
        return T.SS.unheader(open(T.MATO, "rb").read())


if __name__ == "__main__":
    unittest.main()
