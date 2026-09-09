#!/usr/bin/env python3
"""同格多族前沿叠加：哪些格同时是多个族的前沿格(多金属富集候选)。

定义: 读 outputs/prospect_rules_frontiers.csv(各族 P90 且 2° 内无该族已知锚点)，
按格统计"同时是几个族的前沿格"。n≥2 → 多成矿体系共点, 常指向大型多金属富集区。
"未标已知"格内部无锚点(相对各族), 因此避免了美国高密度造成的全民高分饱和。

运行: python scripts/build_hotspots.py [--outdir outputs]
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from earth3d.watchlist import classify_cell  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(REPO / "outputs"))
    args = ap.parse_args()
    od = Path(args.outdir)

    cells = collections.defaultdict(list)
    with open(od / "prospect_rules_frontiers.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            cells[(r["cell_lat"], r["cell_lon"])].append(r["family"])

    rows = []
    for (la, lo), fams in cells.items():
        if len(fams) < 2:
            continue
        country, is_land, glacier, town = classify_cell(float(la), float(lo))
        if not is_land:
            continue
        rows.append({
            "cell_lat": la, "cell_lon": lo, "n_families": len(fams),
            "families": " ".join(sorted(fams)),
            "country": country or "", "is_land": is_land,
            "nearest_city_km": town,
        })
    rows.sort(key=lambda r: (-r["n_families"], -float(r["cell_lat"])))

    with (od / "hotspot_top.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # 画世界图(点大小=族数)
    import matplotlib  # noqa: PLC0415
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: PLC0415
    from matplotlib import font_manager  # noqa: PLC0415
    for _f in ("Noto Sans CJK SC", "Noto Sans CJK JP", "WenQuanYi Micro Hei",
               "Source Han Sans SC", "PingFang SC"):
        if any(_f in f.name for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.sans-serif"] = [_f]
            break
    plt.rcParams["axes.unicode_minus"] = False

    g = json.load(open(REPO / "data" / "geo" / "ne_110m_land.geojson",
                       encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(15, 7.5))
    ax.set_facecolor("#BBD8E8")
    for f in g["features"]:
        geom = f["geometry"]
        if geom is None:
            continue
        if geom["type"] == "Polygon":
            rings = [geom["coordinates"][0]]
        elif geom["type"] == "MultiPolygon":
            rings = [p[0] for p in geom["coordinates"]]
        else:
            continue
        for ring in rings:
            xs = [c[0] for c in ring]
            ys = [c[1] for c in ring]
            ax.fill(xs, ys, color="#DCE6D2", edgecolor="#AAB", lw=0.3, zorder=1)
    ns = [r["n_families"] for r in rows]
    sc = ax.scatter([float(r["cell_lon"]) for r in rows],
                    [float(r["cell_lat"]) for r in rows],
                    s=[30 + 60 * (n - min(ns)) / (max(ns) - min(ns) + 1e-9)
                       for n in ns],
                    c=ns, cmap="magma", edgecolors="k", linewidths=0.3, zorder=4)
    fig.colorbar(sc, ax=ax, label="同时前沿的家族数")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-60, 80)
    ax.grid(True, ls=":", color="#888", lw=0.4, alpha=0.5)
    ax.set_title("同格多族前沿叠加(各族 P90 未标已知格的重叠) → 多金属候选")
    fig.tight_layout()
    fig.savefig(od / "hotspot_world_map.png", dpi=140)
    plt.close(fig)

    json.dump({"n_cells_overlap": len(rows),
               "max_families": max(ns) if ns else 0},
              open(od / "hotspot_meta.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("== 多族叠加热区 top12 ==")
    for r in rows[:12]:
        print(f"  {r['cell_lat']:>6},{r['cell_lon']:>8}  族数{r['n_families']:>2} "
              f"{r['country'][:12]:<12} 城{r['nearest_city_km']:>5}km "
              f"| {r['families'][:60]}")
    print(f"共 {len(rows)} 个叠加格 → outputs/hotspot_top.csv & hotspot_world_map.png")


if __name__ == "__main__":
    main()
