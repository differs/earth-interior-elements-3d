#!/usr/bin/env python3
"""把 McDonough & Sun (1995) 的 CI + Pyrolite 原始表(data/raw/*_raw.csv)
解析为统一质量 ppm 的干净表 data/raw/ci_pyrolite_mcd95_ppm.csv。

原始表单位规则(原文献)：
  - 主量元素以 wt% 标注 (如 "Mg (%)")，少数标注 ppm/ppb；
  - 自 Nb 行起(含)未标注行实为 ppb；
  - 其余未标注行默认为 ppm。
氧未在表中列出，这里按"100% 减其余元素"反算(质量守恒)，两列各自归一。

输出列: element, ppm_CI, ppm_BSE_pyrolite, unit_in_source
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "data" / "raw"
SRC = RAW / "McDonough_Sun__1995__CI_Pyrolite_raw.csv"
DST = RAW / "ci_pyrolite_mcd95_ppm.csv"

SYM = re.compile(r"^([A-Z][a-z]?)\b")
UNIT = re.compile(r"(\((%|ppm|ppb)\))")

# 原表中自 Nb 起整段为 ppb(与 M&S 1995 原文一致)，此处按符号锁定以防误读
PPB_SYMBOLS = {
    "Nb", "Mo", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb", "Te", "I",
    "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho",
    "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au",
    "Hg", "Tl", "Pb", "Bi", "Th", "U",
}
UNIT_MUL = {"%": 1e4, "ppm": 1.0, "ppb": 1e-3}


def main() -> int:
    rows = []
    seen = set()
    with SRC.open(encoding="utf-8") as fh:
        rd = csv.reader(fh)
        next(rd)
        for label, ci, py in rd:
            m = SYM.match(label.strip())
            if not m:
                print(f"!! 无法解析元素符号: {label!r}", file=sys.stderr)
                continue
            el = m.group(1)
            if el in seen:
                raise SystemExit(f"重复元素 {el}")
            seen.add(el)
            u = UNIT.search(label)
            unit = "ppm"
            if u:
                unit = "ppb" if u.group(2) == "ppb" else "ppm"
                if u.group(2) == "%":
                    unit = "%"
            elif el in PPB_SYMBOLS:
                unit = "ppb"
            mul = UNIT_MUL[unit]
            rows.append((el, float(ci) * mul, float(py) * mul, unit))

    # 反算氧(质量守恒到 100%)
    sum_ci = sum(r[1] for r in rows)
    sum_py = sum(r[2] for r in rows)
    rows.append(("O", 1e6 - sum_ci, 1e6 - sum_py, "diff-by-100%"))

    with DST.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["element", "ppm_CI", "ppm_BSE_pyrolite", "unit_in_source"])
        for el, ci, py, unit in rows:
            w.writerow([el, f"{ci:.6g}", f"{py:.6g}", unit])

    # 校验
    s_ci = sum(r[1] for r in rows)
    s_py = sum(r[2] for r in rows)
    print(f"元素数(含O): {len(rows)}")
    print(f"CI    之和 = {s_ci:.0f} ppm (目标 1e6)")
    print(f"Pyrolite 之和 = {s_py:.0f} ppm (目标 1e6)")
    print(f"CI O = {[r[1] for r in rows if r[0]=='O'][0]:.0f} ppm"
          f" ({[r[1] for r in rows if r[0]=='O'][0]/1e4:.1f} wt%)")
    print(f"写至 {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
