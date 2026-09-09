#!/usr/bin/env python3
"""构建 2° 勘探潜力/前沿格产物。

运行: python scripts/build_prospect.py [--outdir outputs]
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
    ANCHOR_CAP, LAT_MAX, LAT_MIN, frontier_cells, build_grid, load_anchors,
    score_family,
)

FAM_ZH = {"Au": "金 Au", "Cu": "铜 Cu", "Fe": "铁 Fe", "NiCo": "镍钴 Ni-Co",
          "Li": "锂 Li", "REE": "稀土 REE", "PGE": "铂族 PGE", "U": "铀 U",
          "Diamond": "金刚石", "Coal": "煤", "OilGas": "油气",
          "ZnPb": "锌铅 Zn-Pb", "Cr": "铬 Cr", "Mn": "锰 Mn", "W": "钨 W",
          "Sn": "锡 Sn", "Sb": "锑 Sb", "V": "钒 V", "Ti": "钛 Ti",
          "TaNb": "钽铌 Ta-Nb", "Ag": "银 Ag", "Mo": "钼 Mo", "Re": "铼 Re",
          "Bi": "铋 Bi", "As": "砷 As", "Be": "铍 Be", "CsRb": "铯铷 Cs-Rb",
          "Sc": "钪 Sc", "Zr": "锆 Zr", "Graphite": "石墨",
          "Ga": "镓 Ga", "Ge": "锗 Ge", "In": "铟 In", "Tl": "铊 Tl",
          "Se": "硒 Se", "Te": "碲 Te", "Hf": "铪 Hf", "Sr": "锶 Sr",
          "Ba": "钡 Ba", "F": "氟 F", "K": "钾 K", "P": "磷 P"}


def _write(path, rows, cols):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in cols})


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


def draw_map(out, results, lat_c, lon_c):
    fams = [f for f in results if results[f]["has"]]
    n = len(fams)
    ncol = 3
    nrow = (n + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(5.2 * ncol, 3.4 * nrow))
    axes = np.atleast_1d(axes).ravel()
    for ax in axes:
        ax.axis("off")
    for ax, fam in zip(axes, fams):
        pct = results[fam]["pct"]
        known = results[fam]["known"]
        ax.set_facecolor("#BBD8E8")
        for ring in _land():
            xs = [c[0] for c in ring]
            ys = [c[1] for c in ring]
            ax.fill(xs, ys, color="#DCE6D2", edgecolor="#999", lw=0.3, zorder=0)
        pc = ax.pcolormesh(lon_c, lat_c, pct, cmap="YlOrRd",
                           shading="nearest", vmin=0, vmax=100,
                           alpha=0.78, zorder=2)
        a = results[fam]["anchors"]
        if len(a):
            ax.scatter(a[:, 1], a[:, 0], s=1.2, c="k", alpha=0.28, zorder=3)
        ax.set_title(f"{FAM_ZH.get(fam, fam)}  (n={len(a)})", fontsize=9)
        ax.set_xlim(-180, 180)
        ax.set_ylim(LAT_MIN - 2, LAT_MAX + 2)
        ax.grid(True, ls=":", color="#888", lw=0.3, alpha=0.5, zorder=1)
        fig.colorbar(pc, ax=ax, fraction=0.046, pad=0.02)
    fig.suptitle("2° 网格“已知富集引力”百分位：高分=已知邻域; 前沿格=高分未标记"
                 " (σ=4°, 见 docs/prospectivity.md)", fontsize=11)
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

    results = {}
    for fam, a in anchors.items():
        pct, known, _ = score_family(a, lat_c, lon_c)
        results[fam] = {"pct": pct, "known": known, "anchors": a,
                        "has": len(a) > 0}
    print("=" * 64)
    print("2° 网格 勘探引力/前沿格 汇总")
    print("-" * 64)
    allf = []
    for fam, res in results.items():
        if not res["has"]:
            continue
        a = res["anchors"]
        fz = frontier_cells(fam, res["pct"], res["known"], a)
        allf += fz
        nf = len(fz)
        print(f"  {fam:<9} 锚点 {len(a):>5}  前沿格(P90+) {nf:>3}  "
              f"最高分格 {res['pct'].max():.0f}%")
    _write(od / "prospect_frontiers.csv", allf,
           ["family", "cell_lat", "cell_lon", "score_pct",
            "nearest_anchor_lat", "nearest_anchor_lon", "nearest_km"])
    # 图面板太多时只画锚点最多的 N 个族(CSV 前沿格仍覆盖全部族)
    plot_fams = sorted(results, key=lambda f: -len(results[f]["anchors"]))[:24]
    draw_map(od / "prospect_world_frontiers.png",
             {f: results[f] for f in plot_fams}, lat_c, lon_c)

    n_anchor_src = {f: len(a) for f, a in anchors.items() if len(a) > 0}
    json.dump({"sigma_deg": 4.0, "grid_deg": 2.0,
               "anchor_cap_per_family": ANCHOR_CAP,
               "method": "gaussian-kernel known-deposit gravity + frontier cells",
               "caveats": ["MRDS 美国记录偏重", "未预测未发现新矿, 只外推已知邻域",
                           "坐标 2° 单元, 用于全球尺度"],
               "frontiers_total": len(allf),
               "anchors": n_anchor_src},
              open(od / "prospect_meta.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("-" * 64)
    print("产物:", od / "prospect_frontiers.csv",
          "& prospect_world_frontiers.png & prospect_meta.json")


if __name__ == "__main__":
    main()
