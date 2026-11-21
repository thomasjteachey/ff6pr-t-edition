"""T-Edition's art for the Pixel Remaster (bc-sprites, for the T-Edition lead; pr/ted/MEDIA_PLAN.md "Graphics").

    python tools/ted_art.py monsters [--out data/ted_monster_images.json] [--sheet build/t-edition/art/monsters.png]

Monsters (MEDIA_INVENTORY.md 2): every T-Edition monster as the SNES draws it (tools/snes_sprites.py TEDITION layout, T-Edition's
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
import snes_sprites as SA  # noqa: E402  (Layout: T-Edition's moved tables)

TED_ROM = os.path.join(ROOT, "..", "build", "t-edition", "T-Edition 3.0.7 (Mato).sfc")
EX_ROM = os.path.join(ROOT, "..", "build", "t-edition", "T-Edition EX 2.0.6 (Mato).sfc")
EXT = os.path.join(ROOT, "mods", "TEditionPort", "monster_ext.json")
OUT = os.path.join(ROOT, "data", "ted_monster_images.json")
ASSET_BASE = 2000


def slot_table(rgba, table):
    """A color table {PR rgb: new rgb} in MonsterImages' slot form (no game colors in the data): (how many distinct
    opaque colors the source has, ["k:RRGGBB"]: the k-th of them, sorted as 0xRRGGBB, -> the new color)."""
    colors = sorted({rgba[i] << 16 | rgba[i + 1] << 8 | rgba[i + 2] for i in range(0, len(rgba), 4) if rgba[i + 3]})
    rank = {c: k for k, c in enumerate(colors)}

    def word(c):
        return c if isinstance(c, int) else c[0] << 16 | c[1] << 8 | c[2]
    missing = [c for c in table if word(c) not in rank]
    if missing:
        raise ValueError(f"color table keys not in the source image: {missing[:3]}")
    return len(colors), sorted((f"{rank[word(c)]}:{word(n):06x}" for c, n in table.items()),
                               key=lambda s: int(s.split(":")[0]))


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
                    n_colors, map_slots = slot_table(rgba, table)
                    images.append({"monster": e, "name": name, "key": key, "group": sgroup, "w": w, "h": h,
                                   "from": src, "from_sha1": PS.sha1(rgba), "colors": n_colors, "map_slots": map_slots,
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


# --- costumes -------------------------------------------------------------------------------------------------
#
# T-Edition's characters (MEDIA_INVENTORY.md 3; ROM read 2026-11-20): a look is a graphic slot, the byte the dressing
# room's events set with 37 (obj, slot) + 43 (obj, field palette); everything else is looked up by that slot:
#   field sheet   F8/0400 (2-byte offset) + F8/0600 (bank, then 0x20) per slot; banks C0-FF and 40-7D (ExHiROM)
#   battle sheet  42/6000 (3-byte pointer) per slot (C1/3D46): some differ from the field sheet
#   battle colors FE/F000 + 32 x [42/5E00 + slot] (C1/3E0A; vanilla C2/CE2B into ED/6300)
#   portrait      F8/0A00 (offset into 49/0000, 0x320 each) and F8/0B00 (palette id into 41/5200) per slot (C3/6EA8)
#   field colors  E6/8000 + 32 x the event's palette (as vanilla)
# The 56 costumes are slots 26-39 (costume 1), 40-53 (2), 54-67 (3), 68-72 and 76-84 (4), in no character order:
# which character wears which comes from the events (costume_slots).
COSTUMES = os.path.join(ROOT, "data", "ted_costume_art.json")
COSTUME_OUT = os.path.join(ROOT, "..", "build", "t-edition", "art", "costumes")
CAST = ["Terra", "Locke", "Cyan", "Shadow", "Edgar", "Sabin", "Celes", "Strago", "Relm", "Setzer", "Mog", "Gau",
        "Gogo", "Umaro"]
CHAMELEON = ["Leo", "Banon", "Trance Terra", "Merchant", "Ghost", "Kefka", "Gestahl", "Cid", "Daryl", "Rachel"]   # slots 16-25
ACCESSORY_LOOKS = [("kappa", 73), ("pig", 74)]   # relics Imp's Token / Piggy's Badge: battle sheets 39/3F80, 3E/C600
COSTUME_RANGES = [(1, range(26, 40)), (2, range(40, 54)), (3, range(54, 68)), (4, list(range(68, 73)) + list(range(76, 85)))]


def _file(bank, off):
    if bank >= 0xC0:
        return (bank - 0xC0) << 16 | off
    if 0x40 <= bank < 0x7E:
        return bank << 16 | off
    return None


def look(rom, slot, field_pal):
    """A graphic slot's sheets and colors: {field, battle (0x16A0-byte 4bpp sheets), field_pal, battle_pal (32 B),
    portrait (0x320 B), portrait_pal (32 B)}."""
    d = rom
    f = _file(d[0x380600 + 2 * slot], d[0x380400 + 2 * slot] | d[0x380401 + 2 * slot] << 8)
    p = 0x426000 + 3 * slot
    b = _file(d[p + 2], d[p] | d[p + 1] << 8)
    bp = 0x3EF000 + 0x20 * d[0x425E00 + slot]
    po = 0x490000 + (d[0x380A00 + 2 * slot] | d[0x380A01 + 2 * slot] << 8)
    pp = 0x415200 + 0x20 * d[0x380B00 + slot]
    return {"field": d[f:f + 0x16A0], "battle": d[b:b + 0x16A0], "field_pal": d[0x268000 + 0x20 * field_pal:][:0x20],
            "battle_pal": d[bp:bp + 0x20], "portrait": d[po:po + 0x320], "portrait_pal": d[pp:pp + 0x20],
            "at": {"field": f, "battle": b, "battle_pal": bp, "portrait": po, "portrait_pal": pp}}


def costume_slots(log=print):
    """Each character's looks from T-Edition's events (the slow part: a walk of all its event code): {name: [{costume,
    slot, pal}]}, costume 0 = the default (slot = the character's own)."""
    import snes_events as E
    import ted_events  # noqa: F401  (registers "ted")
    prog = E.Program(E.load("ted"))
    prog.walk_all()
    ins = [i for _, i in sorted(prog.code.items(), key=lambda kv: kv[0])]
    votes = collections.defaultdict(collections.Counter)    # (char, slot) -> palettes
    for k, i in enumerate(ins):
        if i.op != 0x37 or i.args["obj"] >= 14:
            continue
        c, s = i.args["obj"], i.args["gfx"]
        n = ins[k + 1] if k + 1 < len(ins) else None
        if n is not None and n.op == 0x43 and n.args.get("obj") == c:
            votes[(c, s)][n.args["pal"]] += 1
    out = {}
    for c, name in enumerate(CAST):
        looks = [{"costume": 0, "slot": c, "pal": votes[(c, c)].most_common(1)[0][0]}]
        for k, slots in COSTUME_RANGES:
            mine = [s for s in slots if votes[(c, s)]]
            if len(mine) != 1:
                raise SystemExit(f"{name} costume {k}: slots {mine}")
            looks.append({"costume": k, "slot": mine[0], "pal": votes[(c, mine[0])].most_common(1)[0][0]})
        out[name] = looks
    log("costume slots: " + "; ".join(f"{n} {[x['slot'] for x in v[1:]]}" for n, v in out.items()))
    return out


def costumes(out=COSTUME_OUT, walk=False, sheet=None, log=print):
    """Every character's 5 looks (default + 4 costumes) as ArtSwap folders <out>/<Name>_<costume>: the battle group
    (bc_ff6_pNNN), the field atlas (mo_ff6_pNNN: the field sheet's frames, which can differ) and the portrait
    (fa_ff6_pNNN). The slot table is data/ted_costume_art.json (rebuilt with walk=True)."""
    import shutil
    import snes_charsprites as C
    import pr_art
    rom = open(TED_ROM, "rb").read()
    if walk or not os.path.exists(COSTUMES):
        table = costume_slots(log)
        with open(COSTUMES, "w", encoding="utf-8") as f:
            json.dump({"_doc": "T-Edition's looks per character (tools/ted_art.py costumes): costume 0 = default, "
                       "1-4 the dressing room's; slot = the graphic slot the events set (37), pal = their field "
                       "palette (43). The art itself is read from the ROM by slot.", "characters": table}, f, indent=1)
    table = json.load(open(COSTUMES, encoding="utf-8"))["characters"]
    slots = C.data()["slots"]
    review = []
    default = os.path.join(out, "default")      # all 14 default looks in one folder (ArtSwap.Load, no layers needed)
    if os.path.isdir(default):
        shutil.rmtree(default)
    for c, name in enumerate(CAST):
        g = slots[str(c)]
        names = C.frame_names(g["battle"])
        for lk in table[name]:
            L = look(rom, lk["slot"], lk["pal"])
            folder = os.path.join(out, f"{name}_{lk['costume']}")
            if os.path.isdir(folder):
                shutil.rmtree(folder)
            for folder in ([folder, default] if lk["costume"] == 0 else [folder]):
                _write_look(pr_art.ArtWriter(folder), C, g, names, L, lk, name)
            review.append((name, lk, C.group_frames(L["battle"], L["battle_pal"], names),
                           C.group_frames(L["field"], C.palette(L["field_pal"]), names),
                           C.portrait(L["portrait"], L["portrait_pal"])))
    # the Imp status look (T-Edition redrew it as a toad: slot 15, the PR's Imp group) goes into default/
    imp = slots["15"]
    L = look(rom, 15, imp["palette"])
    _write_look(pr_art.ArtWriter(default), C, imp, C.frame_names(imp["battle"]), L, {"costume": 0, "slot": 15,
                                                                                    "pal": imp["palette"]}, "Imp")
    # T-Edition's own NPC sprites on the new maps (the audit's G6): free vanilla NPC groups redrawn, in default/
    import ted_npc_art
    ted_npc_art.write(default, log=log)
    ted_npc_art.write_story(default, log=log)
    # Gogo's Chameleon Robe: each battle one of 10 battle-only looks, the battle sheets of slots 16-25 (ROM read:
    # 42/6000 + its colors at 42/5E00) drawn on Gogo's battle group (no field atlas, no portrait)
    gogo = slots["12"]
    for k, form in enumerate(CHAMELEON):
        s = 16 + k
        L = look(rom, s, 0)
        folder = os.path.join(out, f"Gogo_chameleon_{k}")
        if os.path.isdir(folder):
            shutil.rmtree(folder)
        w = pr_art.ArtWriter(folder)
        frames = C.group_frames(L["battle"], L["battle_pal"], C.frame_names(gogo["battle"]))
        w.character(gogo["battle"], frames)
        w.art["ted"] = [{"character": "Gogo", "chameleon": form, "slot": s}]
        w.save()
        review.append((f"Gogo/{form}", {"costume": k % 5, "slot": s}, frames, {}, b"\0" * 6400))
    # the cosmetic relics Imp's Token (ImpToken, the kappa amulet) and Piggy's Badge (PigBadge), armor.html's relics 115
    # and 116 (Mato's scan tool calls them 0x115 "Kappa's Favor" / 0x116), draw the wearer in battle as a kappa
    # (battle slot 73) or a pig (74), statuses unchanged; one battle-only folder per character
    for acc, s in ACCESSORY_LOOKS:
        L = look(rom, s, 0)
        for c, name in enumerate(CAST):
            g = slots[str(c)]
            folder = os.path.join(out, f"{name}_{acc}")
            if os.path.isdir(folder):
                shutil.rmtree(folder)
            w = pr_art.ArtWriter(folder)
            frames = C.group_frames(L["battle"], L["battle_pal"], C.frame_names(g["battle"]))
            w.character(g["battle"], frames)
            w.art["ted"] = [{"character": name, "accessory": acc, "slot": s}]
            w.save()
        review.append((acc, {"costume": acc, "slot": s}, frames, {}, b"\0" * 6400))
    log(f"T-Edition looks: {len(review)} looks ({len(CAST)} characters x 5 + {len(CHAMELEON)} Chameleon Robe forms "
        f"+ {len(ACCESSORY_LOOKS)} relic looks x {len(CAST)}) "
        f"+ default in {out}")
    if sheet:
        costume_sheet(review, sheet)
    return review


def _write_look(w, C, g, names, L, lk, name):
    """One look into an ArtWriter folder: battle group, field atlas (its own sheet and colors), portrait."""
    w.character(g["battle"], C.group_frames(L["battle"], L["battle_pal"], names))
    png, rects = C.pack(C.group_frames(L["field"], C.palette(L["field_pal"]), names))
    fn = g["field"] + ".png"
    w.png(fn, png)
    w.art["atlases"][g["field"].upper()] = {n: {"png": fn, "rect": r, "pivot": [0.5, 0]} for n, r in rects.items()}
    w.face(g["face"], C.portrait(L["portrait"], L["portrait_pal"]))
    w.art.setdefault("ted", []).append({"character": name, "costume": lk["costume"], "slot": lk["slot"],
                                        "field_pal": lk["pal"]})
    w.save()


def costume_sheet(review, path, scale=2):
    from PIL import Image, ImageDraw
    show = ["Default_00", "WalkL_00", "Idle_00", "Win_00", "Down_00"]
    cw = (len(show) * 2 * 32 + 40 + 16) * scale
    rows = (len(review) + 4) // 5
    im = Image.new("RGBA", (5 * cw, rows * 44 * scale + 10), (52, 52, 60, 255))
    dr = ImageDraw.Draw(im)
    for n, (name, lk, battle, field, face) in enumerate(review):
        r, k = n // 5, n % 5
        x, y = k * cw, r * 44 * scale + 10
        dr.text((x + 2, y - 10), f"{name} {lk['costume']} (slot {lk['slot']})", fill=(255, 255, 0, 255))
        im.alpha_composite(Image.frombytes("RGBA", (40, 40), face).resize((40 * scale, 40 * scale), Image.NEAREST), (x, y))
        for j, nm in enumerate(show):
            for h, src in enumerate((field, battle)):
                if nm in src:
                    fr = Image.frombytes("RGBA", (32, 32), src[nm]).resize((32 * scale, 32 * scale), Image.NEAREST)
                    im.alpha_composite(fr, (x + (40 + 4 + (2 * j + h) * 32) * scale, y + 4 * scale))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("monsters")
    m.add_argument("--out", default=OUT)
    m.add_argument("--sheet", default=None, help="a review sheet: each converted monster beside the SNES's")
    p = sub.add_parser("apply", help="the monster art's rows on a port folder (ted_build does this)")
    p.add_argument("folder", nargs="?", default=os.path.join(ROOT, "mods", "TEditionPort"))
    c = sub.add_parser("costumes", help="every character's default look and 4 costumes as ArtSwap folders")
    c.add_argument("--out", default=COSTUME_OUT)
    c.add_argument("--walk", action="store_true", help="re-read the costume slots from the events (slow)")
    c.add_argument("--sheet", default=None)
    a = ap.parse_args()
    if a.cmd == "costumes":
        costumes(a.out, a.walk, a.sheet)
    elif a.cmd == "monsters":
        monsters(a.out, a.sheet)
    elif a.cmd == "apply":
        apply(a.folder)


if __name__ == "__main__":
    main()
