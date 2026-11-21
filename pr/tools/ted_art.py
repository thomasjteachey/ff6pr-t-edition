"""T-Edition's art for the Pixel Remaster (bc-sprites, for the T-Edition lead; pr/ted/MEDIA_PLAN.md "Graphics").

    python tools/ted_art.py monsters [--out data/ted_monster_images.json] [--sheet build/t-edition/art/monsters.png]

Monsters (MEDIA_INVENTORY.md 2): every T-Edition monster as the SNES draws it (tools/snes_sprites_at.py, T-Edition's
tables: entries CF/1A00, tiles F0/F4/F5 by monster id, palettes 41/6200; EX's bosses 512-539 from EX's own ROM by
their EX slot) is compared with vanilla's sprites the way tools/port_sprites.py compares BNW's (classify: same /
swap / recolor / new):
  same     vanilla's art in its slot (or a touch-up in vanilla's colors): nothing to do
  swap     exactly another vanilla monster: the PR row points at that monster's PR image (vanilla range only)
  recolor  a vanilla shape in T-Edition's colors: a color table over the PR art of the closest-colored vanilla
           monster of that shape (port_sprites' rule: the PR's shading kept)
  new      T-Edition's own art (98 new + EX's, and the 76 redrawn in 0-383): palette + pixels
The result is a recipe in MonsterImages' format (plugin/PrKit/MonsterImages.cs; BNW's bnw_data.json "monster_images"),
built into Magicite files on the player's machine at startup, and "assets": the monster_asset rows (2000 + e, key
{GROUP}_B{e:03}, in the group of the monster's own image or, for a new monster, of its stand-in: its shadow and
bestiary place) and which PR monster row (e + 1 below 384, 1000 + e above: tools/idmap.py) points at which.
Recolors keep the PR's own art: what ships is the color table (as BNW's), the art is the player's.

Dev PC only (reads the T-Edition, EX and vanilla ROMs and the game).
"""
import argparse
import base64
import collections
import hashlib
import json
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
try:
    import kitpath  # noqa: F401
except ImportError:
    pass
import snes_sprites_at as SA  # noqa: E402

TED_ROM = os.path.join(ROOT, "..", "build", "t-edition", "T-Edition 3.0.7 (Mato).sfc")
EX_ROM = os.path.join(ROOT, "..", "build", "t-edition", "T-Edition EX 2.0.6 (Mato).sfc")
EXT = os.path.join(ROOT, "mods", "TEditionPort", "monster_ext.json")
OUT = os.path.join(ROOT, "data", "ted_monster_images.json")
ASSET_BASE = 2000


def pr_id(e):
    return e + 1 if e < 384 else 1000 + e


def readers():
    """(vanilla sprites, T-Edition's sprite(e) for 0-539)."""
    import prdata as P
    import ff6snes as S
    van = SA.Sprites(S.rom_bytes(P.VANILLA_ROM), SA.VANILLA)
    ted = SA.Sprites(S.rom_bytes(TED_ROM), SA.TEDITION)
    ex = None
    if os.path.exists(EX_ROM):
        import ted_ex
        exs = SA.Sprites(S.rom_bytes(EX_ROM), SA.TEDITION)
        slot = {v: k for k, v in ted_ex.EX_IDS.items()}
        ex = lambda e: exs.sprite(slot[e]) if e in slot else None   # noqa: E731

    def sprite(e):
        return ted.sprite(e) if e < 512 else (ex(e) if ex else None)
    return van, sprite


def classify(V, by_size, b, i):
    """port_sprites.classify's decision for one T-Edition crop b of monster i: (kind, vanilla monster, diff)."""
    import port_sprites as PS
    if b.empty:
        return "empty", None, 1.0
    scored = []
    for j in by_size.get((b.w, b.h), ()):
        if sum(x != y for x, y in zip(V[j].mask, b.mask)) > 0.2 * len(b.mask):
            continue
        scored.append((PS.shape_diff(V[j], b), j != i, j))
    scored.sort()
    if not scored or scored[0][0] > 0.2:
        return "new", None, scored[0][0] if scored else 1.0
    family = [j for s, _, j in scored if s <= 0.2]
    c, _, j = min((PS.color_diff(V[j], b), j != i, j) for j in family)
    if c <= 4:
        return ("same" if j == i or (i < 384 and PS.color_diff(V[i], b) <= 4) else "swap"), j, scored[0][0]
    return "recolor", j, scored[0][0]


