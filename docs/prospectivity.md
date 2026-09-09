# 勘探潜力层：从"已知宝藏"外推"值得再看一眼的地方" (prospectivity)

## 一句话

用 **USGS MRDS 30 万个矿点 + 本仓库 70 个世界级省**做正样本，在 2° 网格上做
每族的"富集引力"高斯平滑，再挖出**分数很高、却还没标过已知矿点**的格子——
这些就是欠勘查(under-explored)但紧挨已知富集区的"前沿格 frontier"。

## 数据与锚点

| 来源 | 内容 | 仓库内位置 |
|---|---|---|
| USGS MRDS (mrdata.usgs.gov) | 全球 304,632 个矿床/矿化点(公开域) | 原始 137MB **不入库**；清洗结果 `data/raw/mrds_anchors.csv` |
| 本仓库世界级省 | 54 金属省 + 16 油气煤省(权重更高, 补稀疏族) | `data/raw/geo_*.csv` |

清洗(scripts/ingest_mrds.py)：合法坐标 + 商品词→族(Au/Cu/Fe/NiCo/Li/REE/PGE/U/
Diamond/Coal)，按 0.02° 去重；**各族上限 5000 点**(确定性抽样，性能与去美国
偏重的折中)。原始大文件从本地 `MRDS_CSV` 环境变量读取，不入 git——保证仓库轻量、
复现路径透明。

## 评分公式

$$
\text{score}(cell)=\sum_{anchor} w_a \exp\Big(-\frac{d^2}{2\sigma^2}\Big),
\qquad \sigma=4^\circ\,(\approx 440\text{ km})
$$

- 网格步长 2°；分数转**族内百分位** 0-100。
- **已知格**：与某锚点距离 ≤2°。
- **前沿格**：score ≥ P90 且非已知格 → "宝藏就旁边，这里却没标过"。

## 诚实的边界（防止过度解读）

1. 这是**已知富集的空间平滑 + 欠标记格挖掘**，不是"预测新矿"；
   高分只意味着"该处离已知同类宝藏很近、构造上值得复查"。
2. MRDS **美国记录严重偏重**——美国外的前沿格数量会被系统性低估。
3. 2° 网格与各向同性高斯核**不含地质掩码**(弧/克拉通/裂谷/盆地)；真正把构造
   地质规则(如"金刚石只在克拉通根")织进来的规则打分是下一步(v0.3c)。
4. 前沿格可能落在海洋/冰川等工程不可采区——本层只回答"地质上多像有货"，
   不回答可采性(那需要叠加 geo_distribution 的 access/基础设施)。

## 用法与产物

```bash
# (可选, 需要本地有 mrds.csv) 生成更密锚点
MRDS_CSV=/path/to/mrds.csv python3 scripts/ingest_mrds.py
python3 scripts/build_prospect.py    # 5 秒内复算
```

- `outputs/prospect_frontiers.csv`：各族前沿格 top（分数百分位 + 距最近锚点经纬度/千米）
- `outputs/prospect_world_frontiers.png`：各族热力百分位图(黑点=已知锚点)
- `outputs/prospect_meta.json`：参数与偏差声明

## 规则版：把 EF/生成窗逻辑换成"加权规则评分"（v0.3c）

各向同性核的升级版——不再是"每个已知点同等膨胀"，而是三类**真实环境核**按族加权：

$$
\text{score}(cell)=\underbrace{\alpha\cdot\text{nearAnchor}}_{\text{已知矿锚点}}
+\underbrace{\beta\cdot\text{nearArc}}_{\text{弧火山(GVP 俯冲型)}}
+\underbrace{\gamma\cdot\text{nearRift}}_{\text{裂谷火山(GVP 裂谷型)}}
$$

每个核都是"到最近特征的距离"高斯 $\exp(-d^2/2\sigma^2)$、$\sigma=4°$。
权重表(锚点/弧/裂谷 + 理由)见 `outputs/prospect_rules_weights.csv`，核心几行：

| 族 | 锚点 | 弧 | 裂谷 | 理由(EF/窗口) |
|---|---|---|---|---|
| Cu | 0.8 | **+1.6** | 0.2 | 斑岩铜主在俯冲弧(地壳富集+弧岩浆窗) |
| Au | 1.0 | +1.0 | 0.2 | 浅成低温/斑岩金在弧；造山型金靠锚点 |
| REE | 1.6 | 0.3 | +0.8 | 碳酸岩/碱性省多与裂谷/板内张裂有关 |
| NiCo | 1.2 | 0.3 | +0.8 | 岩浆Ni-Cu伴大火成岩省；红土在低纬锚点 |
| **Diamond** | 2.5 | **−1.0** | 0 | 金刚石只谈克拉通根、**远离俯冲弧**(负规则) |
| OilGas | 1.2 | 0 | +1.0 | 油气在被动陆缘/裂谷盆地，弧区无 |

环境数据是**真实的**：GVP 5.4.0 全球全新世火山 1,215 座，按 Tectonic Setting 字段分
弧(838)/裂谷(221)/板内——`data/geo/gvp_holocene_volcanoes.csv`。

**v0.3k 扩展到 30 族**：在 Au/Cu/Fe/NiCo/Li/REE/PGE/U/Diamond/Coal/OilGas 之上
新增 Zn-Pb、Cr、Mn、W、Sn、Sb、V、Ti、Ta-Nb(20) 与 Ag、Mo、Re、Bi、As、Be、
Cs-Rb、Sc、Zr、石墨(30)。数据=MRDS 商品词 + mrdata podchrome/sedznpb +
USGS PP1802(1,450 条)。权重理由全在 `prospect_rules_weights.csv`。

**规则版真的改变了语义**（抽查验证）：
- Cu 前沿从"已知矿团外围"移到**弧区无已知矿的格**（新几内亚弧、意大利弧、墨西哥弧）；
- 金刚石前沿回到**远离弧的克拉通内部/边缘**（西澳、巴西、西伯利亚、卡普瓦尔）；
- REE 前沿聚焦 Basin&Range/裂谷碱性省。

### 规则版仍缺的掩码（诚实清单）
- **克拉通多边形**：全球免费档缺（只有 AK/澳洲局部）→ 金刚石靠"锚点+弧负规则"间接表达；
- **沉积盆地多边形**：油气/煤靠锚点+弱裂谷，不能单独"盆地掩码"；
- GVP 火山含热点(板内)不是纯弧；把这些织进来 + 更细的族内规则是下一步。

产物：`prospect_rules_frontiers.csv` / `prospect_rules_weights.csv` /
`prospect_rules_world_map.png` / `prospect_rules_meta.json`。

## 怎么读前沿格

示例(全球尺度第一印象)：
- **油气**：波斯湾-阿拉伯地台边缘 200-350 km 的"无井但有邻"格。
- **Li**：美国 Great Basin(NV/UT/CO) 盐湖黏土外围——与已知 Silver Peak/Clayton
  Valley 邻接。
- **金刚石**：圭亚那/委内瑞拉克拉通边缘——与已知岩筒/砂矿邻接的欠勘查带。
- **Au**：加州近海陆架带(距 Mother Lode 地区 ~250-360 km)。

这些都是**假设生成器**：每个格子应回查 1:100 万地质图与权属/保护地后再谈部署。
