#!/usr/bin/env python3
"""构建"构造规则版"勘探潜力产物。

规则 = 锚点(已知矿) + 弧火山(俯冲) + 裂谷火山 三类距离核的加权组合，
权重与理由见 prospect.RULES（来源：EF/生成窗/教科书成矿类型）。

运行: python scripts/build_prospect_rules.py [--outdir outputs]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import numpy as np  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

for _f in ("Noto Sans CJK SC", "Noto Sans CJK JP", "WenQuanYi Micro Hei",
           "Source Han Sans SC", "PingFang SC"):
    if any(_f in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [_f]
        break
plt.rcParams["axes.unicode_minus"] = False

from earth3d.prospect import (  # noqa: E402
    RULES, build_grid, frontier_cells, load_anchors, load_gvp_env,
    rule_grids,
)

FAM_ZH = {"Au": "金 Au", "Cu": "铜 Cu", "Fe": "铁 Fe", "NiCo": "镍钴", "Li": "锂 Li",
          "REE": "稀土", "PGE": "铂族", "U": "铀 U", "Diamond": "金刚石",
          "Coal": "煤", "OilGas": "油气",
          "ZnPb": "锌铅", "Cr": "铬", "Mn": "锰", "W": "钨",
          "Sn": "锡", "Sb": "锑", "V": "钒", "Ti": "钛", "TaNb": "钽铌",
          "Ag": "银", "Mo": "钼", "Re": "铼", "Bi": "铋", "As": "砷",
          "Be": "铍", "CsRb": "铯铷", "Sc": "钪", "Zr": "锆", "Graphite": "石墨",
          "Ga": "镓 Ga", "Ge": "锗 Ge", "In": "铟 In", "Tl": "铊 Tl",
          "Se": "硒 Se", "Te": "碲 Te", "Hf": "铪 Hf", "Sr": "锶 Sr",
          "Ba": "钡 Ba", "F": "氟 F", "K": "钾 K", "P": "磷 P"}


def _land():
    g = json.load(open(REPO / "data" / "geo" / "ne_110m_land.geojson",
                       encoding="utf-8"))
    for f in g["features"]:
        geom = f["geometry"]
        if geom is None:
            continue
        if geom["type"] == "Polygon":
            yield geom["coordinates"][0]
        elif geom["type"] == "MultiPolygon":
            for p in geom["coordinates"]:
                yield p[0]


def _write(path, rows, cols):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in cols})


def draw(out, results, lat_c, lon_c, envs):
    fams = [f for f, r in results.items() if r["pct"] is not None]
    ncol = 3
    nrow = (len(fams) + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(5.4 * ncol, 3.4 * nrow))
    axes = np.atleast_1d(axes).ravel()
    for ax in axes:
        ax.axis("off")
    for ax, fam in zip(axes, fams):
        r = results[fam]
        ax.set_facecolor("#BBD8E8")
        for ring in _land():
            xs = [c[0] for c in ring]
            ys = [c[1] for c in ring]
            ax.fill(xs, ys, color="#DCE6D2", edgecolor="#999", lw=0.3, zorder=0)
        pc = ax.pcolormesh(lon_c, lat_c, r["pct"], cmap="YlOrRd",
                           shading="nearest", vmin=0, vmax=100,
                           alpha=0.75, zorder=2)
        a = r["anchors"]
        if len(a):
            ax.scatter(a[:, 1], a[:, 0], s=1.4, c="k", alpha=0.3, zorder=4)
        # 环境参考点：弧(红三角) 裂谷(青点)
        ax.scatter(envs["arc"][1], envs["arc"][0], s=2, c="#D55E00",
                   alpha=0.5, marker="^", zorder=3)
        ax.scatter(envs["rift"][1], envs["rift"][0], s=3, c="#009E73",
                   alpha=0.6, marker="o", zorder=3)
        ax.set_title(f"{FAM_ZH.get(fam, fam)}  规则分(n锚={len(a)})", fontsize=9)
        ax.set_xlim(-180, 180)
        ax.set_ylim(-60, 80)
        fig.colorbar(pc, ax=ax, fraction=0.046, pad=0.02)
    fig.suptitle("2° 构造规则版评分：锚点×权重 + 弧/裂谷距离核(百分位; "
                 "见 docs/prospectivity.md §规则版)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out, dpi=130)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(REPO / "outputs"))
    args = ap.parse_args()
    od = Path(args.outdir)
    od.mkdir(parents=True, exist_ok=True)
    lat_c, lon_c = build_grid()
    anchors = load_anchors()
    envs = load_gvp_env()

    results, frontier_all, wrows = {}, [], []
    for fam, weights in RULES.items():
        a = anchors.get(fam, np.empty((0, 3)))
        if len(a) == 0:
            results[fam] = {"pct": None, "anchors": a}
            continue
        raw, pct, known = rule_grids(a, envs, weights[:3], lat_c, lon_c)
        results[fam] = {"pct": pct, "anchors": a}
        fz = frontier_cells(fam, pct, known, a)
        frontier_all += fz
        wrows.append({"family": fam, "anchor_w": weights[0], "arc_w": weights[1],
                      "rift_w": weights[2], "reason": weights[3]})

    print("=" * 64)
    print("构造规则版评分 汇总 (锚点/弧/裂谷 加权)")
    print("-" * 64)
    for fam, w in RULES.items():
        if results[fam]["pct"] is None:
            continue
        nf = sum(1 for r in frontier_all if r["family"] == fam)
        print(f"  {fam:<9} a{w[0]:.1f} arc{w[1]:+.1f} rift{w[2]:.1f}  "
              f"前沿格 {nf}")
    _write(od / "prospect_rules_frontiers.csv", frontier_all,
           ["family", "cell_lat", "cell_lon", "score_pct",
            "nearest_anchor_lat", "nearest_anchor_lon", "nearest_km"])
    _write(od / "prospect_rules_weights.csv", wrows,
           ["family", "anchor_w", "arc_w", "rift_w", "reason"])
    draw(od / "prospect_rules_world_map.png", results, lat_c, lon_c, envs)
    meta = {"weights_table": wrows,
            "sigma_deg": 4.0,
            "caveats": ["GVP 火山=岩浆活动代理(含热点), 非纯弧",
                        "缺少克拉通/沉积盆地掩码: Diamond/OilGas 主要靠锚点+负规则",
                        "MRDS 美国偏重"],
            "gvp_n": {k: len(v[0]) for k, v in envs.items()},
            "frontiers_total": len(frontier_all)}
    json.dump(meta, open(od / "prospect_rules_meta.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("-" * 64)
    print("产物:", od / "prospect_rules_frontiers.csv", "& weights & map & meta")


if __name__ == "__main__":
    main()
