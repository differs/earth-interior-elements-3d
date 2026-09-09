"""商品词 → 本仓库"族(family)"的共享分类。

被 scripts/ingest_mrds.py 与 scripts/ingest_usgs_expert.py、parse PP1802 共用。
短词(≤4 字母, 如 tin/lead/zinc/coal/iron)用词边界匹配防误命中(如 mountain 含 tin)；
长词与词组(如 "rare earth")用子串匹配。
"""

from __future__ import annotations

import re

# (family, (patterns,...))  保持顺序 = 输出排序基准
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
    ("PGE", ("platinum", "palladium", "osmium", "iridium", "ruthenium",
             "rhodium", "pgm", "platinum group")),
    ("U", ("uranium",)),
    ("Diamond", ("diamond", "kimberlite", "lamproite")),
    ("Coal", ("coal",)),
    # v0.3h 扩展: 临界/基础金属(PP1802、mrdata podchrome/sedznpb、MRDS)
    ("ZnPb", ("zinc", "lead", "sphalerite", "galena", "zinc-lead")),
    ("Cr", ("chromium", "chromite")),
    ("Mn", ("manganese", "pyrolusite")),
    ("W", ("tungsten", "wolfram", "scheelite")),
    ("Sn", ("tin", "cassiterite")),
    ("Sb", ("antimony", "stibnite")),
    ("V", ("vanadium",)),
    ("Ti", ("titanium", "ilmenite", "rutile")),
    ("TaNb", ("tantalum", "niobium", "columbite", "pyrochlore")),
]

_short = {p for _, ps in FAM_RULES for p in ps if len(p) <= 4}
# 词组不参与短词边界判断
_words = {p for _, ps in FAM_RULES for p in ps if " " not in p}
_bound = _short & _words


def _hit(c: str, p: str) -> bool:
    if p in _bound:
        return re.search(rf"\b{re.escape(p)}\b", c) is not None
    return p in c


def classify(text: str) -> list:
    """文本含哪些族(可多族)。"""
    c = (text or "").lower()
    return [fam for fam, pats in FAM_RULES if any(_hit(c, p) for p in pats)]
