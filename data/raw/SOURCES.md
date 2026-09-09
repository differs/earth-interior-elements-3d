# 数据来源与出处（本仓库所有原始成分表）
#
# 1. data/raw/crust_crc97.csv — 大陆地壳元素丰度(质量ppm)
#    source: CRC Handbook of Chemistry and Physics 97th ed (2016-2017) sec.14 p.17
#    经 Wikipedia "Abundance of elements in Earth's crust" (rev 1368008262) 转录，
#    转录脚本见 scripts/scrape_notes.md
#
# 2. BSE(原始地幔/pyrolite) 主量元素 — 氧化物 wt% 来自 McDonough & Sun (1995),
#    "The composition of the Earth", Chem. Geol. 120:223-253 的 pyrolite 模型；
#    录入位置 src/earth3d/data/mantle.py，见其模块 docstring。
#
# 3. 地核成分(Fe-Ni-轻元素) — 汇编自 McDonough (2003) "Compositional model for
#    the Earth's core", Treatise on Geochemistry vol.2, 及 PREM 密度约束；
#    录入位置 src/earth3d/data/core.py。
#
# 4. 洋壳(MORB)主量 — 汇编自 Gale et al. (2013) MORB 玻璃平均值，
#    录入位置 src/earth3d/data/ocean_crust.py。
#
# 5. 圈层质量/几何 — 近似 PREM(1D 平均密度剖面)，密度分带与调参说明见
#    docs/derivation.md。
