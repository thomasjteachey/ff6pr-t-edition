using System;
using System.Collections.Generic;
using System.Diagnostics;
using PrKit;
using UnityEngine;
using Object = UnityEngine.Object;

namespace TEdition.PR
{
    // Runtime tile changes on field maps (T-Edition's event commands 73/74: doors, bridges), from ted-events'
    // SysCall "TED:tiles px,py=SRC[:attr] ..." (one item per changed PR cell, tilemap x/y):
    //   SRC "sx,sy": that PR cell's look on all four tile layers as the map loaded (sx,sy == px,py: put it back);
    //       "#b/g/u/c": the tilemap's gids per layer (0 none); "-": no look (attr only).
    //   ":attr": the collision value the cell should get (passability cells only).
    // What the PR does (decompiled tools/decomp/ted_tiles): each field layer is a MapLayerMesh; its
    // MapTileGroupLayerData.MapTileUvDatas holds one MapTileUVData per cell (tileId: an index into the map group's
    // TexUVTable); MapLayerMesh.ReflectUvDatas rewrites the UVs of the visible cells whose MapTileUVData is animated,
    // every frame when the layer has chip animations (IsExistChipAnim). So a cell changes look by getting a one-frame
    // animated MapTileUVData (or the source cell's own animation) on a layer marked IsExistChipAnim.
    // Unverified until a run (ted-8's tedtile probe): the cell index (y x width + x), gid -> tileId (gid - 1 assumed).
    // Walkability (":attr" and ted_tile_cells.json): see the walkability part below.
    static class TedTiles
    {
        internal static string Last = "";
        internal static int Calls, Cells, AttrCells, Missing;
        static readonly Dictionary<IntPtr, MapTileUVData[]> snapshot = new Dictionary<IntPtr, MapTileUVData[]>();

        static List<MapLayerMesh> Layers()
        {
            var list = new List<MapLayerMesh>();
            foreach (var m in Object.FindObjectsOfType<MapLayerMesh>()) if (m != null && m.LayerData != null) list.Add(m);
            return list;
        }

        // a layer's width in cells: its tilemap layer group's (TileMapLayerGroupData.width, else its first layer's)
        static int Width(MapLayerMesh m)
        {
            try
            {
                var g = m?.LayerData?.TileMapLayerGroupData;
                if (g == null) return 0;
                if (g.width > 0) return g.width;
                return g.layers != null && g.layers.Length > 0 && g.layers[0] != null ? g.layers[0].width : 0;
            }
            catch (Exception) { return 0; }
        }

        static MapTileUVData[] Original(MapLayerMesh m)
        {
            var key = m.LayerData.Pointer;
            if (!snapshot.TryGetValue(key, out var orig))
            {
                var uvs = m.LayerData.MapTileUvDatas;
                orig = new MapTileUVData[uvs?.Length ?? 0];
                for (int i = 0; i < orig.Length; i++) orig[i] = uvs[i];
                snapshot[key] = orig;
            }
            return orig;
        }

        static MapTileUVData Frame(int id)
        {
            var frames = new Il2CppInterop.Runtime.InteropTypes.Arrays.Il2CppReferenceArray<TileMapTileAnimData>(1);
            frames[0] = new TileMapTileAnimData { tileid = id, duration = 1000000 };
            return new MapTileUVData(id, frames);
        }

        // the cell's new entry: a copy of an original cell (its own animation kept) or a tile id
        static MapTileUVData Copy(MapTileUVData src)
        {
            if (src == null) return null;
            var anim = src.TileAnimDatas;
            return anim != null && anim.Length > 0 ? new MapTileUVData(src.TileId, anim) : Frame(src.TileId);
        }

        static readonly string[] Order = { "bottom", "ground", "upper", "ceil" };

        static int LayerSlot(MapLayerMesh m)
        {
            var n = (m.LayerData.LayerName ?? "").ToLowerInvariant();
            for (int i = 0; i < Order.Length; i++) if (n.Contains(Order[i])) return i;
            return -1;
        }

