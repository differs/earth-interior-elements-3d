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
EXPERT_FILE = REPO / "data" / "raw" / "usgs_expert_anchors.csv"
PP1802_FILE = REPO / "data" / "raw" / "usgs_pp1802_anchors.csv"
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
                           "U", "Diamond", "Coal", "OilGas",
                           "ZnPb", "Cr", "Mn", "W", "Sn", "Sb", "V",
                           "Ti", "TaNb",
                           "Ag", "Mo", "Re", "Bi", "As", "Be", "CsRb",
                           "Sc", "Zr", "Graphite")}
    if MRDS_FILE.exists():
        with MRDS_FILE.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                fam = row["family"]
                if fam in raw:
                    raw[fam].append((float(row["lat"]), float(row["lon"]), 1.0))
    # USGS 全球专家汇编(去偏: 补 MRDS 对俄/中/非洲的低估)
    for path in (EXPERT_FILE, PP1802_FILE):
        if path.exists():
            with path.open(encoding="utf-8") as fh:
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


# ---------- 规则版：构造环境(弧/裂谷/板内)掩码评分 ----------

GVP_FILE = REPO / "data" / "geo" / "gvp_holocene_volcanoes.csv"
ENV_SIGMA_DEG = 4.0

_ENV_TYPES = {
    "arc": "subduction zone",
    "rift": "rift zone",
    "intra": "intraplate",
}


def load_gvp_env() -> dict:
    """从 GVP 5.4.0(Holocene 火山, 真实) 读取环境点集 → {env: (lat[], lon[])}。"""
    if not GVP_FILE.exists():
        return {k: (np.empty(0), np.empty(0)) for k in _ENV_TYPES}
    out = {k: ([], []) for k in _ENV_TYPES}
    with GVP_FILE.open(encoding="utf-8", errors="replace") as fh:
        fh.readline()
        for row in csv.DictReader(fh):
            ts = (row["Tectonic Setting"] or "").strip().lower()
            env = next((k for k, tag in _ENV_TYPES.items() if tag in ts), None)
            if env is None:
                continue
            try:
                la, lo = float(row["Latitude"]), float(row["Longitude"])
            except ValueError:
                continue
            out[env][0].append(la)
            out[env][1].append(lo)
    return {k: (np.array(v[0]), np.array(v[1])) for k, v in out.items()}


def nearest_prox_grid(feat_lat, feat_lon, lat_c, lon_c, sigma=ENV_SIGMA_DEG):
    """每个网格单元到最近环境特征的距离核 prox = exp(-dmin²/2σ²)，0..1。"""
    n = len(feat_lat)
    if n == 0:
        return np.zeros((len(lat_c), len(lon_c)))
    grid = np.zeros((len(lat_c), len(lon_c)))
    for i, la in enumerate(lat_c):
        dlat = la - feat_lat
        cosl = np.cos(np.deg2rad(la))
        for j0 in range(0, len(lon_c), 30):
            j1 = min(j0 + 30, len(lon_c))
            dlon = (lon_c[j0:j1, None] - feat_lon[None, :]) * cosl
            d2 = dlat[None, :] ** 2 + dlon ** 2
            grid[i, j0:j1] = np.exp(-d2.min(axis=1) / (2 * sigma ** 2))
    return grid


