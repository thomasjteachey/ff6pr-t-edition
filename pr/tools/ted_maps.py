"""T-Edition's maps: where 3.0.7 keeps its map tables, and its 93 new maps as Pixel Remaster maps.

    .venv/Scripts/python tools/ted_maps.py read      (every map's tables -> build/t-edition/ted_map_tables.json)
    .venv/Scripts/python tools/ted_maps.py diff      (what T-Edition changed on vanilla maps 0-415)
    python tools/ted_maps.py build                   (mods/TEditionMaps + data/ted_maps.json, the new maps'
                                                      events too (tools/ted_map_events.py; --no-events: none);
                                                      any Python with numpy for the pictures: --shots)

T-Edition (on the Japanese ROM) has 511 map slots (0-510; vanilla 416) and moved most of the field
tables into the ExHiROM expansion. Found 2026-11-20 from the long loads in its field code (C0 bank:
the same instructions as the Japanese ROM, new operands), each checked against the data (records of
the right size, offsets rising map by map):

    map properties  4D/0000            C0/1CBF (JP ED/8F00), 33 bytes x 512
    layouts         41/0000 pointers   C0/2892, 28E6, 293C (JP D9/CD90); data D9/D1B0 + pointer as before
                                       (T-Edition's new layouts 381-390 at FF/4B60-FF/....)
    NPCs            C4/1A10 offsets    C0/52BC-52C2 (as JP); records at 4D/7CC0 + offset (C0/52D4...)
    event tiles     C4/0000 offsets    C0/BBE3-BBE9 (as JP); records at 4B/0000 + offset (C0/BBF2...)
    short exits     DF/BB00 offsets    C0/1A7D-1A83 (as JP); records at 4B/9BFE + offset (C0/1A8F...)
                                       (the "Map Exit Data 4BA000" of the address list: offset 0x402)
    long exits      ED/F480            unchanged (C0/18EA...): 512 offsets now
    chests          ED/8584 offsets    C0/15DD (JP ED/82F4); records at 4B/4000 (C0/15F1; JP ED/8634)
    map palettes    4B/6000            C0/266C (JP ED/C480)
    map graphics    40/0B00 pointers   C0/26F6 (JP DF/DA00); sets 82-85 are T-Edition's own
    entrance events D1/FA00            unchanged (C0/BF23), 3 bytes x 512
    tile properties D9/CD10 + D9/A800  unchanged (C0/1CD5); tilesets DF/BA00 + DE/0000 unchanged

Each offset list has 512 entries (maps 0-510 and the end); map 511 is empty. One list isn't
rising: map 130's short exits (T-Edition gave the vanilla-empty map three) sit after map 147's,
which snes_maps.Tables.ranges handles. The producer's address list (For Producers/FF6-T Edition
address changes.txt, CP932, written for 2.9.2) names the palettes, exits and chest offsets; the
rest come from the code. Its other entries (monster data, AI, portraits...) are profile_tedition's.

The new maps (`build`): 88 of the 93 use a vanilla layout. Where a vanilla map with that layout
(and size) has PR maps, the new map is a copy of the PR room(s) its doors, chests and people are in
(`snes_rooms.clone_map`: the PR's own tiles and collision; cells T-Edition's entrance event redraws
are converted and patched in). The rest are converted (`snes_rooms.Model`): the 5 on T-Edition's
layouts 381-390, 10 on vanilla layouts the PR never drew, and 25 on layout 298, which is blank: their
entrance events draw the whole room (event command 73, `entrance_tiles`). Doors become GotoMaps,
arrival spots PointIns (every spot an exit or an event warp arrives at), chests chest objects;
NPCs and event tiles are listed in data/ted_maps.json with their PR spots for the event translator.
PR map ids from 644 (1-643 are the game's, 800-805 its system maps), map scripts from 629.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitpath  # noqa: E402,F401
import prdata as P  # noqa: E402
import snes_maps as SM  # noqa: E402

PROJECT = os.path.normpath(os.path.join(P.ROOT, ".."))
MATO = os.path.join(PROJECT, "build", "t-edition", "T-Edition 3.0.7 (Mato).sfc")
BUILD = os.path.join(P.ROOT, "build", "t-edition")
TABLES_JSON = os.path.join(BUILD, "ted_map_tables.json")
OUT = os.path.join(P.ROOT, "mods", "TEditionMaps")
MAPS_JSON = os.path.join(P.ROOT, "data", "ted_maps.json")
# other workstreams' changes to these maps (ted-ex: the Mog House door to EX's boss room), applied by the
# build: {"<T-Edition map>": {"tiles": [[x, y | layer << 6, w, h, [tiles...]]] (as event command 73),
# "exits": [{"tiles": [[x, y]], "to": [PR map id, point id], "facing": 0-3}],
# "points": [{"x": x, "y": y, "point_id": n (90+), "facing": 0-3}]}} in SNES coordinates
EXTRA_JSONS = [os.path.join(P.ROOT, "data", "ted_ex_maps.json")]
MAP_PACKS = 0x0F5600   # CF/5600: a map's random-battle pack (C0/C306; 512 maps fit before CF/5800)
# location names: C0/8008 reads a 16-bit pointer at E6/8400 + 2 x (props byte 0) like the JP ROM, but
# T-Edition loads bank 5F (LDA #$5F) and drops the JP ROM's ADC #$84C0: Mato's English, in his menu font
NAME_PTRS, NAME_BANK, NAMES = 0x268400, 0x5F0000, 128
NAME_KEY = "TEDMAP_NAME_{}"     # their text keys (system_en), one per index
SHOW_NAME = 0x04                # an exit's flag (map word bit 11): the SNES shows the map name on arrival
MESSAGE = "Assets/GameAssets/Serial/Data/Message/system_en"


def location_names(data):
    """{index: name} of T-Edition's location names (index = map properties byte 0)."""
    from profile_tedition import mato_text
    w = lambda a: data[a] | data[a + 1] << 8
    first = w(NAME_PTRS)
    out = {}
    for i in range(NAMES):
        a = w(NAME_PTRS + 2 * i)
        if a < first:
            continue
        raw = data[NAME_BANK + a:NAME_BANK + a + 48].split(bytes(1))[0]
        text = mato_text(raw)
        if text:
            out[i] = text
    return out
SETS_JSON = os.path.join(P.ROOT, "mods", "TEditionPort", "ted_map_sets.json")    # the porter's, when written
SONGS_JSON = os.path.join(P.ROOT, "data", "ted_songs.json")   # ted-events: the songs that are vanilla's


def _json_ints(path, key):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return {int(k): int(v) for k, v in json.load(f).get(key, {}).items()}
SHOTS = os.path.join(BUILD, "maps")

TED = SM.Tables(name="T-Edition 3.0.7", maps=511, props=0x4D0000, layout_ptrs=0x410000,
                exit_data=0x4B9BFE, npc_data=0x4D7CC0, event_data=0x4B0000,
                chest_ptrs=0x2D8584, chest_data=0x4B4000, palettes=0x4B6000, gfx_ptrs=0x400B00)
