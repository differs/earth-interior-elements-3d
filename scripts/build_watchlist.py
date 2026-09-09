#!/usr/bin/env python3
"""生成"全球再勘查观察清单" + 世界分布图 + 汇总。

运行: python scripts/build_watchlist.py [--outdir outputs]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

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

from earth3d.watchlist import build_watchlist  # noqa: E402

TIER_COLOR = {"不可行-海上": "#B0BEC5", "低-极地冰盖": "#CFD8DC",
              "高优先级-标准复查": "#FBC02D",
              "高优先级-数据空洞优先核验": "#E53935"}
TIER_ORDER = ["高优先级-数据空洞优先核验", "高优先级-标准复查",
              "低-极地冰盖", "不可行-海上"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(REPO / "outputs"))
    args = ap.parse_args()
    od = Path(args.outdir)
    od.mkdir(parents=True, exist_ok=True)

    src = od / "prospect_rules_frontiers.csv"
    rows = build_watchlist(src, od / "reexploration_watchlist.csv")
    stats = Counter(r["tier"] for r in rows)
    per_fam = Counter((r["tier"], r["family"]) for r in rows
                      if r["tier"].startswith("高优先级"))
    print("=" * 64)
    print("全球再勘查观察清单 汇总")
    print("-" * 64)
    for t in TIER_ORDER:
        if stats[t]:
            print(f"  {t:<18} {stats[t]}")
    print("-" * 64)
    print("  (高优先级里各族分布):")
    for (t, fam), n in sorted(per_fam.items()):
        print(f"    {fam:<9} {t[:10]:<10} {n}")

    # 地图：按 tier 着色
    g = json.load(open(REPO / "data" / "geo" / "ne_110m_land.geojson",
                       encoding="utf-8"))
    rings = []
    for f in g["features"]:
        geom = f["geometry"]
        if geom is None:
            continue
        if geom["type"] == "Polygon":
            rings.append(geom["coordinates"][0])
        elif geom["type"] == "MultiPolygon":
            rings += [p[0] for p in geom["coordinates"]]
    fig, ax = plt.subplots(figsize=(16, 8))
    ax.set_facecolor("#BBD8E8")
    for ring in rings:
        xs = [c[0] for c in ring]
        ys = [c[1] for c in ring]
        ax.fill(xs, ys, color="#DCE6D2", edgecolor="#AAB", lw=0.3, zorder=1)
    for t in TIER_ORDER:
        sub = [r for r in rows if r["tier"] == t]
        if sub:
            ax.scatter([float(r["cell_lon"]) for r in sub],
                       [float(r["cell_lat"]) for r in sub],
                       s=26, c=TIER_COLOR[t], edgecolors="k", linewidths=0.2,
                       label=f"{t} ({len(sub)})", zorder=4)
    ax.legend(fontsize=8, loc="lower left")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-60, 80)
    ax.grid(True, ls=":", color="#888", lw=0.4, alpha=0.5)
    ax.set_title("全球再勘查观察清单：红=数据空洞优先核验 / 黄=标准复查 / 灰=不可行")
    fig.tight_layout()
    fig.savefig(od / "reexploration_watchlist_map.png", dpi=140)
    plt.close(fig)

    json.dump({"tier_stats": dict(stats), "total": len(rows),
               "high_priority": sum(1 for r in rows
                                    if r["tier"].startswith("高优先级"))},
              open(od / "reexploration_meta.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("产物:", od / "reexploration_watchlist.csv")


if __name__ == "__main__":
    main()
