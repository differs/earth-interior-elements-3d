"""可视化：径向丰度剖面、圈层储量份额、地壳/地幔富集因子图。"""

from __future__ import annotations

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

for _f in ("Noto Sans CJK SC", "Noto Sans CJK JP", "Noto Sans CJK HK",
           "Noto Serif CJK SC", "Noto Serif CJK JP", "WenQuanYi Micro Hei",
           "Source Han Sans SC", "PingFang SC", "Microsoft YaHei"):
    if any(_f in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [_f]
        break
plt.rcParams["axes.unicode_minus"] = False

from .elements import ATOMIC_MASS_G_PER_MOL as AM  # noqa: E402


_MAJORS = ["O", "Si", "Mg", "Fe", "Al", "Ca", "Na", "K", "Ti"]
_ECON = ["Cu", "Ni", "Co", "Au", "Ag", "Pt", "Pd", "Li", "U", "Th",
         "Zn", "Pb", "Sn", "W", "Mo", "REE", "Cr", "Mn"]


def fig_radial_abundance(out_path, radial_long_rows, elements=None):
    """各元素质量浓度(ppm，对数)随深度的剖面。"""
    elements = elements or _MAJORS + ["Ni", "Co", "Cu", "Au"]
    data = {}
    for r in radial_long_rows:
        if r["element"] in elements:
            data.setdefault(r["element"], {})[r["depth_mid_km"]] = r["ppm_mass"]
    fig, ax = plt.subplots(figsize=(7, 8))
    cmap = plt.get_cmap("tab20")
    for i, el in enumerate(elements):
        xs = sorted(data.get(el, {}))
        if not xs:
            continue
        ys = [data[el][x] for x in xs]
        ax.semilogx(ys, xs, marker=".", ms=2.5, lw=1.4,
                    color=cmap(i % 20), label=el)
    ax.invert_yaxis()
    ax.set_xlabel("质量浓度 ppm (log)")
    ax.set_ylabel("深度 km")
    ax.set_ylim(6500, -50)
    ax.grid(True, which="both", ls=":", alpha=0.4)
    # 圈层分界
    for dep, name in [(22, "地壳底"), (410, "410km"), (660, "660km"),
                      (2891, "核幔边界"), (5150, "内外核边界")]:
        ax.axhline(dep, color="0.6", lw=0.6, ls="--")
        ax.text(1.01, dep, name, transform=ax.get_yaxis_transform(),
                fontsize=6, va="center", color="0.35")
    ax.legend(ncol=3, fontsize=7, loc="lower right", framealpha=0.6)
    ax.set_title("元素质量浓度随深度(1D 平均地球模型, v0.1)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def fig_reservoir_share(out_path, fate_rows, elements=None):
    """关键金属在 地壳/地幔/地核 三大储库的质量份额(对数值域混合用堆叠条)。"""
    elements = elements or ["Au", "Pt", "Pd", "Cu", "Ni", "Co", "Li", "Zn",
                            "Pb", "U", "Th", "Mo", "W", "Cr", "Mn", "Fe"]
    pick = {r["element"]: r for r in fate_rows if r["element"] in elements}
    order = sorted(elements, key=lambda e: AM.get(e, 1e9))
    rows = [pick[e] for e in order if e in pick]
    names = [r["element"] for r in rows]
    shares = np.array([[r["share_crust_pct"], r["share_mantle_pct"],
                        r["share_core_pct"]] for r in rows])
    fig, ax = plt.subplots(figsize=(max(7, len(names) * 0.45), 6))
    bottom = np.zeros(len(rows))
    labels = ["地壳", "地幔", "地核"]
    colors = ["#4C9F70", "#8C5A2B", "#C0392B"]
    for j, (lab, col) in enumerate(zip(labels, colors)):
        ax.bar(names, shares[:, j], bottom=bottom, label=lab,
               color=col, edgecolor="white", lw=0.4)
        bottom += shares[:, j]
    ax.set_ylabel("占该元素已建模储量的份额 %")
    ax.set_title("关键元素在 地壳/地幔/地核 的立体质量份额(v0.1)")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=60, ha="right", fontsize=8)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def fig_enrichment(out_path, enrichment_rows):
    """地壳/地幔富集因子 vs 原子序数(按金施密特类着色)。"""
    rows = [r for r in enrichment_rows if r["enrichment_factor"] is not None]
    ef = np.array([r["enrichment_factor"] for r in rows])
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.semilogy(ef, "o", ms=4, alpha=0.75)
    ax.axhline(5.0, color="green", ls="--", lw=0.8)
    ax.axhline(1.0, color="gray", ls=":", lw=0.8)
    ax.axhline(0.2, color="red", ls="--", lw=0.8)
    ax.text(len(ef) - 1, 6, "地壳富集 EF=5", color="green", fontsize=7, ha="right")
    ax.text(len(ef) - 1, 0.1, "地幔相容 EF=0.2", color="red", fontsize=7, ha="right")
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels([r["element"] for r in rows], rotation=90, fontsize=6)
    ax.set_ylabel("富集因子 地壳/地幔(BSE)  (log)")
    ax.set_title("地壳 vs 地幔 富集因子：立体分异的第一个可查询量(v0.1)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def fig_core_inversion(out_path, inv_rows, core_merged_ppm=None):
    """地核成分：反演合成表 vs 文献对照。

    - Fe 取合成表值(已扣除轻元素预算)；Ni/Co/Cr/W/Mo 取反演金属端；
    - 其余金属(ppm 量级)在纵轴 wt% 下不可见，故仅在图注说明。
    """
    rows = {r["element"]: r for r in inv_rows}
    lit_map = {"Fe": 85.5, "Ni": 5.2, "Co": 0.25, "Cr": 0.9, "Si": 6.0, "S": 1.9}
    model = {}
    lit = {}
    for e, lv in lit_map.items():
        if e == "Fe":
            if core_merged_ppm:
                model[e] = core_merged_ppm.get("Fe", 0.0) / 1e4
        else:
            r = rows.get(e)
            if r is None:
                continue
            model[e] = r["C_core_pure_metal_pct"]
        lit[e] = lv
    names = [e for e in ["Fe", "Ni", "Co", "Cr"] + ["Si", "S"] if e in model]
    x = np.arange(len(names))
    w = 0.36
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.bar(x - w / 2, [model[e] for e in names], w, label="本模型反演合成表",
           color="#C0392B", alpha=0.9)
    ax.bar(x + w / 2, [lit[e] for e in names], w, label="文献 (McDonough 2003)",
           color="#8C5A2B", alpha=0.65)
    for xi, e in zip(x, names):
        ax.text(xi - w / 2, model[e], f"{model[e]:.2f}",
                ha="center", va="bottom", fontsize=7)
        ax.text(xi + w / 2, lit[e], f"{lit[e]:.1f}",
                ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel("地核成分 wt%")
    ax.set_title("核幔质量平衡反演的地核成分 vs 文献 (PGE 等为 ppm 级见图表文件)")
    ax.legend(fontsize=8)
    ax.set_ylim(0, max(max(model.values()), max(lit.values())) * 1.18)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