VANILLA_MAPS = 416
ENTRANCE = 0x11FA00          # D1/FA00: entrance event addresses, 3 bytes per map
FIRST_MAP_ID, FIRST_SCRIPT_ID = 644, 629
FIRST_CHEST_FLAG = 300       # treasure flags 300-369 for the new maps' chests (vanilla chests use 0-272; the PR
CHEST_FLAGS = (300, 369)     # has 1024: UserDataManager kTreasureFlags); the lead keeps other allocators off them
ITEMS_JSON = os.path.join(P.ROOT, "mods", "TEditionPort", "ted_items.json")   # the porter's item slots -> PR content
GOTO_GID, POINT_GID, CHEST_GID = 996, 997, 1023   # the PR's GotoMap / PointIn / chest objects
VANILLA_OBJECT_IDS = 3000    # first Tiled object id for objects added to vanilla entity files
DIRECTION = {0: 1, 1: 2, 2: 4, 3: 8}   # SNES facing (up, right, down, left) -> PR direction bits
PARENT, WORLD_MAPS = 0x1FF, (0, 1, 2)


def rom():
    with open(MATO, "rb") as f:
        return f.read()


def jp_rom():
    import jp_layout as J
    with open(J.jp_rom_path(), "rb") as f:
        return f.read()


def used_maps(data):
    """Map slots with properties (T-Edition: 505 of 511, the 93 new ones included)."""
    return [m for m in range(TED.maps) if any(data[TED.props + 33 * m:TED.props + 33 * m + 33])]


REUSED = (415,)   # vanilla's unused slot 415 (garbage properties in the JP/US ROMs) is a T-Edition map


def new_maps(data):
    """The maps T-Edition added (416-510), and the vanilla slot it reused (415)."""
    return [m for m in used_maps(data) if m >= VANILLA_MAPS or m in REUSED]


def read_all(data=None):
    """Every T-Edition map's tables (snes_maps.map_data), by map number."""
    data = data or rom()
    out = {}
    for m in used_maps(data):
        d = SM.map_data(data, m, TED)
        d["properties"] = {k: v for k, v in d["properties"].items() if k != "raw"} | \
            {"raw": d["properties"]["raw"].hex()}
        out[m] = d
    return out


def diff_vanilla(data=None, jp=None):
    """Per vanilla map (0-415): T-Edition's records that differ from the Japanese ROM's."""
    data, jp = data or rom(), jp or jp_rom()
    out = {}
    for m in range(VANILLA_MAPS):
        a, b = SM.map_data(jp, m), SM.map_data(data, m, TED)
        ch = {}
        for k in ("npcs", "events", "exits", "chests"):
            strip = lambda rs: [{x: v for x, v in r.items() if x != "index"} for r in rs]
            if strip(a[k]) != strip(b[k]):
                ch[k] = (len(a[k]), len(b[k]))
        if a["properties"]["raw"] != b["properties"]["raw"]:
            ch["properties"] = [i for i in range(33) if a["properties"]["raw"][i] != b["properties"]["raw"][i]]
        if ch:
            out[m] = ch
    return out


# --- layouts as the game shows them ------------------------------------------------------------------
def entrance_event(data, m):
    """Map m's entrance event address (offset from CA/0000)."""
    return int.from_bytes(data[ENTRANCE + 3 * m:ENTRANCE + 3 * m + 3], "little")


def entrance_tiles(ev_rom, addr, depth=0):
    """The tile changes (event commands 73/74: x, y | layer << 6, w, h, tiles) an entrance event
    makes on its way through: its straight line and the subroutines it calls (not the branches)."""
    import snes_events as E
    out = []
    for ins in E.script(ev_rom, addr):
        if ins.op in (0x73, 0x74):
            out.append((ins.args["x"], ins.args["y"], ins.args["w"], ins.args["h"], bytes(ins.raw[5:])))
        elif ins.flow == "call" and depth < 3:
            for kind, t in ins.targets:
                out += entrance_tiles(ev_rom, t, depth + 1)
    return out


def apply_tiles(layers, sizes, commands):
    """Layouts [BG1, BG2, BG3] (rows or None) with tile commands applied (y bits 6-7 = the layer)."""
    out = [[r[:] for r in L] if L else None for L in layers]
    for x, y, w, h, tiles in commands:
        layer, y = y >> 6, y & 0x3F
        if layer > 2:
            continue
        if out[layer] is None:
            W, H = sizes[layer]
            out[layer] = [[0] * W for _ in range(H)]
        L = out[layer]
        H, W = len(L), len(L[0])
        for j in range(h):
            for i in range(w):
                if j * w + i < len(tiles):
                    L[(y + j) % H][(x + i) % W] = tiles[j * w + i]
    return out


def shown_layouts(data, ev_rom, m):
    """Map m's BG1 and BG2 as its entrance event leaves them (its layouts + tile commands)."""
    p = SM.properties(data, m, TED.props)
    base = [SM.layout(data, m, k, t=TED) for k in (0, 1, 2)]
    cmds = entrance_tiles(ev_rom, entrance_event(data, m))
    shown = apply_tiles(base, (p["bg1_size"], p["bg2_size"], p["bg2_size"]), cmds)
    return shown[0], shown[1], cmds


def like_map(mdl):
    """A vanilla PR map in a snes_rooms model's group to copy the layer setup, map script and map.csv
    row of (write_map's `like`): one of the rooms the model learned from, else any in that group."""
    import snes_rooms as R
    v = R.vanilla()
    for key, _ in mdl.tiers:
        for sm in v.by_key.get(key, []):
            for _, pr, _, _ in v.pairs[sm]:
                if R.group_of(pr) == mdl.group:
                    return pr
    return next(n for n in SM.pr_tilemaps() if R.group_of(n) == mdl.group)


def convert_room(rom, m, t, ev_rom, out, name, map_id, script_id, objects, group=None, map_row=None,
                 entrance=None):
    """Draw SNES map m of `rom` (its Tables `t`) as a new PR map: its layouts with its entrance event's
    tile commands applied (`ev_rom`: snes_events' ROM, None for none; `entrance`: the event's address
    as an offset from CA/0000, default the map's D1/FA00 entry), converted by a snes_rooms model
    (in `group`, else the group that draws it best) and written by snes_rooms.write_map into the
    Magicite folder `out` as `name` (Map_<group>_<n>: pick an n no other folder uses). `objects`:
    PointIn/GotoMap... in PR tiles (PR = SNES here). Returns (model, room, assets)."""
    import snes_rooms as R
    p = SM.properties(rom, m, t.props)
    base = [SM.layout(rom, m, k, t=t) for k in (0, 1, 2)]
    if entrance is None:
        entrance = entrance_event(rom, m)
    cmds = entrance_tiles(ev_rom, entrance) if ev_rom is not None else []
    bg1, bg2, _ = apply_tiles(base, (p["bg1_size"], p["bg2_size"], p["bg2_size"]), cmds)
    mdl = R.model(rom, m, t.props, group=group, rows=bg1, t=t)
    room = mdl.convert(bg1, bg2, SM.tile_props(rom, m, t.props))
    assets = R.write_map(out, mdl.group, name, map_id, script_id, like_map(mdl), room, objects,
                         map_row=map_row or {"monster_set_id": 0})
    return mdl, room, assets


