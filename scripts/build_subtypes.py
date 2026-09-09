#!/usr/bin/env python3
"""族内细分：5 个子型的独立前沿格 + 父族格"最像子型"提示。

运行: python scripts/build_subtypes.py [--outdir outputs]
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
    KNOWN_R_DEG, build_grid, frontier_cells,
)
from earth3d.subtypes import SUBTYPES, build_subtype_anchors, score_subtypes  # noqa: E402

SUB_ZH = {"Cu_porphyry": "Cu·斑岩", "Cu_sediment": "Cu·沉积岩容矿",
          "Cu_VMS": "Cu·VMS", "Au_sed": "Au·沉积岩容矿(卡林式)",
          "ZnPb_SEDEX": "Zn-Pb·SEDEX/MVT"}


def _land():
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
    return rings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(REPO / "outputs"))
    args = ap.parse_args()
    od = Path(args.outdir)
    od.mkdir(parents=True, exist_ok=True)
    lat_c, lon_c = build_grid()
    ab = build_subtype_anchors()
    scored = score_subtypes(ab, lat_c, lon_c)

    rows = []
    fig, axes = plt.subplots(1, len(scored),
                             figsize=(4.6 * len(scored), 3.6))
    axes = np.atleast_1d(axes).ravel()
    land = _land()
    for ax, (sub, res) in zip(axes, scored.items()):
        ax.set_facecolor("#BBD8E8")
        for ring in land:
            xs = [c[0] for c in ring]
            ys = [c[1] for c in ring]
            ax.fill(xs, ys, color="#DCE6D2", edgecolor="#999", lw=0.3, zorder=0)
        if res is None:
            ax.set_title(f"{SUB_ZH[sub]} (无锚点)")
            ax.axis("off")
            continue
        pc = ax.pcolormesh(lon_c, lat_c, res["pct"], cmap="YlOrRd",
                           shading="nearest", vmin=0, vmax=100,
                           alpha=0.75, zorder=2)
        a = res["anchors"]
        ax.scatter(a[:, 1], a[:, 0], s=1.5, c="k", alpha=0.3, zorder=4)
        fz = frontier_cells(sub, res["pct"], res["known"], a)
        rows += fz
        ax.set_title(f"{SUB_ZH[sub]}  n锚={len(a)} 前沿{len(fz)}", fontsize=9)
        ax.set_xlim(-180, 180)
        ax.set_ylim(-60, 80)
        fig.colorbar(pc, ax=ax, fraction=0.046, pad=0.02)
    fig.suptitle("族内细分：斑岩/沉积/VMS/卡林式/SEDEX 各自的前沿格", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(od / "subtype_world_map.png", dpi=130)
    plt.close(fig)

    # 父族格"最像哪个子型"提示
    hints = []
    fam_of = {s: p for s, (_, p) in SUBTYPES.items()}
    fams_want = set(fam_of.values())
    with open(od / "prospect_rules_frontiers.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["family"] not in fams_want:
                continue
            cla, clo = float(r["cell_lat"]), float(r["cell_lon"])
            best, bname, bkm = 1e18, None, None
            for sub, (la, lo) in ab.items():
                if fam_of[sub] != r["family"] or len(la) == 0:
                    continue
                d2 = (la - cla) ** 2 + ((lo - clo) * np.cos(np.deg2rad(cla))) ** 2
                i = int(np.argmin(d2))
                km = np.sqrt(d2[i]) * 111.0
                if km < best:
                    best, bname, bkm = km, sub, km
            hints.append({**{k: r[k] for k in
                             ("family", "cell_lat", "cell_lon", "score_pct")},
                         "closest_subtype": bname or "",
                         "closest_subtype_km": round(bkm, 0) if bkm else ""})
    with open(od / "subtype_frontiers.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (-float(r["score_pct"]))))
    with open(od / "subtype_parent_hints.csv", "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(hints[0].keys()))
        w.writeheader()
        w.writerows(hints)
    json.dump({"subtypes": {s: len(ab[s][0]) for s in ab},
               "note": "父族前沿格附 closest_subtype 提示, 用于'同族不同成矿类型'拆读"},
              open(od / "subtype_meta.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("=" * 60)
    for s in SUBTYPES:
        n = sum(1 for r in rows if r["family"] == s)
        print(f"  {s:<14} 锚 {len(ab[s][0]):>4}  前沿格 {n}")
    print("产物:", od / "subtype_frontiers.csv",
          "& subtype_parent_hints.csv & subtype_world_map.png")


if __name__ == "__main__":
    main()
