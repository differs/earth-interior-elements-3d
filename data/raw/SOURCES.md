# 数据来源与出处（本仓库所有原始成分表）
#
# 1. data/raw/crust_crc97.csv — 大陆地壳元素丰度(质量ppm)
#    source: CRC Handbook of Chemistry and Physics 97th ed (2016-2017) sec.14 p.17
#    经 Wikipedia "Abundance of elements in Earth's crust" (rev 1368008262) 转录，
#    转录脚本见 scripts/scrape_notes.md
#
# 2. data/raw/McDonough_Sun__1995__CI_Pyrolite_raw.csv — CI 球粒陨石 + Pyrolite(BSE)
#    全元素表原始档(含单位标注)
#    source: 转录自 R 包 georefdatar (github.com/abuseki/georefdatar, file
#    data-raw/CI_Pyrolite__McDonough_Sun__1995__full.csv)，原始文献为
#    McDonough & Sun (1995) "The composition of the Earth", Chem. Geol. 120:223-253
#
# 3. data/raw/ci_pyrolite_mcd95_ppm.csv — 同一表经 scripts/parse_mcd95.py 解析：
#    主量 %→ppm、Nb 起整段 ppb→ppm、氧按 100% 差反算，两列各自归一化到 1e6 ppm
#
# 4. BSE(原始地幔/pyrolite) 与地核成分建模：见 src/earth3d/reservoirs.py 与
#    src/earth3d/inversion.py；地幔由 BSE 扣除地壳的质量平衡导出；地核金属由
#    CI/BSE 核幔质量平衡反演解出(见 docs/derivation.md 第 6 节)，轻元素预算
#    汇编自 McDonough (2003) "Compositional model for the Earth's core"
#
# 5. 洋壳(MORB)主量 — 汇编自 Gale et al. (2013) MORB 玻璃平均值，
#    录入位置 src/earth3d/reservoirs.py
#
# 6. 圈层质量/几何 — 近似 PREM(1D 平均密度剖面)，密度分带与调参说明见
#    docs/derivation.md