        // SysCall "TED:tiles <items>": returns a line for the log
        public static string Apply(string[] items)
        {
            var clock = Stopwatch.StartNew();
            Calls++;
            var layers = Layers();
            if (layers.Count == 0) return Last = "no field layers";
            // another map since the last call: its layers are new objects, the old snapshot goes
            var live = new HashSet<IntPtr>();
            foreach (var l in layers) live.Add(l.LayerData.Pointer);
            foreach (var k in new List<IntPtr>(snapshot.Keys)) if (!live.Contains(k)) snapshot.Remove(k);
            int width = 0;
            foreach (var l in layers) { width = Width(l); if (width > 0) break; }
            if (width <= 0) return Last = "no layer width";
            var touched = new HashSet<MapLayerMesh>();
            int cells = 0, attrs = 0, missing = 0;
            foreach (var item in items)
            {
                if (string.IsNullOrWhiteSpace(item)) continue;
                int eq = item.IndexOf('=');
                if (eq < 0) { missing++; continue; }
                var dst = item.Substring(0, eq).Split(',');
                var rest = item.Substring(eq + 1);
                int colon = rest.IndexOf(':');
                string attrText = colon >= 0 ? rest.Substring(colon + 1) : null;
                if (colon >= 0) { attrs++; rest = rest.Substring(0, colon); }
                if (dst.Length != 2 || !int.TryParse(dst[0], out int px) || !int.TryParse(dst[1], out int py)) { missing++; continue; }
                if (attrText != null && int.TryParse(attrText, out int attr)) SetWalk(px, py, attr);
                if (rest == "-") continue;
                int dcell = py * width + px;
                if (rest.StartsWith("#"))
                {
                    var gids = rest.Substring(1).Split('/');
                    foreach (var m in layers)
                    {
                        int slot = LayerSlot(m);
                        if (slot < 0 || slot >= gids.Length || !long.TryParse(gids[slot], out long gid)) continue;
                        var uvs = m.LayerData.MapTileUvDatas;
                        if (uvs == null || dcell < 0 || dcell >= uvs.Length) { missing++; continue; }
                        Original(m);
                        int id = (int)(gid & 0x0FFFFFFF);   // flip bits dropped
                        uvs[dcell] = id == 0 ? null : Frame(id - 1);
                        touched.Add(m);
                    }
                    cells++;
                    continue;
                }
                var src = rest.Split(',');
                if (src.Length != 2 || !int.TryParse(src[0], out int sx) || !int.TryParse(src[1], out int sy)) { missing++; continue; }
                int scell = sy * width + sx;
                foreach (var m in layers)
                {
                    var uvs = m.LayerData.MapTileUvDatas;
                    if (uvs == null || dcell < 0 || dcell >= uvs.Length || scell < 0 || scell >= uvs.Length) { missing++; continue; }
                    var orig = Original(m);
                    uvs[dcell] = Copy(orig[scell]);
                    touched.Add(m);
                }
                cells++;
            }
            foreach (var m in touched)
            {
                m.LayerData.IsExistChipAnim = true;
                try { m.ReflectUvDatas(); } catch (Exception e) { Hooks.WarnOnce("ted-tiles-reflect", e); }
            }
            Cells += cells; AttrCells += attrs; Missing += missing;
            Last = $"{cells} cells on {touched.Count} layers ({attrs} passability; {missing} skipped) in {clock.Elapsed.TotalMilliseconds:0.0} ms";
            return Last;
        }


        // --- walkability (the map's physics colliders and the PR's per-step gate) ------------------------------------
        // ted-events' ted_tile_cells.json {pr map id: [[x, y, attr], ...]}: every cell a T-Edition tile change can open or
        // block, with its load-time collision value (0 walk, else blocked). A map's table starts from it on entry; ":attr"
        // items change it; nothing persists (the SNES's entrance events re-apply their changes). A step into a cell the
        // table blocks is refused (FieldController.IsCanMoveToDestPosition postfix: the PR's per-step gate); a step a map
        // collider would stop into a cell the table opens is let through (FieldColliderEntity.CanEnter postfix).
        // Cells: FieldController.ConvertWorldPositionToCellPosition (x, y as ted-events' tilemap.json: unverified).
        static Dictionary<int, List<int[]>> fileCells;
        static readonly Dictionary<long, int> walk = new Dictionary<long, int>();
        static int walkMap = -1;
        static Last.Map.FieldController controller;
        internal static int Refused, Opened;

        public static void LoadCells(string path)
        {
            fileCells = new Dictionary<int, List<int[]>>();
            if (!System.IO.File.Exists(path)) return;
            try
            {
                using var doc = System.Text.Json.JsonDocument.Parse(System.IO.File.ReadAllText(path));
                foreach (var m in doc.RootElement.EnumerateObject())
                {
                    if (!int.TryParse(m.Name, out int id)) continue;
                    var list = new List<int[]>();
                    foreach (var c in m.Value.EnumerateArray())
                    {
                        var a = new List<int>();
                        foreach (var v in c.EnumerateArray()) a.Add(v.GetInt32());
                        if (a.Count >= 3) list.Add(a.ToArray());
                    }
                    fileCells[id] = list;
                }
                Plugin.L.LogInfo($"[ted tiles] passability cells for {fileCells.Count} rooms");
            }
            catch (Exception e) { Plugin.L.LogWarning($"[ted tiles] {path}: {e.Message}"); }
        }

        static long Key(int x, int y) => ((long)x << 32) | (uint)y;

        static void SyncMap()
        {
            int id = MapScripts.MapId;
            if (id == walkMap) return;
            walkMap = id;
            walk.Clear();
            if (fileCells != null && fileCells.TryGetValue(id, out var list))
                foreach (var c in list) walk[Key(c[0], c[1])] = c[2];
        }

        static void SetWalk(int x, int y, int attr)
        {
            SyncMap();
            walk[Key(x, y)] = attr;
        }

