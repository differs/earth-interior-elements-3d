"""族内细分(subtype)勘探引力。

正样本直接来自各"子型专属"专家库(USGS mrdata)，互不混淆：

| subtype | 父族 | 来源库 | 语义 |
|---|---|---|---|
| Cu_porphyry | Cu | porcu | 斑岩型(安第斯/西南太平洋弧…) |
| Cu_sediment | Cu | sedcu | 沉积岩容矿(中非铜带式红层) |
| Cu_VMS | Cu | vms(含Cu) | 火山块状硫化物 |
| Au_sed | Au | sedau | 沉积岩容矿金(卡林式) |
| ZnPb_SEDEX | ZnPb | sedznpb | 喷流-沉积/MVT 层控 Zn-Pb |

方法：各子型做独立的"最近锚点高斯引力"(σ=4°) → 子型内百分位 → P90 前沿格。
用途：把父族(如 Cu)高分前沿格"拆开读"——同样铜格，是更像斑岩弧还是更像
沉积铜带？锚点来源:
  scripts/ingest_usgs_expert.py 用到的 mrdata *-csv.zip(需先解压到 $USGS_EX_DIR)。
运行时若无 ex 目录，读仓库内提交的 data/raw/subtype_anchors.csv。
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
EX = Path(os.environ.get("USGS_EX_DIR",
          str(Path.home() / ".cache/opencode-tmp/opencode/usgs/ex")))
ANCHORS_CSV = REPO / "data" / "raw" / "subtype_anchors.csv"

SUBTYPES = {
    "Cu_porphyry": ("porcu/main.csv", "Cu"),
    "Cu_sediment": ("sedcu/main.csv", "Cu"),
    "Cu_VMS": ("vms/main.csv", "Cu"),
    "Au_sed": ("sedau/main.csv", "Au"),
    "ZnPb_SEDEX": ("sedznpb/main.csv", "ZnPb"),
}


def _reader(which):
    def porcu(r):
        return (r.get("latitude"), r.get("longitude"), r.get("country"))
    def vms(r):
        g = r.get("cugrd")
        try:
            if g is None or float(g) == 0:
                return None
        except ValueError:
            return None
        return (r.get("latitude"), r.get("longitude"), r.get("country"))
    return {"porcu/main.csv": porcu, "vms/main.csv": vms}.get(which, porcu)


def build_subtype_anchors() -> dict:
    """返回 {subtype: (lat[], lon[])}。优先 ex 源，否则读提交的 csv。"""
    out = {s: ([], []) for s in SUBTYPES}
    if EX.exists():
        for sub, (db, _parent) in SUBTYPES.items():
            p = EX / db
            if not p.exists():
                continue
            rd = _reader(db)
            with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
                for row in csv.DictReader(fh):
                    try:
                        hit = rd(row)
                    except Exception:
                        continue
                    if hit is None:
                        continue
                    la, lo, _ = hit
                    try:
                        la, lo = float(la), float(lo)
                    except (TypeError, ValueError):
                        continue
                    out[sub][0].append(la)
                    out[sub][1].append(lo)
    if all(len(v[0]) == 0 for v in out.values()) and ANCHORS_CSV.exists():
        with ANCHORS_CSV.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row["subtype"] in out:
                    out[row["subtype"]][0].append(float(row["lat"]))
                    out[row["subtype"]][1].append(float(row["lon"]))
    return {s: (np.array(a), np.array(b)) for s, (a, b) in out.items()}


def score_subtypes(anchors_by_sub, lat_c, lon_c):
    """每子型 → (pct2D, known2D, anchors_pts)。"""
    from .prospect import KNOWN_R_DEG, nearest_prox_grid
    res = {}
    for sub, (la, lo) in anchors_by_sub.items():
        n = len(la)
        if n == 0:
            res[sub] = None
            continue
        prox = nearest_prox_grid(la, lo, lat_c, lon_c)
        flat = prox.ravel()
        pct = np.zeros_like(prox)
        order = flat.argsort()
        pct.ravel()[order] = np.linspace(0, 100, len(flat), endpoint=True)
        pts = np.column_stack([la, lo, np.ones(n)])
        # known = 距锚点 ≤2°
        known = np.zeros((len(lat_c), len(lon_c)), bool)
        for i, laa in enumerate(lat_c):
            cosl = np.cos(np.deg2rad(laa))
            for j0 in range(0, len(lon_c), 40):
                j1 = min(j0 + 40, len(lon_c))
                dlon = (lon_c[j0:j1, None] - lo[None, :]) * cosl
                d2 = (laa - la)[None, :] ** 2 + dlon ** 2
                known[i, j0:j1] = np.sqrt(d2).min(axis=1) <= KNOWN_R_DEG
        res[sub] = {"pct": pct, "known": known, "anchors": pts}
    return res
