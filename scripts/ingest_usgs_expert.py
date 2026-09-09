#!/usr/bin/env python3
"""把 USGS 全球专家汇编矿床库(mrdata, 公开域)归一化成去偏锚点。

这些库是"专家全球汇编"(不止美国)，能补 MRDS 对美国外的系统性低估：
- 中国/俄罗斯/非洲在 porcu/sedcu/vms/评估点/REE/carbonatite/laterite/
  major-deposits/sedau 里都有系统记录。

输入: 需要先下载 *-csv.zip 并解压(见下方 URL 清单)到 $USGS_EX_DIR，
默认 $HOME/.cache/opencode-tmp/opencode/usgs/ex
输出: data/raw/usgs_expert_anchors.csv (schema 同 mrds_anchors.csv)

URL 清单(USGS MRDATA, 公有领域):
  https://mrdata.usgs.gov/porcu/porcu-csv.zip
  https://mrdata.usgs.gov/sedcu/sedcu-csv.zip
  https://mrdata.usgs.gov/vms/vms-csv.zip
  https://mrdata.usgs.gov/sedau/sedau-csv.zip
  https://mrdata.usgs.gov/laterite/laterite-csv.zip
  https://mrdata.usgs.gov/ree/ree-csv.zip
  https://mrdata.usgs.gov/carbonatite/carbonatite-csv.zip
  https://mrdata.usgs.gov/major-deposits/ofr20051294-csv.zip
  https://mrdata.usgs.gov/sir20105090z/sir20105090z-csv.zip (取 *deps_pros.csv)
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from earth3d.commodities import classify  # noqa: E402

EX = Path(os.environ.get("USGS_EX_DIR",
          str(Path.home() / ".cache/opencode-tmp/opencode/usgs/ex")))
DST = REPO / "data" / "raw" / "usgs_expert_anchors.csv"


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _rows(db_path, reader, family, dedup=True):
    """reader(csvrow)-> (lat,lon,country,name,dep_type) 或 None"""
    rows, seen = [], set()
    p = EX / db_path
    if not p.exists():
        print(f"[ingest_usgs] 缺 {p}, 跳过 {family}/{db_path}")
        return rows
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                out = reader(row)
            except Exception:
                continue
            if out is None:
                continue
            lat, lon, country, name, dtype = out
            try:
                lat, lon = float(lat), float(lon)
            except (TypeError, ValueError):
                continue
            if not (-85 <= lat <= 85 and -180 <= lon <= 180):
                continue
            key = (round(lat, 2), round(lon, 2))
            if dedup and key in seen:
                continue
            seen.add(key)
            rows.append([family, round(lat, 4), round(lon, 4),
                         country or "", (name or "").strip()[:120], db_path,
                         (dtype or "").strip()[:80]])
    return rows


def main() -> int:
    if not EX.exists():
        print(f"[ingest_usgs] 找不到 {EX}，请先按 URL 清单下载解压(见脚本头)。")
        return 1
    all_rows = []

    def add(fam, path, fn):
        all_rows.extend(_rows(path, fn, fam))

    # 斑岩铜 / 沉积岩铜 / 沉积岩型金 → Cu / Au
    for db, fam in [("porcu/main.csv", "Cu"), ("sedcu/main.csv", "Cu"),
                    ("sedau/main.csv", "Au")]:
        def rd(r):
            return (r.get("latitude"), r.get("longitude"), r.get("country"),
                    r.get("depname"), r.get("deptype") or r.get("subtype"))
        all_rows.extend(_rows(db, rd, fam))
    # VMS 只收含铜记录(Cu>0)
    def vms(r):
        if r.get("cugrd") is None or _f(r["cugrd"]) is None or _f(r["cugrd"]) == 0:
            return None
        return (r.get("latitude"), r.get("longitude"), r.get("country"),
                r.get("depname"), r.get("deptype"))
    all_rows.extend(_rows("vms/main.csv", vms, "Cu"))
    # 红土镍钴
    all_rows.extend(_rows("laterite/main.csv",
                          lambda r: (r.get("latitude"), r.get("longitude"),
                                     r.get("country"), r.get("depname"),
                                     r.get("subtype")), "NiCo"))
    # 碳酸岩 Nb/REE 与 REE 矿床
    all_rows.extend(_rows("carbonatite/main.csv",
                          lambda r: (r.get("latitude"), r.get("longitude"),
                                     r.get("country"), r.get("depname"),
                                     r.get("mintype")), "REE"))
    def ree(r):
        if r.get("latitude") in (None, ""):
            return None
        return (r.get("latitude"), r.get("longitude"), r.get("country"),
                r.get("depname"), r.get("deptype"))
    all_rows.extend(_rows("ree/main.csv", ree, "REE"))
    # 豆荚状铬铁矿 → Cr；沉积岩型 Zn-Pb → ZnPb
    all_rows.extend(_rows("podchrome/main.csv",
                          lambda r: (r.get("latitude"), r.get("longitude"),
                                     r.get("country"), r.get("depname"),
                                     r.get("deptype")), "Cr"))
    all_rows.extend(_rows("sedznpb/main.csv",
                          lambda r: (r.get("latitude"), r.get("longitude"),
                                     r.get("country"), r.get("depname"),
                                     r.get("deptype")), "ZnPb"))
    # 全球主要矿床(按 commodity 词归族, 一个记录可多族)
    p = EX / "ofr20051294/deposit.csv"
    if p.exists():
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                fams = classify(row.get("commodity") or "")
                for fam in fams:
                    all_rows.append([fam, row.get("latitude"), row.get("longitude"),
                                     row.get("country"), row.get("dep_name"),
                                     "ofr20051294/deposit.csv", row.get("dep_type")])
    # 全球铜资源评估的矿床/矿点(斑岩+沉积岩铜)
    def cu_assess(r):
        return (r.get("latitude"), r.get("longitude"), r.get("country"),
                r.get("name"), r.get("dep_type"))
    all_rows.extend(_rows("sir20105090z/pcu_deps_pros.csv", cu_assess, "Cu"))
    all_rows.extend(_rows("sir20105090z/sedcu_deps_pros.csv", cu_assess, "Cu"))

    # 展开/去重(0.02°)
    rows = [r for r in all_rows if r[1] is not None and r[2] is not None]
    out, seen = [], set()
    for fam, lat, lon, country, name, db, dtype in rows:
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            continue
        if not (-85 <= lat <= 85 and -180 <= lon <= 180):
            continue
        key = (fam, round(lat, 2), round(lon, 2))
        if key in seen:
            continue
        seen.add(key)
        out.append([fam, round(lat, 4), round(lon, 4), country or "",
                    f"{str(name)[:100]} [{db}]"])
    with DST.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["family", "lat", "lon", "country", "commodity"])
        w.writerows(sorted(out))
    print("[ingest_usgs] 写入", DST, "合计", len(out), "条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
