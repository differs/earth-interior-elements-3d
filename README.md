# 地球内部元素立体分布模型 (Earth Interior Elements 3D)

> 大胆假设 · 仔细推导 · 全可复算
> 一个把"地球内部各种元素/矿产藏在哪、以多少质量存在"做成**公开数据 + 分层几何模型**的工程仓库。

地球不是一块均匀岩石，而是一台分了层的"反应釜"：铁镍在 2900 km 深处聚成地核，
亲铁元素被抽走、亲石元素被火山/热液抬回地表、油气和矿体只在特定温度压力"窗口"
里生成。本项目把这些经典地球化学知识做成**可复算的 1D 立体分布模型**：

```
地表 ── 地壳(≈21.6 km, 等效) ── 地幔(≈410/660/2891 km) ── 外核 ── 内核(6371 km)
        └ 成分=大陆地壳+洋壳加权    └ 成分=pyrolite/BSE        └ Fe-Ni-轻元素假设档
```

模型保证**几何质量 = 文献质量**（地壳 3.20e22 kg / 地幔 4.002e24 kg / 地核 1.939e24 kg，
合计恰好 5.972e24 kg = 真实地球质量），再把每个圈层的元素丰度摊到每一深度壳上，
输出"哪一层、哪个元素、多少 ppm、多少公斤"的长表数据与图。

## 快速上手

```bash
python3 scripts/build_models.py     # 生成全部 CSV/JSON（质量守恒校验会打印）
python3 scripts/make_plots.py       # 生成 4 张图（径向丰度/圈层储量/富集因子/地核反演）
python3 scripts/build_geo.py        # 地理层：世界级矿床/油气省 + 世界分布图
python3 scripts/build_prospect.py   # 勘探潜力层：2° 前沿格(已知富集引力 P90)
python3 scripts/build_prospect_rules.py  # 规则版：锚点+弧/裂谷加权评分(EF/窗口逻辑)
python3 scripts/build_watchlist.py  # 全球再勘查观察清单(可采性过滤+数据空洞标注)
# 可选：用 USGS MRDS 逐矿点(30 万)生成更密锚点(需先有 mrds.csv)
#   MRDS_CSV=/path/to/mrds.csv python3 scripts/ingest_mrds.py
```

只需 `numpy`（画图再加 `matplotlib`），无 pandas 依赖。输出落在 `outputs/`：

| 文件 | 内容 |
|---|---|
| `reservoir_elements.csv` | 每个储库×每个元素的 ppm 与总质量（带出处/置信级） |
| `radial_elements.csv` | 每个深度壳×元素 的浓度与质量（≈630 壳，立体分布主表） |
| `radial_region_element_mass.csv` | 按圈层聚合的元素质量 |
| `element_fate_crust_mantle_core.csv` | 关键元素在地壳/地幔/地核的储量份额 |
| `enrichment_crust_vs_mantle.csv` | 地壳/地幔(BSE)富集因子 + 归宿判定 |
| `core_inversion_metals.csv` / `core_inversion_meta.json` | **核幔质量平衡反演**的地核金属解(纯金属端±σ)与合成一致表 |
| `geo_deposits_processed.csv` / `geo_hydrocarbon_processed.csv` | 世界级金属省 / 超级油气煤省的"易采宝藏"分布（坐标/类型/可采档/EF/置信度） |
| `geo_family_summary.csv` / `geo_meta.json` | 按金属族统计与汇总 |
| `prospect_frontiers.csv` / `prospect_meta.json` | 勘探潜力层：各族"前沿格"（高分 P90 且未标已知矿，附距最近锚点距离） |
| `prospect_rules_frontiers.csv` / `prospect_rules_weights.csv` | **规则版评分**：锚点+弧/裂谷加权的前沿格与权重表（EF/生成窗逻辑规则化） |
| `reexploration_watchlist.csv` / `reexploration_meta.json` | **全球再勘查观察清单**：前沿格 + 可采性过滤(陆/冰/极地/城市距离) + 数据空洞标注(224 格欠报国优先) |
| `fig_*.png` | 径向剖面 / 圈层储量 / 富集因子 / 地核反演 / 世界"宝藏"分布图 / 前沿热力图 / **观察清单世界图** |

