"""地理层：世界级成矿省/油气省 → "容易开采的宝藏"分布。

思路(与 docs/geo_distribution.md 一致)：
- 已知世界级矿床 = 地下成矿"窗口"在浅部真实打开过的最强证据(勘探旋回已很充分)；
- 每个省的"易采性"由 开采方式(access) 映射成 tier；
- 主元素 EF(地壳/地幔富集因子) 把立体模型与地理锚点串起来：
  高 EF + 浅表成矿 = 该元素"最容易在地表附近被开采"。
坐标均为**省/区带质心，±1.5° 近似**，须复核后再用于精确定位。
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PRIMARY_FAMILY = {
    "Au": "Au", "Cu": "Cu", "Fe": "Fe", "Ni": "NiCo", "Co": "NiCo",
    "Li": "Li", "REE": "REE", "PGE": "PGE", "U": "U", "Diamond": "Diamond",
    "Oil": "OilGas", "Gas": "OilGas", "Coal": "Coal",
}

ACCESS_TIER = {
    # 最易采：不需要破碎/溶浸直接可得
    "卤水抽取": 5, "卤水/溶液法": 5, "原地浸出": 4,
    "井采": 5, "露天": 4, "露天+井下": 3, "露天+地下": 3,
    "地下": 2, "水平压裂+井采": 5,
    "海上井采": 3, "海上深水井采": 2, "海上+陆上井采": 3,
    "溶液/地浸": 4,
}


def load_deposits(path=None, hydrocarbon=False) -> list[dict]:
    p = Path(path or (ROOT / "data" / "raw"
                      / ("geo_hydrocarbon_provinces.csv" if hydrocarbon
                         else "geo_world_class_deposits.csv")))
    rows = []
    with p.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            r["family"] = PRIMARY_FAMILY.get(r["primary"], "other")
            r["lat"] = float(r["lat"])
            r["lon"] = float(r["lon"])
            r["tier"] = ACCESS_TIER.get(r["access"], 1)
            rows.append(r)
    return rows


def attach_enrichment(rows) -> list[dict]:
    """把主元素的 地壳/地幔富集因子(EF, 来自立体模型)挂到每个省上。"""
    from .enrichment import enrichment_table
    ef = {r["element"]: r["enrichment_factor"] for r in enrichment_table()}
    for r in rows:
        r["ef_primary"] = ef.get(r["primary"])
    return rows


def family_summary(rows) -> list[dict]:
    out = []
    fams = sorted({r["family"] for r in rows})
    for f in fams:
        sub = [r for r in rows if r["family"] == f]
        countries = sorted({r["country"].split("(")[0].strip() for r in sub})
        out.append({
            "family": f,
            "n_provinces": len(sub),
            "countries": "、".join(countries),
            "median_tier": sorted(r["tier"] for r in sub)[len(sub) // 2],
            "high_conf": sum(1 for r in sub if r["confidence"] == "high"),
        })
    return out