# 规则权重表：每条给出理由(来源=EF/生成窗/教科书成矿省类型)
RULES = {
    # family: (anchor_w, arc_w, rift_w, reason)
    "Au":      (1.0, 1.0, 0.2, "斑岩/浅成低温金在弧; 造山型金靠锚点"),
    "Cu":      (0.8, 1.6, 0.2, "斑岩铜主产俯冲弧(EF地壳富集+弧岩浆窗)"),
    "Fe":      (1.6, 0.1, 0.1, "BIF 与前寒武纪克拉通锚点为主, 环境弱"),
    "NiCo":    (1.2, 0.3, 0.8, "岩浆Ni-Cu多伴大火成岩省/裂谷; 红土在热带锚点"),
    "Li":      (1.0, 0.6, 0.6, "盐湖锂在安第斯弧后; 伟晶岩在增生/裂谷带"),
    "REE":     (1.6, 0.3, 0.8, "碳酸岩/碱性省多与裂谷或板内有关"),
    "PGE":     (1.8, 0.2, 0.4, "层状杂岩体/撞击为锚点主导"),
    "U":       (1.8, 0.1, 0.3, "不整合面/砂岩铀主要靠锚点"),
    "Diamond": (2.5, -1.0, 0.0, "金刚石在克拉通根, 远离弧(负规则); 锚点为主"),
    "Coal":    (1.6, 0.0, 0.4, "煤在陆内/裂谷盆地(无弧)"),
    "OilGas":  (1.2, 0.0, 1.0, "油气在被动陆缘/裂谷盆地; 弧区无"),
    # --- v0.3h 扩展族(临界/基础金属; 权重=锚点为主+构造倾向) ---
    "ZnPb":    (1.6, 0.4, 0.5, "SEDEX/MVT 在裂谷-被动陆缘盆地, VMS 在弧"),
    "Cr":      (1.8, 1.0, 0.4, "豆荚状铬铁矿在蛇绿岩/汇聚带, 层状在杂岩锚点"),
    "Mn":      (1.8, 0.1, 0.4, "锰多在沉积盆地/洋壳锰结核背景, 锚点为主"),
    "W":       (1.5, 1.2, 0.2, "白钨矿矽卡岩/黑钨矿脉伴弧-碰撞花岗岩"),
    "Sn":      (1.5, 1.2, 0.2, "锡石多与弧/后碰撞酸性花岗岩有关"),
    "Sb":      (1.5, 1.2, 0.2, "辉锑矿浅成低温多沿俯冲弧/造山带"),
    "V":       (1.7, 0.2, 0.3, "钒在沉积岩/钒钛磁铁矿, 锚点为主"),
    "Ti":      (1.6, 0.3, 0.4, "钛铁矿砂矿/层状侵入体与岩体相关"),
    "TaNb":    (1.6, 0.5, 0.7, "Ta-Nb 伟晶岩/碳酸岩多沿裂谷与增生带"),
    # --- v0.3k 第三批扩展族 ---
    "Ag":      (1.2, 1.2, 0.2, "银浅成低温/脉状多沿火山弧"),
    "Mo":      (1.4, 1.4, 0.2, "钼(斑岩 Cu-Mo/独立斑岩钼)主在弧"),
    "Re":      (1.8, 0.8, 0.2, "铼多为 Cu-Mo 副产, 跟随斑岩锚点"),
    "Bi":      (1.6, 0.5, 0.3, "铋多高温脉/矽卡岩伴花岗岩"),
    "As":      (1.6, 0.6, 0.3, "砷在浅成低温/造山带硫化物脉"),
    "Be":      (1.7, 0.4, 0.3, "铍在伟晶岩/凝灰岩, 偏弧-造山"),
    "CsRb":    (1.7, 0.5, 0.3, "铯铷在 LCT 伟晶岩(常伴锂)"),
    "Sc":      (1.8, 0.3, 0.4, "钪在红土/铁氧化物, 锚点为主"),
    "Zr":      (1.5, 0.4, 0.5, "锆在砂矿/碱性杂岩"),
    "Graphite":(1.7, 0.3, 0.4, "石墨在变质地层/伟晶岩, 锚点为主"),
}


def rule_grids(anchors, envs, weights, lat_c, lon_c):
    """计算组合规则分数(原始)与锚点已知掩码。"""
    a_w, arc_w, rift_w = weights
    A = nearest_prox_grid(anchors[:, 0], anchors[:, 1], lat_c, lon_c) if len(anchors) else np.zeros((len(lat_c), len(lon_c)))
    AR = nearest_prox_grid(envs["arc"][0], envs["arc"][1], lat_c, lon_c)
    RI = nearest_prox_grid(envs["rift"][0], envs["rift"][1], lat_c, lon_c)
    raw = a_w * A + arc_w * AR + rift_w * RI
    # 已知格：离锚点 ≤2° (同 isotropic)
    mind = np.full((len(lat_c), len(lon_c)), np.inf)
    if len(anchors):
        for i, la in enumerate(lat_c):
            dlat = la - anchors[:, 0]
            cosl = np.cos(np.deg2rad(la))
            for j0 in range(0, len(lon_c), 40):
                j1 = min(j0 + 40, len(lon_c))
                dlon = (lon_c[j0:j1, None] - anchors[:, 1][None, :]) * cosl
                mind[i, j0:j1] = np.sqrt(dlat[None, :] ** 2 + dlon ** 2).min(axis=1)
    known = mind <= KNOWN_R_DEG
    flat = raw.ravel()
    pct = np.zeros_like(raw)
    order = flat.argsort()
    pct.ravel()[order] = np.linspace(0, 100, len(flat), endpoint=True)
    return raw, pct, known
