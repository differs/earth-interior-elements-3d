"""圈层成分库。

成分来源(全部带出处)：
- 大陆地壳  : CRC Handbook 97th (2016) via Wikipedia(见 data/raw/crust_crc97.csv)
- 洋壳MORB  : Gale et al. (2013) 主量
- CI 与 BSE : McDonough & Sun (1995) 全元素表(见 data/raw/ci_pyrolite_mcd95_ppm.csv，
              由 scripts/parse_mcd95.py 从原始表解析，含单位换算与氧差反算)
- 地幔      : 由 BSE(pyrolite) 扣除地壳成分的质量平衡解出
              C_mantle = (M_sil·C_BSE − M_crust·C_crust)/M_mantle
              避免"壳+幔各自全用原岩丰度"造成的重复计算。
- 地核      : 默认=文献直给假设档；build 时由 inversion.py 用核幔质量平衡
              "方程解出"的强亲铁金属 + 地震学约束的轻元素预算合成并覆盖。
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# ---- 地球质量与圈层质量(kg) ----
M_EARTH = 5.9722e24
M_CORE = 1.9387e24          # 约 32.46% M_Earth
M_SILICATE = M_EARTH - M_CORE  # 4.0335e24 (BSE: 地幔+地壳)
M_CONT_CRUST = 2.6e22
M_OCEAN_CRUST = 0.6e22
M_CRUST = M_CONT_CRUST + M_OCEAN_CRUST
M_MANTLE = M_SILICATE - M_CRUST  # 4.0015e24

F_SIL = M_SILICATE / M_EARTH   # 0.6754
F_CORE = M_CORE / M_EARTH      # 0.3246

# ---- 半径(km)，近似 PREM ----
R_EARTH_KM = 6371.0
R_CMB_KM = 3480.0
R_ICB_KM = 1221.5

_SYM = re.compile(r"^([A-Z][a-z]?)")


def _load_mcd95() -> dict[str, dict[str, float]]:
    """解析 data/raw/ci_pyrolite_mcd95_ppm.csv -> {"CI": {el:ppm}, "BSE": {...}}"""
    p = ROOT / "data" / "raw" / "ci_pyrolite_mcd95_ppm.csv"
    out = {"CI": {}, "BSE": {}}
    with p.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            el = row["element"]
            out["CI"][el] = float(row["ppm_CI"])
            out["BSE"][el] = float(row["ppm_BSE_pyrolite"])
    return out


def _oxides_to_elements(oxides_wt: dict, label: str) -> dict:
    """氧化物 wt% -> 元素 ppm(氧=100% 减其余)。"""
    from .elements import ATOMIC_MASS_G_PER_MOL as M

    ratio = {"SiO2": 1, "TiO2": 1, "Al2O3": 2, "Cr2O3": 2, "FeO": 1, "MnO": 1,
             "MgO": 1, "CaO": 1, "Na2O": 2, "K2O": 2, "P2O5": 2, "NiO": 1}
    form_wt = {"SiO2": 60.08, "TiO2": 79.87, "Al2O3": 101.96, "Cr2O3": 152.00,
               "FeO": 71.85, "MnO": 70.94, "MgO": 40.30, "CaO": 56.08,
               "Na2O": 61.98, "K2O": 94.20, "P2O5": 141.94, "NiO": 74.69}
    el_map = {"SiO2": "Si", "TiO2": "Ti", "Al2O3": "Al", "Cr2O3": "Cr",
              "FeO": "Fe", "MnO": "Mn", "MgO": "Mg", "CaO": "Ca",
              "Na2O": "Na", "K2O": "K", "P2O5": "P", "NiO": "Ni"}
    out, accounted = {}, 0.0
    for ox, wt in oxides_wt.items():
        el = el_map[ox]
        v = wt * (ratio[ox] * M[el] / form_wt[ox]) * 1e4
        out[el] = v
        accounted += v
    if accounted > 1e6:
        raise ValueError(f"{label}: 主量元素之和超 100%")
    out["O"] = 1e6 - accounted
    return out


# ---------------- 大陆地壳(CRC97) ----------------
def _crust_csv_ppm() -> dict:
    p = ROOT / "data" / "raw" / "crust_crc97.csv"
    ppm = {}
    with p.open(encoding="utf-8") as fh:
        lines = [ln for ln in fh if not ln.lstrip().startswith("#")]
    for row in csv.DictReader(lines):
        ppm[row["element"]] = float(row["ppm"])
    return ppm


def _oceanic_ppm() -> dict:
    ox = {"SiO2": 50.5, "TiO2": 1.40, "Al2O3": 14.8, "FeO": 11.3, "MnO": 0.19,
          "MgO": 7.60, "CaO": 11.6, "Na2O": 2.70, "K2O": 0.13, "P2O5": 0.14}
    return _oxides_to_elements(ox, "oceanic_crust")


def global_crust_ppm() -> dict:
    """大陆+洋壳按质量加权的全球地壳成分(ppm, 元素并集)。"""
    cc, oc = _crust_csv_ppm(), _oceanic_ppm()
    els = sorted(set(cc) | set(oc))
    return {el: (cc.get(el, 0.0) * M_CONT_CRUST + oc.get(el, 0.0) * M_OCEAN_CRUST)
            / M_CRUST for el in els}


def _bse_ppm() -> dict:
    return _load_mcd95()["BSE"]


def _mantle_ppm() -> dict:
    """地幔 = (BSE·M_sil − 全球地壳·M_crust)/M_mantle；负值归零并补回氧。"""
    bse, crust = _bse_ppm(), global_crust_ppm()
    out = {}
    for el in sorted(set(bse) | set(crust)):
        v = (bse.get(el, 0.0) * M_SILICATE - crust.get(el, 0.0) * M_CRUST) / M_MANTLE
        out[el] = max(v, 0.0)
    non_o = sum(v for k, v in out.items() if k != "O")
    out["O"] = max(1e6 - non_o, 0.0)
    return out


# ---------------- 各储库装配 ----------------
def continental_crust() -> dict:
    return {"key": "continental_crust", "name": "大陆地壳",
            "mass_kg": M_CONT_CRUST, "ppm": _crust_csv_ppm(),
            "ref": "CRC Handbook 97th (2016), via Wikipedia rev 1368008262",
            "confidence": "high"}


def oceanic_crust() -> dict:
    return {"key": "oceanic_crust", "name": "洋壳(MORB)", "mass_kg": M_OCEAN_CRUST,
            "ppm": _oceanic_ppm(),
            "ref": "Gale et al. (2013), MORB 玻璃主量平均",
            "confidence": "high(major)"}


def mantle() -> dict:
    return {"key": "mantle", "name": "地幔(BSE 扣除地壳)", "mass_kg": M_MANTLE,
            "ppm": _mantle_ppm(),
            "ref": "McDonough & Sun (1995) pyrolite/BSE − 全球地壳质量平衡",
            "confidence": "high(major)/medium(trace)",
            "derived": "C=(BSE·M_sil−crust·M_crust)/M_mantle"}


def _core_lit_ppm() -> dict:
    """文献直给假设档(供对照，build 时被 inversion 合成表覆盖)。"""
    return {"Fe": 855000.0, "Ni": 52000.0, "Si": 60000.0, "S": 19000.0,
            "O": 9000.0, "C": 2000.0, "H": 1000.0}


def core(ppm: dict | None = None) -> dict:
    p = dict(_core_lit_ppm()) if ppm is None else dict(ppm)
    return {"key": "core", "name": "地核", "mass_kg": M_CORE, "ppm": p,
            "ref": "见 src/earth3d/inversion.py 与 docs/derivation.md",
            "confidence": "见 inversion 校验表"}


def get_reservoirs(core_ppm: dict | None = None) -> dict:
    if core_ppm is None:
        try:
            from .inversion import solve_core
            core_ppm = solve_core()["core_ppm"]
        except Exception:  # 数据缺失时退回文献直给档
            core_ppm = None
    return {"continental_crust": continental_crust(),
            "oceanic_crust": oceanic_crust(),
            "mantle": mantle(),
            "core": core(core_ppm)}


def get_reference_tables() -> dict[str, dict]:
    """CI 与 BSE(pyrolite) 参考表，供 inversion 使用。"""
    t = _load_mcd95()
    return {"CI": t["CI"], "BSE": t["BSE"]}
