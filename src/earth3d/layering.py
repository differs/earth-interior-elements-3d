"""1D 径向几何：把地球剖成同心球壳带(近似 PREM)，质量自洽。

设计：三大"质量区"——地壳 / 地幔 / 地核——的质量锁定为文献目标值
(reservoirs.M_CRUST / M_MANTLE / M_CORE)。各区在给定深度分带的基础密度形状上
做单个全局缩放，使该区体积积分质量精确等于目标值；因此最终总质量 = M_EARTH。
相对密度形状取自近似 PREM，缩放系数一般在 1±10%，会在校验输出里打印。
"""

from __future__ import annotations

import numpy as np

from .reservoirs import (
    M_CORE, M_CRUST, M_MANTLE, R_CMB_KM, R_EARTH_KM, R_ICB_KM,
)


def _depth_to_r_top(depth_top_km: float) -> float:
    """该深度上覆地球半径下限(km)。"""
    return R_EARTH_KM - depth_top_km


def _shell_volume_km3(r_in_km: float, r_out_km: float) -> float:
    return 4.0 / 3.0 * np.pi * (r_out_km**3 - r_in_km**3)


def _crust_thickness_km() -> float:
    """地壳等效厚度：使壳层在 2.9 g/cc 下质量恰为 M_CRUST 的球壳厚度。"""
    rho = 2900.0  # kg/m3
    area = 4.0 * np.pi * (R_EARTH_KM * 1e3) ** 2
    return M_CRUST / (area * rho) / 1e3  # -> km


def _base_density_bins(depth_edges_km) -> np.ndarray:
    """近似 PREM 的分段基准密度(g/cc)。edges: 递增深度数组，返回每段密度。"""
    n = len(depth_edges_km) - 1
    rho = np.empty(n)

    def set_range(lo, hi, val):
        for i in range(n):
            if lo <= depth_edges_km[i] < hi:
                rho[i] = val

    # 地壳段(整体 2.9，majors 阶段近似)
    set_range(0.0, 30.0, 2.90)
    # 上地幔
    set_range(30.0, 120.0, 3.38)
    set_range(120.0, 410.0, 3.50)
    # 过渡带(410-660)
    set_range(410.0, 520.0, 3.85)
    set_range(520.0, 660.0, 4.10)
    # 下地幔
    set_range(660.0, 1200.0, 4.60)
    set_range(1200.0, 1800.0, 4.90)
    set_range(1800.0, 2400.0, 5.15)
    set_range(2400.0, 2891.0, 5.40)
    # 外核
    set_range(2891.0, 3800.0, 10.4)
    set_range(3800.0, 4600.0, 11.2)
    set_range(4600.0, 5150.0, 12.0)
    # 内核
    set_range(5150.0, 6371.0, 12.9)
    return rho


def _depth_edges(kind: str, crust_bottom: float):
    """每个质量区内的深度分带(m)。返回 [r_out..., r_in] km 下边界数组。

    kind in {"crust","mantle","outer_core","inner_core"}
    """
    if kind == "crust":
        n = max(4, int(crust_bottom) + 1)
        edges = np.linspace(0.0, crust_bottom, n + 1)
    elif kind == "mantle":
        edges = np.concatenate([
            np.arange(crust_bottom, 660.0 + 1e-9, 2.0),
            np.arange(660.0, 2891.0 + 1e-9, 20.0),
        ])
    elif kind == "outer_core":
        edges = np.arange(2891.0, 5150.0 + 1e-9, 20.0)
    elif kind == "inner_core":
        edges = np.arange(5150.0, R_EARTH_KM + 1e-9, 20.0)
    else:
        raise KeyError(kind)
    edges = np.round(edges, 6)
    return np.unique(edges)


class RegionBins:
    """一个质量区的径向 bin 列表(每行一个壳)。"""

    def __init__(self, kind, depth_edges_km, density_gcc, mass_kg, comp_key):
        self.kind = kind
        self.depth_top = depth_edges_km[:-1]
        self.depth_bot = depth_edges_km[1:]
        self.density_gcc = density_gcc
        self.mass_kg = mass_kg
        self.comp_key = comp_key


