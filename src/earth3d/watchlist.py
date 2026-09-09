"""全球再勘查观察清单：给规则前沿格加"可采性过滤 + 数据空洞标注"。

方法论(详见 docs/methodology_watchlist.md)：
- 输入: prospect_rules_frontiers.csv(各族 P90 前沿格)
- 每格附加:
   1) 可采性: is_land(NE 陆地) / 冰盖(NE glaciated) / 极地(高纬) / 最近主要城市(km)
   2) 数据空洞: 该格所在国 的 MRDS 记录数 vs 该国被本仓库收录的世界级省数
      → reporting_gap = MRDS 偏少但有世界级已知矿(说明"已知在,但全球库没收录")
   3) 就近富集上下文: 同族锚点在 ±5° 内的条数(家族级数据密度)
- 分层(tier):
     不可行-海上 / 低-极地冰盖 /
     高优先级-数据空洞优先核验 / 高优先级-标准复查
诚实边界: 观察清单 = 假设排序 + 过滤，不是矿床预测；
       MRDS 数据空洞标注用于提示"先补当地权威图件再下结论"。
"""

from __future__ import annotations

import csv
import json
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MplPath

REPO = Path(__file__).resolve().parents[2]
GEO = REPO / "data" / "geo"

POLAR_LAT = 72.0
GAP_MRDS_N = 5000       # 国家 MRDS 条数低于此且又有一级矿 → 判 reporting gap
GAP_PROV_N = 2

# NE(英文) -> 该仓库 curate/ MRDS 里常见的国名书写别名
ALIAS = {
    "United States of America": ["美国", "United States", "USA", "Nevada美国"],
    "Russia": ["俄罗斯", "Russia", "Russian Federation", "萨哈", "伊尔库茨克"],
    "China": ["中国", "China", "内蒙古", "赣南", "四川", "山西", "黑龙江"],
    "Canada": ["加拿大", "Canada", "安大略", "魁北克", "萨斯喀彻温",
               "拉布拉多", "西北领地", "阿萨巴斯卡"],
    "Australia": ["澳大利亚", "Australia", "西澳", "北领地", "昆士兰"],
    "South Africa": ["南非", "South Africa"],
    "Botswana": ["博茨瓦纳", "Botswana"],
    "Brazil": ["巴西", "Brazil"],
    "Mexico": ["墨西哥", "Mexico"],
    "Argentina": ["阿根廷", "Argentina"],
    "Chile": ["智利", "Chile"],
    "Bolivia": ["玻利维亚", "Bolivia"],
    "Peru": ["秘鲁", "Peru"],
    "Colombia": ["哥伦比亚", "Colombia"],
    "Guyana": ["圭亚那", "Guyana"],
    "Venezuela": ["委内瑞拉", "Venezuela"],
    "Angola": ["安哥拉", "Angola"],
    "Namibia": ["纳米比亚", "Namibia"],
    "Zimbabwe": ["津巴布韦", "Zimbabwe"],
    "Tanzania": ["坦桑尼亚", "Tanzania"],
    "Ghana": ["加纳", "Ghana"],
    "DR Congo": ["刚果金", "刚果(金)", "DRC"],
    "Zambia": ["赞比亚", "Zambia"],
    "Uganda": ["乌干达", "Uganda"],
    "Kazakhstan": ["哈萨克斯坦", "Kazakhstan"],
    "Uzbekistan": ["乌兹别克斯坦", "Uzbekistan"],
    "Mongolia": ["蒙古", "Mongolia"],
    "Indonesia": ["印度尼西亚", "Indonesia", "印尼"],
    "New Caledonia": ["新喀里多尼亚"],
    "Norway": ["挪威", "Norway"],
    "Saudi Arabia": ["沙特阿拉伯", "Saudi Arabia"],
    "Kuwait": ["科威特", "Kuwait"],
    "Qatar": ["卡塔尔", "Qatar"],
    "Iran": ["伊朗", "Iran"],
    "Ukraine": ["乌克兰", "Ukraine"],
    "France": ["法国", "France"],
    "Italy": ["意大利", "Italy"],
    "Ethiopia": ["埃塞俄比亚", "Ethiopia"],
}


def _aliases(ne_name):
    return ALIAS.get(ne_name, [ne_name])


def _contains(cell, ne_name):
    cell = (cell or "").lower()
    for t in _aliases(ne_name):
        if not t:
            continue
        t = t.lower()
        # 防误判: 新墨西哥(美国州名) ≠ 墨西哥
        if t == "墨西哥" and "新墨西哥" in cell:
            continue
        if t in cell:
            return True
    return cell in ne_name.lower() or ne_name.lower() in cell


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return R * 2 * asin(sqrt(a))


def _load_polygon_sets(path, name_key):
    """geojson -> [(name, list_of_ring_paths)]"""
    g = json.load(open(path, encoding="utf-8"))
    sets = []
    for f in g["features"]:
        geom = f["geometry"]
        if geom is None:
            continue
        name = (f["properties"].get(name_key) or
                f["properties"].get("NAME") or
                f["properties"].get("name") or "")
        rings = []
        if geom["type"] == "Polygon":
            rings = geom["coordinates"]
        elif geom["type"] == "MultiPolygon":
            rings = [r for p in geom["coordinates"] for r in p]
        sets.append((name, [MplPath(np.array(r)) for r in rings]))
    return sets


