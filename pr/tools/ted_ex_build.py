"""T-Edition EX's boss room as a Magicite folder: pr/mods/TEditionEX (merged into mods/TEdition by
tools/ted_build.py with the porter's, ted-maps' and ted-events' folders: tools/magicite_merge.py).

    .venv/Scripts/python tools/ted_ex_build.py          (writes mods/TEditionEX and build/t-edition/ex/*)

What it holds (pr/ted/EX_PLAN.md; the user: the boss room, its 12 fights, Omega Weapon as a 13th):
  * EX's own attacks (31: Big Bang, Supernova, Grand Cross... written over T-Edition's 166-237 in EX) as
    abilities 7000 + SNES attack, each with the look of the vanilla spell of the same name or of its slot
    (port_spells.SpellPorter's templates and effects), named from Mato's EX tables;
  * the texts: EX's battle lines (TEDX_BTL_*), its menus and lines (TEDX_E<n>_*: story_mes/cha_en), the
    abilities' names (system_en);
  * EX's two shops as product groups 9228/9229 (TedPlugin answers the scripts' SysCall "TED:shop <group>");
  * the boss room: PR map 780 (Map_20451_90: ted_maps.convert_room of EX's map 471), its arrival and its way
    back to 3.0.7's Mog House (PR 700 point 90), the Moogle and the shopkeepers with their scripts (the
    scenes ted_ex_events translates: script.csv 9700+), and data/ted_ex_maps.json: the Mog House door that
    ted-maps' build adds to its copy of map 467;
  * build/t-edition/ex/ted_ex_ai.json: the bosses' SNES AI for TedPlugin (tools/ted_ex_ai.py).
The bosses' monster rows (1512-1539) and parties (30768-30792) are the porter's (port_monster_ext, fed by
ted_ex.ex_records() from profile_tedition.build).

Ids of its own rows come from reserved blocks, so a re-port of T-Edition (which allocates from the game's
maximum up) never lands on them: content 9000 + attack, function groups 9000+, condition groups 9000+.
Only this folder's own rows are written (partial master tables; text by key), as the merge expects.
"""
import collections
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitpath  # noqa: E402,F401
import prdata as P  # noqa: E402
import ted_ex as X  # noqa: E402

OUT = os.path.join(P.ROOT, "mods", "TEditionEX")
MASTER_PATH = "Assets/GameAssets/Serial/Data/Master"
MESSAGE_PATH = "Assets/GameAssets/Serial/Data/Message"
ABILITY_BASE = 7000          # EX's own attack s -> ability 7000 + s (the PR's abilities end at 5917;
CONTENT_BASE = 9000          # port_monster_ext's specials 6000-6539, port_ai's marks 7680+, item abilities 7700+)
FUNCTION_GROUP_BASE = 9000   # new function_group rows (the game's end at 2000)
CONDITION_ROW_BASE = 9000    # new condition_group rows (4201) and group ids (2002)


def ex_spells(R):
    """EX's own attacks as ff6snes.Spell records (EX's 14 bytes at C4/6AC0, as the US/JP table), named
    from Mato's EX tables: {attack: Spell}."""
    import ff6snes as S
    import ted_ex_ai as AI
    sai, _ = AI.export(R, log=lambda *a: None)
    ex_rom = S.Rom(X.EX_ROM)
    spells = S.spells(ex_rom)
    out = {}
    for s in sorted(int(k) for k in sai["attack_overrides"]):
        sp = spells[s]
        sp.name = R.spell(R.ex, s)
        out[s] = sp
    return out


