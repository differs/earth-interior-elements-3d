"""核幔质量平衡反演：从 CI + BSE 全表"方程解出"地核成分。

推导(见 docs/derivation.md 第 6 节与 hypotheses.md H-7)：

对"难挥发 + 无显著挥发亏损"的元素，设全地/CI 富集系数为常数
    X_ref = mean_i [ (M_sil/M_Earth)·(C_BSE,i / C_CI,i) ]
其中样本 i 取难挥发亲石元素(Al,Ca,Ti,Sc,Y,Zr,Hf,Nb,Ta,Th,U 与全部 REE)——
它们的存量应几乎全在硅酸盐地球(BSE)，因此 X_ref 可由观测直接锁定。

然后对强亲铁/难挥发金属 e(Fe,Ni,Co,Cr,W,Mo,Re,Os,Ru,Rh,Ir,Pt,Pd)反解：
    全地浓度  C_E,e = X_ref·C_CI,e            (假设: 无挥发亏损, 从 CI 等比继承)
    质量守恒  C_E,e = F_sil·C_BSE,e + F_core·C_core,e
    ⇒  C_core,e = (C_E,e − F_sil·C_BSE,e) / F_core

不确定性: 从 X_ref 样本的弥散(std)按比例传播到每个 C_core,e。

注意：地核真实含约 5-10% 轻元素(Si/S/O/C/H，来自地震学密度亏损)，本反演给出的是
"纯金属端"解；最终合成表把地震学轻元素预算(L)放回、令 Fe=100%−其余，作为物理一致表。
"""

from __future__ import annotations

from statistics import mean, stdev

from .reservoirs import F_CORE, F_SIL, get_reference_tables

# 难挥发亲石样本(用于锁定 X_ref)：存量全在硅酸盐
REFRACTORY_LITHOPHILE = [
    "Al", "Ca", "Ti", "Sc", "Y", "Zr", "Hf", "Nb", "Ta", "Th", "U",
    "La", "Ce", "Pr", "Nd", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er",
    "Tm", "Yb", "Lu",
]

# 可解元素：难挥发 + 强亲铁/亲核(存量部分在地核)。
# 注：Au 中等挥发性(T_c≈1060K)，此处按难挥发处理会略高估其入核量级，
#     但结论方向(>99% 地球 Au 在地核)稳健。
SOLVABLE_SIDEROPHILE = ["Fe", "Ni", "Co", "Cr", "W", "Mo",
                        "Re", "Os", "Ru", "Rh", "Ir", "Pt", "Pd", "Au"]

# 轻元素预算(地震学密度亏损约束；来源: McDonough 2003 汇编) → wt% 后再转 ppm
LIGHT_PPM = {"Si": 60000.0, "S": 19000.0, "O": 9000.0, "C": 2000.0, "H": 1000.0}

# 文献对照(重量分数, McDonough 2003 / McDonough & Sun 1995 汇编)
LIT_CORE = {"Fe": 0.855, "Ni": 0.052, "Co": 0.0025, "Cr": 0.009,
            "Si": 0.060, "S": 0.019}


def _x_ref(ci: dict, bse: dict) -> tuple[float, float, list]:
    xs = [F_SIL * bse[e] / ci[e] for e in REFRACTORY_LITHOPHILE
          if e in bse and e in ci and ci[e] > 0]
    return mean(xs), stdev(xs), xs


def solve_core() -> dict:
    """返回反演全结果。"""
    ref = get_reference_tables()
    ci, bse = ref["CI"], ref["BSE"]
    x_ref, x_std, xs = _x_ref(ci, bse)

    rows = []
    for e in SOLVABLE_SIDEROPHILE:
        c_e = x_ref * ci[e]                      # 全地浓度(ppm)
        c_sil = F_SIL * bse[e]                   # 硅酸盐贡献(ppm)
        c_core = (c_e - c_sil) / F_CORE          # 纯金属端地核浓度(ppm)
        rel = x_std / x_ref
        rows.append({
            "element": e,
            "C_CI_ppm": ci[e],
            "C_BSE_ppm": bse[e],
            "C_earth_ppm": c_e,
            "C_core_pure_metal_ppm": c_core,
            "C_core_pure_metal_pct": c_core / 1e4,
            "sigma_rel": rel,
            "C_core_plus_lo_ppm": c_core * (1 - rel),
            "C_core_plus_hi_ppm": c_core * (1 + rel),
            "lit_wt": LIT_CORE.get(e),
        })

    # 合并物理一致地核表：金属反演解 + 轻元素预算，Fe=100%−其余
    metals = {r["element"]: r["C_core_pure_metal_ppm"] for r in rows}
    non_fe = {e: v for e, v in metals.items() if e != "Fe"}
    merged = dict(non_fe)
    merged.update(LIGHT_PPM)
    fe = 1e6 - sum(merged.values())
    if fe < 0:
        raise ValueError(f"地核 Fe 反解为负 {fe:.0f} ppm，输入不一致")
    merged["Fe"] = fe

    lit = {e: v * 1e4 for e, v in LIT_CORE.items()}
    meta = {
        "x_ref_mean": x_ref,
        "x_ref_std": x_std,
        "x_ref_rel_std": x_std / x_ref,
        "n_refractory_sample": len(xs),
        "f_sil": F_SIL, "f_core": F_CORE,
        "light_budget_ppm_total": sum(LIGHT_PPM.values()),
        "merged_core_sum_ppm": sum(merged.values()),
        "merged_Fe_pct": merged["Fe"] / 1e4,
        "lit_comparison": {e: {"model_pct": merged[e] / 1e4,
                               "lit_pct": (LIT_CORE.get(e) or 0.0) * 100}
                           for e in merged},
    }
    return {"rows": rows, "meta": meta, "core_ppm": merged, "x_stats": xs}


if __name__ == "__main__":
    import json
    res = solve_core()
    print("X_ref =", round(res["meta"]["x_ref_mean"], 4),
          "±", round(res["meta"]["x_ref_rel_std"] * 100, 2), "%")
    print("\n纯金属端地核解 (wt%):")
    for r in res["rows"]:
        lit = f"  [lit {r['lit_wt']*100:.1f}%]" if r["lit_wt"] else ""
        print(f"  {r['element']:<3} {r['C_core_pure_metal_pct']:6.2f}%{lit}")
    print("\n合成物理一致表(含轻元素预算):")
    for e, p in res["core_ppm"].items():
        print(f"  {e:<3} {p/1e4:6.2f}%")
    print("\nmeta:", json.dumps({k: v for k, v in res["meta"].items()
                                 if k != "lit_comparison"}, indent=1))