# --- the build -----------------------------------------------------------------------------------------
class Room:
    """One PR map made for a T-Edition map: a copy of a vanilla PR room or a converted room."""

    def __init__(self, ted, kind, group, name, pr_id, script_id, dx, dy, walk, src=None, room=None, patch=None):
        self.ted, self.kind, self.group, self.name, self.pr_id, self.script_id = ted, kind, group, name, pr_id, script_id
        self.dx, self.dy, self.walk, self.src, self.room, self.patch = dx, dy, walk, src, room, patch or {}
        self.objects, self.points = [], {}

    def holds(self, x, y, near=1):
        px, py = x + self.dx, y + self.dy
        return any((px + a, py + b) in self.walk for a in range(-near, near + 1) for b in range(-near, near + 1))


class Builder:
    def __init__(self, log=print):
        import snes_events as E
        import ted_events  # noqa: F401  (registers "ted" in snes_events.LOADERS)
        import snes_rooms as R
        self.E, self.R, self.log = E, R, log
        self.data = rom()
        self.ev = E.load("ted")
        self.us = R.vanilla().us
        # the world maps too: their properties are blank, but their exit tables enter new maps (WoB
        # (19, 38) -> 439 Darill's Tomb, WoR -> 447, 508, 510)
        self.tables = {m: SM.map_data(self.data, m, TED) for m in sorted(set(used_maps(self.data)) | set(WORLD_MAPS))}
        self.new = new_maps(self.data)
        self.rooms = collections.defaultdict(list)     # ted map -> [Room]
        self.ids = {r["map_name"]: int(r["id"]) for r in P.Table("map")}
        self.next_id, self.next_script, self.next_flag = FIRST_MAP_ID, FIRST_SCRIPT_ID, FIRST_CHEST_FLAG
        self.names = collections.defaultdict(set)      # map folder -> names taken
        self._vanilla_folders = set()
        # ids stay put from build to build (tests, the event translator and the merge hold them): a room
        # the last build made keeps its PR id, name and script id; a new one takes the next free ones
        self.prev, self.prev_points = {}, {}     # rooms' and arrival points' ids from the last build
        if os.path.exists(MAPS_JSON):
            with open(MAPS_JSON, encoding="utf-8") as f:
                for m, rec in json.load(f).get("maps", {}).items():
                    for r in rec.get("rooms", []):
                        key = (int(m), r["source"] if r["kind"] == "clone" else "convert")
                        self.prev[key] = (r["pr_id"], r["pr_map"], r["script_id"])
                        self.names[r["pr_map"].rsplit("_", 1)[0]].add(r["pr_map"])
                    for pt in rec.get("points", []):
                        self.prev_points[(pt["pr_id"], pt["pr_x"], pt["pr_y"])] = pt["point_id"]
        if self.prev:
            self.next_id = max(self.next_id, 1 + max(v[0] for v in self.prev.values()))
            self.next_script = max(self.next_script, 1 + max(v[2] for v in self.prev.values()))
        self.additions = collections.defaultdict(list)  # vanilla PR map -> objects to add
        self.vanilla_points = {}                        # (PR map, x, y) -> object id (found or added)
        self.notes = collections.Counter()
        self.unresolved = []
        self.info, self.recs = {}, {}
        self.location_names = location_names(self.data)
        self.titled = set()        # (map, x, y) arrivals the SNES announces with the map's name
        self.guessed_parents = []
        # the porter's maps of T-Edition's packs -> PR monster sets and songs -> PR BGMs, when it has
        # written them ({"packs": {pack: set id}}, {"songs": {song: bgm id}})
        self.sets = _json_ints(SETS_JSON, "packs")
        self.map_sets = _json_ints(SETS_JSON, "maps")   # per map first: each carries its map's battle background
        self.songs = _json_ints(SONGS_JSON, "songs")
        self.extra = collections.defaultdict(lambda: {"tiles": [], "exits": [], "points": []})
        for path in EXTRA_JSONS:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    for m, rec in json.load(f).items():
                        if not m.isdigit():
                            continue
                        for k in ("tiles", "exits", "points"):
                            self.extra[int(m)][k] += rec.get(k, [])

    # names and ids
    def room_ids(self, m, key, group, folder):
        """(PR map id, script id, name) for a room of map m: the last build's, else new ones."""
        if (m, key) in self.prev:
            return self.prev[(m, key)]
        mid, sid = self.take_ids()
        return mid, self.new_name(group, folder), sid

    def new_name(self, group, folder):
        if folder not in self._vanilla_folders:     # the vanilla maps of the folder, once
            self._vanilla_folders.add(folder)
            import glob
            base = os.path.join(P.VANILLA, group, *self.R.RES.split("/"), folder)
            self.names[folder] |= {os.path.basename(p) for p in glob.glob(os.path.join(base, "*")) if os.path.isdir(p)}
        n = 1 + max([int(x.rsplit("_", 1)[1]) for x in self.names[folder] if x.count("_") == 2 and
                     x.rsplit("_", 1)[1].isdigit()] or [0])
        name = f"{folder}_{n}"
        self.names[folder].add(name)
        return name

    def take_ids(self):
        mid, sid = self.next_id, self.next_script
        self.next_id += 1
        self.next_script += 1
        return mid, sid

    # planning
    def clone_source(self, m):
        """(vanilla SNES map, its PR pairs) whose BG1 layout and size map m shares, best first."""
        p = SM.properties(self.data, m, TED.props)
        g = self.R.graphics(self.data, m, TED.props)
        best = None
        for v in range(VANILLA_MAPS):
            q = SM.properties(self.us, v)
            if q["layouts"][0] != p["layouts"][0] or q["bg1_size"] != p["bg1_size"] or not SM.pr_maps(v):
                continue
            pairs = [t for t in SM.pr_maps(v) if t.pr in SM.pr_tilemaps()]
            if not pairs:
                continue
            score = (q["layouts"][1] == p["layouts"][1], self.R.graphics(self.us, v) == g,
                     any(t.how != "layout" for t in pairs), -v)
            if best is None or score > best[0]:
                best = (score, v, pairs)
        return (best[1], best[2]) if best else (None, [])

    def spots(self, m):
        """Every SNES spot of map m something is placed at or arrives on."""
        d = self.tables[m]
        out = [t for e in d["exits"] for t in e["tiles"]]
        out += [(c["x"], c["y"]) for c in d["chests"]] + [(n["x"], n["y"]) for n in d["npcs"]]
        out += [(e["x"], e["y"]) for e in d["events"]] + self.arrivals.get(m, [])
        return out

    def plan(self, m):
        R = self.R
        bg1, bg2, cmds = shown_layouts(self.data, self.ev, m)
        if self.extra.get(m, {}).get("tiles"):     # another workstream's tile changes (ted-ex's door)
            p0 = SM.properties(self.data, m, TED.props)
            bg1, bg2, _ = apply_tiles([bg1, bg2, None], (p0["bg1_size"], p0["bg2_size"], p0["bg2_size"]),
                                      [(x, y, w, h, bytes(t)) for x, y, w, h, t in self.extra[m]["tiles"]])
            self.notes["tile changes from other workstreams"] += len(self.extra[m]["tiles"])
        v, pairs = self.clone_source(m)
        info = {"map": m, "entrance_event": f"{0xCA0000 + entrance_event(self.data, m):06X}",
                "tile_commands": len(cmds), "properties": SM.properties(self.data, m, TED.props)["raw"].hex()}
        props = SM.tile_props(self.data, m, TED.props)
        if v is not None:
            # the PR rooms of the vanilla map that hold this map's things (one version of each room)
            spots = self.spots(m)
            chosen, covered = [], set()
            for t in pairs:
                wk = SM.pr_walkable(t.pr)
                snes_cells = {(x - t.dx, y - t.dy) for x, y in wk}
                if len(snes_cells & covered) > 0.5 * max(1, len(snes_cells)):
                    continue     # another version of a room already chosen (World of Ruin, a scene's copy)
                hits = sum(any((x + t.dx + a, y + t.dy + b) in wk for a in (-1, 0, 1) for b in (-1, 0, 1)) for x, y in spots)
                if hits or not chosen:
                    chosen.append((t, wk, hits))
                    covered |= snes_cells
            if any(h for _, _, h in chosen):
                chosen = [c for c in chosen if c[2]]
            vb1, vb2 = SM.layout(self.us, v, 0), SM.layout(self.us, v, 1)
            for t, wk, hits in chosen:
                group = R.group_of(t.pr)
                folder = t.pr.rsplit("_", 1)[0] if t.pr.count("_") == 2 else t.pr
                patch = {}
                changed = [(x, y) for y in range(len(bg1)) for x in range(len(bg1[0]))
                           if vb1 and (y >= len(vb1) or x >= len(vb1[0]) or bg1[y][x] != vb1[y][x] or
                                       (bg2 and vb2 and y < len(vb2) and x < len(vb2[0]) and bg2[y][x] != vb2[y][x]))]
                if changed:
                    mdl = R.model(self.data, m, TED.props, group=group, t=TED)
                    cells, tm = R._cells(t.pr)
                    for x, y in changed:
                        px, py = x + t.dx, y + t.dy
                        if not (0 <= py < tm["height"] and 0 <= px < tm["width"]):
                            continue
                        b = bg2[y][x] if bg2 and y < len(bg2) and x < len(bg2[0]) else None
                        s, _ = mdl.stack(bg1[y][x], b, R._around(bg1, x, y), R._shape(bg1, props, x, y))
                        if s is not None:
                            patch[(px, py)] = (s, mdl.collision(bg1[y][x], b, props[bg1[y][x]]))
                    wk = set(wk) | {p for p, (_, c) in patch.items() if c == 0}
                    wk -= {p for p, (_, c) in patch.items() if c != 0}
                mid, name, sid = self.room_ids(m, t.pr, group, folder)
                room = Room(m, "clone", group, name, mid, sid, t.dx, t.dy, wk, src=t.pr,
                            patch=patch)
                self.rooms[m].append(room)
            info.update({"how": "clone", "source": {"snes_map": v, "pr_maps": [r.src for r in self.rooms[m]]},
                         "patched_cells": sum(len(r.patch) for r in self.rooms[m])})
        else:
            mdl = R.model(self.data, m, TED.props, rows=bg1, t=TED, rows2=bg2)
            if mdl.group is None:
                self.notes["no model"] += 1
                info.update({"how": "none", "why": "no vanilla room with this look"})
                self.info[m] = info
                return
            # no room of this look to learn from (a look of T-Edition's own): only the walkable cells and
            # the edge around them; nearest pictures for the void around are noise
            conv = mdl.convert(bg1, bg2, props, trim=3 if mdl.tiers else 1)
            like = self.like_map(mdl)
            folder = like.rsplit("_", 1)[0] if like.count("_") == 2 else like
            wk = {(x, y) for y in range(conv.height) for x in range(conv.width) if conv.collision[y][x] == 0}
            mid, name, sid = self.room_ids(m, "convert", mdl.group, folder)
            room = Room(m, "convert", mdl.group, name, mid, sid, 0, 0, wk, src=like, room=conv)
            self.rooms[m].append(room)
            lk = R.look(R.graphics(self.data, m, TED.props))
            info.update({"how": "convert", "group": mdl.group, "like": like, "cells": conv.shown,
                         "no_pr_tile": conv.unknown, "guessed": conv.guessed,
                         "look": {"sets": list(lk["sets"]), "tilesets": [lk["ts1"], lk["ts2"]]},
                         "tiers": [k[0] for k, t in mdl.tiers if t.cells]})
        self.info[m] = info

    def like_map(self, mdl):
        return like_map(mdl)

    # placing
    def place(self, m, x, y):
        """(Room, PR x, PR y) of map m's SNES (x, y): the room whose walkable cells are there (or
        nearest), else its first room."""
        rooms = self.rooms.get(m, [])
        if not rooms:
            return None
        for near in (0, 1, 2):
            for r in rooms:
                if r.holds(x, y, near):
                    return r, x + r.dx, y + r.dy
        r = rooms[0]
        return r, x + r.dx, y + r.dy

    def point(self, m, x, y, facing=2):
        """(PR map id, point id) of an arrival on new map m at SNES (x, y), made on first use."""
        hit = self.place(m, x, y)
        if not hit:
            return None
        r, px, py = hit
        if (px, py) not in r.points:
            # the id the last build gave this spot, else the next one free in the room (then and now)
            oid = self.prev_points.get((r.pr_id, px, py))
            if oid is None or oid in r.points.values():
                taken = set(r.points.values()) | {v for (pid, _, _), v in self.prev_points.items() if pid == r.pr_id}
                oid = 1 + max([i for i in taken if i < 90] or [0])
            r.points[(px, py)] = oid
            r.objects.append({"name": "PointIn", "x": px, "y": py, "gid": POINT_GID, "properties": {
                "direction": DIRECTION.get(facing, 4), "entity_id": 0, "link_object_id": 0, "object_id": oid,
                "object_type": 0, "title_id": "", "title_type": 0}})
        key = self.title_key(m)
        if key and (m, x, y) in self.titled:     # the PR's arrival banner (title_type 1, as its towns)
            for o in r.objects:
                if o["name"] == "PointIn" and (o["x"], o["y"]) == (px, py):
                    o["properties"].update({"title_id": key, "title_type": 1})
        return r.pr_id, r.points[(px, py)]

    def title_key(self, m):
        """The text key of map m's name (TEDMAP_NAME_<index>), or None (no name)."""
        n = SM.properties(self.data, m, TED.props)["name"]
        return NAME_KEY.format(n) if n in self.location_names else None

    def vanilla_point(self, m, x, y, facing=2):
        """(PR map id, point id) of an arrival on vanilla SNES map m at (x, y): the PR map's own
        PointIn there (or a tile off), else one added to it (`additions`)."""
        hit = SM.to_pr(m, x, y)
        if not hit:
            return None
        pr, px, py = hit
        if pr not in self.ids:
            return None
        key = (pr, px, py)
        if key not in self.vanilla_points:
            d = SM.pr_map_dirs().get(pr)
            _, points = SM.pr_links(d) if d else ([], {})
            found = next((oid for oid, (qx, qy) in sorted(points.items(), key=lambda kv: abs(kv[1][0] - px) + abs(kv[1][1] - py))
                          if abs(qx - px) <= 1 and abs(qy - py) <= 1), None)
            if found is None:
                taken = set(points) | {o["properties"]["object_id"] for o in self.additions[pr] if o["name"] == "PointIn"}
                found = max([k for k in taken if isinstance(k, int)] or [0]) + 1
                found = max(found, 100)
                while found in taken:
                    found += 1
                self.additions[pr].append({"name": "PointIn", "x": px, "y": py, "gid": POINT_GID, "properties": {
                    "direction": DIRECTION.get(facing, 4), "entity_id": 0, "link_object_id": 0, "object_id": found,
                    "object_type": 0, "title_id": "", "title_type": 0}})
                self.notes["PointIns added to vanilla maps"] += 1
            self.vanilla_points[key] = found
        return self.ids[pr], self.vanilla_points[key]

    def target(self, dest, x, y, facing, src=None):
        """(PR map id, point id) for an exit or warp to SNES map dest at (x, y), or None. An exit to
        the parent map (0x1FF) from map `src` goes back to where the one map that enters `src`
        does it (the SNES keeps that spot when the party enters)."""
        if dest == PARENT and src is not None:
            parents = sorted({(v, t) for v, d in self.tables.items() for e in d["exits"] if e["dest"] == src
                              for t in e["tiles"][:1] if v != src})
            if len({v for v, _ in parents}) == 1:
                v, (px, py) = parents[0]
                return self.target(v, px, py + (1 if v in WORLD_MAPS else 0), 2)
            if not parents:
                # nothing T-Edition's tables or decoded events have leads in (an event this decoder
                # doesn't follow): the world-map entrance of the vanilla room with its layout, if one
                # (T-Edition's 439 "Darill's Tomb" took vanilla 297's place: WoR (25, 52))
                lay = SM.properties(self.data, src, TED.props)["layouts"][0]
                world = sorted({(v, t) for r in range(VANILLA_MAPS)
                                if SM.properties(self.us, r)["layouts"][0] == lay
                                for v in WORLD_MAPS for e in SM.exits(self.us, v) if e["dest"] == r
                                for t in e["tiles"][:1]})
                if len(world) == 1:
                    v, (px, py) = world[0]
                    self.notes["parent exits by the vanilla room with the layout"] += 1
                    self.guessed_parents.append({"map": src, "parent": v, "at": [px, py]})
                    return self.target(v, px, py + 1, 2)
            return None
        if (dest >= VANILLA_MAPS or dest in REUSED) and dest != PARENT:
            return self.point(dest, x, y, facing)
        if dest == PARENT or dest >= TED.maps:
            return None
        return self.vanilla_point(dest, x, y, facing)

    @staticmethod
    def goto(x, y, target, facing):
        return {"name": "GotoMap", "x": x, "y": y, "gid": GOTO_GID, "properties": {
            "action_id": 3, "direction": 0, "entity_id": 0, "link_object_id": 0, "map_id": target[0],
            "object_id": 0, "object_type": 3, "point_id": target[1], "script_id": 0}}

    def collect_arrivals(self):
        """Every SNES spot on a new map an exit (from any map) or an event warp arrives at."""
        arr = collections.defaultdict(list)
        for m, d in self.tables.items():
            for e in d["exits"]:
                if VANILLA_MAPS <= e["dest"] < TED.maps or e["dest"] in REUSED:
                    arr[e["dest"]].append((e["dest_x"], e["dest_y"]))
                    if e["flags"] & SHOW_NAME:
                        self.titled.add((e["dest"], e["dest_x"], e["dest_y"]))
        prog = self.E.Program(self.ev)
        prog.walk_all()
        warps = set()
        for ins in prog.code.values():
            a = ins.args
            if a.get("map") is not None and "x" in a and (VANILLA_MAPS <= a["map"] < TED.maps or a["map"] in REUSED):
                warps.add((a["map"], a["x"], a["y"], a.get("dir", 2)))
                if a.get("mapflags", 0) & 0x800:     # 6A/6B's map word bit 11: show the name
                    self.titled.add((a["map"], a["x"], a["y"]))
        for m, x, y, f in sorted(warps):
            arr[m].append((x, y))
        self.warps = sorted(warps)
        self.arrivals = {m: sorted(set(v)) for m, v in arr.items()}

    def chest_object(self, c, px, py, items):
        """A PR chest object for a T-Edition chest (None for a monster-in-a-box: its battle is the
        event translator's)."""
        import port_chests as C
        import idmap as M
        if c["type"] == "monster":
            return None, None
        if c["type"] == "item":
            slot = items.get(c["contents"])
            if isinstance(slot, dict):      # the porter's ted_items.json: the content id it made
                cid = slot.get("content")
            else:
                row = (slot.table, slot.pr_id) if slot else M.default_item(c["contents"])
                try:
                    cid = M.content_id(*row) if row else None
                except KeyError:    # a new item's row (made by the porter's item identity step)
                    cid = None
            num, msg = 1, C.MSG_ITEM
            if cid is None:
                self.notes["chest items without a PR row yet (new items)"] += 1
        elif c["type"] == "gil":
            cid, num, msg = 1, c["contents"] * 100, C.MSG_GIL
        else:
            cid, num, msg = 1, 0, C.MSG_EMPTY
        flag = self.next_flag
        self.next_flag += 1
        if flag > CHEST_FLAGS[1]:
            raise SystemExit(f"more chests than treasure flags {CHEST_FLAGS}: ask the lead for a wider range")
        obj = {"name": "TEditionChest", "x": px, "y": py, "gid": CHEST_GID, "properties": {
            "accept_action_direction": 15, "action_id": 6, "asset_id": 0, "collision": True,
            "content_id": cid or 0, "content_num": num, "direction": 15, "entity_id": 0, "flag_id": flag,
            "interactive_icon_type": 5, "interactive_icon_v_offset": 0, "link_object_id": 0,
            "message_key": msg, "object_id": 0, "object_type": 7, "pick_up": False, "script_id": 0, "se_id": 909,
            "talk_target_transportation_ids": ""}}
        return obj, flag

    def item_slots(self):
        """T-Edition's items by slot: the porter's mods/TEditionPort/ted_items.json ({slot: {table, id,
        content, name}}, new rows included; rewritten by every port), else item_identity.identify()
        ({slot: Slot}: new items' rows wait for the next port)."""
        if os.path.exists(ITEMS_JSON):
            with open(ITEMS_JSON, encoding="utf-8") as f:
                return {int(k): v for k, v in json.load(f)["items"].items()}
        try:
            import item_identity as I
            import profile_tedition as PT
            import ff6snes as S
            PT.build()
            r = S.Rom(PT.MATO)
            n = PT._Image.names
            slots = I.identify(I.mod_items_from(r, n.items, n.item_icons), log=lambda *a: None)
            return {s.slot: s for s in slots}
        except Exception as e:     # noqa: BLE001 (the identity step is the lead's; fall back on idmap)
            self.log(f"item identity unavailable ({e}): chest contents by idmap's default rows")
            return {}

    with_events = True

    def build(self, shots=False):
        R = self.R
        self.collect_arrivals()
        for m in self.new:
            self.plan(m)
        # objects: doors, arrivals, chests; NPCs and event tiles listed
        items = self.item_slots()
        out_maps = {}
        for m in self.new:
            d = self.tables[m]
            rec = dict(self.info[m])
            rec["rooms"] = [{"pr_map": r.name, "pr_id": r.pr_id, "group": r.group, "kind": r.kind, "source": r.src,
                             "dx": r.dx, "dy": r.dy, "script": f"sc_map_{r.name[4:].lower()}", "script_id": r.script_id}
                            for r in self.rooms[m]]
            for x, y in self.arrivals.get(m, []):
                self.point(m, x, y)
            exits = []
            for e in d["exits"]:
                facing = e["flags"] >> 3 & 3
                tgt = self.target(e["dest"], e["dest_x"], e["dest_y"], facing, src=m)
                placed = []
                for (x, y) in e["tiles"]:
                    hit = self.place(m, x, y)
                    if hit and tgt:
                        r, px, py = hit
                        r.objects.append(self.goto(px, py, tgt, facing))
                        placed.append([r.name, px, py])
                if not tgt:
                    self.unresolved.append({"map": m, "exit": e["tiles"][0], "dest": e["dest"], "dest_xy": [e["dest_x"], e["dest_y"]]})
                exits.append({"kind": e["kind"], "tiles": e["tiles"], "dest": e["dest"], "dest_x": e["dest_x"],
                              "dest_y": e["dest_y"], "flags": e["flags"], "pr": placed,
                              "to": list(tgt) if tgt else None})
            rec["exits"] = exits
            chests = []
            for c in d["chests"]:
                hit = self.place(m, c["x"], c["y"])
                if not hit:
                    continue
                r, px, py = hit
                obj, flag = self.chest_object(c, px, py, items)
                if obj:
                    r.objects.append(obj)
                chests.append({k: c[k] for k in ("index", "x", "y", "type", "contents", "bit")} |
                              {"pr_map": r.name, "pr_x": px, "pr_y": py, "flag_id": flag,
                               "content_id": obj["properties"]["content_id"] if obj else None,
                               "placed": obj is not None})
            rec["chests"] = chests
            for key in ("npcs", "events"):
                rows = []
                for n in d[key]:
                    hit = self.place(m, n["x"], n["y"])
                    row = {k: v for k, v in n.items() if k != "raw"}
                    row["event"] = f"{n['event']:06X}"
                    if hit:
                        row.update({"pr_map": hit[0].name, "pr_id": hit[0].pr_id, "pr_x": hit[1], "pr_y": hit[2]})
                    rows.append(row)
                rec[key] = rows
            p = SM.properties(self.data, m, TED.props)
            rec["song"], rec["random_battles"], rec["name_index"] = p["music"], p["random_battles"], p["name"]
            rec["pack"] = self.data[MAP_PACKS + m]     # its random-battle pack (CF/5600 + map, C0/C306)
            rec["title"] = self.title_key(m)
            rec["monster_set_id"] = (self.map_sets.get(m) or self.sets.get(rec["pack"], 0)) if p["random_battles"] else 0
            # song 0 is the SNES's silence: bgm_id 0, as the PR's map rows for vanilla's song-0 rooms (98 of them)
            rec["bgm_id"] = 0 if p["music"] == 0 else self.songs.get(p["music"])
            out_maps[str(m)] = rec
            self.recs[m] = rec
        # exits on vanilla maps that lead into the new maps: doors added to their PR maps
        into = []
        for v in range(VANILLA_MAPS):
            if v in REUSED:
                continue
            for e in self.tables.get(v, {}).get("exits", []):
                if not (VANILLA_MAPS <= e["dest"] < TED.maps or e["dest"] in REUSED):
                    continue
                facing = e["flags"] >> 3 & 3
                tgt = self.point(e["dest"], e["dest_x"], e["dest_y"], facing)
                for (x, y) in e["tiles"]:
                    hit = SM.to_pr(v, x, y)
                    if hit and tgt and hit[0] in self.ids:
                        self.additions[hit[0]].append(self.goto(hit[1], hit[2], tgt, facing))
                into.append({"map": v, "tiles": e["tiles"], "dest": e["dest"], "to": list(tgt) if tgt else None,
                             "pr": [list(SM.to_pr(v, x, y) or []) for x, y in e["tiles"]]})
        # the events on the new maps (tools/ted_map_events.py): NPC objects, step triggers, translated
        # scripts (their warps make arrival points here too); `events=False` builds the maps alone
        self.events = None
        if self.with_events:
            import ted_map_events
            self.events = ted_map_events.Events(self, self.log)
            self.events.prepare()
        # other workstreams' doors and arrival points (ids they chose, 90+, clear of the build's 1..n)
        for m, rec in sorted(self.extra.items()):
            if m not in self.rooms:
                continue
            for e in rec["exits"]:
                for x, y in e["tiles"]:
                    hit = self.place(m, x, y)
                    if hit:
                        hit[0].objects.append(self.goto(hit[1], hit[2], tuple(e["to"]), e.get("facing", 0)))
                        self.notes["doors from other workstreams"] += 1
            for pt in rec["points"]:
                hit = self.place(m, pt["x"], pt["y"])
                if not hit:
                    continue
                r, px, py = hit
                if pt["point_id"] in r.points.values():
                    raise SystemExit(f"map {m}: point id {pt['point_id']} from {EXTRA_JSONS} is taken by the build")
                r.points[(px, py)] = pt["point_id"]
                r.objects.append({"name": "PointIn", "x": px, "y": py, "gid": POINT_GID, "properties": {
                    "direction": DIRECTION.get(pt.get("facing", 2), 4), "entity_id": 0, "link_object_id": 0,
                    "object_id": pt["point_id"], "object_type": 0, "title_id": "", "title_type": 0}})
                self.notes["points from other workstreams"] += 1
        # a room nothing arrives in still gets an arrival (for warps and tests): inside its first door,
        # else its walkable cell nearest the middle
        for m in self.new:
            for r in self.rooms[m]:
                if r.points or not r.walk:
                    continue
                doors = [(o["x"], o["y"]) for o in r.objects if o["name"] == "GotoMap"]
                spot = None
                for dx_, dy_ in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    if doors and (doors[0][0] + dx_, doors[0][1] + dy_) in r.walk:
                        spot = (doors[0][0] + dx_, doors[0][1] + dy_)
                        break
                if spot is None:
                    cx = sum(x for x, _ in r.walk) / len(r.walk)
                    cy = sum(y for _, y in r.walk) / len(r.walk)
                    spot = min(sorted(r.walk), key=lambda q: (q[0] - cx) ** 2 + (q[1] - cy) ** 2)
                self.point(m, spot[0] - r.dx, spot[1] - r.dy)
                if not r.points:      # the spot placed itself in another room: put it here
                    r.points[spot] = 1
                    r.objects.append({"name": "PointIn", "x": spot[0], "y": spot[1], "gid": POINT_GID, "properties": {
                        "direction": 4, "entity_id": 0, "link_object_id": 0, "object_id": 1, "object_type": 0,
                        "title_id": "", "title_type": 0}})
                self.notes["default arrivals"] += 1
        for m in self.new:
            out_maps[str(m)]["points"] = [{"pr_map": r.name, "pr_id": r.pr_id, "pr_x": px, "pr_y": py, "point_id": oid,
                                           "snes": [px - r.dx, py - r.dy]}
                                          for r in self.rooms[m] for (px, py), oid in r.points.items()]
        self.write(out_maps, into, shots)

    def write(self, out_maps, into, shots):
        """Writes the folder beside OUT, then puts it in OUT's place (an install copying OUT meanwhile
        never sees half a build)."""
        import shutil
        global OUT
        final, OUT = OUT, OUT + ".build"
        try:
            if os.path.isdir(OUT):
                shutil.rmtree(OUT)
            self._write(out_maps, into, shots)
        finally:
            built, OUT = OUT, final
        if os.path.isdir(final):
            shutil.rmtree(final)
        os.replace(built, final)

    def _write(self, out_maps, into, shots):
        R = self.R
        for m in self.new:
            for r in self.rooms[m]:
                # its own title (T-Edition's location name: TEDMAP_NAME_<index>, not the source map's);
                # a battle set and BGM when the porter / ted-events have mapped its pack and song
                rec = self.recs[m]
                row = {"monster_set_id": rec["monster_set_id"], "map_title": self.title_key(m) or "None"}
                if rec.get("bgm_id") is not None:
                    row["bgm_id"] = rec["bgm_id"]
                if r.kind == "clone":
                    R.clone_map(OUT, r.src, r.name, r.pr_id, r.script_id, r.objects, map_row=row, patch=r.patch)
                else:
                    R.write_map(OUT, r.group, r.name, r.pr_id, r.script_id, r.src, r.room, r.objects, map_row=row)
        if self.events is not None:
            self.events.write(OUT)
        # T-Edition's location names as text keys (all of them: other workstreams may name places too)
        lines = [NAME_KEY.format(i) + "\t" + t for i, t in sorted(self.location_names.items())]
        path = os.path.join(OUT, "message", *MESSAGE.split("/")) + ".txt"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        R.add_keys(OUT, "message", "ted_maps", [("system_en", MESSAGE)])
        # vanilla PR maps that get doors or arrival points
        for pr, objs in sorted(self.additions.items()):
            src = SM.pr_map_dirs()[pr]
            group = os.path.relpath(src, P.VANILLA).replace("\\", "/").split("/")[0]
            with open(os.path.join(src, "entity_default.json"), encoding="utf-8") as f:
                ent = json.load(f)
            ids = []

            def all_ids(ls):
                for lay in ls:
                    ids.extend(o["id"] for o in lay.get("objects") or [])
                    all_ids(lay.get("layers", []))
            all_ids(ent["layers"])
            # Tiled ids from VANILLA_OBJECT_IDS up: the porter adds objects at the file's highest id + 1,
            # ted-events from 5000 (the lead, 2026-11-20): the merge never sees one id twice
            R.put_objects(ent, R.object_layer(src), R._objects(objs, max([VANILLA_OBJECT_IDS] + [i + 1 for i in ids])))
            rel = os.path.relpath(src, os.path.join(P.VANILLA, group)).replace("\\", "/")
            dest = os.path.join(OUT, group, rel)
            os.makedirs(dest, exist_ok=True)
            with open(os.path.join(dest, "entity_default.json"), "w", encoding="utf-8") as f:
                json.dump(ent, f, ensure_ascii=False)
            folder = rel.split("/")
            R.add_keys(OUT, group, "ted_maps", [(f"{pr}/entity_default", f"{'/'.join(folder[:-1])}/{pr}/entity_default")])
        doc = {"_about": "tools/ted_maps.py build: T-Edition 3.0.7's new maps (416-510) as PR maps. Per map: how "
                         "(clone: a copy of the PR room(s) of the vanilla map with its layout, cells its entrance event "
                         "redraws patched in; convert: drawn by snes_rooms from vanilla rooms that look alike), its "
                         "rooms (PR map name/id/group, PR = SNES + (dx, dy)), points (PointIn object ids by spot: "
                         "ChangeMap [pr_id, point_id]), exits (as GotoMaps), chests (flag_id: the PR treasure flag), "
                         "npcs and events (SNES records with their PR spots; event = SNES address). into: exits on "
                         "vanilla maps that lead into new maps (doors added to the PR maps in additions). warps: event "
                         "map loads into new maps (SNES map, x, y, facing): each has a point. unresolved: exits with "
                         "no PR target (to the parent map 0x1FF, or a place without a PR map).",
               "first_map_id": FIRST_MAP_ID, "first_script_id": FIRST_SCRIPT_ID, "first_chest_flag": FIRST_CHEST_FLAG,
               "chest_flags": list(CHEST_FLAGS),
               "map_ids": [min(r.pr_id for rs in self.rooms.values() for r in rs),
                           max(r.pr_id for rs in self.rooms.values() for r in rs)],
               "script_ids": [min(r.script_id for rs in self.rooms.values() for r in rs),
                              max(r.script_id for rs in self.rooms.values() for r in rs)],
               "maps": out_maps, "into": into,
               "warps": [list(w) for w in self.warps],
               "additions": {pr: objs for pr, objs in sorted(self.additions.items())},
               "unresolved": self.unresolved, "guessed_parents": self.guessed_parents}
        with open(MAPS_JSON, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=1, ensure_ascii=False)
        hows = collections.Counter(v["how"] for v in out_maps.values())
        n_rooms = sum(len(v) for v in self.rooms.values())
        conv = [v for v in out_maps.values() if v["how"] == "convert"]
        all_ids = [r.pr_id for rs in self.rooms.values() for r in rs]
        all_sc = [r.script_id for rs in self.rooms.values() for r in rs]
        self.log(f"{len(out_maps)} new maps: {dict(hows)}; {n_rooms} PR maps (ids {min(all_ids)}-{max(all_ids)}, "
                 f"scripts {min(all_sc)}-{max(all_sc)}); converted cells without a PR tile: "
                 f"{sum(v['no_pr_tile'] for v in conv)} of {sum(v['cells'] for v in conv)}; doors "
                 f"{sum(len(e['pr']) for v in out_maps.values() for e in v['exits'])}, chests "
                 f"{sum(c['placed'] for v in out_maps.values() for c in v['chests'])} of "
                 f"{sum(len(v['chests']) for v in out_maps.values())}, arrival points "
                 f"{sum(len(v['points']) for v in out_maps.values())}; vanilla PR maps changed: {len(self.additions)}; "
                 f"unresolved exits: {len(self.unresolved)}; {dict(self.notes)}")
        self.log(f"-> {os.path.normpath(OUT[:-6] if OUT.endswith('.build') else OUT)}, {os.path.normpath(MAPS_JSON)}")
        if shots:
            import shutil as _sh
            _sh.rmtree(SHOTS, ignore_errors=True)
            os.makedirs(SHOTS, exist_ok=True)
            for m in self.new:
                for r in self.rooms[m]:
                    path = os.path.join(SHOTS, f"{m}_{r.name}.png")
                    if r.kind == "convert":
                        rows = [[tuple(r.room.layers[n][y][x] for n in R.LAYERS) for x in range(r.room.width)]
                                for y in range(r.room.height)]
                        coll = r.room.collision
                    else:
                        cells, _ = R._cells(r.src)
                        rows = [[c[0] for c in row] for row in cells]
                        coll = [[c[1] for c in row] for row in cells]
                        for (x, y), (s, c) in r.patch.items():
                            rows[y][x], coll[y][x] = s, c
                    if not r.walk:
                        continue
                    xs, ys = [p[0] for p in r.walk], [p[1] for p in r.walk]
                    box = (max(0, min(xs) - 4), max(0, min(ys) - 4), min(len(rows[0]), max(xs) + 5),
                           min(len(rows), max(ys) + 5))
                    R.render(rows, path, coll, box=box)


