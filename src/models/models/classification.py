from collections import Counter
from collections.abc import Iterable
from typing import Literal, get_args


type Classification = Literal[
    "disinformation",
    "security incident",
    "vulnerability",
    "threat intelligence",
    "security policy",
    "security news",
    "general news",
    "other",
]

CLASSIFICATION_CATEGORIES: tuple[str, ...] = get_args(Classification.__value__)
SECURITY_CATEGORIES = frozenset({"security incident", "vulnerability", "threat intelligence", "security policy", "security news"})


def story_classification(categories: Iterable[str]) -> str:
    counts = Counter(category for category in categories if category in CLASSIFICATION_CATEGORIES)
    # Category order breaks ties consistently, independently of news-item ordering.
    return max(CLASSIFICATION_CATEGORIES, key=lambda category: counts[category]) if counts else "none"
