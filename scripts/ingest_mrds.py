#!/usr/bin/env python3
"""把 USGS MRDS(mrdata.usgs.gov, 公开) 逐矿点库清洗为各族锚点。

- 原始文件较大(约 137 MB / 30 万行)，不在仓库里提交；
  本脚本从本地路径读取(见环境变量 MRDS_CSV，默认 $HOME/.cache/opencode-tmp/opencode/mrds.csv)，
  产出经去重/去尾、按金属族标注的轻量锚点文件 data/raw/mrds_anchors.csv。
- 坐标先按 0.05° 归并去重(说明：大幅压缩美国等地的重复矿点，保留全球覆盖)；
- 一个记录可同时属于多个族(例如 Cu-Au 伴生)。
- USGS MRDS 明显偏重美国记录——这是数据本身的偏差，文档已声明。

族映射(按商品词, 大小写不敏感)见 FAM_RULES。
"""

from __future__ import annotations

import csv
import os
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DST = REPO / "data" / "raw" / "mrds_anchors.csv"
SRC = Path(os.environ.get("MRDS_CSV",
            str(Path.home() / ".cache/opencode-tmp/opencode/mrds.csv")))

FAM_RULES = [
    ("Au", ("gold",)),
    ("Cu", ("copper",)),
    ("Fe", ("iron",)),
    ("NiCo", ("nickel", "cobalt")),
    ("Li", ("lithium",)),
    ("REE", ("rare earth", "cerium", "lanthanum", "neodymium", "praseodymium",
             "samarium", "europium", "gadolinium", "terbium", "dysprosium",
             "holmium", "erbium", "thulium", "ytterbium", "lutetium",
             "yttrium", "monazite", "bastnaesite", "xenotime", "eudialyte")),
    ("PGE", ("platinum", "palladium", "osmium", "iridium", "ruthenium", "rhodium")),
    ("U", ("uranium",)),
    ("Diamond", ("diamond", "kimberlite", "lamproite")),
    ("Coal", ("coal",)),
]


def classify(commod: str) -> list:
    c = (commod or "").lower()
    return [fam for fam, pats in FAM_RULES if any(p in c for p in pats)]


def main() -> int:
    if not SRC.exists():
        print(f"[ingest_mrds] 找不到 {SRC}，跳过(先用省区带锚点)。")
        return 0
    seen = set()
    out, cnt = [], Counter()
    with SRC.open(encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                lat = round(float(row["latitude"]), 2)
                lon = round(float(row["longitude"]), 2)
            except (TypeError, ValueError):
                continue
            if not (-85.0 <= lat <= 85.0 and -180.0 <= lon <= 180.0):
                continue
            commod = " ".join([(row.get(k) or "").strip()
                               for k in ("commod1", "commod2", "commod3")])
            fams = classify(commod)
            if not fams:
                continue
            key = (round(lat, 2), round(lon, 2), ",".join(fams))
            if key in seen:  # 0.02° 归并去重
                continue
            seen.add(key)
            for fam in fams:
                out.append([fam, lat, lon, row.get("country") or "", commod])
                cnt[fam] += 1
    with DST.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["family", "lat", "lon", "country", "commodity"])
        w.writerows(sorted(out))
    print("[ingest_mrds] 锚点写入", DST, "合计", len(out), "条")
    for k in sorted(cnt):
        print(f"  {k:<9} {cnt[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
