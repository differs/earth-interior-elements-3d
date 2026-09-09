#!/usr/bin/env python3
"""一键构建地球内部元素立体分布模型，把全部产物写入 outputs/。

运行:  python scripts/build_models.py [--outdir outputs]
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from earth3d.enrichment import element_fate, enrichment_table  # noqa: E402
from earth3d.layering import build_regions  # noqa: E402
from earth3d.model import (  # noqa: E402
    M_CORE, M_CRUST, M_MANTLE, global_crust_ppm, radial_profile_rows,
    reservoir_matrix, write_csv, write_json,
)
from earth3d.reservoirs import get_reservoirs  # noqa: E402


def _fmt(x):
    return f"{x:.3e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(REPO / "outputs"))
    args = ap.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rs = get_reservoirs()
    meta, bins = build_regions()

    # ---- 校验：几何质量 vs 文献目标 ----
    crust_m = sum(b.mass_kg.sum() for b in bins
                  if b.kind == "crust")
    mantle_m = sum(b.mass_kg.sum() for b in bins
                   if b.kind == "mantle")
    core_m = sum(b.mass_kg.sum() for b in bins
                 if b.kind in ("outer_core", "inner_core"))
    total = crust_m + mantle_m + core_m
    print("=" * 62)
    print("地球 1D 分层质量模型 校验")
    print("-" * 62)
    for name, geo, lit in [("地壳", crust_m, M_CRUST),
                           ("地幔", mantle_m, M_MANTLE),
                           ("地核", core_m, M_CORE)]:
        err = (geo - lit) / lit * 100
        print(f"{name:<4} 几何质量={_fmt(geo)} kg  目标={_fmt(lit)} kg"
              f"  偏差={err:+.3f}%")
    print(f"合计  几何质量={_fmt(total)} kg  (地球真实质量 5.972e24 kg,"
          f" 偏差={(total-5.9722e24)/5.9722e24*100:+.4f}%)")
    print(f"地壳等效厚度 = {meta['crust_thickness_km']:.3f} km")
    print(f"密度缩放系数 = { {k: round(v, 4) for k, v in meta['scales'].items()} }")

    # ---- 1. 储库级元素储量长表 ----
    mat = reservoir_matrix(rs)
    write_csv(outdir / "reservoir_elements.csv", mat,
              ["reservoir", "reservoir_zh", "reservoir_mass_kg", "element",
               "ppm_mass", "element_mass_kg", "confidence", "ref"])

    # ---- 2. 径向剖面(每壳每元素) ----
    radial_rows, rmeta = radial_profile_rows(rs)
    write_csv(outdir / "radial_elements.csv", radial_rows,
              ["depth_top_km", "depth_bot_km", "depth_mid_km", "density_gcc",
               "region", "region_zh", "shell_mass_kg", "element", "ppm_mass",
               "shell_element_mass_kg"])
    write_json(outdir / "radial_meta.json", rmeta)

    # ---- 3. 富集因子 & 立体归宿 ----
    enrich = enrichment_table(rs)
    write_csv(outdir / "enrichment_crust_vs_mantle.csv", enrich,
              ["element", "ppm_crust_avg", "ppm_mantle_bse",
               "enrichment_factor", "verdict"])
    fate = element_fate(rs)
    write_csv(outdir / "element_fate_crust_mantle_core.csv", fate,
              ["element", "mass_crust_kg", "mass_mantle_kg", "mass_core_kg",
               "share_crust_pct", "share_mantle_pct", "share_core_pct"])

    # ---- 4. 每壳元素质量小计(便于核对) ----
    agg = defaultdict(float)
    for r in radial_rows:
        agg[(r["region"], r["element"])] += r["shell_element_mass_kg"]
    region_rows = [{"region": k, "element": e, "element_mass_kg": v}
                   for (k, e), v in sorted(agg.items())]
    write_csv(outdir / "radial_region_element_mass.csv", region_rows,
              ["region", "element", "element_mass_kg"])

    # ---- 汇总 json ----
    summary = {
        "version": "v0.1",
        "masses_kg": {"crust": crust_m, "mantle": mantle_m,
                      "core": core_m, "total": total},
        "crust_thickness_km": meta["crust_thickness_km"],
        "density_scales": {k: round(v, 4) for k, v in meta["scales"].items()},
        "element_count": {
            k: len(v["ppm"]) for k, v in rs.items()
        },
        "files": [p.name for p in sorted(outdir.iterdir())],
    }
    write_json(outdir / "summary.json", summary)
    print("-" * 62)
    print("产物已写入:", outdir)
    for p in sorted(outdir.iterdir()):
        print("  ", p.name, f"({p.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
