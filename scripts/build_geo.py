#!/usr/bin/env python3
"""构建地理层产物：世界级矿床/油气省 + 世界分布图 + 汇总。

运行: python scripts/build_geo.py [--outdir outputs]
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
from matplotlib.collections import PathCollection  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from matplotlib.path import Path as MplPath  # noqa: E402

for _f in ("Noto Sans CJK SC", "Noto Sans CJK JP", "WenQuanYi Micro Hei",
           "Source Han Sans SC", "PingFang SC"):
    if any(_f in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [_f]
        break
plt.rcParams["axes.unicode_minus"] = False

from earth3d.geo import attach_enrichment, family_summary, load_deposits  # noqa: E402

FAM_COLOR = {
    "Au": "#D4AF37", "Cu": "#B87333", "Fe": "#6E6E6E", "NiCo": "#7FB069",
    "Li": "#B983FF", "REE": "#5B7B9A", "PGE": "#4B8BBE", "U": "#2E7D32",
    "Diamond": "#3A86FF", "OilGas": "#343A40", "Coal": "#231F20",
}


def _land_polys(geojson_path):
    g = json.load(open(geojson_path, encoding="utf-8"))
    polys = []
    for f in g["features"]:
        geom = f["geometry"]
        if geom is None:
            continue
        if geom["type"] == "Polygon":
            polys.append(geom["coordinates"][0])
        elif geom["type"] == "MultiPolygon":
            for p in geom["coordinates"]:
                polys.append(p[0])
    return polys


def draw_map(out_path, metal_rows, hydro_rows):
    fig, ax = plt.subplots(figsize=(16, 8))
    for ring in _land_polys(REPO / "data" / "geo" / "ne_110m_land.geojson"):
        xs = [c[0] for c in ring]
        ys = [c[1] for c in ring]
        ax.fill(xs, ys, color="#DCE6D2", edgecolor="#AAB", lw=0.3, zorder=1)
    ax.set_facecolor("#BBD8E8")

    def scatter(rows, marker, s, z, edge):
        if not rows:
            return
        xs = [r["lon"] for r in rows]
        ys = [r["lat"] for r in rows]
        cols = [FAM_COLOR.get(r["family"], "#999") for r in rows]
        ax.scatter(xs, ys, c=cols, marker=marker, s=s, zorder=z,
                   edgecolors=edge, linewidths=0.3, alpha=0.92)

    scatter(metal_rows, "o", 90, 3, "white")
    scatter(hydro_rows, "^", 55, 2, "white")

    handles = [plt.Line2D([0], [0], marker="o", color="w", ms=9,
                          markerfacecolor=c, label=lb)
               for lb, c in FAM_COLOR.items()]
    ax.legend(handles=handles, loc="lower left", ncol=2, fontsize=8,
              framealpha=0.9, title="● 固体金属矿   ▲ 油气/煤省")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-60, 75)
    ax.set_aspect(1.0 / np.cos(np.deg2rad(30)))
    ax.grid(True, ls=":", color="#888", lw=0.4, alpha=0.6)
    ax.set_title("世界级“宝藏”分布：容易开采的固体矿产省与超级油气省 (v0.3)")
    ax.set_xlabel("经度"); ax.set_ylabel("纬度")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def _dump(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if v is None else v) for k, v in r.items()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(REPO / "outputs"))
    args = ap.parse_args()
    od = Path(args.outdir)
    od.mkdir(parents=True, exist_ok=True)

    metals = attach_enrichment(load_deposits())
    hydro = attach_enrichment(load_deposits(hydrocarbon=True))
    print("=" * 60)
    print("地理层 世界级矿床/油气省 汇总")
    print("-" * 60)
    for f in ("Au", "Cu", "Fe", "NiCo", "Li", "REE", "PGE", "U",
              "Diamond", "OilGas", "Coal"):
        n = sum(1 for r in metals + hydro if r["family"] == f)
        if n:
            print(f"  {f:<9} 省/区带 = {n}")
    print(f"  {'总计':<9} 省/区带 = {len(metals) + len(hydro)}"
          f"  (固体矿 {len(metals)} / 油气煤 {len(hydro)})")

    _dump(metals, od / "geo_deposits_processed.csv")
    _dump(hydro, od / "geo_hydrocarbon_processed.csv")
    sum_all = family_summary(metals + hydro)
    _dump(sum_all, od / "geo_family_summary.csv")
    draw_map(od / "geo_world_map.png", metals, hydro)
    json.dump({"n_metals": len(metals), "n_hydro": len(hydro),
               "families": sum_all},
              open(od / "geo_meta.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("图与表已写入:", od)


if __name__ == "__main__":
    main()