def abilities(R, tables, messages, log=print):
    """Ability rows 7000 + s for EX's own attacks (+ content rows, names). -> {table: ids}."""
    import port_spells as PS
    import ff6snes as S
    van = S.Rom(P.VANILLA_ROM)
    sp = PS.SpellPorter(van, van, tables, {}, log)
    sp.next_fg = max(sp.next_fg, FUNCTION_GROUP_BASE)
    sp.next_cg_row = max(sp.next_cg_row, CONDITION_ROW_BASE)
    sp.next_group = max(sp.next_group, CONDITION_ROW_BASE)
    content = tables.setdefault("content", P.Table("content"))
    changed = collections.defaultdict(set)
    names = {}
    for s, b in ex_spells(R).items():
        k = ABILITY_BASE + s
        tslot, matched = sp.template(s, b.name)
        tmpl_spell = sp.vsp[tslot]
        tmpl_row = sp.vab[sp_spell(tslot)]
        new = dict(tmpl_row)
        new["id"], new["sort_id"] = str(k), str(k)
        new["use_value"] = str(b.mp)
        direct = tmpl_row["standard_value"] == str(tmpl_spell.power)
        new["standard_value"] = str(b.power) if direct else tmpl_row["standard_value"]
        new["accuracy_rate"] = sp.convert(sp.maps.get("accuracy_rate"), b.accuracy, tmpl_row["accuracy_rate"])
        for col in ("attribute_id", "attribute_group_id"):
            new[col] = sp.convert(sp.maps.get(col), b.elements, tmpl_row[col])
        for col in ("renge_id", "battle_renge_id", "menu_renge_id"):
            new[col] = sp.convert(sp.maps.get(col), b.targets, tmpl_row[col])
        new["battle_function_group_id"] = str(sp.effects(tmpl_spell, tmpl_row, b))
        sp.ab.rows[k] = new
        changed["ability"].add(k)
        cid = CONTENT_BASE + s
        tmpl_content = sp.content_by_ability.get(sp_spell(tslot))
        key = f"TEDX_ABILITY_NAME_{k}"
        row = dict(tmpl_content) if tmpl_content else {"id": "", "mes_id_name": "", "mes_id_battle": "None",
                                                         "mes_id_description": "None", "icon_id": "0",
                                                         "type_id": "4", "type_value": ""}
        row.update(id=str(cid), mes_id_name=key, type_value=str(k), mes_id_description="None")
        content.rows[cid] = row
        changed["content"].add(cid)
        messages[key] = b.name
        names[s] = (b.name, tslot, matched)
    for t, ids in sp.changed.items():
        if t != "ability":
            changed[t] |= ids
    log(f"EX attacks: {len(names)} abilities {ABILITY_BASE}+; looks: "
        + ", ".join(f"{s} {n} <- {t}{'' if m else ' (slot)'}" for s, (n, t, m) in names.items()))
    return changed


def shops(tables, log=print):
    """EX's two boss-room shops as product groups 9100 + merged shop (9228, 9229), stock rows from 9000
    (the shopkeepers' scripts open them: SysCall "TED:shop <group>", ted_ex_events.shop_ops). Item rows are
    T-Edition's (its item identity, as ted_events reads them)."""
    import idmap as M
    import ted_events as TE
    import ted_ex_events as XE
    groups = tables.setdefault("product_group", P.Table("product_group"))
    product = tables.setdefault("product", P.Table("product"))
    template = product.rows[min(product.rows)]
    changed = collections.defaultdict(set)
    saved = dict(M.ITEM_OVERRIDES)
    M.ITEM_OVERRIDES.clear()
    M.ITEM_OVERRIDES.update(TE.item_overrides())
    try:
        d = X.Roms().ex
        pid = PRODUCT_BASE
        for ex_shop, shop in sorted(XE.SHOPS.items()):
            g = XE.shop_group(shop)
            groups.rows[g] = {"id": str(g), "mes_id_name": "MSG_SYSTEM_433"}      # "Items"
            changed["product_group"].add(g)
            raw = d[X.SHOPS + 9 * ex_shop:X.SHOPS + 9 * ex_shop + 9]
            for item in raw[1:]:
                if item == 0xFF:
                    continue
                product.rows[pid] = dict(template, id=str(pid), content_id=str(M.item_content(item)), group_id=str(g),
                                         coefficient="0", purchase_limit="0")
                changed["product"].add(pid)
                pid += 1
    finally:
        M.ITEM_OVERRIDES.clear()
        M.ITEM_OVERRIDES.update(saved)
    log(f"shops: product groups {sorted(changed['product_group'])}, {len(changed['product'])} products")
    return changed


PRODUCT_BASE = 9000          # product rows of EX's shops (the game's end at 633)


def sp_spell(slot):
    import idmap as M
    return M.spell(slot)


def write(out, tables, changed, texts):
    """Partial master tables (header + this folder's rows) and text files (this folder's keys)."""
    mdir = os.path.join(out, "master")
    keys, values = [], []
    for name, ids in sorted(changed.items()):
        if not ids:
            continue
        path = os.path.join(mdir, *MASTER_PATH.split("/"), name + ".csv")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(tables[name].to_csv(sorted(ids)))
        keys.append(name)
        values.append(f"{MASTER_PATH}/{name}")
    if keys:
        os.makedirs(os.path.join(mdir, "keys"), exist_ok=True)
        with open(os.path.join(mdir, "keys", "mod_master.json"), "w", encoding="utf-8") as fh:
            json.dump({"keys": keys, "values": values}, fh, indent=2)
    gdir = os.path.join(out, "message")
    files = {n: t for n, t in texts.items() if t}
    for fname, lines in files.items():
        path = os.path.join(gdir, *MESSAGE_PATH.split("/"), fname + ".txt")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            for k in sorted(lines):
                fh.write(f"{k}\t{lines[k]}\r\n")
    if files:
        os.makedirs(os.path.join(gdir, "keys"), exist_ok=True)
        with open(os.path.join(gdir, "keys", "mod_message.json"), "w", encoding="utf-8") as fh:
            json.dump({"keys": list(files), "values": [f"{MESSAGE_PATH}/{n}" for n in files]}, fh, indent=2)


