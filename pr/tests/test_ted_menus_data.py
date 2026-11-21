"""Offline checks of T-Edition's menu data tools (TedPlugin session): tools/ted_music_list.py, tools/ted_costumes.py.

    .venv/Scripts/python -m unittest tests/test_ted_menus_data.py

Small HTML fixtures in the guides' shapes (no game, no ROM); the committed data files when they exist.
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PR = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PR, "tools"))
import ted_costumes as C  # noqa: E402
import ted_music_list as M  # noqa: E402

SONGS_HTML = """<html><body><table>
<tr><td>Original BGM</td></tr>
<tr><th>No.</th><th>Song Name</th><th>Music Player Display Name</th><th>Notes</th><th>Song ID</th></tr>
<tr><td>001</td><td>予兆（１）</td><td>Opening Theme 1</td><td></td><td>02</td></tr>
<tr><td>002</td><td>予兆（２）</td><td>Opening Theme 2</td><td></td><td>03</td></tr>
<tr><td>Final Fantasy IV</td></tr>
<tr><td>120</td><td>ゴルベーザ</td><td>FF4 Golbez</td><td>Battle VS.<br>Golbez.</td><td>E9</td></tr>
<tr><td>Music Not Included in the Music Player (Victory Fanfares)</td></tr>
<tr><td>001</td><td>勝利</td><td>-</td><td>Fanfare</td><td>D2</td></tr>
</table></body></html>"""

COSTUMES_HTML = """<html><body>
<p>| Terra (ティナ)</p>
<p>Silk Dress: Hybrid</p><p>《 シルクのドレス : ハーフ 》</p>
<p>This costume is obtained in a treasure box in Maduin's House.</p>
<p>The BGM played in the Falcon while wearing this costume is "Romancing Saga 3: Catalina's Theme".</p>
<p>Flower Seller's Dress: Cetra</p><p>《 花売りのワンピース：古代種 》</p>
<p>This costume is obtained once you've cleared the achievement "Character Master".</p>
<p>The costume is designed after Aerith's dress from Final Fantasy VII.</p>
<p>The BGM played in the Falcon while wearing this costume is "Final Fantasy VII: Aerith's Theme".</p>
<p>▲</p>
</body></html>"""


class MusicList(unittest.TestCase):
    def test_parse(self):
        sections, songs = M.parse(SONGS_HTML)
        self.assertEqual(sections[0], "Original BGM")
        self.assertIn("Final Fantasy IV", sections)
        listed = [s for s in songs if s["in_player"]]
        self.assertEqual([s["no"] for s in listed], [1, 2, 120])
        self.assertEqual(listed[0]["name"], "Opening Theme 1")
        self.assertEqual(listed[0]["song"], 0x02)
        self.assertEqual(listed[2]["section"], "Final Fantasy IV")
        self.assertEqual(listed[2]["notes"], "Battle VS. Golbez.")
        fanfare = [s for s in songs if not s["in_player"]]
        self.assertEqual(len(fanfare), 1)
        self.assertEqual(fanfare[0]["song"], 0xD2)

    def test_data_file(self):
        if not os.path.exists(M.OUT):
            self.skipTest("no data/ted_music_player.json")
        with open(M.OUT, encoding="utf-8") as f:
            d = json.load(f)
        listed = [s for s in d["songs"] if s["in_player"]]
        self.assertGreater(len(listed), 200)
        self.assertEqual(len({s["no"] for s in listed}), len(listed))
        self.assertTrue(all(0 <= s["song"] <= 0xFF and s["name"] for s in listed))
        self.assertTrue(any(s["pr_bgm"] for s in listed), "no song with a PR track")


class Costumes(unittest.TestCase):
    def test_parse(self):
        chars = C.parse(C.text_lines(COSTUMES_HTML))
        self.assertEqual([c["name"] for c in chars], ["Terra"])
        cs = chars[0]["costumes"]
        self.assertEqual([k["name"] for k in cs], ["Silk Dress: Hybrid", "Flower Seller's Dress: Cetra"])
        self.assertIsNone(cs[0]["achievement"])
        self.assertEqual(cs[1]["achievement"], "Character Master")
        self.assertEqual(cs[1]["falcon_song"], "Final Fantasy VII: Aerith's Theme")
        self.assertIn("treasure box", cs[0]["unlock"])

    def test_data_file(self):
        if not os.path.exists(C.OUT):
            self.skipTest("no data/ted_costumes.json")
        with open(C.OUT, encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(len(d["characters"]), 14)
        self.assertTrue(all(len(c["costumes"]) == 4 for c in d["characters"]))
        self.assertTrue(all(k["falcon_song"] for c in d["characters"] for k in c["costumes"]))


if __name__ == "__main__":
    unittest.main()
