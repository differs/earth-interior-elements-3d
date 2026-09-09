"""组装模型：储库质量矩阵 + 径向元素剖面。

输出均为"长表"csv/json，字段自解释，便于复算与审阅。
"""

from __future__ import annotations

import json

import numpy as np

from .layering import build_regions, concat_bins
from .reservoirs import M_CRUST, M_MANTLE, M_CORE, get_reservoirs

RESERVOIR_ZH = {
    "continental_crust": "大陆地壳", "oceanic_crust": "洋壳",
    "mantle": "地幔", "core": "地核",
}


def global_crust_ppm(rs: dict) -> dict:
    """大陆+洋壳按质量加权的平均地壳成分(元素并集)。"""
    m_cc = rs["continental_crust"]["mass_kg"]
    m_oc = rs["oceanic_crust"]["mass_kg"]
    els = set(rs["continental_crust"]["ppm"]) | set(rs["oceanic_crust"]["ppm"])
    return {
        el: (rs["continental_crust"]["ppm"].get(el, 0.0) * m_cc
             + rs["oceanic_crust"]["ppm"].get(el, 0.0) * m_oc) / (m_cc + m_oc)
        for el in els
    }


def reservoir_matrix(rs: dict) -> list[dict]:
    """每储库每元素的储量长表。"""
    rows = []
    for key, r in rs.items():
        for el, ppm in r["ppm"].items():
            rows.append({
                "reservoir": key,
                "reservoir_zh": RESERVOIR_ZH[key],
                "reservoir_mass_kg": r["mass_kg"],
                "element": el,
                "ppm_mass": ppm,
                "element_mass_kg": ppm * 1e-6 * r["mass_kg"],
                "confidence": r["confidence"],
                "ref": r["ref"],
            })
    return rows


def _comp_for(profile_region: str, rs: dict) -> dict:
    if profile_region in ("crust",):
        return global_crust_ppm(rs)
    if profile_region in ("upper_mantle", "transition", "lower_mantle", "mantle"):
        return rs["mantle"]["ppm"]
    if profile_region in ("outer_core", "inner_core"):
        return rs["core"]["ppm"]
    raise KeyError(profile_region)


def radial_profile_rows(rs: dict | None = None) -> tuple[list[dict], dict]:
    """径向剖面：每个壳×每个元素一行(element 为 - 表示只给壳质量)。"""
    rs = rs or get_reservoirs()
    _, bins = build_regions()
    prof = concat_bins(bins)
    zh = {"crust": "地壳(等效)", "mantle": "地幔", "outer_core": "外核", "inner_core": "内核"}
    rows = []
    for i in range(len(prof["depth_top"])):
        region = prof["reservoir"][i]
        comp = _comp_for(region, rs)
        shell_mass = prof["mass_kg"][i]
        for el, ppm in comp.items():
            rows.append({
                "depth_top_km": round(float(prof["depth_top"][i]), 3),
                "depth_bot_km": round(float(prof["depth_bot"][i]), 3),
                "depth_mid_km": round(float(prof["depth_mid"][i]), 3),
                "density_gcc": round(float(prof["density_gcc"][i]), 4),
                "region": region,
                "region_zh": zh[region],
                "shell_mass_kg": float(shell_mass),
                "element": el,
                "ppm_mass": float(ppm),
                "shell_element_mass_kg": float(ppm * 1e-6 * shell_mass),
            })
    meta = {"total_mass_kg": float(sum(prof["mass_kg"]))}
    return rows, meta


def write_csv(path, rows, cols):
    import csv
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in cols})


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