def build_regions() -> tuple[dict, list[RegionBins]]:
    """返回 (meta, bins)。meta 记录各区质量/密度校验。"""
    h_c = _crust_thickness_km()

    def _region(kind, comp_key, target_mass, lo_d, hi_d):
        edges = _depth_edges(kind, h_c)
        # 选取 lo_d..hi_d 之间的内部边界，再补两端
        interior = edges[(edges > lo_d + 1e-6) & (edges < hi_d - 1e-6)]
        edges = np.concatenate([[lo_d], interior, [hi_d]])
        base = _base_density_bins(edges) * 1e3  # kg/m3
        vol = np.array([_shell_volume_km3(R_EARTH_KM - b, R_EARTH_KM - a)
                        for a, b in zip(edges[:-1], edges[1:])]) * 1e9  # m3
        base_mass = base * vol
        scale = target_mass / base_mass.sum()
        density = base * scale
        mass = density * vol
        rb = RegionBins(kind, edges, density / 1e3, mass, comp_key)
        return rb, scale

    crust, s_c = _region("crust", "crust", M_CRUST, 0.0, h_c)
    mantle, s_m = _region("mantle", "mantle", M_MANTLE, h_c, 2891.0)
    # 按 base 密度与体积比例把 M_CORE 分摊给内外核
    e_o = _depth_edges("outer_core", h_c)
    e_i = _depth_edges("inner_core", h_c)
    v_o = sum(_shell_volume_km3(R_EARTH_KM - b, R_EARTH_KM - a)
              for a, b in zip(e_o[:-1], e_o[1:])) * 1e9
    v_i = sum(_shell_volume_km3(R_EARTH_KM - b, R_EARTH_KM - a)
              for a, b in zip(e_i[:-1], e_i[1:])) * 1e9
    rho_o = np.average(_base_density_bins(e_o)) * 1e3
    rho_i = np.average(_base_density_bins(e_i)) * 1e3
    m_oc_target = M_CORE * (v_o * rho_o) / (v_o * rho_o + v_i * rho_i)
    m_ic_target = M_CORE - m_oc_target
    oc, s_oc = _region("outer_core", "outer_core", m_oc_target, 2891.0, 5150.0)
    ic, s_ic = _region("inner_core", "inner_core", m_ic_target, 5150.0, R_EARTH_KM)

    bins = [crust, mantle, oc, ic]
    total = sum(rb.mass_kg.sum() for rb in bins)
    meta = {
        "crust_thickness_km": h_c,
        "scales": {"crust": s_c, "mantle": s_m, "outer_core": s_oc, "inner_core": s_ic},
        "mass_kg": {"crust": crust.mass_kg.sum(), "mantle": mantle.mass_kg.sum(),
                    "core": oc.mass_kg.sum() + ic.mass_kg.sum()},
        "total_mass_kg": total,
    }
    return meta, bins


def concat_bins(bins: list[RegionBins]) -> dict:
    """把各区 bins 拼成一个按深度(地心到地表 逆序→地表到地心)排序的连续剖面。"""
    tops = np.concatenate([b.depth_top for b in bins])
    bots = np.concatenate([b.depth_bot for b in bins])
    dens = np.concatenate([b.density_gcc for b in bins])
    mass = np.concatenate([b.mass_kg for b in bins])
    comp = []
    for b in bins:
        comp.extend([b.comp_key] * len(b.depth_top))
    order = np.argsort(tops)  # 深度从小到大 = 地表->地心
    return {
        "depth_top": tops[order], "depth_bot": bots[order],
        "depth_mid": 0.5 * (tops[order] + bots[order]),
        "density_gcc": dens[order], "mass_kg": mass[order],
        "reservoir": [comp[i] for i in order],
    }
