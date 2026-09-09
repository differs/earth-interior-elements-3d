"""富集因子与"立体归宿"判定。

地壳/地幔富集因子 EF = ppm_crust / ppm_mantle(BSE)：
- EF >> 1  → 该元素被强烈抽提进地壳(岩浆分异/流体搬运/热液富集)
- EF ~ 1   → 中性，分布按质量比例自然分摊
- EF << 1  → 地幔相容元素(亲铁/相容主量)，大量留在深部

这是把"元素在地球内部的立体分布"转成可查询"资源可及性"的第一步：
地壳富集型 = 地表浅层最可能成矿(现在的矿山)；地幔相容型 = 存量在深处、
只有地幔柱/折返机制能把它们带到近地表。推导逻辑见 docs/derivation.md。
"""

from __future__ import annotations

from .model import global_crust_ppm
from .reservoirs import get_reservoirs

EF_CUTS = {"crust_enriched": 5.0, "mantle_compatible": 0.2}


def enrichment_table(rs: dict | None = None) -> list[dict]:
    rs = rs or get_reservoirs()
    crust = global_crust_ppm(rs)
    mantle = rs["mantle"]["ppm"]
    rows = []
    for el in sorted(set(crust) & set(mantle)):
        pc, pm = crust[el], mantle[el]
        ef = pc / pm if pm > 0 else float("inf")
        if ef >= EF_CUTS["crust_enriched"]:
            verdict = "地壳富集型(浅层成矿潜力高)"
        elif ef <= EF_CUTS["mantle_compatible"]:
            verdict = "地幔相容型(存量深藏)"
        else:
            verdict = "近中性分布"
        rows.append({
            "element": el,
            "ppm_crust_avg": round(pc, 6),
            "ppm_mantle_bse": round(pm, 6),
            "enrichment_factor": round(ef, 3) if ef != float("inf") else None,
            "verdict": verdict,
        })
    rows.sort(key=lambda r: -(r["enrichment_factor"] or 1e9))
    return rows


def element_fate(rs: dict | None = None) -> list[dict]:
    """三储库(壳/幔/核)对某元素在"已建模元素集合"内的质量份额。"""
    rs = rs or get_reservoirs()
    shell_mass = {
        "crust": rs["continental_crust"]["mass_kg"] + rs["oceanic_crust"]["mass_kg"],
        "mantle": rs["mantle"]["mass_kg"],
        "core": rs["core"]["mass_kg"],
    }
    comp = {
        "crust": global_crust_ppm(rs),
        "mantle": rs["mantle"]["ppm"],
        "core": rs["core"]["ppm"],
    }
    out = []
    for el in set(comp["crust"]) | set(comp["mantle"]) | set(comp["core"]):
        share = {k: comp[k].get(el, 0.0) * 1e-6 * shell_mass[k] for k in comp}
        tot = sum(share.values())
        if tot <= 0:
            continue
        out.append({
            "element": el,
            "mass_crust_kg": share["crust"],
            "mass_mantle_kg": share["mantle"],
            "mass_core_kg": share["core"],
            "share_crust_pct": round(100 * share["crust"] / tot, 2),
            "share_mantle_pct": round(100 * share["mantle"] / tot, 2),
            "share_core_pct": round(100 * share["core"] / tot, 2),
        })
    return out
