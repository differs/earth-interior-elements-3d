"""勘探潜力评分引擎：从"已知"外推"值得再看的邻域"。

方法(诚实声明, 详见 docs/prospectivity.md)：
- 正样本 = USGS MRDS 逐矿点(各族去重后, 上限 5000 点/族, 确定性抽样)
          + 本仓库世界级省/区带(权重更高, 补稀疏族如 REE/OilGas/Coal)。
- 每个 2° 网格单元按高斯核累加邻域"富集引力"：
      score(cell) = Σ_anchor w·exp(-d²/2σ²),   σ=4°≈440km
- 把分数转成族内百分位(0-100)。"已知格" = 与某个锚点距离 ≤2°；
  **前沿格(frontier)** = 高分(≥P90)但本身没有已知矿点的邻接单元 → "宝藏就旁边，
  这里却没标过"的再勘查候选。
- 不宣称预测新矿床：模型只做已发现富集的空间平滑与欠标记格挖掘，地质偏差
  (如美国记录偏重)在 meta 里原样报出。

输出可在 2 分钟量级复算。
"""

from __future__ import annotations

import csv
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]

SIGMA_DEG = 4.0            # 核宽(度)，~440 km
KNOWN_R_DEG = 2.0          # "已知"半径
STEP_DEG = 2.0             # 网格步长
LAT_MIN, LAT_MAX = -58.0, 78.0
ANCHOR_CAP = 5000          # 每族上限(性能+去美国偏重的折中)
PROVINCE_WEIGHT = 3.0
MRDS_FILE = REPO / "data" / "raw" / "mrds_anchors.csv"
PROVINCE_FILE = REPO / "data" / "raw" / "geo_world_class_deposits.csv"
HYDRO_FILE = REPO / "data" / "raw" / "geo_hydrocarbon_provinces.csv"


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return R * 2 * asin(sqrt(a))


def _read(f, path, weight_col=None, w=1.0):
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            lat, lon = float(row["lat"]), float(row["lon"])
            fam = row["family"] if weight_col is None else row[weight_col]
            yield fam, lat, lon, w


def _provinces():
    out = []
    for p, w in ((PROVINCE_FILE, PROVINCE_WEIGHT),
                 (HYDRO_FILE, PROVINCE_WEIGHT)):
        if not p.exists():
            continue
        for row in csv.DictReader(p.open(encoding="utf-8")):
            fam = {
                "Au": "Au", "Cu": "Cu", "Fe": "Fe", "NiCo": "NiCo",
                "Li": "Li", "REE": "REE", "PGE": "PGE", "U": "U",
                "Diamond": "Diamond", "Oil": "OilGas", "Gas": "OilGas",
                "Coal": "Coal",
            }.get(row["primary"])
            if fam:
                out.append([fam, float(row["lat"]), float(row["lon"]), w])
    return out


def load_anchors() -> dict:
    """返回 {family: np 数组 [ [lat,lon,weight] ... ]} 与计数说明。"""
    raw = {f: [] for f in ("Au", "Cu", "Fe", "NiCo", "Li", "REE", "PGE",
                           "U", "Diamond", "Coal", "OilGas")}
    if MRDS_FILE.exists():
        with MRDS_FILE.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                fam = row["family"]
                if fam in raw:
                    raw[fam].append((float(row["lat"]), float(row["lon"]), 1.0))
    for fam, lat, lon, w in _provinces():
        raw[fam].append((lat, lon, w))

    rng = np.random.default_rng(2026)
    out = {}
    for fam, pts in raw.items():
        arr = np.array(pts, dtype=np.float64).reshape(-1, 3) if pts else np.empty((0, 3))
        if len(arr) > ANCHOR_CAP:
            idx = rng.choice(len(arr), size=ANCHOR_CAP, replace=False)
            arr = arr[idx]
        out[fam] = arr
    return out


def build_grid():
    lat_c = np.arange(LAT_MIN, LAT_MAX + 1e-9, STEP_DEG)
    lon_c = np.arange(-180.0, 180.0 + 1e-9, STEP_DEG)
    return lat_c, lon_c


def score_family(anchors, lat_c, lon_c):
    """返回 (score_pct 2D[lat,lon], known 2D, min_deg 2D)。"""
    na = len(anchors)
    if na == 0:
        return (np.zeros((len(lat_c), len(lon_c))),
                np.zeros((len(lat_c), len(lon_c)), bool),
                np.full((len(lat_c), len(lon_c)), np.inf))
    latA, lonA, wA = anchors[:, 0], anchors[:, 1], anchors[:, 2]
    s = np.zeros((len(lat_c), len(lon_c)))
    mind = np.full((len(lat_c), len(lon_c)), np.inf)
    # 分块算，避免一次建 (ncell × na) 大矩阵
    for i, la in enumerate(lat_c):
        dlat = la - latA
        cosl = np.cos(np.deg2rad(la))
        for j0 in range(0, len(lon_c), 40):
            j1 = min(j0 + 40, len(lon_c))
            dlon = (lon_c[j0:j1, None] - lonA[None, :]) * cosl
            d2 = dlat[None, :] ** 2 + dlon ** 2
            # 每个列(lon cell)独立算 cos 差异略不计(≤2°)
            wgt = np.exp(-d2 / (2 * SIGMA_DEG ** 2))
            s[i, j0:j1] = (wgt * wA[None, :]).sum(axis=1)
            d = np.sqrt(d2)
            # 用与真实纬度的差近似经向距离(对已知掩码足够)
            mind[i, j0:j1] = d.min(axis=1)
    known = mind <= KNOWN_R_DEG
    pct = np.zeros_like(s)
    flat = s.ravel()
    order = flat.argsort()
    pct.ravel()[order] = np.linspace(0, 100, len(flat), endpoint=True)
    return pct, known, mind


def frontier_cells(family, pct, known, anchors, top=120, min_pct=90.0):
    rows = []
    if anchors is None or len(anchors) == 0:
        return rows
    lat_c, lon_c = build_grid()
    ys, xs = np.where((pct >= min_pct) & (~known))
    for k in np.argsort(-pct[ys, xs])[:top]:
        i, j = ys[k], xs[k]
        la, lo = lat_c[i], lon_c[j]
        # 到最近锚点距离(度→km 由最近锚点纬向近似)
        dlat = la - anchors[:, 0]
        dlon = lo - anchors[:, 1]
        d2 = dlat ** 2 + (dlon * np.cos(np.deg2rad(la))) ** 2
        kmin = int(np.argmin(d2))
        km = haversine_km(la, lo, anchors[kmin, 0], anchors[kmin, 1])
        rows.append({"family": family, "cell_lat": round(float(la), 2),
                     "cell_lon": round(float(lo), 2),
                     "score_pct": round(float(pct[i, j]), 1),
                     "nearest_anchor_lat": round(float(anchors[kmin, 0]), 2),
                     "nearest_anchor_lon": round(float(anchors[kmin, 1]), 2),
                     "nearest_km": round(float(km), 0)})
    return rows