# --- the boss room (EX's map 471) and the Mog House door ------------------------------------------------
ROOM_MAP_ID = ROOM_SCRIPT_ID = 780   # ted-maps' ids for it (its own rooms: 644-779 / 629-779)
ROOM_N = 90                          # Map_<group>_90: ted-maps' rooms take the next free numbers below
MOG_HOUSE = (700, 90)                # 3.0.7's Mog House (map 467) is ted-maps' Map_20011_15 = PR 700; point 90 ours
ROOM_POINT = 1                       # the boss room's arrival, from the Mog House's new door
MAPS_JSON = os.path.join(P.ROOT, "data", "ted_ex_maps.json")
MOOGLE_ASSET = 130                   # the PR's moogle (vanilla Mog NPCs, SNES sprite 10)
DIRECTION = {0: 1, 1: 2, 2: 4, 3: 8}  # SNES facing -> PR direction bits (as ted_maps)
OLD_DOOR = ((80, 37), (79, 35))      # CD/A090's first two commands: they close 3.0.7's Developers' Room door


def mog_house_door():
    """EX's Mog House changes for ted-maps' build (data/ted_ex_maps.json: it applies them on its copy of
    3.0.7's map 467): the cells EX's entrance event CD/A090 draws for the new door (its first two
    commands close 3.0.7's door to the Developers' Room: left out, that door stays), the door
    (79, 26) -> the boss room, and the arrival (79, 28) the boss room's way back comes to."""
    import snes_events as E
    import ted_events as TE
    import ted_maps as TM
    ev = TE.load("ted-ex")
    cmds = TM.entrance_tiles(ev, E.parse_addr("CD/A090"))
    tiles = [[c[0], c[1], c[2], c[3], list(c[4])] for c in cmds if (c[0], c[1] & 0x3F) not in OLD_DOOR]
    return {"467": {"tiles": tiles,
                    "exits": [{"tiles": [[79, 26]], "to": [ROOM_MAP_ID, ROOM_POINT], "facing": 0}],
                    "points": [{"x": 79, "y": 28, "point_id": MOG_HOUSE[1], "facing": 2}]},
            "_about": "tools/ted_ex_build.py: T-Edition EX's door from 3.0.7's Mog House (467) to its boss room (PR 780)"}


def npc_object(x, y, asset, script_id, facing, name):
    """An NPC entity (the PR shopkeeper port_merchants copies, its look and script replaced)."""
    import port_merchants as PM
    o = PM.template_npc()
    props = {q["name"]: q["value"] for q in o["properties"]}
    props.update(asset_id=asset, script_id=script_id, direction=DIRECTION.get(facing, 4), entity_id=0)
    return {"name": name, "x": x, "y": y, "gid": o["gid"], "properties": props}


