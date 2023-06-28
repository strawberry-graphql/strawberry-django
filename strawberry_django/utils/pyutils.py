from typing import Any, Dict, Mapping, TypeVar

from typing_extensions import TypeAlias

_K = TypeVar("_K", bound=Any)
_V = TypeVar("_V", bound=Any)

DictTree: TypeAlias = Dict[str, "DictTree"]


def dicttree_merge(dict1: Mapping[_K, _V], dict2: Mapping[_K, _V]) -> Dict[_K, _V]:
    new = {
        **dict1,
        **dict2,
    }

    for k, v1 in dict1.items():
        if not isinstance(v1, dict):
            continue

        v2 = dict2.get(k)
        if isinstance(v2, Mapping):
            new[k] = dicttree_merge(v1, v2)  # type: ignore

    for k, v2 in dict2.items():
        if not isinstance(v2, dict):
            continue

        v1 = dict1.get(k)
        if isinstance(v1, Mapping):
            new[k] = dicttree_merge(v1, v2)  # type: ignore

    return new


def dicttree_insersection_differs(
    dict1: Mapping[_K, _V],
    dict2: Mapping[_K, _V],
) -> bool:
    for k in set(dict1) & set(dict2):
        v1 = dict1[k]
        v2 = dict2[k]

        if isinstance(v1, Mapping) and isinstance(v2, Mapping):
            if dicttree_insersection_differs(v1, v2):
                return True
        elif v1 != v2:
            return True

    return False
