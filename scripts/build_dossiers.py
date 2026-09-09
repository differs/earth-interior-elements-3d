#!/usr/bin/env python3
"""把"全球再勘查观察清单"top 格合成**立项卡**(一眼可派活的核查结论)。

每个候选格聚合整条证据链：
  族分数 → 富集因子(EF, 立体模型) → 生成窗/成矿语义 → 规则理由
  → 数据空洞+现役采矿证据(该国) → 最近锚点/主要城市 → 该做的第一步
产出: outputs/reexploration_dossiers.md / .csv

运行: python scripts/build_dossiers.py
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from earth3d.enrichment import enrichment_table  # noqa: E402
from earth3d.prospect import RULES  # noqa: E402

# 每族 -> (代表金属, 生成窗/成矿一句话)
WIN = {
    "Au": "造山/卡林型金：绿岩带或沉积岩热液交代，0-5 km",
    "Cu": "斑岩铜在弧岩浆窗；沉积铜在红层盆地",
    "Fe": "BIF 前寒武绿岩 + 近代风化再富集",
    "NiCo": "红土型(低纬)或大火成岩省岩浆硫化物",
    "Li": "盐湖卤水(干旱盆地)或 LCT 伟晶岩",
    "REE": "碳酸岩/碱性省或离子吸附风化壳",
    "PGE": "层状镁铁质杂岩体(如 Bushveld/Great Dyke)",
    "U": "不整合面型(高品位)或砂岩型地浸",
    "Diamond": "克拉通根(≥150 km)金伯利岩筒爆发携带",
    "Coal": "陆内/裂谷含煤盆地煤系",
    "OilGas": "沉积盆地生油-生气窗 + 圈闭",
    "ZnPb": "SEDEX/MVT(裂谷-被动陆缘盆地)或 VMS(弧)",
    "Cr": "蛇绿岩(缝合带)豆荚状铬铁矿或层状铬",
    "Mn": "沉积/火山-沉积锰建造",
    "W": "白钨矿矽卡岩/黑钨矿脉，弧或造山花岗岩",
    "Sn": "锡石，弧后/后碰撞酸性花岗岩",
    "Sb": "辉锑矿浅成低温，弧或造山带",
    "V": "黑色页岩/沉积钒或钒钛磁铁矿",
    "Ti": "钛铁矿海滨砂矿或层状侵入体",
    "TaNb": "Ta-Nb 伟晶岩或碳酸岩(裂谷/增生带)",
}
METAL = {"Au": "Au", "Cu": "Cu", "Fe": "Fe", "NiCo": "Ni", "Li": "Li",
         "REE": "Ce", "PGE": "Pt", "U": "U", "ZnPb": "Zn", "Cr": "Cr",
         "Mn": "Mn", "W": "W", "Sn": "Sn", "Sb": "Sb", "V": "V",
         "Ti": "Ti", "TaNb": "Nb"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(REPO / "outputs"))
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()
    od = Path(args.outdir)

    ef = {r["element"]: r["enrichment_factor"] for r in enrichment_table()}
    with open(od / "reexploration_watchlist.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    hp = [r for r in rows if r["tier"].startswith("高优先级")]
    hp.sort(key=lambda r: (-(r["reporting_gap"] == "True"), -float(r["score_pct"])))

    fams = []
    for fam in RULES:
        sub = [r for r in hp if r["family"] == fam][:args.top]
        if not sub:
            continue
        fams.append((fam, sub))

    out_csv = []
    md = []
    md.append("# 全球再勘查立项卡 (top 格证据包)")
    md.append("")
    md.append(f"> 来源: outputs/reexploration_watchlist.csv(高优先级, 各族 top{args.top})。"
              "每个候选格 = 假设，不是矿床预测；派活前先翻该国 1:20 万图/权属。")
    md.append("")
    md.append(f"- 覆盖族: {len(fams)}")
    md.append(f"- 含数据空洞标注的: {sum(1 for _, s in fams for r in s if r['reporting_gap']=='True')}")
    md.append("")

    for fam, sub in fams:
        metal = METAL.get(fam, "")
        efv = ef.get(metal)
        md.append(f"## {fam}  (EF[{metal}]={'%.1f' % efv if efv else '—'})")
        md.append("")
        md.append(f"生成窗: {WIN.get(fam, '')}  ")
        md.append(f"规则理由: {RULES[fam][3]}  ")
        md.append("")
        md.append("| 格 | 国家 | 数据空洞 | 分数% | 该国采矿面 | 最近城市km | 距锚点km | 下一步动作 |")
        md.append("|---|---|---|---|---|---|---|---|")
        for r in sub:
            out_csv.append({**r, "metal": metal,
                            "ef": efv, "generation_window": WIN.get(fam, "")})
            if r["reporting_gap"] == "True":
                first = ("① 找该国/区域地调成矿图件回查"
                         if int(r["mining_polygons_n"]) > 50
                         else "① 该区采矿证据少：先 Google Earth + 卫星查迹"
                              " + 区域化探图")
            else:
                first = "① 对照已知矿区扩展方向做野外踏勘/化探"
            action = (f"{first}；② 航磁/重力异常复核；③ 查权属与保护地"
                      if r["is_land"] == "True" else "——(海上, 已被过滤)")
            md.append(f"| {r['family']} {r['cell_lat']},{r['cell_lon']} | "
                      f"{r['country'] or '—'} | {'是' if r['reporting_gap']=='True' else '—'} | "
                      f"{r['score_pct']} | {r['mining_polygons_n']} | "
                      f"{r['nearest_city_km']} | {r['nearest_anchor_km']} | {action} |")
        md.append("")

    (od / "reexploration_dossiers.md").write_text("\n".join(md), encoding="utf-8")
    cols = list(out_csv[0].keys())
    with (od / "reexploration_dossiers.csv").open("w", newline="",
                                                  encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out_csv)
    print(f"立项卡已写入 {od}/reexploration_dossiers.md(+.csv), "
          f"覆盖 {len(fams)} 族 / {len(out_csv)} 格")


if __name__ == "__main__":
    main()