def monsters(out=OUT, sheet=None, log=print):
    import prdata as P
    import port_sprites as PS
    import pr_art
    van, sprite = readers()
    ext = json.load(open(EXT, encoding="utf-8"))["monsters"] if os.path.exists(EXT) else {}
    vmon, vasset = P.Table("monster"), P.Table("monster_asset")

    def asset_id(i):
        r = vmon.rows.get(i + 1)
        return int(r["monster_asset_id"]) if r else None

    def key_of(aid):
        a = vasset.rows.get(aid)
        return (a["group_name"], f"{a['group_name'].upper()}_{a['asset_name'].upper()}") if a else (None, None)
    V = [PS.Crop(van.sprite(i)) for i in range(384)]
    by_size = collections.defaultdict(list)
    for j, c in enumerate(V):
        if not c.empty:
            by_size[(c.w, c.h)].append(j)
    placeholder = asset_id(0)
    ids = list(range(384)) + sorted(int(e) for e in ext)
    images, assets, notes, left = [], [], collections.defaultdict(list), []
    review = []
    for e in ids:
        sp = sprite(e)
        if sp is None:
            left.append(f"{e} (no sprite)")
            continue
        b = PS.Crop(sp)
        kind, j, _ = classify(V, by_size, b, e)
        info = ext.get(str(e), {})
        name = info.get("name", "")
        if kind in ("same", "empty") and e < 384:
            continue
        own = e if e < 384 else info.get("template")          # the image group: own, or the stand-in's
        if own is None or asset_id(own) is None:
            left.append(f"{e} {name} (no stand-in)")
            continue
        group = key_of(asset_id(own))[0]
        aid = ASSET_BASE + e
        if kind == "same" or (kind == "swap" and e >= 384):
            # vanilla's art on a T-Edition id: the PR row points at that monster's image (the port does this already)
            assets.append({"monster": e, "pr_id": pr_id(e), "kind": kind, "asset_id": asset_id(j)})
            notes[kind].append(f"{e} {name} = {j}")
            continue
        if kind == "swap":
            assets.append({"monster": e, "pr_id": pr_id(e), "kind": "swap", "asset_id": asset_id(j)})
            notes["swap"].append(f"{e} = {j}")
            continue
        key = f"{group.upper()}_B{e:03d}"
        if kind == "recolor":
            fam = [k for k in range(384) if not V[k].empty and (V[k].w, V[k].h) == (V[j].w, V[j].h)
                   and PS.shape_diff(V[k], V[j]) <= 0.2 and asset_id(k) and asset_id(k) != placeholder]
            best = min(((sum(PS.dE(V[k].pal[v], b.pal[t]) for v, t in PS.pairing(V[k], b).items())
                         / max(1, len(PS.pairing(V[k], b))), k) for k in fam), default=None)
            if best is None:
                kind = "new"                                   # no PR art of its shape: its own pixels
            else:
                k = best[1]
                sgroup, src = key_of(asset_id(k))
                tex = PS.pr_textures(sgroup).get(src)
                if tex is None:
                    kind = "new"
                else:
                    w, h, rgba = tex
                    table = {c: n for c, n in PS.color_table(w, h, rgba, V[k], b).items() if c != n}
                    if not table:
                        notes["touch-up"].append(f"{e} {name}")
                        continue
                    key = f"{sgroup.upper()}_B{e:03d}"
                    img = pr_art.apply_table(rgba, table)
                    images.append({"monster": e, "name": name, "key": key, "group": sgroup, "w": w, "h": h,
                                   "from": src, "from_sha1": PS.sha1(rgba),
                                   "map": sorted(f"{PS.hexrgb(c)}:{PS.hexrgb(n)}" for c, n in table.items()),
                                   "sha1": PS.sha1(img), "thumb": PS.recolor_thumb(src, key, table)})
                    assets.append({"monster": e, "pr_id": pr_id(e), "kind": "recolor", "asset_id": aid,
                                   "group": sgroup, "asset_name": f"b{e:03d}", "from_asset": asset_id(k)})
                    notes["recolor"].append(f"{e} {name} <- {src}")
                    review.append((e, name, "recolor", sp, (w, h, img)))
                    continue
        # new art: T-Edition's own pixels and palette
        pal = sorted(set(b.idx) - {0})
        rgba = b"".join(bytes(b.pal[v]) + b"\xff" if v else b"\0\0\0\0" for v in b.idx)
        images.append({"monster": e, "name": name, "key": key, "group": group, "w": b.w, "h": b.h,
                       "palette": [PS.hexrgb(b.pal[v]) if v in pal else "000000" for v in range(len(b.pal))],
                       "pixels": base64.b64encode(zlib.compress(bytes(b.idx), 9)).decode("ascii"),
                       "sha1": PS.sha1(rgba), "thumb": PS.art_thumb(key, b.w, b.h, rgba)})
        assets.append({"monster": e, "pr_id": pr_id(e), "kind": "new", "asset_id": aid, "group": group,
                       "asset_name": f"b{e:03d}", "stand_in": own})
        notes["new"].append(f"{e} {name}")
        review.append((e, name, "new", sp, (b.w, b.h, rgba)))
    recipe = {"version": 1, "images": images}
    recipe["id"] = hashlib.sha1(json.dumps(recipe, sort_keys=True).encode()).hexdigest()[:16]
    doc = {"_doc": "T-Edition's monster art (tools/ted_art.py monsters): monster_images = a MonsterImages recipe "
                   "(PrKit/MonsterImages.cs: new art as palette + pixels, recolors as color tables over the player's "
                   "own PR art); assets = the monster_asset rows (asset_id, group, asset_name) and which PR monster "
                   "row points at which.",
           "monster_images": recipe, "assets": assets}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    counts = {k: len(v) for k, v in notes.items()}
    log(f"ted_art monsters: {counts}; {len(images)} images, {len(assets)} asset rows -> {out}"
        + (f"; left: {left}" if left else ""))
    if sheet:
        contact(review, sheet)
    return doc