def _name_in(name, s):
    a, b = (name or "").lower(), (s or "").lower()
    return a and b and (a in b or b in a or a.replace(".", "") == b.replace(".", ""))


_LAND = None
_COUNTRIES = None
_GLACIERS = None
_CITIES = None


def _get(kind):
    global _LAND, _COUNTRIES, _GLACIERS, _CITIES
    if kind == "land" and _LAND is None:
        _LAND = _load_polygon_sets(GEO / "ne_110m_land.geojson", "name")
    if kind == "countries" and _COUNTRIES is None:
        _COUNTRIES = _load_polygon_sets(GEO / "ne_110m_admin_0_countries.geojson",
                                        "NAME")
    if kind == "glaciers" and _GLACIERS is None:
        _GLACIERS = _load_polygon_sets(GEO / "ne_110m_glaciated_areas.geojson",
                                       "NAME")
    if kind == "cities" and _CITIES is None:
        _CITIES = _load_polygon_sets  # placeholder, never used
    return {"land": _LAND, "countries": _COUNTRIES,
            "glaciers": _GLACIERS}[kind]


def _cities():
    global _CITIES
    if _CITIES is None:
        g = json.load(open(GEO / "ne_110m_populated_places.geojson",
                           encoding="utf-8"))
        _CITIES = [(f["properties"].get("NAME"),
                    f["geometry"]["coordinates"][1],
                    f["geometry"]["coordinates"][0])
                   for f in g["features"]
                   if f["geometry"] and f["geometry"]["coordinates"]]
    return _CITIES


def classify_cell(lat, lon):
    """返回 (country, is_land, on_glacier, nearest_city_km)。"""
    country, is_land, glacier = None, False, False
    for name, rings in _get("countries"):
        for ring in rings:
            if ring.contains_point((lon, lat)):
                country = name
                break
        if country:
            break
    for name, rings in _get("land"):
        hit = False
        for ring in rings:
            if ring.contains_point((lon, lat)):
                hit = True
                break
        if hit:
            is_land = True
            break
    for name, rings in _get("glaciers"):
        hit = False
        for ring in rings:
            if ring.contains_point((lon, lat)):
                hit = True
                break
        if hit:
            glacier = True
            break
    near = None
    best = 1e9
    for cname, cla, clo in _cities():
        d = haversine_km(lat, lon, cla, clo)
        if d < best:
            best, near = d, cname
    return country, is_land, glacier, round(best)


def country_coverage_stats():
    """国家级(按 NE 国名键): MRDS 条数与 本仓库世界级省数。"""
    from collections import Counter
    mrds_c, prov_c = Counter(), Counter()
    anchors = REPO / "data" / "raw" / "mrds_anchors.csv"
    if anchors.exists():
        with anchors.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                mrds_c[(row["country"] or "").strip()] += 1
    for p in (REPO / "data" / "raw" / "geo_world_class_deposits.csv",
              REPO / "data" / "raw" / "geo_hydrocarbon_provinces.csv"):
        with p.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                prov_c[(row["country"] or "").strip()] += 1
    ne_names = [name for name, _ in _get("countries")]
    def roll(counter):
        out = {}
        for ne in ne_names:
            out[ne] = sum(v for k, v in counter.items() if _contains(k, ne))
        return out
    return roll(mrds_c), roll(prov_c)


def build_watchlist(frontier_path, out_path) -> list[dict]:
    mrds_n, prov_n = country_coverage_stats()
    rows = []
    with open(frontier_path, encoding="utf-8") as fh:
        frontier = list(csv.DictReader(fh))
    for r in frontier:
        fam = r["family"]
        lat, lon = float(r["cell_lat"]), float(r["cell_lon"])
        country, is_land, glacier, town = classify_cell(lat, lon)
        nm = mrds_n.get(country, 0) if country else 0
        np_ = prov_n.get(country, 0) if country else 0
        if not is_land:
            tier = "不可行-海上"
        elif glacier or abs(lat) >= POLAR_LAT:
            tier = "低-极地冰盖"
        else:
            gap = (nm < GAP_MRDS_N and np_ >= GAP_PROV_N) or (nm == 0 and np_ >= 1)
            tier = "高优先级-数据空洞优先核验" if gap else "高优先级-标准复查"
        rows.append({
            "family": fam, "cell_lat": r["cell_lat"], "cell_lon": r["cell_lon"],
            "score_pct": r["score_pct"], "nearest_anchor_km": r["nearest_km"],
            "country": country or "",
            "is_land": is_land, "on_glacier": glacier,
            "nearest_city_km": town,
            "country_mrds_n": nm, "country_province_n": np_,
            "reporting_gap": (tier == "高优先级-数据空洞优先核验"),
            "tier": tier,
        })
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for x in sorted(rows, key=lambda x: (-x["reporting_gap"],
                                             -float(x["score_pct"]))):
            w.writerow(x)
    return rows
