# Roadmap

按"先把存量分布做扎实，再做生成与可达性"的顺序推进。

## v0.1（已交付）
- [x] 1D 分层几何模型，三区质量锁定守恒（0.000% 偏差）
- [x] 地壳全元素表(CRC97) + 洋壳主量 + 地幔 pyrolite + 地核假设档
- [x] 储库级/径向壳级 元素质量长表(csv) 与汇总 json
- [x] 富集因子 + 立体归宿(壳/幔/核份额)
- [x] 四张图：径向丰度剖面 / 圈层储量份额 / 富集因子
- [x] 文档：假设清单 / 推导链 / 生成窗口 / 数据出处

## v0.2（已部分交付）
- [x] **CI + BSE 全元素表并入**：McDonough & Sun (1995) 76 元素，
      原始档 + 解析脚本(scripts/parse_mcd95.py) + 氧差归一，出处进 SOURCES.md
- [x] **地幔改质量平衡解**：BSE 扣除地壳，消除壳/幔不相容元素重复计算
- [x] **核幔质量平衡反演地核成分**(src/earth3d/inversion.py)：
      X_ref=1.8495±0.24%(n=25) → 强亲铁金属差分反解；合成表 Fe 84.1/Ni 5.57/
      Co 0.26/Cr 0.96 wt%，与文献(McDonough 2003) 吻合 ~1.5pp 内；
      输出 core_inversion_metals.csv / meta.json / fig_core_inversion.png
- [ ] 数据机器核对：逐条比对 GeoREM/GERM 全表 + 不确定度带(REVIEW 中)
- [ ] 中等挥发亲硫金属(Cu/Zn/Ga/Ge/Pb/Sn/Sb/As/Ag/Cd/Se/Te/Tl/S…) 引入
      全地挥发亏损参数(相对 CI)后纳入反演
- [ ] P-T 剖面 + 生成窗列(generation_windows.md 数据化)

## v0.3（地理化·已部分交付）
- [x] **地理层初版**：世界级金属省(54) + 油气煤省(16) 数据库带坐标/类型/开采档/
      置信度/出处(geo.py + build_geo.py)；主元素挂 EF 接回立体模型；Ne_110m 世界分布图
- [x] **USGS MRDS 逐矿点接入**：清洗/去重/族标注 → 12.1 万锚点(data/raw/mrds_anchors.csv，
      原始 137MB 不入库，scripts/ingest_mrds.py + MRDS_CSV 环境变量可复现)
- [x] **2° 勘探潜力/前沿格引擎**：高斯核"已知富集引力"(σ=4°, P90+未标已知) → 各族
      prospect_frontiers.csv + 热力图(scripts/build_prospect.py, 5 秒复算)
- [x] **构造规则版评分**：真实环境掩码(锚点 + GVP 弧 838/裂谷 221 火山)加权组合，
      权重表含 EF/生成窗理由(scripts/build_prospect_rules.py)；金刚石带"远离弧"负规则
- [x] **全球再勘查观察清单**：可采性过滤(NE 陆地/冰盖/极地/主要城市距离) + 数据空洞
      标注(国名别名表含防误判)→ tier 分派(scripts/build_watchlist.py)；补齐 NE
      国家/城市/冰川/陆地数据集入仓
- [x] **USGS 全球专家汇编 8 库去偏**：porcu/sedcu/vms/sedau/laterite/ree/carbonatite/
      major-deposits/铜评估 → 7,719 锚点入仓(scripts/ingest_usgs_expert.py, URL 清单在
      脚本头)，MRDS 美国偏重被系统抵消(中/俄/加/澳覆盖翻倍)
- [x] **全球现役采矿证据(OSM/遥感)入仓**：Maus et al. 全球采矿面 19.2 万多边形→质心
      data/geo/osm_mining_points.csv(ODbL, scripts/parse_osm_mining.py)；观察清单新增
      mining_polygons_n 列(俄/中/加/巴西现役采矿证据量)
- [x] **评分族 11→20 扩展**：新增 Zn-Pb/Cr/Mn/W/Sn/Sb/V/Ti/Ta-Nb；数据补 podchrome(铬
      1124)、sedznpb(Zn-Pb 506)、PP1802 临界金属(Mn/W/Sn/Sb/V/Ti/Ta-Nb 437)、MRDS
      商品词(Zn-Pb 3 万/W 6 千...)；全链(prospect/rules/watchlist)重算并字节级稳定
- [x] **立项卡**：scripts/build_dossiers.py——各族 top 候选格聚合 EF/生成窗/规则理由/
      采矿证据/物流 → outputs/reexploration_dossiers.md(.csv) 带"下一步动作"
- [ ] 对中国/俄等仍有大 gap 的国家：喂入该国地质调查成矿图件(俄 1:200万/中 1:100万/
      非洲 SEG 图层)——全球免费档仍缺，最可能来自各机构开放数据页或需申请
- [ ] 把"最近主要城市/距已知矿"合成 1-5 星"分派优先级"打分
- [ ] 横向不均偏离项：俯冲带(含水+富集)、地幔柱(上涌)、克拉通根(加厚/冷)
- [ ] 浅部 0-100 km 分区储量与地理层合并查询
- [ ] 交互式 3D 可视化（球壳切面 + 元素筛选 + 深度滑条 + 地表矿点联动）

## 工程治理
- [ ] 单元测试：质量守恒、壳质量合计、ppm→质量换算、反演 X_ref 回归
- [ ] CI(GitHub Actions)：跑 build_models + pytest，防止数据改动破坏守恒
- [ ] 数据校验器：新表并入前检查 总和≤100%、元素符号合法、出处非空
