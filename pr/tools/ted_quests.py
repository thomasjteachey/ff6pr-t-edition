"""T-Edition's pub quests (Mato's README "NEW PUB QUEST DETAILS": 20 quests behind six pub owners) as PR
scripts in their PR rooms: the Magicite folder pr/mods/TEditionQuests (merged by tools/ted_build.py).

    .venv/Scripts/python tools/ted_quests.py              build mods/TEditionQuests (+ build/t-edition/quests/report.json)
    .venv/Scripts/python tools/ted_quests.py scope        the quest events and how each translates (no writing)

Events: those ted-events' catalog tags with owner "ted-ex" (data/snes_event_ted_catalog.json), else this
batch (BATCH): the pub owners' job menus and the quest steps that are NPCs on vanilla maps. Each is translated
by ted-events' translator (ted_events._translator_class(): Mato's text as TED_* keys, the shared flags,
T-Edition's own bits, porter-gated battles) and wired onto the PR NPC standing at its SNES spot in every PR
version of the room (snes_maps.pr_maps: WoB and WoR rooms are separate PR maps): the NPC's entity in each
layer gets the new script (script.csv 9716-9799, ids kept in data/ted_quests_scripts.json); where the PR NPC
already had a script and the SNES event falls back to vanilla's talk, the PR script is grafted in there.
Unlike ted_events.build this also wires NPCs the PR gave no script (pub owners standing at the counter).
Event tiles, entrance events and quests on T-Edition's new maps (ted-maps' rooms) are listed as pending.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitpath  # noqa: E402,F401
import prdata as P  # noqa: E402

OUT = os.path.join(P.ROOT, "mods", "TEditionQuests")
IDS_FILE = os.path.join(P.ROOT, "data", "ted_quests_scripts.json")
SCRIPT_IDS = list(range(9716, 9800)) + list(range(12000, 12500))   # the lead: 9716-9799, then 12000-12499
REPORT = os.path.join(P.ROOT, "build", "t-edition", "quests", "report.json")
KEYS_NAME = "ted_quests"
RES = "Assets/GameAssets/Serial/Res/Map"

# the six pubs (SNES map: town) and the batch: (SNES event, short name, quest(s))
PUBS = {78: "South Figaro", 172: "Nikeah", 191: "Kohlingen", 330: "Albrook", 461: "Narshe", 225: "Zozo"}
BATCH = [
    ("CA/7D09", "pub_sfigaro", "Cave Monster Cleanup, Defend Mt. Kolts!, Cave Fiend Crackdown, A Girl's Wish, Victory Drink"),
    ("CA/8FED", "pub_nikeah", "I'll Buy Anything!, Supply Haul, Melancholy of a Dancer, Staying Strong"),
    ("CC/6F1F", "pub_kohlingen", "Rest in Peace"),
    ("CD/3DB4", "pub_albrook", "Merchandise Delivery, Ingredient Hunt, Research Assistant"),
    ("CD/FAC0", "pub_zozo", "Super Doctor D"),
    ("CA/8FFF", "nikeah_dancer", "Melancholy of a Dancer"),
    ("CD/5BA0", "mobliz_duane_a", "Supply Haul, Staying Strong"),
    ("CD/5C60", "mobliz_duane_b", "Supply Haul, Staying Strong"),
    ("CC/6565", "merchandise_recipient", "Merchandise Delivery"),
]


def nop_stubs(sc):
    """The translator's unknown commands (SysCall "SNES:<command>") as Nops, the SNES bytes kept in the
    comment (the lead, 2026-11-20: an unknown SysCall is a risk in game, a Nop isn't). -> how many."""
    n = 0
    for m in sc.get("Mnemonics", []):
        sv = m.get("operands", {}).get("sValues") or [""]
        if m.get("mnemonic") == "SysCall" and str(sv[0]).startswith("SNES:"):
            m["comment"] = f"{sv[0]} {m.get('comment', '')}".strip()
            m["mnemonic"] = "Nop"
            m["operands"]["sValues"] = [""] * len(sv)
            n += 1
    return n


NEW_OBJECT_BASE = 5500   # Tiled object ids this folder adds to vanilla rooms (the lead: 5000+; ted-events 5000-5499,
                         # ted-ex 5500-5999, ted-maps 3000+; vanilla's highest is 921)


def _place_npc(rom, prog, Tr, texts, alloc, ids, mod, m, det, addr, name, scripts, added):
    """A new NPC entity in the PR room at the SNES NPC's spot (snes_maps.to_pr), the look event_translate
    learned for its sprite (else port_merchants' shopkeeper), running the event's script. -> wired row."""
    import event_translate as T
    import port_merchants as PM
    import snes_events as E
    import snes_maps as SM
    hit = SM.to_pr(m, det["x"], det["y"])
    if not hit:
        return None
    pr, px, py = hit
    path = SM.pr_tilemaps().get(pr)
    if not path:
        return None
    room = os.path.dirname(path)
    group, folder = _room_of(pr)
    sn = "sc_tedq_%s_%s_new" % (name, pr[4:].lower())
    t = Tr(rom, sn, snes_map=m, alloc=alloc, prog=prog, pr_map=pr)
    t.texts = texts
    sc = t.translate(E.parse_addr(addr))
    scripts[(group, folder, pr)].append((sn, sc))
    for a, s2, w in t.after:
        where = _room_of(w) if w and w != pr else (group, folder)
        if where is not None:
            scripts[(where[0], where[1], w or pr)].append((a, s2))
    sid = ids.get(sn)
    mod.table("script").add({"script_name": sn}, id=sid)
    o = PM.template_npc()
    props = {q["name"]: q["value"] for q in o["properties"]}
    asset = (T.sprite_assets(rom).get(det["sprite"]) or (props["asset_id"],))[0]
    props.update(asset_id=asset, script_id=sid, entity_id=0, direction={0: 1, 1: 2, 2: 4, 3: 8}.get(det.get("direction", 2), 4))
    added[(room, group, folder, pr)].append({"name": f"T-Edition NPC {addr}", "x": px, "y": py, "gid": o["gid"],
                                             "properties": props})
    return {"pr_map": pr, "layer": "entity_default", "object": "new", "was": None, "now": sn, "script_id": sid,
            "asset_id": asset, "translated": sum(t.done.values()), "stubs": dict(t.stubs),
            "needs_formations": sorted(t.needs_formations)}


VANILLA_NPC_BASE = 5900          # entity ids of vanilla NPCs placed anew (ted-ex's 5500-5999; _place_npc's 5500+)
STANDINS_FILE = os.path.join(P.ROOT, "data", "ted_quests_npc_standins.json")   # for bc-sprites, as ted-events'


def _place_vanilla_npc(rom, prog, Tr, texts, alloc, ids, mod, m, det, addr, name, scripts, fixed, hidden,
                       standins, taken_ms):
    """A vanilla NPC the PR room has none of (no PR NPC within 3 tiles; the lead, 11-21): a new NPC object
    as ted-events' TE.build adds them: in the room TE.npc_rooms picks (walkable there, the map's world), its
    look from TE.npc_look (a stand-in listed for bc-sprites), hidden by the room's map script while its SNES
    show bit is clear (written after the loop from `hidden`), talking runs the event. Rooms whose map script
    another folder ships are left out (one owner per map script) and reported. -> [rows]"""
    import event_translate as T
    import snes_events as E
    import snes_maps as SM
    import ted_events as TE
    rec = TE.npc_records(m).get(det["npc"]) or {}
    rows = []
    for pr, (px, py) in TE.npc_rooms(m, (det["x"], det["y"])):
        where = _room_of(pr)
        ms = TE.map_script_name(pr) if where else None
        if ms is None or ms in taken_ms:
            rows.append({"pr_map": pr, "blocked": "no map script" if ms is None else ms + " is another folder's"})
            continue
        group, folder = where
        room = os.path.dirname(SM.pr_tilemaps()[pr])
        key = (room, group, folder, pr)
        # the NPC's entity id (and the scene's other NPCs the room lacks: TE.build's add_scene_npcs), known to
        # the translator before translating, so the scene's moves/shows of them aren't "no PR entity" stubs
        eid = Tr.created.get((pr, m, det["npc"]))     # already placed as another event's scene NPC: talks now
        if eid is None:
            eid = VANILLA_NPC_BASE + len(fixed[key])
            Tr.created[(pr, m, det["npc"])] = eid
            fixed[key].append(None)      # this NPC's slot, filled below
            hidden.setdefault((group, folder, pr), []).append((m, det["npc"], det["bit"], eid))
        probe = Tr(rom, "probe", snes_map=m, alloc=alloc, prog=prog, pr_map=pr)
        probe.layers = "entity_default"
        recs = TE.npc_records(m)
        for n in sorted({i.args["obj"] - 0x10 for i in T.scene(prog, E.parse_addr(addr), "field")
                         if isinstance(i.args.get("obj"), int) and 0x10 <= i.args["obj"] < 0x30}):
            r = recs.get(n)
            if r is None or (pr, m, n) in Tr.created or probe.npc_entity(n) is not None:
                continue
            e2 = VANILLA_NPC_BASE + len(fixed[key])
            Tr.created[(pr, m, n)] = e2
            look2, standin2 = TE.npc_look(rom, r["sprite"])
            sx, sy = r["x"] + px - det["x"], r["y"] + py - det["y"]
            fixed[key].append(TE.npc_object(sx, sy, e2, look2, TE.DIRECTION.get(r.get("direction", 2), 4), 0,
                                            "TEditionNPC_%d_%d" % (m, n)))
            hidden.setdefault((group, folder, pr), []).append((m, n, TE.NPC_BITS + r["show_bit"], e2))
            if standin2:
                standins.append({"sprite": r["sprite"], "snes_map": m, "npc": n, "pr_map": pr, "look": look2,
                                 "entity": e2, "event": addr})
        sn = "sc_tedq_%s_%s_new" % (name, pr[4:].lower())
        t = Tr(rom, sn, snes_map=m, alloc=alloc, prog=prog, pr_map=pr)
        t.texts = texts
        sc = t.translate(E.parse_addr(addr))
        scripts[(group, folder, pr)].append((sn, sc))
        for a, s2, w in t.after:
            dest = _room_of(w) if w and w != pr else (group, folder)
            if dest is not None:
                scripts[(dest[0], dest[1], w or pr)].append((a, s2))
                mod.table("script").add({"script_name": a}, id=ids.get(a))
        sid = ids.get(sn)
        mod.table("script").add({"script_name": sn}, id=sid)
        look, standin = TE.npc_look(rom, det["sprite"])
        fixed[key][eid - VANILLA_NPC_BASE] = TE.npc_object(px, py, eid, look, TE.DIRECTION.get(rec.get("direction", 2), 4),
                                                           sid, "TEditionNPC_%d_%d" % (m, det["npc"]))
        if standin:
            standins.append({"sprite": det["sprite"], "snes_map": m, "npc": det["npc"], "pr_map": pr,
                             "look": look, "entity": eid, "event": addr})
        rows.append({"pr_map": pr, "layer": "entity_default", "object": eid, "was": None, "now": sn,
                     "script_id": sid, "asset_id": look, "standin": standin, "translated": sum(t.done.values()),
                     "stubs": dict(t.stubs), "needs_formations": sorted(t.needs_formations)})
    return rows


def _entrance(rom, prog, Tr, texts, alloc, m, addr, name, entrances, taken_ms):
    """A T-Edition entrance event on a vanilla map, as ted-events' TE.build does them: in every PR room of
    the map's world with a load script (sc_map_<room>), T-Edition's part (from where its code leaves the JP
    ROM's: TE.ted_part; a call to vanilla's own entrance does nothing, the PR's load script does it) runs
    after the room's own load script (written with the NPC prologues, from `entrances`). Rooms whose map
    script another folder ships are left out. -> [{"pr_map", ...} or {"pr_map", "blocked"}]"""
    import event_translate as T
    import snes_events as E
    import snes_maps as SM
    import ted_events as TE
    off = E.parse_addr(addr)
    jp_entry = next((e[0] for e in E.entry_points(E.load("jp")) if e[2] == m and e[1] == "entrance"), None)
    start = TE.ted_part(off, prog) if off == jp_entry else off
    if start is None:
        return [{"pr_map": None, "blocked": "the same as vanilla's"}]
    world = TE.snes_world(m)
    tm = SM.pr_tilemaps()
    rooms = list(dict.fromkeys(mt.pr for mt in SM.pr_maps(m) if mt.pr in tm and TE.map_script_name(mt.pr)
                               and (world is None or TE.pr_world(mt.pr) in (None, world))))
    rows = []
    for pr in rooms:
        ms = TE.map_script_name(pr)
        if ms in taken_ms:
            rows.append({"pr_map": pr, "blocked": ms + " is another folder's"})
            continue
        group, folder = _room_of(pr)
        if any(a_ == addr for _, _, a_ in entrances.get((group, folder, pr), [])):
            rows.append({"pr_map": pr, "script": ms, "shared": True})    # the same event from another SNES map
            continue
        t = Tr(rom, "%s_%s" % (name, pr[4:].lower()), snes_map=m, alloc=alloc, prog=prog, pr_map=pr)
        t.texts = texts
        if jp_entry is not None and jp_entry != off:
            t.fallbacks[jp_entry] = Tr(rom, "empty", snes_map=m, alloc=alloc, prog=prog).assemble(
                "empty", [T.lab("Main"), T.op("Exit")], [])
        sc = t.translate(start)
        entrances.setdefault((group, folder, pr), []).append((m, sc, addr))
        rows.append({"pr_map": pr, "script": ms, "from": E.fmt(start), "translated": sum(t.done.values()),
                     "stubs": dict(t.stubs)})
    return rows


def trigger_entities(snes_map, x, y):
    """[(PR map, room dir, group, folder, layer, Tiled object id, its script id)] for the PR's scripted
    triggers (the PR's form of an event tile: action_id 2, object_type 2/5/30) at SNES (x, y) in every PR
    room of the SNES map."""
    import snes_maps as SM
    paths = SM.pr_tilemaps()
    out = []
    for mt in _rooms_of_world(snes_map):
        path = paths.get(mt.pr)
        if not path:
            continue
        room = os.path.dirname(path)
        folder = os.path.basename(os.path.dirname(room))
        group = os.path.relpath(room, P.VANILLA).replace(os.sep, "/").split("/")[0]
        px, py = x + mt.dx, y + mt.dy
        pk = _json(os.path.join(os.path.dirname(room), "package.json"))
        entry = next((m for m in pk["map"] if m["name"] == mt.pr), {})
        for lay in [e["name"] for e in entry.get("entity", [])] + ["entity_default"]:
            f = os.path.join(room, lay + ".json")
            if not os.path.exists(f):
                continue
            for layer in _json(f).get("layers", []):
                for o in layer.get("objects") or []:
                    props = {q["name"]: q["value"] for q in o.get("properties", [])}
                    if props.get("action_id") != 2 or props.get("object_type") not in TRIGGER_TYPES or "script_id" not in props:
                        continue
                    if (int(o["x"] // 16), int(o["y"] // 16) - (1 if "gid" in o else 0)) == (px, py):
                        out.append((mt.pr, room, group, folder, lay, o["id"], props["script_id"]))
    return out


def _vanilla_tile_event(snes_map, spot):
    """The JP ROM's event tile address at a map's spot (what a T-Edition tile event that wraps it calls)."""
    import snes_events as E
    jp = E.load("jp")
    return next((e[0] for e in E.entry_points(jp) if e[2] == snes_map and e[1] == "tile" and tuple(e[3]) == tuple(spot)), None)


def _rooms_of_world(snes_map):
    """snes_maps.pr_maps of the SNES map, only the PR rooms of its world (ted_events.snes_world/pr_world:
    a WoR-only scene mustn't land in the WoB room; None = both worlds or unknown: kept)."""
    import snes_maps as SM
    import ted_events as TE
    w = TE.snes_world(snes_map)
    return [mt for mt in SM.pr_maps(snes_map) if w is None or TE.pr_world(mt.pr) in (None, w)]


_trigger = None


def trigger_template():
    """A vanilla scripted step-on trigger (action_id 2, object_type 2) to copy for a tile T-Edition added."""
    global _trigger
    if _trigger is None:
        import glob
        import copy
        for f in sorted(glob.glob(os.path.join(P.VANILLA, "map_*", *RES.split("/"), "*", "*", "entity_default.json"))):
            for layer in _json(f).get("layers", []):
                for o in layer.get("objects") or []:
                    props = {q["name"]: q["value"] for q in o.get("properties", [])}
                    if props.get("action_id") == 2 and props.get("object_type") == 2 and props.get("script_id"):
                        _trigger = copy.deepcopy(o)
                        break
                if _trigger:
                    break
            if _trigger:
                break
    return _trigger


def _place_trigger(rom, prog, Tr, texts, alloc, ids, mod, m, spot, addr, name, scripts, added, vanilla=None):
    """A new step-on trigger at a tile T-Edition added (where the PR room has none), running its script."""
    import event_translate as T  # noqa: F401
    import snes_events as E
    import snes_maps as SM
    hit = SM.to_pr(m, *spot)
    if not hit or not SM.pr_tilemaps().get(hit[0]):
        return None
    pr, px, py = hit
    room = os.path.dirname(SM.pr_tilemaps()[pr])
    group, folder = _room_of(pr)
    sn = "sc_tedq_%s_%s_trig" % (name, pr[4:].lower())
    t = Tr(rom, sn, snes_map=m, alloc=alloc, prog=prog, pr_map=pr)
    t.texts = texts
    sc = t.translate(E.parse_addr(addr))
    scripts[(group, folder, pr)].append((sn, sc))
    for a, s2, w in t.after:
        where = _room_of(w) if w and w != pr else (group, folder)
        if where is not None:
            scripts[(where[0], where[1], w or pr)].append((a, s2))
    sid = ids.get(sn)
    mod.table("script").add({"script_name": sn}, id=sid)
    o = trigger_template()
    props = {q["name"]: q["value"] for q in o["properties"]}
    props.update(script_id=sid, entity_id=0)
    for k in ("map_id", "point_id"):
        if k in props:
            props[k] = 0
    added[(room, group, folder, pr)].append({"name": f"T-Edition tile {addr}", "x": px, "y": py,
                                             **({"gid": o["gid"]} if "gid" in o else {}), "properties": props})
    return {"pr_map": pr, "layer": "entity_default", "object": "new trigger", "was": None, "now": sn, "script_id": sid,
            "translated": sum(t.done.values()), "stubs": dict(t.stubs), "needs_formations": sorted(t.needs_formations)}


_jp_npcs = None


def _jp_npc_at(m, npc, x, y):
    """Whether the JP ROM has this map's NPC `npc` within a tile of (x, y): a vanilla NPC (else T-Edition's)."""
    global _jp_npcs
    if _jp_npcs is None:
        import snes_events as E
        _jp_npcs = {(e[2], e[3]["npc"]): (e[3]["x"], e[3]["y"]) for e in E.entry_points(E.load("jp")) if e[1] == "npc"}
    p = _jp_npcs.get((m, npc))
    return p is not None and abs(p[0] - x) <= 1 and abs(p[1] - y) <= 1


def _merge_on_bit(Tr, rom, prog, alloc, texts, m, pr, prior, second, bit):
    """One script for two events on one PR object: `second` when the PR flag of its NPC's show bit is set,
    else the first (prior: (index, name, script)). None when the bit has no PR flag (no way to tell them
    apart: the first keeps the object, reported)."""
    import event_translate as T
    if bit is None:
        return None
    t = Tr(rom, prior[1], snes_map=m, alloc=alloc, prog=prog, pr_map=pr)
    t.texts = texts
    try:
        flag = t.flag(bit)
    except Exception:
        flag = None
    if not flag:
        return None
    cat, idx = flag
    first, second_label = t.graft(prior[2]), t.graft(second[1])
    main = [T.lab("Main"), T.op("Branch", i=[idx, 1, f"@{second_label}"], s=[cat, T.EQ, "imm"],
                                comment=f"SNES NPC show bit {bit:03X}: {second[0]}"),
            T.op("Jump", i=[f"@{first}"])]
    return t.assemble(prior[1], main, t.blocks)


def _room_of(pr):
    """(group, folder) of a vanilla PR map, or None (a new map: ted-maps' room)."""
    import snes_maps as SM
    path = SM.pr_tilemaps().get(pr)
    if not path:
        return None
    room = os.path.dirname(path)
    return (os.path.relpath(room, P.VANILLA).replace(os.sep, "/").split("/")[0], os.path.basename(os.path.dirname(room)))


def _json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


BATCH_KINDS = ("tile", "npc")    # the vanilla-map events built so far (story order: tiles, then entrances, then NPCs)


def catalog_events():
    """The catalog's events tagged for this workstream (owner "ted-ex"), when ted-events has tagged them."""
    path = os.path.join(P.ROOT, "data", "snes_event_ted_catalog.json")
    if not os.path.exists(path):
        return []
    return [(r["event"], ("q_" if r.get("pub") else "e_") + r["event"].replace("/", "").lower(), r.get("pub", ""))
            for r in sorted(_json(path), key=lambda r: (r["map"], r["event"]))
            if (r.get("owner") == "ted-ex" or r["map"] in OWN_MAPS) and r["event"] not in BUILT_ELSEWHERE
            and (r.get("pub") or r["kind"] in BATCH_KINDS or r["map"] in OWN_MAPS)]


# new maps whose events the lead moved here (11-21, audit X8/X10): 467 the EX Moogle's Mog House side, 469 the
# Collection Room (EX's win bits). Until ted_events.owner() says so too
OWN_MAPS = {467, 469}


# vanilla-map events (not pub quests) this workstream took over from ted-events (maps 200-415, the lead,
# 2026-11-20): their own script.csv range and ids file
EVENTS_IDS_FILE = os.path.join(P.ROOT, "data", "ted_ex_events_scripts.json")
EVENTS_SCRIPT_IDS = range(13000, 14000)
TRIGGER_TYPES = (2, 5, 30)     # PR objects an event tile becomes: action_id 2 with these object types


BUILT_ELSEWHERE = {"CD/5850",   # South Figaro's wine old man: ted-events built him in mods/TEditionEvents
                   "CA/5366"}   # Cid's fish game: ted-events edits the PR's own sc_e_0616 (11-21)


# PR rooms snes_maps.pr_maps doesn't pair with an event's SNES map yet: {event: [(PR map, dx, dy)]}
# (empty: the WoR South Figaro pub, map 78 -> Map_20361_4, is in data/snes_pr_maps_overrides.json since 11-21)
EXTRA_ROOMS = {}


def npc_entities(snes_map, x, y, near=0, looks=None, skip=(), extra=()):
    """[(PR map, room dir, group, folder, layer, Tiled object id, its script id)] for the PR NPC standing at
    SNES (x, y) in every PR room of the SNES map (entity_default and the story layers its package lists):
    an object with a gid and an asset_id (an NPC), its script_id 0 or not. With `looks` (PR asset ids):
    the nearest NPC with one of those looks in each room, at any distance (the PR often moved NPCs)."""
    import snes_maps as SM
    paths = SM.pr_tilemaps()
    import types
    out, best = [], {}
    have = {mt.pr for mt in _rooms_of_world(snes_map)}
    for mt in _rooms_of_world(snes_map) + [types.SimpleNamespace(pr=r, dx=dx, dy=dy) for r, dx, dy in extra
                                           if r not in have]:
        path = paths.get(mt.pr)
        if not path:
            continue
        room = os.path.dirname(path)
        folder = os.path.basename(os.path.dirname(room))
        group = os.path.relpath(room, P.VANILLA).replace(os.sep, "/").split("/")[0]
        px, py = x + mt.dx, y + mt.dy
        pk = _json(os.path.join(os.path.dirname(room), "package.json"))
        entry = next((m for m in pk["map"] if m["name"] == mt.pr), {})
        for lay in [e["name"] for e in entry.get("entity", [])] + ["entity_default"]:
            f = os.path.join(room, lay + ".json")
            if not os.path.exists(f):
                continue
            for layer in _json(f).get("layers", []):
                for o in layer.get("objects") or []:
                    props = {q["name"]: q["value"] for q in o.get("properties", [])}
                    if "gid" not in o or "asset_id" not in props or "script_id" not in props:
                        continue
                    ox, oy = int(o["x"] // 16), int(o["y"] // 16) - 1
                    if looks is not None:
                        if props["asset_id"] in looks and (room, group, folder, mt.pr, lay, o["id"]) not in skip:
                            d = abs(ox - px) + abs(oy - py)
                            if mt.pr not in best or d < best[mt.pr][0]:
                                best[mt.pr] = (d, (mt.pr, room, group, folder, lay, o["id"], props["script_id"]))
                    elif abs(ox - px) <= near and abs(oy - py) <= near:
                        out.append((mt.pr, room, group, folder, lay, o["id"], props["script_id"]))
    return out + [v for _, v in best.values()]


def scope(events=None, log=print):
    """Each event: its SNES map/NPC/spot, the PR NPCs it would be wired to, its translation counts."""
    import event_translate as T
    import idmap as M
    import snes_events as E
    import ted_events as TE
    events = events or catalog_events() or BATCH
    rom = TE.load("ted")
    prog = E.Program(rom).walk_all()
    ents = {}
    for off, kind, m, det in prog.entries:
        ents.setdefault(E.fmt(off), []).append((kind, m, det))
    saved = dict(M.ITEM_OVERRIDES)
    M.ITEM_OVERRIDES.clear()
    M.ITEM_OVERRIDES.update(TE.item_overrides())
    rows = []
    try:
        texts, Tr, alloc = TE.Texts(rom), TE._translator_class(), TE.flag_alloc(persist=False)
        for addr, name, quest in events:
            for kind, m, det in ents.get(addr, [("?", None, None)]):
                row = {"event": addr, "name": name, "quest": quest, "kind": kind, "map": m}
                if kind == "npc":
                    row["npc"], row["spot"] = det["npc"], (det["x"], det["y"])
                    row["wire"] = [(p, lay, oid, sid) for p, _, _, _, lay, oid, sid in npc_entities(m, det["x"], det["y"])]
                t = Tr(rom, name, snes_map=m, alloc=alloc, prog=prog)
                t.texts = texts
                t.translate(E.parse_addr(addr))
                row.update(translated=sum(t.done.values()), stubs=dict(t.stubs), needs=sorted(t.needs_formations))
                rows.append(row)
                log(f"{addr} {name:24} {kind:8} map {m} -> {len(row.get('wire', []))} PR NPCs; translated "
                    f"{row['translated']}, stubs {sum(row['stubs'].values())}")
    finally:
        M.ITEM_OVERRIDES.clear()
        M.ITEM_OVERRIDES.update(saved)
    return rows


def build(out=OUT, events=None, write=True, log=print):
    """Translate and wire every event (NPCs on vanilla maps) into the Magicite folder `out`. -> report."""
    import event_translate as T
    import idmap as M
    import pr_script as Sc
    import snes_events as E
    import ted_events as TE
    from prkit import data as PD, magicite as MG
    events = events or catalog_events() or BATCH
    rom = TE.load("ted")
    prog = E.Program(rom).walk_all()
    texts = TE.Texts(rom)
    alloc = TE.flag_alloc(persist=write)   # the shared allocator; a dry run hands out nothing for good
    for bit in TE.EX_BOSS_BITS + (TE.EX_OMEGA_BIT,):     # the pinned flags first, as ted-events' build does
        alloc.get(bit)
    Tr = TE._translator_class()
    Tr.created = {}          # (PR map, SNES map, NPC) -> entity id of NPCs placed here (as TE.build's)
    ids_q = TE.ScriptIds(IDS_FILE, ids=SCRIPT_IDS)
    ids_e = TE.ScriptIds(EVENTS_IDS_FILE, ids=EVENTS_SCRIPT_IDS)
    mod = MG.MagiciteMod(out, PD.GameData("ff6"), keys_name=KEYS_NAME)
    names_by_id = {r["id"]: r["script_name"] for r in P.Table("script")}
    ents = {}
    for off, kind, m, det in prog.entries:
        ents.setdefault(E.fmt(off), []).append((kind, m, det))
    scripts = collections.defaultdict(list)     # (group, folder, PR map) -> [(name, script)]
    edits = collections.defaultdict(dict)       # (room dir, group, folder, PR map, layer) -> {object id: script id}
    report, pending_after = [], []
    added = collections.defaultdict(list)       # (room dir, group, folder, PR map) -> [new NPC objects]
    owners = {}                                 # (room, group, folder, PR map, layer, object) -> (index, name, script)
    sprite_matched, unmatched = [], []          # vanilla NPCs wired by look anywhere in the room / still unmatched
    fixed = collections.defaultdict(list)       # (room, group, folder, PR map) -> [new vanilla NPC objects, ids kept]
    hidden, standins, blocked = {}, [], []      # (group, folder, PR map) -> [(SNES map, NPC, show bit, entity)]
    entrances = {}                              # (group, folder, PR map) -> [(SNES map, T-Edition's entrance script)]
    import glob
    taken_ms = {os.path.basename(f)[:-5] for d in ("TEditionEvents", "TEditionMaps")
                for f in glob.glob(os.path.join(P.ROOT, "mods", d, "map_*", "**", "sc_map_*.json"), recursive=True)}
    saved = dict(M.ITEM_OVERRIDES)
    M.ITEM_OVERRIDES.clear()
    M.ITEM_OVERRIDES.update(TE.item_overrides())
    try:
        for addr, name, quest in events:
            ids = ids_q if quest else ids_e
            for kind, m, det in ents.get(addr, []):
                if kind == "npc_object":    # a decoration (special-graphics NPC, snes_events since 11-21): no event
                    report.append({"event": addr, "name": name, "quest": quest, "kind": kind, "map": m,
                                   "npc": det["npc"], "status": "skipped: a decoration (special-graphics NPC), no event"})
                    continue
                if kind == "entrance" and m < TE.NEW_MAPS:
                    rows = _entrance(rom, prog, Tr, texts, alloc, m, addr, name, entrances, taken_ms)
                    report.append({"event": addr, "name": name, "quest": quest, "kind": kind, "map": m,
                                   "status": "wired: after the room's load script" if any("blocked" not in r for r in rows)
                                   else "pending: entrance (%s)" % ("; ".join(r["blocked"] for r in rows) or "no PR room"),
                                   "wired": [], "entrance": rows})
                    continue
                if kind not in ("npc", "tile") or m >= TE.NEW_MAPS:
                    report.append({"event": addr, "name": name, "quest": quest, "kind": kind, "map": m,
                                   "status": "pending: " + ("new map (ted-maps' room)" if m and m >= TE.NEW_MAPS else kind)})
                    continue
                is_vanilla = False
                if kind == "npc":
                    vanilla = TE._vanilla_npc_event(m, det["npc"])
                    targets = npc_entities(m, det["x"], det["y"], extra=EXTRA_ROOMS.get(addr, ()))
                    is_vanilla = _jp_npc_at(m, det["npc"], det["x"], det["y"])
                    if not targets and is_vanilla:   # a vanilla NPC the PR placed a tile off
                        targets = npc_entities(m, det["x"], det["y"], near=1)
                    if not targets and is_vanilla:   # moved further: the same look anywhere in the PR room
                        targets = npc_entities(m, det["x"], det["y"], looks=set(TE.npc_looks(m, det["npc"])))
                        targets = [tg for tg in targets if (tg[1], tg[2], tg[3], tg[0], tg[4], tg[5]) not in owners]
                        if targets:
                            sprite_matched.append((addr, m, det["npc"], [tg[0] for tg in targets]))
                        else:
                            unmatched.append((addr, m, det["npc"], det.get("sprite")))
                    # a PR NPC another event with the same show bit already took: a different NPC the PR moved
                    # (Map_30700's three, shifted two tiles): the next free one with the same look instead
                    taken = {k for k, o in owners.items() if o[3] == det.get("bit") and f"_{name}_" not in o[1]}
                    if targets and is_vanilla and all((tg[1], tg[2], tg[3], tg[0], tg[4], tg[5]) in taken for tg in targets):
                        targets = npc_entities(m, det["x"], det["y"], looks=set(TE.npc_looks(m, det["npc"])),
                                               skip=set(owners))
                        if targets:
                            sprite_matched.append((addr, m, det["npc"], [tg[0] for tg in targets]))
                else:
                    vanilla = _vanilla_tile_event(m, det)
                    targets = trigger_entities(m, *det)
                wired = []
                conflicts = []
                for pr, room, group, folder, lay, oid, sid in targets:
                    prior = owners.get((room, group, folder, pr, lay, oid))
                    sn = "sc_tedq_%s_%s_%s" % (name, pr[4:].lower(), lay.replace("ev_e_", "l").replace("entity_default", "d"))
                    if prior is not None and prior[1] == sn:
                        # the same event from another SNES map drawn into this room (CA/B71A on maps 231/233/234):
                        # already wired, nothing to merge
                        wired.append({"pr_map": pr, "layer": lay, "object": oid, "was": sid, "now": sn,
                                      "script_id": ids.get(sn), "translated": 0, "stubs": {},
                                      "needs_formations": [], "shared": True})
                        continue
                    my_bit = det.get("bit") if kind == "npc" else None
                    t = Tr(rom, sn, snes_map=m, alloc=alloc, prog=prog, pr_map=pr)
                    t.texts, t.layers = texts, lay
                    orig = names_by_id.get(str(sid)) if sid else None
                    if orig and vanilla is not None:
                        t.fallbacks[vanilla] = Sc.load(orig)
                    sc = t.translate(E.parse_addr(addr))
                    if prior is not None:
                        # two SNES NPCs (or tiles) on one PR object: one script that runs this event when its
                        # NPC's show bit is set, else the first one's (the lead: no first-wins)
                        # the same show bit (Map_30700's three NPCs, all bit 678) can't tell them apart: reported
                        merged = (_merge_on_bit(Tr, rom, prog, alloc, texts, m, pr, prior, (sn, sc), my_bit)
                                  if my_bit is not None and my_bit != prior[3] else None)
                        conflicts.append({"pr_map": pr, "layer": lay, "object": oid, "with": prior[1],
                                          "merged": bool(merged), "bits": [prior[3], my_bit]})
                        if merged:
                            lst = scripts[(group, folder, pr)]
                            lst[prior[0]] = (prior[1], merged)
                            owners[(room, group, folder, pr, lay, oid)] = (prior[0], prior[1], merged, my_bit)
                            for a, s2, w in t.after:
                                where = _room_of(w) if w and w != pr else (group, folder)
                                if where is not None:
                                    scripts[(where[0], where[1], w or pr)].append((a, s2))
                                    mod.table("script").add({"script_name": a}, id=ids.get(a))
                        continue
                    scripts[(group, folder, pr)].append((sn, sc))
                    owners[(room, group, folder, pr, lay, oid)] = (len(scripts[(group, folder, pr)]) - 1, sn, sc, my_bit)
                    for a, s2, w in t.after:     # after-warp scripts run in their destination's room
                        where = _room_of(w) if w and w != pr else (group, folder)
                        if where is None:
                            pending_after.append((addr, a, w))
                            continue
                        scripts[(where[0], where[1], w or pr)].append((a, s2))
                    new_id = ids.get(sn)
                    mod.table("script").add({"script_name": sn}, id=new_id)
                    for a, _, _ in t.after:
                        mod.table("script").add({"script_name": a}, id=ids.get(a))
                    edits[(room, group, folder, pr, lay)][oid] = new_id
                    wired.append({"pr_map": pr, "layer": lay, "object": oid, "was": orig or sid, "now": sn,
                                  "script_id": new_id, "translated": sum(t.done.values()), "stubs": dict(t.stubs),
                                  "needs_formations": sorted(t.needs_formations)})
                placed = None
                merged = [c for c in conflicts if c["merged"]]
                if merged and not wired:     # every object it stands on runs a merged script (first event's id)
                    pass
                elif not wired and kind == "npc" and not is_vanilla:   # an NPC T-Edition added where the PR room has nobody: a new entity
                    placed = _place_npc(rom, prog, Tr, texts, alloc, ids, mod, m, det, addr, name, scripts, added)
                elif not wired and kind == "npc" and is_vanilla and not targets:   # a vanilla NPC the PR dropped
                    rows = _place_vanilla_npc(rom, prog, Tr, texts, alloc, ids, mod, m, det, addr, name, scripts,
                                              fixed, hidden, standins, taken_ms)
                    ok = [r for r in rows if "blocked" not in r]
                    wired.extend(ok[1:])
                    blocked.extend((addr, m, det["npc"], r["pr_map"], r["blocked"]) for r in rows if "blocked" in r)
                    placed = ok[0] if ok else None
                elif not wired and kind == "tile":  # a tile T-Edition added: a new trigger
                    placed = _place_trigger(rom, prog, Tr, texts, alloc, ids, mod, m, det, addr, name, scripts, added)
                if placed:
                    wired.append(placed)
                report.append({"event": addr, "name": name, "quest": quest, "kind": kind, "map": m, "conflicts": conflicts,
                               "npc": det["npc"] if kind == "npc" else None, "spot": det if kind == "tile" else None,
                               "status": ("placed" if placed else "wired") if wired else
                               "merged into the first event's script (branch on its NPC's show bit)" if merged else
                               (("pending: vanilla NPC with no PR NPC within a tile" if is_vanilla else "pending: no PR room at its spot")
                                if kind == "npc" else "pending: no PR trigger at its spot (a new one)"),
                               "wired": wired})
    finally:
        M.ITEM_OVERRIDES.clear()
        M.ITEM_OVERRIDES.update(saved)
    # T-Edition's new maps (ted-maps' rooms): the scripts and data/ted_quests_maps.json, which ted-maps'
    # build reads to place/wire them and list them in its packages (so no package entries here)
    _, new_scripts, (nmes, ncha), nsids, vanilla_after = new_map_events(out, write=write, log=lambda *a: None,
                                                                        prog=prog, ids_q=ids_q, ids_e=ids_e)
    for (g, f), pr, a, s2 in vanilla_after:      # into a vanilla room: listed in its package here
        scripts[(g, f, pr)].append((a, s2))
        mod.table("script").add({"script_name": a}, id=nsids.get(a))
    for (group, folder, pr), items in new_scripts.items():
        for sn, sc in items:
            mod.asset(group, f"{RES}/{folder}/{pr}/{sn}.json", json.dumps(sc, ensure_ascii=False, separators=(",", ":")),
                      key=f"{pr}/{sn}")
            mod.table("script").add({"script_name": sn}, id=nsids.get(sn))
    texts.mes.update({k: v for k, v in nmes.items() if k not in texts.mes})
    texts.cha.update({k: v for k, v in ncha.items() if k not in texts.cha})
    report.append({"status": "new maps: scripts for ted-maps' rooms (data/ted_quests_maps.json)",
                   "scripts": sorted(sn for v in new_scripts.values() for sn, _ in v)})
    # the scripts in their rooms, listed in the rooms' package entries
    packages = {}
    for (group, folder, pr), items in scripts.items():
        for sn, sc in items:
            nop_stubs(sc)
            mod.asset(group, f"{RES}/{folder}/{pr}/{sn}.json", json.dumps(sc, ensure_ascii=False, separators=(",", ":")),
                      key=f"{pr}/{sn}")
            packages.setdefault((group, folder), {}).setdefault(pr, []).append(sn)
    for (group, folder), rooms in packages.items():
        pk = _json(os.path.join(P.VANILLA, group, *RES.split("/"), folder, "package.json"))
        for pr, names in rooms.items():
            entry = next((e for e in pk["map"] if e["name"] == pr), None)
            if entry is None:     # a PR map listed in another folder's package (shouldn't happen): reported
                report.append({"status": f"pending: {pr} isn't in {group}/{folder}'s package", "scripts": names})
                continue
            for sn in names:
                if not any(x["name"] == sn for x in entry["script"]):
                    entry["script"].append({"name": sn, "asset": f"{pr}/{sn}"})
        mod.asset(group, f"{RES}/{folder}/package.json", json.dumps(pk, ensure_ascii=False, separators=(",", ":")),
                  key="package")
    # the rooms' map scripts for the vanilla NPCs placed anew: hide each while its SNES show bit is clear
    # (a bit with no PR tie: always shown), then the PR's own map script (as TE.build's prologue)
    for (group, folder, pr) in sorted(set(hidden) | set(entrances)):
        import event_translate as T
        items = hidden.get((group, folder, pr), [])
        ms = TE.map_script_name(pr)
        t = Tr(rom, ms, snes_map=(items or entrances[(group, folder, pr)])[0][0], alloc=alloc, prog=prog, pr_map=pr)
        t.texts = texts
        ops = []
        for m_, n, bit, eid in items:
            if t.untied(bit):
                continue
            cat, idx = t.flag(bit)
            skip = "shown_%d" % eid
            ops += [T.op("Branch", i=[idx, 1, "@" + skip], s=[cat, T.EQ, "imm"],
                         comment="SNES map %d NPC %d: shown while bit %03X is set" % (m_, n, bit))]
            ops += t.puppet_ops([eid], [[T.op("Hide", kind=2)]])
            ops += [T.lab(skip)]
        tail = [T.op("Call", i=["@" + t.graft(sc_, callable_=True)], comment="T-Edition's entrance (SNES map %d)" % m_)
                for m_, sc_, _ in entrances.get((group, folder, pr), [])]
        if not ops and not tail:         # every one always shown: the room's own map script stays the PR's
            continue
        label = t.graft(Sc.load(ms), callable_=True)
        sc = t.assemble(ms, [T.lab("Main")] + ops + [T.op("Call", i=["@" + label], comment="the PR's own " + ms)]
                        + tail + [T.op("Exit")], t.blocks)
        nop_stubs(sc)                    # (in place; it returns a count)
        mod.asset(group, f"{RES}/{folder}/{pr}/{ms}.json", json.dumps(sc, ensure_ascii=False, separators=(",", ":")),
                  key=f"{pr}/{ms}")
    for key in list(added) + list(fixed):
        edits.setdefault((key[0], key[1], key[2], key[3], "entity_default"), {})
    for (room, group, folder, pr, lay), objs in edits.items():
        doc = _json(os.path.join(room, lay + ".json"))
        if lay == "entity_default" and added.get((room, group, folder, pr)):
            import snes_rooms as RM
            layer = next(x for x in doc["layers"] if x.get("type") == "objectgroup")
            for k, o in enumerate(added[(room, group, folder, pr)]):
                obj = RM._objects([o], first_id=NEW_OBJECT_BASE + k)[0]
                layer["objects"].append(obj)
        if lay == "entity_default" and fixed.get((room, group, folder, pr)):
            layer = next(x for x in doc["layers"] if x.get("type") == "objectgroup")
            layer["objects"].extend(fixed[(room, group, folder, pr)])
        for layer in doc.get("layers", []):
            for o in layer.get("objects") or []:
                if o["id"] in objs:
                    for q in o["properties"]:
                        if q["name"] == "script_id":
                            q["value"] = objs[o["id"]]
                        elif q["name"] == "action_id" and q["value"] in (0, 4):
                            q["value"] = 2     # 0 = no talk, 4 = only its message_key: the script must run
        mod.asset(group, f"{RES}/{folder}/{pr}/{lay}.json", json.dumps(doc, ensure_ascii=False, separators=(",", ":")),
                  key=f"{pr}/{lay}")
    mod.text("story_mes_en").update(texts.mes)
    mod.text("story_cha_en").update(texts.cha)
    if write:
        import ted_build as TB
        with TB._lock(log):              # not while a T-Edition merge reads this folder (the lead, 11-21)
            mod.write()
        alloc.save()
        ids_q.save()
        ids_e.save()
        os.makedirs(os.path.dirname(REPORT), exist_ok=True)
        with open(REPORT, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
        text = json.dumps({"about": "tools/ted_quests.py: vanilla NPCs placed anew on a stand-in look (the PR has "
                                    "no sprite for their SNES sprite), for bc-sprites, as data/ted_npc_standins.json",
                           "npcs": standins}, ensure_ascii=False, indent=1)
        if not os.path.exists(STANDINS_FILE) or open(STANDINS_FILE, encoding="utf-8").read() != text:
            with open(STANDINS_FILE, "w", encoding="utf-8") as f:
                f.write(text)
        with open(os.path.join(os.path.dirname(REPORT), "npc_match.json"), "w", encoding="utf-8") as f:
            json.dump({"by_look": sprite_matched, "unmatched": unmatched, "blocked": blocked,
                       "conflicts": [c for r in report for c in r.get("conflicts", [])]}, f, indent=1)
    log(f"vanilla NPCs matched by look anywhere in the room: {len(sprite_matched)}, still unmatched: "
        f"{len(unmatched)}; conflicts {[(c['pr_map'], c['object'], c['merged']) for r in report for c in r.get('conflicts', [])]}")
    if pending_after:
        report.append({"status": "pending: after-warp scripts into new maps", "after": pending_after})
    n = sum(len(r.get("wired", [])) for r in report)
    log(f"TEditionQuests -> {out}: {len(report)} events, {n} PR NPCs wired, "
        f"{sum(len(v) for v in scripts.values())} scripts, {len(texts.mes)} lines; pending "
        f"{[r.get('event') for r in report if not r['status'].startswith(('wired', 'placed', 'merged', 'new maps', 'skipped'))]}")
    return report


# --- events on T-Edition's new maps: ted-maps' rooms place the entities, this ships the scripts --------
NEW_MAPS_JSON = os.path.join(P.ROOT, "data", "ted_quests_maps.json")


def _new_map_npc_entities(rooms):
    """{(PR room, SNES map, NPC): entity id} of the NPC objects ted-maps' build put in its rooms (mods/TEditionMaps:
    objects named TEditionNPC<n> in entity_default), for every new map's rooms (data/ted_maps.json)."""
    import glob
    out = {}
    base = os.path.join(P.ROOT, "mods", "TEditionMaps")
    for m, rec in rooms.items():
        for r in rec.get("rooms", []):
            for f in glob.glob(os.path.join(base, r["group"], "**", r["pr_map"], "entity_default.json"), recursive=True):
                for layer in _json(f).get("layers", []):
                    for o in layer.get("objects") or []:
                        name = o.get("name") or ""
                        if name.startswith("TEditionNPC") and name[11:].isdigit():
                            eid = next((q["value"] for q in o.get("properties", []) if q["name"] == "entity_id"), None)
                            if eid:
                                out[(r["pr_map"], int(m), int(name[11:]))] = eid
    return out


def new_map_events(out=OUT, write=True, log=print, prog=None, ids_q=None, ids_e=None):
    """The tagged events on T-Edition's new maps (416+): each translated (ted_events.Session) into the PR
    room ted-maps made for it (data/ted_maps.json: its npcs/events/entrance with PR rooms and spots), its
    script file shipped in that room's folder, and data/ted_quests_maps.json telling ted-maps' build what
    to place: {SNES map: {"npcs": [{index, script, script_id, asset_id, direction}], "tiles": [{x, y,
    script, script_id}] (PR spots), "entrance": {script, script_id}}}. -> (the json, {(group, folder,
    PR map): [(name, script)]}, texts)."""
    import event_translate as T
    import snes_events as E
    import ted_events as TE
    rooms = _json(os.path.join(P.ROOT, "data", "ted_maps.json"))["maps"]
    events = [e for e in catalog_events()]
    ids_q = ids_q or TE.ScriptIds(IDS_FILE, ids=SCRIPT_IDS)
    ids_e = ids_e or TE.ScriptIds(EVENTS_IDS_FILE, ids=EVENTS_SCRIPT_IDS)
    plan, scripts, sids = {}, collections.defaultdict(list), {}
    new_groups = {r["pr_map"]: r["group"] for rec in rooms.values() for r in rec.get("rooms", [])}
    to_list, vanilla_after, used_names = {}, [], {}         # new PR room -> after-scripts for its package; [(room, PR map, name, sc)]
    with TE.Session(prog=prog, persist=write) as s:
        # ted-maps' NPC objects on its rooms (TEditionNPC<n>, their entity ids) for the translator, so a scene's
        # shows/hides/moves of the map's NPCs (the Collection Room's paintings) aren't "no PR entity" stubs
        s.Tr.created = _new_map_npc_entities(rooms)
        assets = T.sprite_assets(s.rom)
        ents = {}
        for off, kind, m, det in s.prog.entries:
            ents.setdefault(E.fmt(off), []).append((kind, m, det))
        for addr, name, _ in events:
            for kind, m, det in ents.get(addr, []):
                if m is None or m < TE.NEW_MAPS or str(m) not in rooms or kind not in ("npc", "tile", "entrance"):
                    continue          # (npc_object: a decoration, no event)
                rec = rooms[str(m)]
                code = addr.replace("/", "")
                if kind == "npc":
                    hit = next((n for n in rec["npcs"] if n["index"] == det["npc"]), None)
                    if not hit or not hit.get("pr_map"):
                        continue
                    where = (hit["pr_map"], hit["pr_x"], hit["pr_y"])
                elif kind == "tile":
                    hit = next((t for t in rec["events"] if (t["x"], t["y"]) == tuple(det) and t.get("pr_map")), None)
                    if not hit:
                        continue
                    where = (hit["pr_map"], hit["pr_x"], hit["pr_y"])
                else:
                    if not rec.get("rooms"):
                        continue
                    where = (rec["rooms"][0]["pr_map"], None, None)
                room = next((r for r in rec["rooms"] if r["pr_map"] == where[0]), rec["rooms"][0])
                sn = f"sc_tedq_{code.lower()}_{kind}" + (f"{det['npc']}" if kind == "npc" else "")
                # one event on several SNES maps (CD/5810 on 446 and another): a script per room, since a
                # room's package can name only a file in that room (ted-maps lists each in its own room)
                if used_names.setdefault(sn, where[0]) != where[0]:
                    sn = f"{sn}_{where[0][4:].lower()}"
                sc, after, t = s.translate(E.parse_addr(addr), m, sn, pr_map=where[0])
                nop_stubs(sc)
                key = (room["group"], room["group"].replace("map_", "Map_"), where[0])
                scripts[key].append((sn, sc))
                for a, s2, w in after:
                    # an after-battle / after-warp script runs in its destination room (w): a vanilla room's
                    # package is this folder's (build() lists it); a new room's is ted-maps' ("_list" below)
                    nop_stubs(s2)
                    dest = w or where[0]
                    if dest in new_groups:
                        scripts[(new_groups[dest], new_groups[dest].replace("map_", "Map_"), dest)].append((a, s2))
                        to_list.setdefault(dest, []).append(a)
                    elif _room_of(dest):
                        vanilla_after.append((_room_of(dest), dest, a, s2))
                    else:
                        log(f"{addr}: {a} goes to {dest}, a room with no folder: left out")
                ids = ids_q if name.startswith("q_") else ids_e
                sid = sids[sn] = ids.get(sn)
                for a, _, _ in after:
                    sids[a] = ids.get(a)
                p = plan.setdefault(str(m), {"npcs": [], "tiles": [], "entrance": None})
                if kind == "npc":
                    # no asset_id: ted-maps' build gives the NPC its own look (data/ted_npc_looks.json)
                    p["npcs"].append({"index": det["npc"], "script": sn, "script_id": sid,
                                      "direction": det.get("direction", 2)})
                elif kind == "tile":
                    p["tiles"].append({"x": where[1], "y": where[2], "script": sn, "script_id": sid})
                else:
                    p["entrance"] = {"script": sn, "script_id": sid}
                    # ted-maps grafts it into the room's map script; listed too, so the shipped file is one the
                    # room knows (magicite_check: an unlisted script is an error)
                    to_list.setdefault(where[0], []).append(sn)
                log(f"{addr} {kind} map {m} -> {where[0]} {sn} ({sid}): translated {sum(t.done.values())}, "
                    f"stubs {sum(t.stubs.values())}")
        texts = (dict(s.texts.mes), dict(s.texts.cha))
    if write:
        ids_q.save()
        ids_e.save()
        for p in plan.values():           # no entrance: the key left out (ted-maps' format)
            if not p["entrance"]:
                del p["entrance"]
        text = json.dumps({"_about": "tools/ted_quests.py: pub-quest scripts on T-Edition's new maps, for ted-maps' build. "
                                     "_list: {PR room: [after-battle / after-warp script names]} to list in that room's "
                                     "package entry too (shipped in mods/TEditionQuests like the others)",
                           "_list": to_list, **plan}, indent=1)
        old = open(NEW_MAPS_JSON, encoding="utf-8").read() if os.path.exists(NEW_MAPS_JSON) else None
        if text != old:
            with open(NEW_MAPS_JSON, "w", encoding="utf-8") as f:
                f.write(text)
    return plan, scripts, texts, sids, vanilla_after


if __name__ == "__main__":
    if sys.argv[1:2] == ["scope"]:
        scope()
    elif sys.argv[1:2] == ["newmaps"]:
        new_map_events(write="--write" in sys.argv)[0]
    else:
        build()
