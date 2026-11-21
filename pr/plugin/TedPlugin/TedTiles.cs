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
    // Walkability is the map's physics colliders (FieldColliderEntity), not the tiles: ":attr" is counted and logged,
    // and passability is planned as conditional colliders in ted-maps' map data.
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
                if (colon >= 0) { attrs++; rest = rest.Substring(0, colon); }
                if (dst.Length != 2 || !int.TryParse(dst[0], out int px) || !int.TryParse(dst[1], out int py)) { missing++; continue; }
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
            Last = $"{cells} cells on {touched.Count} layers ({attrs} with passability, logged only; {missing} skipped) in {clock.Elapsed.TotalMilliseconds:0.0} ms";
            return Last;
        }

        // a new map: its layers are new objects (the snapshot is per layer data)
        public static void Forget() => snapshot.Clear();

        // tedtile: list the layers; tedtile LAYER CELL: that cell's tile; tedtile LAYER CELL ID: write it (timed)
        public static string Harness(string[] a)
        {
            var layers = Layers();
            if (layers.Count == 0) return "error: no field layers (not on a map?)";
            if (a.Length > 0 && a[0] == "apply") return Apply(a[1..]);
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
