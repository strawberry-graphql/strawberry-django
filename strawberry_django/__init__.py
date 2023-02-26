import warnings
from typing import Any, Dict

from django.core.exceptions import ImproperlyConfigured
from strawberry import auto as _deprecated_auto  # noqa: F401

from . import auth, filters, mutations, ordering, types
from .fields.field import field
from .fields.types import (
    DjangoFileType,
    DjangoImageType,
    DjangoModelType,
    ManyToManyInput,
    ManyToOneInput,
    OneToManyInput,
    OneToOneInput,
)
from .filters import filter_deprecated as filter  # noqa: A001
from .resolvers import django_resolver
from .type import input, mutation, type
from .utils import fields

try:
    from django.contrib.gis import geos  # noqa: F401

    from .fields.types import (  # noqa: F401
        LinearRing,
        LineString,
        MultiLineString,
        MultiPoint,
        MultiPolygon,
        Point,
        Polygon,
    )
except ImproperlyConfigured:
    # If gdal is not available, skip.
    pass

_deprecated_names: Dict[str, str] = {
    "auto": (
        "importing `auto` from `strawberry_django` is deprecated, "
        "import instead from `strawberry` directly."
    ),
    "is_auto": (
        "`is_auto` is deprecated use `isinstance(value, StrawberryAuto)` instead."
    ),
}


def __getattr__(name: str) -> Any:
    if name in _deprecated_names:
        warnings.warn(_deprecated_names[name], DeprecationWarning, stacklevel=2)
        return globals()[f"_deprecated_{name}"]

    raise AttributeError(f"module {__name__} has no attribute {name}")


__all__ = [
    "auth",
    "filters",
    "filter",
    "ordering",
    "types",
    "field",
    "DjangoFileType",
    "DjangoImageType",
    "DjangoModelType",
    "OneToOneInput",
    "OneToManyInput",
    "ManyToOneInput",
    "ManyToManyInput",
    "fields",
    "mutations",
    "django_resolver",
    "type",
    "input",
    "mutation",
]