        static bool Lookup(Vector3 world, out int attr, out int cx, out int cy)
        {
            attr = 0; cx = cy = 0;
            if (controller == null) return false;
            SyncMap();
            if (walk.Count == 0) return false;
            var cell = controller.ConvertWorldPositionToCellPosition(world);
            cx = Mathf.FloorToInt(cell.x + 0.5f); cy = Mathf.FloorToInt(cell.y + 0.5f);
            return walk.TryGetValue(Key(cx, cy), out attr);
        }

        public static void Patch(HarmonyLib.Harmony h)
        {
            Hooks.Patch(h, typeof(Last.Map.FieldController), "IsCanMoveToDestPosition", typeof(TedTiles), postfix: nameof(Move_Postfix));
            Hooks.Patch(h, typeof(Last.Entity.Field.FieldColliderEntity), "CanEnter", typeof(TedTiles), postfix: nameof(Enter_Postfix));
        }

        public static void Move_Postfix(Last.Map.FieldController __instance, ref Vector3 destPos, ref bool __result)
        {
            try
            {
                controller = __instance;
                if (!__result || !Plugin.TedMode) return;
                if (Lookup(destPos, out int attr, out int cx, out int cy) && attr != 0)
                {
                    __result = false;
                    Refused++;
                    Hooks.NoteOnce("ted-tiles-refused", () => $"[ted tiles] a step into blocked cell {cx},{cy} (map {walkMap}) refused");
                }
            }
            catch (Exception e) { Hooks.WarnOnce("ted-tiles-move", e); }
        }

        public static void Enter_Postfix(Last.Entity.Field.FieldEntity enterEntity, Vector2 moveVector, ref bool __result)
        {
            try
            {
                if (__result || !Plugin.TedMode || enterEntity == null) return;
                var dest = enterEntity.transform.position + new Vector3(moveVector.x, moveVector.y, 0f);
                if (Lookup(dest, out int attr, out int cx, out int cy) && attr == 0)
                {
                    __result = true;
                    Opened++;
                    Hooks.NoteOnce("ted-tiles-opened", () => $"[ted tiles] a step into opened cell {cx},{cy} (map {walkMap}) let through a map collider");
                }
            }
            catch (Exception e) { Hooks.WarnOnce("ted-tiles-enter", e); }
        }

        // the party's cell (for the probe: x, y as the table's)
        static string Where()
        {
            if (controller == null) return "no field controller seen yet (take a step)";
            var p = Object.FindObjectOfType<Last.Entity.Field.FieldPlayer>();
            if (p == null) return "no player";
            var c = controller.ConvertWorldPositionToCellPosition(p.transform.position);
            SyncMap();
            return $"map {walkMap}: player world {p.transform.position} -> cell {c}; table {walk.Count} cells; refused {Refused}, opened {Opened}";
        }

        // a new map: its layers are new objects (the snapshot is per layer data)
        public static void Forget() => snapshot.Clear();

        // tedtile: list the layers; tedtile LAYER CELL: that cell's tile; tedtile LAYER CELL ID: write it (timed)
        public static string Harness(string[] a)
        {
            var layers = Layers();
            if (layers.Count == 0) return "error: no field layers (not on a map?)";
            if (a.Length > 0 && a[0] == "apply") return Apply(a[1..]);
            if (a.Length > 0 && a[0] == "where") return Where();
            if (a.Length == 0)
            {
                var parts = new List<string>();
                for (int i = 0; i < layers.Count; i++)
                {
                    var d = layers[i].LayerData;
                    parts.Add($"#{i} {d.LayerName} (layer {d.Layer}, z {d.ZOrder}, {d.MapTileUvDatas?.Length ?? 0} cells, width {Width(layers[i])}, anim {d.IsExistChipAnim})");
                }
                return string.Join("; ", parts);
            }
            if (!int.TryParse(a[0].TrimStart('#'), out int li) || li < 0 || li >= layers.Count) return "error: tedtile #LAYER CELL [TILEID] | tedtile apply ITEMS";
            var m = layers[li];
            var data = m.LayerData;
            var uvs = data.MapTileUvDatas;
            if (a.Length < 2 || !int.TryParse(a[1], out int cell) || uvs == null || cell < 0 || cell >= uvs.Length)
                return $"error: cell 0..{(uvs?.Length ?? 0) - 1}";
            int before = uvs[cell]?.TileId ?? -1;
            if (a.Length < 3 || !int.TryParse(a[2], out int id)) return $"layer #{li} {data.LayerName} cell {cell}: tile {before}";
            var clock = Stopwatch.StartNew();
            Original(m);
            uvs[cell] = Frame(id);
            data.IsExistChipAnim = true;
            m.ReflectUvDatas();
            Last = $"layer #{li} {data.LayerName} cell {cell}: tile {before} -> {id} ({clock.Elapsed.TotalMilliseconds:0.000} ms)";
            Plugin.L.LogInfo($"[ted tiles] {Last}");
            return Last;
        }
    }
}