def room(R, out, scripts, script_ids, log=print):
    """EX's boss room as PR map 780 (ted_maps.convert_room: its layout drawn by its entrance event EA/0000,
    converted in the PR map group that draws it best), with its arrival, its way back to the Mog House,
    the Moogle and the two shopkeepers (their scripts: `scripts` {name: PR script}, ids `script_ids`).
    The six sprite-101 objects around the Moogle are left out (their PR look isn't known yet).
    -> (PR map name, group)."""
    import port_merchants as PM
    import snes_maps as SM
    import snes_rooms as RM
    import ted_events as TE
    import ted_maps as TM
    t = R.maps[0]
    ev = TE.load("ted-ex")
    entrance = TM.entrance_event(R.ex, X.HUB_MAP)
    p = SM.properties(R.ex, X.HUB_MAP, t.props)
    base = [SM.layout(R.ex, X.HUB_MAP, k, t=t) for k in (0, 1, 2)]
    bg1, _, _ = TM.apply_tiles(base, (p["bg1_size"], p["bg2_size"], p["bg2_size"]), TM.entrance_tiles(ev, entrance))
    group = RM.model(R.ex, X.HUB_MAP, t.props, rows=bg1, t=t).group
    name = f"Map_{group[4:]}_{ROOM_N}"
    npcs = {r["index"]: r for r in R.map_data("ex", X.HUB_MAP)["npcs"]}
    shopkeeper = {q["name"]: q["value"] for q in PM.template_npc()["properties"]}["asset_id"]
    objects = [
        {"name": "PointIn", "x": 24, "y": 31, "gid": TM.POINT_GID, "properties": {
            "direction": DIRECTION[0], "entity_id": 0, "link_object_id": 0, "object_id": ROOM_POINT,
            "object_type": 0, "title_id": "", "title_type": 0}},
        TM.Builder.goto(24, 32, MOG_HOUSE, 2),
    ]
    for n, (sc, asset, label) in {0: ("sc_tedx_moogle", MOOGLE_ASSET, "EX Moogle"),
                                  1: ("sc_tedx_shop_items", shopkeeper, "EX shop: items"),
                                  2: ("sc_tedx_shop_cures", shopkeeper, "EX shop: cures")}.items():
        r = npcs[n]
        objects.append(npc_object(r["x"], r["y"], asset, script_ids[sc], r["direction"], label))
    TM.convert_room(R.ex, X.HUB_MAP, t, ev, out, name, ROOM_MAP_ID, ROOM_SCRIPT_ID, objects, group=group,
                    entrance=entrance)
    # the scenes' scripts in the room's folder, listed in its package entry and keys
    folder = name.rsplit("_", 1)[0]
    dest = os.path.join(out, group, *RM.RES.split("/"), folder, name)
    pkg_path = os.path.join(out, group, *RM.RES.split("/"), folder, "package.json")
    with open(pkg_path, encoding="utf-8") as fh:
        pkg = json.load(fh)
    entry = next(e for e in pkg["map"] if e["name"] == name)
    assets = []
    for sn, sc in scripts.items():
        with open(os.path.join(dest, sn + ".json"), "w", encoding="utf-8") as fh:
            json.dump(sc, fh, ensure_ascii=False, separators=(",", ":"))
        if not any(x["name"] == sn for x in entry["script"]):
            entry["script"].append({"name": sn, "asset": f"{name}/{sn}"})
        assets.append((f"{name}/{sn}", f"{RM.RES}/{folder}/{name}/{sn}"))
    with open(pkg_path, "w", encoding="utf-8") as fh:
        json.dump(pkg, fh, ensure_ascii=False)
    RM.add_keys(out, group, "tedx_scripts", assets)
    log(f"boss room: {name} (PR {ROOM_MAP_ID}) in {group}; {len(scripts)} scripts; way back to PR {MOG_HOUSE[0]} "
        f"point {MOG_HOUSE[1]}")
    return name, group


def build(out=OUT, log=print, with_room=True):
    import ted_events as TE
    import ted_ex_ai as AI
    import ted_ex_events as XE
    R = X.Roms()
    tables, system, story, cha = {}, {}, {}, {}
    changed = collections.defaultdict(set)
    for t, ids in abilities(R, tables, system, log).items():
        changed[t] |= ids
    for t, ids in shops(tables, log).items():
        changed[t] |= ids
    rows, specials = AI.port_data()
    sai, line_texts = AI.export(R, party_rows=rows, specials=specials, log=log)
    story.update(line_texts)
    # the scenes (ted-events' translator) and their script.csv rows (ted_events.EX_SCRIPT_IDS, 9700-9799)
    res, texts, alloc = XE.translate(log=log)
    ids = TE.ScriptIds(XE.SCRIPT_IDS_FILE, ids=TE.EX_SCRIPT_IDS)
    scripts = {}
    for name, sc, after, t in res:
        if name == "sc_tedx_room_enter":    # the room is drawn already; the Moogle's dance needs its entity
            continue
        scripts[name] = sc
        for an, asc, _ in after:
            scripts[an] = asc
    st = tables.setdefault("script", P.Table("script"))
    script_ids = {}
    for n in scripts:
        sid = ids.get(n)
        st.rows[sid] = {"id": str(sid), "script_name": n}
        changed["script"].add(sid)
        script_ids[n] = sid
    story.update(texts["story_mes_en"])
    cha.update(texts["story_cha_en"])
    if os.path.isdir(out):
        shutil.rmtree(out)
    write(out, tables, changed, {"system_en": system, "story_mes_en": story, "story_cha_en": cha})
    if with_room:
        room(R, out, scripts, script_ids, log)
        with open(MAPS_JSON, "w", encoding="utf-8") as fh:
            json.dump(mog_house_door(), fh, indent=1)
    ids.save()
    alloc.save()
    os.makedirs(X.OUT, exist_ok=True)
    with open(AI.OUT, "w", encoding="utf-8") as fh:
        json.dump({"snes_ai": sai}, fh, indent=1, ensure_ascii=False)
    log(f"TEditionEX -> {out}: tables {', '.join(f'{t} {len(i)}' for t, i in sorted(changed.items()))}; "
        f"{len(system)} system texts, {len(story)} story texts; AI -> {AI.OUT}")
    return changed


if __name__ == "__main__":
    build()
