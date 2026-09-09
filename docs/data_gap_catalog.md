# 数据缺口清单：为"欠报国家"找权威矿床数据的结果

> 目的：给 `reexploration_watchlist.csv` 的 reporting_gap 高分区喂更全的锚点。
> 更新日期：2026-09。每行给出 URL、格式、门(gate)。

## 已找到并可自动下载（已入仓）

| 源 | 内容 | 格式 | 入仓 |
|---|---|---|---|
| USGS mrdata 专家汇编 8 库 | 斑岩/沉积 Cu、VMS、沉积 Au、红土 Ni-Co、REE、碳酸岩、主要矿床、全球铜评估 | csv.zip | `usgs_expert_anchors.csv` (7,719) |
| USGS PP1802 全球关键矿产 | 2125 个矿点(坐标+国家+类型) | KML | `usgs_pp1802_anchors.csv` (468 命中本仓库 11 族；另有大量 Sb/Mn/V/Ti/W/Ta 等临界金属可扩展族后入库) |
| USGS MRDS | 全球矿点(美国偏重) | CSV 137MB→去重 | `mrds_anchors.csv` |

## 已定位、但被"门"挡住（需注册/人工/申请或非开放）

| 目标 | 找到的入口 | 门 |
|---|---|---|
| 中国全国矿产地数据库(2021版, 22.8万+点) | 知乎/CSDN 分享文(格式 CSV/SHP)；官方出口 geodata.cgs.gov.cn | 官方需单位账号；第三方分享含云盘提取码，非稳定直链 → **不直接入仓** |
| 中国 1:100万 数字地质图(公开版) | geochina.cgs.gov.cn / selectdataset.com(DOI 元数据) | 数据在 CGS 平台；下载需注册(科研用户) |
| 中国 1:20万 公开版数字地质图 | selectdataset 同名条目 | 同上，需 CGS 申请 |
| 俄罗斯 VSEGEI 国家地质图(1:1M/1:2.5M) 与矿点预测图 P3 | vsegei.com/en/info/ggk.html；webmapget.html | VSEGEI 页面为"占位文本"；实际数据在 Rosnedra 门户需账号 |
| 俄罗斯 GIS(webmapget) | www.vsegei.com/en/info/webmapget.html | 页空；GIS Centre 目录无开放 zip |
| 非洲(泛非单一矿床 GIS 库) | 未找到单一开放库；候选=AAGS(非洲地质调查联盟)地图服务 / 各国地调开放文件 | 需逐国查明服务端点；USGS 有非洲多国 open-file 评估(如坦桑/博茨/加纳)但分散 |
| 哈萨克斯坦矿床 GIS | 未验证到开放直链 | 待查(KAZ 地调门户) |

## 结论与建议

1. **免费且能自动抓的已经基本抓完**（MRDS + 8 专家库 + PP1802），中/俄/巴/南非/澳的
   公开库覆盖已翻倍；grep 见 watchlist 的 reporting_gap 快速下降。
2. 剩余大缺口（中国矿产地库、俄 1:2.5M、非洲统一库）**本质是"需授权数据"**，不是
   "没找到"——都定位到了入口，缺的是账号/申请/商业授权。
3. **免费两件已做成**：
   - ~~把 PP1802 临界金属扩族~~（已入 468 条现有族；扩族需重定义评分族，可选做）
   - ✅ **OSM/遥感全球采矿面已拉取**(Maus et al., 192,584 多边形→质心点)：
     `data/geo/osm_mining_points.csv`(中 15,458/俄 12,232/加 16,415/巴西 6,019)，
     ODbL；观察清单带 `mining_polygons_n`(该国现役采矿证据)。
4. 若追求"找新矿"级别的数据库，商业源 S&P Global 是最佳但非开放——超出本仓库定位。
