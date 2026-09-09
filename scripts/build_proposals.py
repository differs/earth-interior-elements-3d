#!/usr/bin/env python3
"""从观察清单 top 格生成 5 份"一页纸野外立项建议书"。

选择原则：陆上、分数高、物流可达、数据空洞或成矿概念清晰、地域分散。
每个候选格 = 假设生成器；建议书用于立项前桌面核查，**不是矿床预测**。

运行: python scripts/build_proposals.py  → outputs/proposal_briefs.md
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from earth3d.enrichment import enrichment_table  # noqa: E402

# (family, cell_lat, cell_lon) —— 从 dossiers 里挑的 5 个代表格
PICKS = [
    ("Sn", 0.0, 100.0),
    ("REE", 18.0, 42.0),
    ("Au", -6.0, 146.0),
    ("Sb", 22.0, -104.0),
    ("OilGas", 24.0, 48.0),
]

# 每格: 目标概念(标题/正文), 立项逻辑, 风险
NARRATIVE = {
    "Sn": ("苏门答腊弧后 S 型花岗岩 Sn-W 带",
           "Sn 与相邻 W(2°N/100°E)同源: 二叠-三叠弧后过铝质花岗岩(与马来西亚锡带同一"
           "岩浆省北延)。EF[Sn]=16、EF[W]=48 均为地壳富集型; 距最近同类已知锚点约数百 km"
           "且该国 MRDS 欠录(gap)。",
           "已知锡带主体在邦加勿里洞(-2°S), 此处为其北延推测段; 需先核实现有矿权与"
           "地表风化锡石重砂证据, 目标为原生锡石-石英脉/云英岩或次生砂锡。"),
    "REE": ("阿拉伯地盾过碱性花岗岩/碳酸岩 REE-Ta-Nb 潜力",
           "沙特阿拉伯地盾存在多处过碱性花岗岩(Ghurayyah 型 Ta-Nb-Zr-REE 类比)与碳酸岩;"
           "EF[Ce]=43 强地壳富集; 该国采矿证据 719 个面但全球库收录少(gap), 属'欠报但"
           "确在开采'。",
           "地盾内此类岩体剥露浅、遥感蚀变清晰; 但需绕开国家公园与矿区重合面, 目标"
           "碳酸岩-碱性交代型轻稀土+伴生 Nb。"),
    "Au": ("巴布亚弧(新几内亚折返带)浅成低温-斑岩 Au 邻域",
           "PNG 弧岩浆活动强(已知 Ok Tedi/Porgera 同带), 本格(-6,146)为高分但全球库"
           "未标已知的弧内格; EF[Au]=3.3。",
           "此带真实成矿, 但陆权/社区谈判成本高; 目标浅成低温 Au-Ag, 需航磁+河流化探"
           "限定蚀变带。"),
    "Sb": ("墨西哥 Sierra Madre Occidental 锑-浅成低温邻域",
           "SMO 是已知 Ag-Au 浅成低温省, Sb 常共生(辉锑矿); EF[Sb]=38; 该国采矿证据"
           "2190 面、数据覆盖尚可(非 gap)。",
           "Sb 为关键金属价高; 目标脉状辉锑矿, 建议先 1:5 万化探重砂+ASM 老硐复查,"
           "成本低见效快。"),
    "OilGas": ("阿拉伯地台内部'无井但有邻'的盆地复查",
           "波斯湾周边为世界级生烃盆, 本格(24°N,48°E)紧邻已探区但本底图未标井场;"
           "距最近主要城市仅 148 km(基建好)。",
           "风险: 多半位于已勘探但未商业化的构造或保护地; 立项前必须查 2D/3D 地震"
           "覆盖与矿权, 桌面即可否掉——便宜的第一步。"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(REPO / "outputs"))
    args = ap.parse_args()
    od = Path(args.outdir)
    ef = {r["element"]: r["enrichment_factor"] for r in enrichment_table()}
    with open(od / "reexploration_dossiers.csv", encoding="utf-8") as fh:
        doss = list(csv.DictReader(fh))

    def find(fam, lat, lon):
        for r in doss:
            if (r["family"] == fam and float(r["cell_lat"]) == lat
                    and float(r["cell_lon"]) == lon):
                return r
        return None

    md = ["# 一页纸野外立项建议书（5 个代表格）", "",
          "> 全部来自 outputs/reexploration_dossiers.csv 高分候选。",
          "> **性质：假设生成器 + 立项前桌面核查包，不是矿床预测。**",
          "> 每个格子执行前都必须：① 该国 1:20 万-1:5 万图/矿权/保护地复核；",
          "> ② 航磁-重力-化探复核；③ 对已知邻区做踏勘对照。", ""]
    for i, (fam, lat, lon) in enumerate(PICKS, 1):
        r = find(fam, lat, lon)
        if r is None:
            continue
        title, logic, risk = NARRATIVE[fam]
        md += [
            f"## 建议 {i}. {title}",
            "",
            f"**候选格**：{fam} {r['cell_lat']}°N/S, {r['cell_lon']}°E/W"
            f"　| 国家 {r['country']}　| 分数 {r['score_pct']}%",
            "",
            "| 关键证据 | 值 |",
            "|---|---|",
            f"| 族富集因子 EF | {r['ef'] or '—'} (代表金属 {r['metal']}) |",
            f"| 生成窗/语义 | {r['generation_window']} |",
            f"| 规则理由 | {r['_reason'] if '_reason' in r else _reason(fam)} |",
            f"| 距最近同类已知锚点 | {r['nearest_anchor_km']} km |",
            f"| 该国现役采矿面 | {r['mining_polygons_n']} |",
            f"| 最近主要城市 | {r['nearest_city_km']} km |",
            f"| 数据空洞标注 | {'是(优先核验)' if r['reporting_gap']=='True' else '否'} |",
            "",
            f"**立项逻辑**：{logic}",
            "",
            f"**主要风险**：{risk}",
            "",
            "---", "",
        ]

    (od / "proposal_briefs.md").write_text("\n".join(md), encoding="utf-8")
    print("5 份立项建议书写入", od / "proposal_briefs.md")


def _reason(fam):
    from earth3d.prospect import RULES
    return RULES[fam][3]


if __name__ == "__main__":
    main()
