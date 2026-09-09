#!/usr/bin/env python3
"""解析 Maus et al. 全球采矿多边形成品(gpkg) → 采矿质心点。

数据源: Zenodo record 7307210 "Global mining deforestation footprint data
from 2000 to 2019", file global_mining_polygons.gpkg (~117MB, 192,584 个
采矿多边形, 含 isoa3/country/area_km²)。授权: ODbL——本派生文件沿用 ODbL,
请在使用时对原数据署名。
该数据集即"全球 OSM 采矿面/遥感解译"的整理成品, 覆盖中国/俄罗斯/非洲等
MRDS 欠报地区。

用法: OSM_MINING_GPKG=/path/to/global_mining_polygons.gpkg python3 scripts/parse_osm_mining.py
输出: data/geo/osm_mining_points.csv  (lat, lon, country, isoa3, area_km2)
"""

from __future__ import annotations

import csv
import os
import sqlite3
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = Path(os.environ.get("OSM_MINING_GPKG",
            str(Path.home() / ".cache/opencode-tmp/opencode"
                / "global_mining_polygons.gpkg")))
DST = REPO / "data" / "geo" / "osm_mining_points.csv"


def centroid_from_gpkg_blob(blob: bytes):
    """返回 (lon, lat) 或 None。兼容标准/扩展 GP 头的 Polygon/MultiPolygon。"""
    if blob is None:
        return None
    i = 0
    n = len(blob)
    if n < 9:
        return None
    if blob[:2] == b"GP":
        ver = blob[2]
        flags = blob[3]
        env = (flags >> 1) & 7
        i = 8 + env * 32
    else:
        ver = blob[0]
        flags = blob[1]
        env = (flags >> 1) & 7
        i = 8 + env * 32
    if i + 5 > n:
        return None
    order = blob[i]
    if order == 1:
        fmt = "<"
    elif order == 0:
        fmt = ">"
    else:
        return None
    gtype = struct.unpack(fmt + "I", blob[i + 1:i + 5])[0]

    def read_polygon(off):
        nrings = struct.unpack(fmt + "I", blob[off:off + 4])[0]
        off += 4
        xs, ys = [], []
        for _ in range(nrings):
            npts = struct.unpack(fmt + "I", blob[off:off + 4])[0]
            off += 4
            for _p in range(npts):
                x, y = struct.unpack(fmt + "dd", blob[off:off + 16])
                off += 16
                xs.append(x)
                ys.append(y)
        return off, xs, ys

    try:
        if gtype == 3:  # Polygon
            off, xs, ys = read_polygon(i + 5)
            return (sum(xs) / len(xs), sum(ys) / len(ys))
        if gtype == 6:  # MultiPolygon
            npolys = struct.unpack(fmt + "I", blob[i + 5:i + 9])[0]
            off = i + 9
            allx, ally = [], []
            for _ in range(npolys):
                off, xs, ys = read_polygon(off)
                allx += xs
                ally += ys
            if not allx:
                return None
            return (sum(allx) / len(allx), sum(ally) / len(ally))
    except struct.error:
        return None
    return None


def main() -> int:
    if not SRC.exists():
        print(f"[parse_osm_mining] 缺 {SRC}，先下载:\n"
              "  curl -L -C - https://zenodo.org/api/records/7307210/files/"
              "global_mining_polygons.gpkg/content -o <path>")
        return 1
    con = sqlite3.connect(str(SRC))
    cur = con.execute(
        "select country, isoa3, area, geom from mining_polygons "
        "where geom is not null")
    with DST.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["lat", "lon", "country", "isoa3", "area_km2"])
        n = ok = 0
        for country, isoa3, area, geom in cur:
            n += 1
            c = centroid_from_gpkg_blob(geom)
            if c is None:
                continue
            lon, lat = c
            if not (-85 <= lat <= 85 and -180 <= lon <= 180):
                continue
            ok += 1
            w.writerow([f"{lat:.4f}", f"{lon:.4f}", (country or "").strip(),
                        (isoa3 or "").strip(),
                        f"{area:.3f}" if area is not None else ""])
    print(f"[parse_osm_mining] 读取 {n} 多边形, 输出 {ok} 点 -> {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