def contact(review, path, scale=2):
    """Each converted monster next to how the SNES draws it (T-Edition's sprite as decoded)."""
    from PIL import Image, ImageDraw
    rows = []
    for e, name, kind, sp, (w, h, rgba) in review:
        c = SA.cropped(sp)
        snes = Image.frombytes("RGBA", (c[0], c[1]), c[2]) if c else None
        rows.append((f"{e} {name} ({kind})", snes, Image.frombytes("RGBA", (w, h), rgba)))
    cols = 4
    cw = 2 * 130 * scale + 20
    heights = [max(a.height if a else 0, b.height) * scale + 16 for _, a, b in rows]
    lines = [max(heights[i:i + cols]) for i in range(0, len(rows), cols)]
    im = Image.new("RGBA", (cols * cw, sum(lines) + 10), (50, 54, 80, 255))
    dr = ImageDraw.Draw(im)
    y = 0
    for r in range(0, len(rows), cols):
        for k, (label, snes, mine) in enumerate(rows[r:r + cols]):
            x = k * cw
            dr.text((x + 2, y + 1), label, fill=(255, 255, 0, 255))
            if snes:
                a = snes.resize((snes.width * scale, snes.height * scale), Image.NEAREST)
                im.paste(a, (x, y + 12), a)
            b = mine.resize((mine.width * scale, mine.height * scale), Image.NEAREST)
            im.paste(b, (x + 130 * scale + 10, y + 12), b)
        y += lines[r // cols]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)


def apply(folder, data=OUT, log=print):
    """The monster art's rows on a port folder (ted_build: the porter's output, before the merge; idempotent):
    each new or recolored image a monster_asset row of its own (the game's row of its source image, or of its
    stand-in for new art, with its id, group and name), and each listed PR monster row pointed at its image
    (swaps at the vanilla image they copy). The PNGs themselves are MonsterImages' (TedPlugin at startup)."""
    import ted_build as TB
    doc = json.load(open(data, encoding="utf-8"))
    mon, asset = TB.MasterRows(folder, "monster"), TB.MasterRows(folder, "monster_asset")
    vmon = asset.van
    missing, made, pointed = [], 0, 0
    for a in doc["assets"]:
        rid = a["pr_id"]
        if rid not in mon.ids():
            missing.append(rid)
            continue
        if a["kind"] in ("new", "recolor"):
            src = a.get("from_asset")
            if src is None:          # new art: the stand-in's image row (its shadow, its bestiary place)
                src = int(mon.van[a["stand_in"] + 1]["monster_asset_id"]) if a.get("stand_in") is not None else None
            tmpl = dict(vmon[src] if src in vmon.rows else next(iter(vmon)))
            tmpl.update(id=str(a["asset_id"]), group_name=a["group"], asset_name=a["asset_name"])
            asset.add(tmpl)
            made += 1
        row = mon.row(rid)
        if str(row["monster_asset_id"]) != str(a["asset_id"]):
            row["monster_asset_id"] = str(a["asset_id"])
            pointed += 1
    asset.save()
    mon.save()
    log(f"T-Edition monster art: {made} image rows, {pointed} monster rows pointed at their images"
        + (f"; no port row for {missing}" if missing else ""))
    return made, pointed, missing


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("monsters")
    m.add_argument("--out", default=OUT)
    m.add_argument("--sheet", default=None, help="a review sheet: each converted monster beside the SNES's")
    p = sub.add_parser("apply", help="the monster art's rows on a port folder (ted_build does this)")
    p.add_argument("folder", nargs="?", default=os.path.join(ROOT, "mods", "TEditionPort"))
    a = ap.parse_args()
    if a.cmd == "monsters":
        monsters(a.out, a.sheet)
    elif a.cmd == "apply":
        apply(a.folder)


if __name__ == "__main__":
    main()
