#!/usr/bin/env python3
"""输出可视化图：径向丰度剖面 / 圈层储量份额 / 富集因子。

运行: python scripts/make_plots.py [--outdir outputs]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from earth3d.vis import (  # noqa: E402
    fig_core_inversion, fig_enrichment, fig_radial_abundance,
    fig_reservoir_share,
)


def _rows(path):
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _conv(rows):
    keys = ("depth_top_km", "depth_bot_km", "depth_mid_km", "density_gcc",
            "shell_mass_kg", "ppm_mass", "shell_element_mass_kg",
            "ppm_crust_avg", "ppm_mantle_bse", "enrichment_factor",
            "mass_crust_kg", "mass_mantle_kg", "mass_core_kg",
            "share_crust_pct", "share_mantle_pct", "share_core_pct",
            "C_core_pure_metal_pct", "lit_pct", "C_CI_ppm", "C_BSE_ppm",
            "C_earth_ppm", "C_core_pure_metal_ppm", "C_core_plus_lo_ppm",
            "C_core_plus_hi_ppm", "sigma_rel")
    out = []
    for r in rows:
        rr = dict(r)
        for k in keys:
            if k in rr and rr[k] not in ("",):
                try:
                    rr[k] = float(rr[k])
                except ValueError:
                    rr[k] = None
        out.append(rr)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(REPO / "outputs"))
    args = ap.parse_args()
    od = Path(args.outdir)

    radial = _conv(_rows(od / "radial_elements.csv"))
    fate = _conv(_rows(od / "element_fate_crust_mantle_core.csv"))
    enrich = _conv(_rows(od / "enrichment_crust_vs_mantle.csv"))

    fig_radial_abundance(od / "fig_radial_abundance.png", radial)
    fig_reservoir_share(od / "fig_element_fate.png", fate)
    fig_enrichment(od / "fig_enrichment_crust_vs_mantle.png", enrich)

    # 地核反演图(需要 meta 中的合成表 Fe)
    import json
    inv = _conv(_rows(od / "core_inversion_metals.csv"))
    merged = None
    mf = od / "core_inversion_meta.json"
    if mf.exists():
        merged = json.load(open(mf, encoding="utf-8")).get("core_ppm_merged")
    fig_core_inversion(od / "fig_core_inversion.png", inv, merged)
    print("图已写入", od)


if __name__ == "__main__":
    main()
