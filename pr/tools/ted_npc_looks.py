"""A PR look for each NPC sprite number T-Edition's new maps use (112 of them): data/ted_npc_looks.json, read
by tools/ted_map_events.py when it places the new maps' NPCs.

T-Edition renumbered its field sprites and redrew or recoloured many (its table: offsets F8/0400, banks
F8/0600, 2 bytes a slot; vanilla's: C0/D0F2 + C0/D23C, 165 slots; the bank word's high byte is 0x20 in
both), so a number means a sheet, not vanilla's NPC. In order:
  1. "voted": T-Edition's own NPCs on vanilla maps standing where a PR entity stands give their number the
     PR entity's look (event_translate.sprite_assets on T-Edition's ROM);
  2. "same sheet": its first frame is, byte for byte, a vanilla sprite's (a drawn frame, not a blank one):
     that vanilla number's look;
  3. "look-alike": the vanilla sheet whose silhouette (drawn pixels of the first two frames) is most alike,
     at least LIKE (intersection over union): the same figure redrawn or recoloured;
  4. none: listed (T-Edition's own figures: new PR sprites needed); placed with ted_map_events.DEFAULT_ASSET.
A vanilla number's PR look (mapobject.csv ids: mo_ff6_pNNN the cast, mo_ff6_nNNN_cMM townsfolk): the cast,
SNES 0-13, is mapobject 120 + n (p001-p014); the rest event_translate.sprite_assets on the US ROM, else a
looser vote here (`loose_votes`: one sighting within 2 tiles is enough).

  .venv/Scripts/python tools/ted_npc_looks.py
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitpath  # noqa: E402,F401
import prdata as P  # noqa: E402

OUT = os.path.join(P.ROOT, "data", "ted_npc_looks.json")
FRAME = 0xC0                 # one frame: 6 tiles (16x24)
VANILLA_SLOTS = 165          # (D23C - D0F2) / 2
LIKE = 0.9                   # silhouette IoU for a look-alike (same figures score 0.94-1.0; others <= 0.88)


def _file(bank, off):
    if bank >= 0xC0:
        return (bank - 0xC0) << 16 | off
    if 0x40 <= bank < 0x7E:
        return bank << 16 | off
    return None


def sheet(rom, slot, ted, size=2 * FRAME):
    """The first `size` bytes of a sprite number's sheet (None: no sheet)."""
    if ted:
        off = rom[0x380400 + 2 * slot] | rom[0x380401 + 2 * slot] << 8
        bank = rom[0x380600 + 2 * slot]
    else:
        if slot >= VANILLA_SLOTS:
            return None
        off = rom[0xD0F2 + 2 * slot] | rom[0xD0F3 + 2 * slot] << 8
        bank = rom[0xD23C + 2 * slot]
    f = _file(bank, off)
    if f is None or f + size > len(rom):
        return None
    return bytes(rom[f:f + size])


def pixels(raw):
    """4bpp SNES tiles -> colour indices (64 a tile)."""
    out = []
    for t in range(0, len(raw) - 31, 32):
        for y in range(8):
            p0, p1, p2, p3 = raw[t + 2 * y], raw[t + 2 * y + 1], raw[t + 16 + 2 * y], raw[t + 17 + 2 * y]
            for x in range(7, -1, -1):
                out.append((p0 >> x & 1) | (p1 >> x & 1) << 1 | (p2 >> x & 1) << 2 | (p3 >> x & 1) << 3)
    return out


def silhouette(raw):
    return [1 if p else 0 for p in pixels(raw)]


def iou(a, b):
    u = sum(x | y for x, y in zip(a, b))
    return sum(x & y for x, y in zip(a, b)) / u if u else 0.0


CAST = 14                    # SNES 0-13 -> mapobject 120-133 (mo_ff6_p001-p014)


