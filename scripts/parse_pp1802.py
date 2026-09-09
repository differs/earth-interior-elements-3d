#!/usr/bin/env python3
"""USGS PP1802 全球关键矿产 KML → 锚点 csv(可复现)。

用法: PP1802_KML=/path/to/pp1802.kml python3 scripts/parse_pp1802.py
默认读取 ~/.cache/opencode-tmp/opencode/pp1802.kml
输出: data/raw/usgs_pp1802_anchors.csv
数据源: https://mrdata.usgs.gov/pp1802/pp1802.kml (公有领域)
"""

from __future__ import annotations

import csv
import html
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from earth3d.commodities import classify  # noqa: E402

SRC = Path(os.environ.get("PP1802_KML",
            str(Path.home() / ".cache/opencode-tmp/opencode/pp1802.kml")))
DST = REPO / "data" / "raw" / "usgs_pp1802_anchors.csv"


def main() -> int:
    if not SRC.exists():
        print(f"[parse_pp1802] 缺 {SRC}, 先下载:\n"
              "  curl -L https://mrdata.usgs.gov/pp1802/pp1802.kml -o <path>")
        return 1
    s = SRC.read_text(encoding="utf-8", errors="replace")
    rows, seen = [], set()
    for m in re.finditer(r"<Placemark>(.*?)</Placemark>", s, re.S):
        frag = m.group(1)
        nm = re.search(r"<name>(.*?)</name>", frag, re.S)
        name = html.unescape(nm.group(1)).strip() if nm else ""
        sn = re.search(r"<Snippet>(.*?)</Snippet>", frag, re.S)
        comm = html.unescape(sn.group(1)).strip() if sn else ""
        fams = classify(comm)
        if not fams:
            continue
        cd = re.search(r"<description><!\[CDATA\[(.*?)\]\]></description>",
                       frag, re.S)
        country, dtype = "", ""
        if cd:
            b = html.unescape(cd.group(1))
            loc = re.search(r"Location</td><td>(.*?)</td>", b)
            country = loc.group(1).strip() if loc else ""
            dt = re.search(r"Deposit type</td><td>(.*?)</td>", b)
            dtype = dt.group(1).strip() if dt else ""
        co = re.search(r"<coordinates>\s*([-\d.]+)\s*,\s*([-\d.]+)", frag)
        if not co:
            continue
        lon, lat = float(co.group(1)), float(co.group(2))
        key = (fams[0], round(lat, 2), round(lon, 2))
        if key in seen:
            continue
        seen.add(key)
        for fam in fams:
            rows.append([fam, round(lat, 4), round(lon, 4), country,
                         f"{name[:70]} [{comm}|{dtype}]".strip()])
    with DST.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["family", "lat", "lon", "country", "commodity"])
        w.writerows(sorted(rows))
    print(f"[parse_pp1802] {len(rows)} 条 -> {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
