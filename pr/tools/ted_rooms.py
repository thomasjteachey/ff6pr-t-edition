"""T-Edition's new rooms -> new PR maps (feasibility, 2026-11-20): one room, map 431 ($1AF, a 16x16
cave room on T-Edition's own layouts 383/384, drawn with the Veldt cave's graphics).

    .venv/Scripts/python tools/ted_rooms.py         (writes mods/TEditionMapTest/: a test-only Magicite folder)

The room is redrawn with the PR's tiles for the same SNES tiles (tools/snes_rooms.py, learned from
the PR's Veldt cave, SNES map 353 = Map_30761_1-5) and added to the Veldt cave's map group as
Map_30761_6 (PR map id 806, map script 629). For testing it gets a door: Map_30761_1's entrance
corridor (33, 59) leads in (arriving at its doorway, facing up), the room's doorway (8, 13) leads back to
(33, 60). Not a T-Edition release: its exits, NPCs and events would come from T-Edition's own tables.
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kitpath  # noqa: E402,F401
import ff6snes as S  # noqa: E402
import jp_layout as J  # noqa: E402
import prdata as P  # noqa: E402
import snes_maps as SM  # noqa: E402
import snes_rooms as R  # noqa: E402
from profile_tedition import MATO  # noqa: E402

OUT = os.path.join(P.ROOT, "mods", "TEditionMapTest")
PROPS, LAYOUT_PTRS = 0x4D0000, 0x410000   # T-Edition: map properties 4D/0000; layouts 41/0000 (+ D9/D1B0)
ROOM, GROUP, NAME, MAP_ID, SCRIPT_ID = 431, "map_30761", "Map_30761_6", 806, 629
HOST, HOST_ID = "Map_30761_1", 488
GOTO_GID, POINT_GID = 996, 997   # the PR's GotoMap / PointIn tile objects


def ted_layout(rom, m, layer):
    p = SM.properties(rom, m, PROPS)
    idx = p["layouts"][layer]
    if not idx:
        return None
    off = int.from_bytes(rom[LAYOUT_PTRS + 3 * idx:LAYOUT_PTRS + 3 * idx + 3], "little")
    at = J.file_offset((0xD9D1B0 + off) & 0xFFFFFF)
    raw = SM.lzss(rom[at:at + 0x10000])
    w, h = p["bg1_size"] if layer == 0 else p["bg2_size"]
    return [list(raw[r * w:(r + 1) * w]) for r in range(h)]


def goto(x, y, map_id, point, entity):
    return {"name": "GotoMap", "x": x, "y": y, "gid": GOTO_GID,
            "properties": {"action_id": 3, "direction": 0, "entity_id": entity, "link_object_id": 0,
                           "map_id": map_id, "object_id": 0, "object_type": 3, "point_id": point, "script_id": 0}}


def point_in(x, y, object_id, direction, entity):
    return {"name": "PointIn", "x": x, "y": y, "gid": POINT_GID,
            "properties": {"direction": direction, "entity_id": entity, "link_object_id": 0, "object_id": object_id,
                           "object_type": 0, "title_id": "MSG_ARA_NAME_13", "title_type": 1}}


def main():
    import shutil
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    us = S.rom_bytes(P.VANILLA_ROM)
    with open(MATO, "rb") as f:
        ted = f.read()
    look = R.graphics(ted, ROOM, PROPS)
    same = [m for m in range(SM.MAPS) if R.graphics(us, m) == look and SM.pr_maps(m)]
    pairs = [(m, t.pr, t.dx, t.dy) for m in same for t in SM.pr_maps(m)]
    tiles = R.learn(us, pairs)
    room = tiles.convert(ted_layout(ted, ROOM, 0), ted_layout(ted, ROOM, 1))
    print(f"T-Edition map {ROOM}: {room.width}x{room.height}, tiles learned from SNES maps {same} "
          f"({len(pairs)} PR maps, {tiles.cells} cells); {room.unknown} cells with no PR tile")
    walk = [(x, y) for y in range(room.height) for x in range(room.width) if room.collision[y][x] == 0]
    door = max(walk, key=lambda p: (p[1], -abs(p[0] - room.width // 2)))   # the lowest walkable tile
    objects = [point_in(door[0], door[1] - 1, 1, 1, 2), goto(door[0], door[1], HOST_ID, 4, 3),
               # a second way out, beside the arrival (one step left): to the host's own entrance (point 1),
               # to tell a problem with the door's arrival point from one with leaving a new map
               goto(door[0] - 1, door[1] - 1, HOST_ID, 1, 4)]
    R.write_map(OUT, GROUP, NAME, MAP_ID, SCRIPT_ID, HOST, room, objects, tilesets=tiles.tilesets,
                map_row={"monster_set_id": 0})
    # the way in: Map_30761_1's entrance corridor (x 33, y 56-62): a door at (33, 59), the way back
    # arriving at (33, 60) facing down
    src = os.path.join(os.path.dirname(SM.pr_tilemaps()[HOST]), "entity_default.json")
    with open(src, encoding="utf-8") as f:
        ent = json.load(f)
    for lay in ent["layers"]:
        if lay.get("name") == "GroundObject":
            nid = max(o["id"] for o in lay["objects"]) + 1
            for o in (goto(33, 59, MAP_ID, 1, 100), point_in(33, 60, 4, 4, 101)):
                lay["objects"].append({"height": 16, "id": nid, "name": o["name"], "rotation": 0, "type": "",
                                       "visible": True, "width": 16, "x": 16 * o["x"], "y": 16 * (o["y"] + 1),
                                       "gid": o["gid"], "properties": [
                                           {"name": k, "type": "string" if isinstance(v, str) else "int", "value": v}
                                           for k, v in sorted(o["properties"].items())]})
                nid += 1
    dest = os.path.join(OUT, GROUP, *R.RES.split("/"), "Map_30761", HOST)
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "entity_default.json"), "w", encoding="utf-8") as f:
        json.dump(ent, f, ensure_ascii=False)
    R.add_keys(OUT, GROUP, "new_maps", [(f"{HOST}/entity_default", f"{R.RES}/Map_30761/{HOST}/entity_default")])
    print(f"wrote {OUT}: {NAME} (map {MAP_ID}), its door at {door} back to {HOST} point 4; "
          f"{HOST} (33, 59) leads in")
    for y in range(room.height):
        print("   " + "".join("D" if (x, y) == door else "." if room.collision[y][x] == 0 else "#" for x in range(room.width)))


if __name__ == "__main__":
    main()