## 数据出处与置信度

| 储库 | 来源 | 置信度 |
|---|---|---|
| 大陆地壳 | CRC Handbook 97th (2016-2017) 大陆地壳丰度表 | 高 |
| 洋壳(MORB) | Gale et al. (2013) MORB 玻璃主量平均 | 高(主量) |
| CI + BSE(pyrolite) | **McDonough & Sun (1995) 全元素表**（76 元素，脚本解析自 georefdatar 转录档） | 高 |
| 地幔 | BSE 扣除地壳的质量平衡解 | 主量高/微量中 |
| 地核 | **CI/BSE 核幔质量平衡反演**（强亲铁金属）+ 地震学轻元素预算 | Fe/Ni/Co/Cr 与文献吻合 ~1.5pp 内 |
| 世界级矿床/油气省 | 汇编自 USGS 商品年鉴/公司披露/Wikipedia(见各 csv 行) | 高/中(坐标质心±1.5°) |
| 全球矿点锚点 | **USGS MRDS**(mrdata.usgs.gov, 公开域 304k 点)，清洗去重后 12.1 万条 | 原始不入库；文件含来源 |

详见 `data/raw/SOURCES.md` 与 `docs/*`。所有"没把握"的地方都标了置信度，
**不会**为缺失数据凭空编造 ppm。

## 文档导航

- `docs/hypotheses.md` —— 大胆假设清单（H-1…H-9，每一条都写明后果与可撤性）
- `docs/derivation.md` —— 仔细推导链（球壳质量积分、三区缩放守恒、富集因子、核幔反演）
- `docs/generation_windows.md` —— 附加章：矿物/烃类的"生成窗口"与可达性
- `docs/geo_distribution.md` —— 地理层：容易开采的世界级"宝藏"分布与规律
- `docs/prospectivity.md` —— 勘探潜力层：从 MRDS 已知锚点外推的 2° "前沿格"方法与边界
- `docs/methodology_watchlist.md` —— 观察清单方法论：可采性过滤 + 数据空洞标注
- `docs/roadmap.md` —— 路线图（核幔反演已落地、地理层/潜力层/观察清单已交付、细则待办）

## 已知局限（诚实声明）

- v0.1 是 **1D 平均模型**：横向不均（俯冲带、地幔柱、大陆根）被平均掉。
- 下地幔成分假设与上地幔相同（存在 bridgmanite 分层争议，见 roadmap）。
- 地核轻元素(Si/S/O/C/H)配比只是假设档位，不是定论。
- 地核成分表只收录了 Fe/Ni/轻元素候选；因此 Au/Pt/Pd 等强亲铁元素在
  `element_fate` 表里的"地核份额"会被低估（真实情况它们绝大多数在地核），
  这是"未建模不臆造"原则的代价，见 `docs/hypotheses.md` H-6。
- 微量元素表需机器核对（见 roadmap），提交前请对照原始文献。
- 地理层坐标是**世界级省/区带质心，±1.5° 近似**，只够看图与全球尺度统计，
  精确定位需接 USGS MRDS 逐矿点库（见 `docs/geo_distribution.md`）。

## Roadmap 预览

- [x] CI/BSE 全元素表(M&S 1995, 76 元素) 并入并做氧差归一
- [x] **核幔质量平衡反演地核成分**（强亲铁金属；Fe/Ni/Co/Cr 与文献吻合）
- [ ] 中等挥发亲硫金属(Cu/Zn/Pb/…/S) 加入挥发亏损参数后纳入反演
- [ ] 下地幔成分歧见参数化 + 横向不均(俯冲带/地幔柱) 的 3D 偏离项
- [ ] P-T 剖面 + 生成窗 → 从"分布"走向"产状与可达性"
- [ ] 单元测试 + CI + 数据校验器、交互式 3D 可视化

MIT License。数据引用见 `data/raw/SOURCES.md`。