# --- lookups for other tools (the event translator) -------------------------------------------------
_doc = None


def table():
    global _doc
    if _doc is None:
        with open(MAPS_JSON, encoding="utf-8") as f:
            _doc = json.load(f)
    return _doc


def to_pr(m, x, y):
    """T-Edition (map, x, y) -> (PR map name, PR map id, x, y): a new map through data/ted_maps.json
    (the room whose spots are nearest), a vanilla one through snes_maps."""
    if m < VANILLA_MAPS:
        hit = SM.to_pr(m, x, y)
        if not hit:
            return None
        ids = {r["map_name"]: int(r["id"]) for r in P.Table("map")}
        return hit[0], ids.get(hit[0]), hit[1], hit[2]
    rec = table()["maps"].get(str(m))
    if not rec or not rec["rooms"]:
        return None
    best = None
    for r in rec["rooms"]:
        spots = [(p["snes"][0], p["snes"][1]) for p in rec["points"] if p["pr_map"] == r["pr_map"]]
        spots += [(n["x"], n["y"]) for k in ("npcs", "events", "chests") for n in rec[k] if n.get("pr_map") == r["pr_map"]]
        dist = min([abs(sx - x) + abs(sy - y) for sx, sy in spots] or [999])
        if best is None or dist < best[0]:
            best = (dist, r)
    r = best[1]
    return r["pr_map"], r["pr_id"], x + r["dx"], y + r["dy"]