def loose_votes(rom):
    """{SNES sprite: (PR asset ids)} from every NPC of `rom` standing within 2 tiles of a PR entity in its
    PR room (event_translate.sprite_assets wants 2 sightings within 1 tile)."""
    import event_translate as T
    import snes_maps as SM
    votes = collections.defaultdict(collections.Counter)
    for (m, n), det in T.snes_npcs(rom).items():
        r = SM.to_pr(m, det["x"], det["y"])
        if not r:
            continue
        best = None
        for layer, objs in T.pr_entities(r[0]):
            for name, x, y, eid, asset in objs:
                if eid and asset and name not in T.NOT_NPCS:
                    d = abs(x - r[1]) + abs(y - r[2])
                    if d <= 2 and (best is None or d < best[0]):
                        best = (d, asset)
        if best:
            votes[det["sprite"]][best[1]] += 1
    return {sp: tuple(a for a, _ in v.most_common()) for sp, v in votes.items()}


def build(log=print):
    import event_translate as T
    import snes_events as E
    import snes_maps as SM
    import ted_maps as TM
    ted = TM.rom()
    with open(P.VANILLA_ROM, "rb") as f:
        us = f.read()
    if len(us) % 0x8000 == 0x200:
        us = us[0x200:]
    use = collections.Counter(n["sprite"] for m in TM.new_maps(ted) for n in SM.npcs(ted, m, TM.TED))
    ted_votes = T.sprite_assets(TM.Builder().ev)
    usr = E.load("us")
    us_votes = dict(loose_votes(usr))
    us_votes.update({k: v for k, v in T.sprite_assets(usr).items() if v})
    us_votes.update({n: (120 + n,) for n in range(CAST)})
    us_sheets = {v: sheet(us, v, False) for v in range(VANILLA_SLOTS) if us_votes.get(v)}
    us_sheets = {v: s for v, s in us_sheets.items() if s}
    first = {}
    for v, s in us_sheets.items():
        if sum(1 for p in pixels(s[:FRAME]) if p) >= 32:       # a drawn frame
            first.setdefault(s[:FRAME], v)
    us_sil = {v: silhouette(s) for v, s in us_sheets.items()}
    out, none = {}, []
    for s in sorted(use):
        rec = {"placements": use[s]}
        raw = sheet(ted, s, True)
        if ted_votes.get(s):
            rec.update(how="voted", assets=list(ted_votes[s]))
        elif raw and raw[:FRAME] in first:
            v = first[raw[:FRAME]]
            rec.update(how="same sheet", vanilla=v, assets=list(us_votes[v]))
        elif raw:
            sil = silhouette(raw)
            sc, v = max((iou(sil, us_sil[v]), v) for v in us_sil)
            rec.update(nearest=v, likeness=round(sc, 3))
            if sc >= LIKE:
                rec.update(how="look-alike", vanilla=v, assets=list(us_votes[v]))
        else:
            rec["note"] = "no sheet in T-Edition's table"
        if "assets" not in rec:
            rec["how"] = "none"
            none.append(s)
        out[str(s)] = rec
    counts = collections.Counter(r["how"] for r in out.values())
    placed = collections.Counter()
    for r in out.values():
        placed[r["how"]] += r["placements"]
    doc = {"_": "T-Edition NPC sprite number -> PR look (asset ids, most often first); tools/ted_npc_looks.py",
           "counts": dict(counts), "placements": dict(placed), "none": none, "looks": out}
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    os.replace(tmp, OUT)
    log(f"NPC looks for {len(out)} sprite numbers: {dict(counts)}; placements {dict(placed)}; none: {none} -> {OUT}")
    return doc


def looks():
    """{sprite number: (asset ids)} from data/ted_npc_looks.json ({} before it's built)."""
    if not os.path.exists(OUT):
        return {}
    with open(OUT, encoding="utf-8") as f:
        doc = json.load(f)
    return {int(k): tuple(v["assets"]) for k, v in doc["looks"].items() if v.get("assets")}


if __name__ == "__main__":
    build()
