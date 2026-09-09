"""商品词 → 本仓库"族(family)"的共享分类。

被 scripts/ingest_mrds.py 与 scripts/ingest_usgs_expert.py 共用，保证口径一致。
"""

from __future__ import annotations

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
]


def classify(text: str) -> list:
    """文本含哪些族(可多族)。"""
    c = (text or "").lower()
    return [fam for fam, pats in FAM_RULES if any(p in c for p in pats)]