def point(m, x, y):
    """(PR map id, point id) of an arrival spot on new map m (made by the build for every exit and
    event warp into the map), or None."""
    rec = table()["maps"].get(str(m))
    for p in (rec or {}).get("points", []):
        if p["snes"] == [x, y]:
            return p["pr_id"], p["point_id"]
    return None


def arrival(m, x, y):
    """(PR map id, PR map name, PR x, PR y, point id) of an arrival on new map m (416+, and 415) at SNES
    (x, y), or None: for other tools' event warps into the new maps (ted-events' TedTranslator.place).
    The build makes a point for every exit and every event warp into a new map in T-Edition's whole event
    code (Builder.collect_arrivals), so any warp the ROM has is here; read from data/ted_maps.json."""
    rec = table()["maps"].get(str(m))
    for p in (rec or {}).get("points", []):
        if p["snes"] == [x, y]:
            return p["pr_id"], p["pr_map"], p["pr_x"], p["pr_y"], p["point_id"]
    return None


def walk_steps(maps, shots_dir, per_map=1):
    """Harness steps that warp to each listed T-Edition map's arrival points and walk out through
    the door next to one (`per_map` points a map): warp, wait for the map, a shot, then press toward
    the door until the map changes, a shot. Returns (steps, checks: [(ted map, PR id, door target)])."""
    doc = table()
    steps, checks = [], []
    dirs = {(0, -1): "up", (0, 1): "down", (-1, 0): "left", (1, 0): "right"}
    for m in maps:
        rec = doc["maps"][str(m)]
        done = 0
        for p in rec["points"]:
            if done >= per_map:
                break
            doors = [(e, pr) for e in rec["exits"] for pr in e["pr"] if pr[0] == p["pr_map"] and e["to"]]
            near = [(abs(pr[1] - p["pr_x"]) + abs(pr[2] - p["pr_y"]), pr, e) for e, pr in doors]
            near = [n for n in near if n[0] == 1]
            if not near:
                continue
            _, pr, e = min(near, key=lambda n: n[0])
            way = dirs[(pr[1] - p["pr_x"], pr[2] - p["pr_y"])]
            tgt = e["to"][0]
            shot = f"{shots_dir}/ted_{m}_{p['pr_id']}_{p['point_id']}".replace("\\", "/")
            steps += [f"warp {p['pr_id']} {p['point_id']}", f"until map {p['pr_id']}(?![0-9]) 20", "sleep 2",
                      f"shot {shot}.png", f"until map {tgt}(?![0-9]) 20 repeat press {way} 20", "sleep 2",
                      f"shot {shot}_out.png"]
            checks.append((m, p["pr_id"], tgt))
            done += 1
    return steps, checks


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "read"
    if cmd == "read":
        tables = read_all()
        os.makedirs(BUILD, exist_ok=True)
        with open(TABLES_JSON, "w", encoding="utf-8") as f:
            json.dump(tables, f, indent=1)
        n = len(tables)
        cnt = {k: sum(len(v[k]) for v in tables.values()) for k in ("npcs", "events", "exits", "chests")}
        new = [m for m in tables if m >= VANILLA_MAPS]
        cnt_new = {k: sum(len(tables[m][k]) for m in new) for k in ("npcs", "events", "exits", "chests")}
        print(f"{n} maps read ({len(new)} new): {cnt}; on new maps: {cnt_new} -> {os.path.normpath(TABLES_JSON)}")
    elif cmd == "diff":
        d = diff_vanilla()
        for m, ch in d.items():
            print(m, ch)
        print(f"{len(d)} vanilla maps changed")
    elif cmd == "build":
        b = Builder()
        b.with_events = "--no-events" not in sys.argv
        b.build(shots="--shots" in sys.argv)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
