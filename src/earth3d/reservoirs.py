"""圈层成分库。

每个"储库(reservoir)"给出质量加权平均的化学组成(质量 ppm)与来源注释。
v0.1 录入策略：能拿到真实表的地方用真实表(地壳=CRC97)，其余主量用氧化物质谱
转换，微量只收录稳定到 ~2 位有效数字的教科书级参考值，并在 note 里标注置信级别。
- 未收录元素在该储库中按"缺失"处理(模型不为其凭空赋值)。
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# 地球质量与圈层质量的文献目标值(kg)。推导过程见 docs/derivation.md
M_EARTH = 5.9722e24
M_CORE = 1.9387e24          # 约 32.46% M_Earth (大地测量+地震学约束)
M_SILICATE = M_EARTH - M_CORE  # 4.0335e24
M_CONT_CRUST = 2.6e22
M_OCEAN_CRUST = 0.6e22
M_CRUST = M_CONT_CRUST + M_OCEAN_CRUST
M_MANTLE = M_SILICATE - M_CRUST  # 4.0015e24

# 半径(km)。CMB=核幔边界, ICB=内外核边界(近似 PREM)
R_EARTH_KM = 6371.0
R_CMB_KM = 3480.0
R_ICB_KM = 1221.5


def _load_crust_csv() -> dict:
    """读取 CRC97 大陆地壳丰度表(data/raw/crust_crc97.csv)。"""
    path = ROOT / "data" / "raw" / "crust_crc97.csv"
    ppm, gold = {}, {}
    with path.open(encoding="utf-8") as fh:
        lines = [ln for ln in fh if not ln.lstrip().startswith("#")]
    for row in csv.DictReader(lines):
        el = row["element"].strip()
        ppm[el] = float(row["ppm"])
        gold[el] = row["goldschmidt_class"].strip()
    return {"ppm": ppm, "gold": gold}


def _oxides_to_elements(oxides_wt: dict, label: str) -> dict:
    """把氧化物 wt% 换算为元素质量 ppm(wt%*1e4 后扣除氧)。

    注意：氧由"100% - 其余元素"反算，保证每储库质量守恒到 100%。
    """
    from .elements import ATOMIC_MASS_G_PER_MOL as M

    ratio = {
        # 每个氧化物分子中目标元素的总质量占比
        "SiO2": 1, "TiO2": 1, "Al2O3": 2, "Cr2O3": 2, "FeO": 1, "MnO": 1,
        "MgO": 1, "CaO": 1, "Na2O": 2, "K2O": 2, "P2O5": 2, "NiO": 1,
    }
    form_wt = {  # 分子量
        "SiO2": 60.08, "TiO2": 79.87, "Al2O3": 101.96, "Cr2O3": 152.00,
        "FeO": 71.85, "MnO": 70.94, "MgO": 40.30, "CaO": 56.08,
        "Na2O": 61.98, "K2O": 94.20, "P2O5": 141.94, "NiO": 74.69,
    }
    el_map = {
        "SiO2": "Si", "TiO2": "Ti", "Al2O3": "Al", "Cr2O3": "Cr", "FeO": "Fe",
        "MnO": "Mn", "MgO": "Mg", "CaO": "Ca", "Na2O": "Na", "K2O": "K",
        "P2O5": "P", "NiO": "Ni",
    }
    out, accounted = {}, 0.0
    for ox, wt in oxides_wt.items():
        if ox not in form_wt:
            raise KeyError(f"{label}: 未知氧化物 {ox}")
        mass_frac = ratio[ox] * M[el_map[ox]] / form_wt[ox]
        el = el_map[ox]
        out[el] = wt * mass_frac * 1e4  # wt% -> ppm
        accounted += out[el]
    if accounted > 1e6:
        raise ValueError(f"{label}: 主量元素之和超 100%，数据有误 {accounted / 1e4:.1f}%")
    out["O"] = 1e6 - accounted  # 氧 = 100% - 其余
    return out


# ---------------- 大陆地壳(CRC97) ----------------
def continental_crust() -> dict:
    d = _load_crust_csv()
    return {
        "key": "continental_crust",
        "name": "大陆地壳",
        "mass_kg": M_CONT_CRUST,
        "ppm": d["ppm"],
        "gold": d["gold"],
        "ref": "CRC Handbook 97th (2016), via Wikipedia rev 1368008262",
        "confidence": "high",
    }


# ---------------- 洋壳(MORB 玻璃平均值) ----------------
def oceanic_crust() -> dict:
    # Gale, Dalton, Langmuir, Su, Schilling (2013) MORB 玻璃主量平均(wt% 归一)
    ox = {
        "SiO2": 50.5, "TiO2": 1.40, "Al2O3": 14.8, "FeO": 11.3, "MnO": 0.19,
        "MgO": 7.60, "CaO": 11.6, "Na2O": 2.70, "K2O": 0.13, "P2O5": 0.14,
    }
    return {
        "key": "oceanic_crust",
        "name": "洋壳(MORB)",
        "mass_kg": M_OCEAN_CRUST,
        "ppm": _oxides_to_elements(ox, "oceanic_crust"),
        "gold": {},
        "ref": "Gale et al. (2013), Geochem. Geophys. Geosyst., MORB 玻璃平均",
        "confidence": "high(major)",
    }


# ---------------- 地幔(pyrolite / BSE) ----------------
def mantle() -> dict:
    """原始地幔 pyrolite 模型(McDonough & Sun 1995)。主量为氧化物换算；
    微量仅收录稳定参考值，注"≈"并见 docs/roadmap.md 复核计划。"""
    ox = {
        "SiO2": 45.0, "TiO2": 0.201, "Al2O3": 4.45, "Cr2O3": 0.39, "FeO": 8.10,
        "MnO": 0.135, "MgO": 37.8, "CaO": 3.55, "Na2O": 0.36, "K2O": 0.029,
        "P2O5": 0.022, "NiO": 0.25,
    }
    ppm = _oxides_to_elements(ox, "mantle")
    # 教科书级 BSE 微量(ppm，质量)，源: McDonough & Sun (1995) 及综述常用值
    ppm.update({
        # 碱土/碱
        "Li": 1.6, "Rb": 0.60, "Sr": 21.0, "Ba": 6.8, "Cs": 0.021,
        # 高场强
        "Zr": 10.5, "Hf": 0.28, "Nb": 0.70, "Ta": 0.037, "Y": 4.3,
        # REE(约，Lu-La 平坦模式)
        "La": 0.60, "Ce": 1.60, "Pr": 0.23, "Nd": 1.25, "Sm": 0.40,
        "Eu": 0.15, "Gd": 0.54, "Tb": 0.10, "Dy": 0.67, "Ho": 0.15,
        "Er": 0.44, "Tm": 0.068, "Yb": 0.44, "Lu": 0.067,
        # 不相容发热元素
        "U": 0.0203, "Th": 0.0795, "Pb": 0.15,
        # 过渡/亲硫
        "V": 82.0, "Sc": 16.0, "Cu": 30.0, "Zn": 55.0, "Co": 105.0,
        "Ga": 4.0, "Ge": 1.3, "Mo": 0.05, "B": 0.30,
        # HSE/贵金属(来自 ppb，÷1000 -> ppm)
        "Os": 0.0034, "Ir": 0.0032, "Ru": 0.0050, "Pt": 0.0076,
        "Pd": 0.0039, "Re": 0.00028, "Au": 0.0010,
        # 挥发分(干地幔假设的边界注释: H2O/CO2 以矿物相计入 O/Si 体系，未单独建模)
        "S": 250.0,
    })
    return {
        "key": "mantle",
        "name": "地幔(pyrolite/BSE)",
        "mass_kg": M_MANTLE,
        "ppm": ppm,
        "gold": {},
        "ref": "McDonough & Sun (1995) pyrolite；微量≈教科书参考值待机器复核",
        "confidence": "high(major)/medium(trace)",
    }


# ---------------- 地核(Fe-Ni-轻元素) ----------------
def core() -> dict:
    """外核为主的"大核"平均成分假设表。轻元素候选(Si/S/O/C/H)配比不确定性
    很大，这里是 docs/hypotheses.md 假设 A-3 的参数化档位，而非定论。"""
    ppm = {
        "Fe": 855000.0, "Ni": 52000.0, "Si": 60000.0, "S": 19000.0,
        "O": 9000.0, "C": 2000.0, "H": 1000.0,
    }
    return {
        "key": "core",
        "name": "地核(Fe-Ni-轻元素假设)",
        "mass_kg": M_CORE,
        "ppm": ppm,
        "gold": {},
        "ref": "McDonough (2003) 汇编；轻元素配比=本文假设档(见 hypotheses.md)",
        "confidence": "medium(Fe,Ni)/low(light elements)",
    }


RESERVOIR_BUILDERS = {
    "continental_crust": continental_crust,
    "oceanic_crust": oceanic_crust,
    "mantle": mantle,
    "core": core,
}


def get_reservoirs() -> dict:
    return {k: b() for k, b in RESERVOIR_BUILDERS.items()}


# 各储库在 1D 径向几何上的归属(comp key)，供 radial 模型取用
REGION_TO_RESERVOIR = {
    "crust": "global_crust",       # 大陆+洋壳的质量加权平均，运行时计算
    "upper_mantle": "mantle",
    "transition": "mantle",
    "lower_mantle": "mantle",
    "outer_core": "core",
    "inner_core": "core",
}
