"""快速体验：打印模型核心结论（无需写 outputs）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from earth3d.enrichment import element_fate  # noqa: E402
from earth3d.layering import build_regions  # noqa: E402
from earth3d.reservoirs import get_reservoirs  # noqa: E402

rs = get_reservoirs()
meta, _ = build_regions()
print("质量守恒校验:", {k: round(float(v), 4) for k, v in meta["mass_kg"].items()})
print("地壳等效厚度 km:", round(meta["crust_thickness_km"], 2))

print("\n关键金属储量命运（谁霸占了谁）:")
for r in element_fate(rs):
    if r["element"] in {"Au", "Cu", "Ni", "Li", "Fe"}:
        print(f"  {r['element']:<3} 地壳 {r['share_crust_pct']:>6}%  "
              f"地幔 {r['share_mantle_pct']:>6}%  地核 {r['share_core_pct']:>6}%")
