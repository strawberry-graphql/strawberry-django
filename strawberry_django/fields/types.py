import datetime
import decimal
import uuid
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    NewType,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import django
import strawberry
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db.models import Field, Model, fields
from django.db.models.fields import files, json, related, reverse_related
from strawberry import UNSET, relay
from strawberry.scalars import JSON
from typing_extensions import Self

from strawberry_django import filters

if TYPE_CHECKING:
    from strawberry_django.type import StrawberryDjangoDefinition

K = TypeVar("K")


@strawberry.type
class DjangoFileType:
    name: str
    path: str
    size: int
    url: str


@strawberry.type
class DjangoImageType(DjangoFileType):
    width: int
    height: int


@strawberry.type
class DjangoModelType:
    pk: strawberry.ID


@strawberry.input
class OneToOneInput:
    set: Optional[strawberry.ID]  # noqa: A003


@strawberry.input
class OneToManyInput:
    set: Optional[strawberry.ID]  # noqa: A003


@strawberry.input
class ManyToOneInput:
    add: Optional[List[strawberry.ID]] = UNSET
    remove: Optional[List[strawberry.ID]] = UNSET
    set: Optional[List[strawberry.ID]] = UNSET  # noqa: A003


@strawberry.input
class ManyToManyInput:
    add: Optional[List[strawberry.ID]] = UNSET
    remove: Optional[List[strawberry.ID]] = UNSET
    set: Optional[List[strawberry.ID]] = UNSET  # noqa: A003


@strawberry.input(
    description="Input of an object that implements the `Node` interface.",
)
class NodeInput:
    id: relay.GlobalID  # noqa: A003

    def __eq__(self, other: Self):
        if not isinstance(other, NodeInput):
            return NotImplemented

        return self.id == other.id

    def __hash__(self):
        return hash((self.__class__, self.id))


@strawberry.input(
    description="Input of an object that implements the `Node` interface.",
)
class NodeInputPartial(NodeInput):
    # FIXME: Without this pyright will not let any class inheric from this and define
    # a field that doesn't contain a default value...
    if TYPE_CHECKING:
        id: Optional[relay.GlobalID]  # noqa: A003
    else:
        id: Optional[relay.GlobalID] = UNSET  # noqa: A003


@strawberry.input(description="Add/remove/set the selected nodes.")
class ListInput(Generic[K]):
    """Add/remove/set the selected nodes.

    Notes
    -----
        To pass data to an intermediate model, type the input in a
        `throught_defaults` key inside the input object.

    """

    # FIXME: Without this pyright will not let any class inheric from this and define
    # a field that doesn't contain a default value...
    if TYPE_CHECKING:
        set: Optional[List[K]]  # noqa: A003
        add: Optional[List[K]]
        remove: Optional[List[K]]
    else:
        set: Optional[List[K]] = UNSET  # noqa: A003
        add: Optional[List[K]] = UNSET
        remove: Optional[List[K]] = UNSET

    def __eq__(self, other: Self):
        if not isinstance(other, ListInput):
            return NotImplemented

        return self._hash_fields() == other._hash_fields()

    def __hash__(self):
        return hash((self.__class__, *self._hash_fields()))

    def _hash_fields(self):
        return (
            tuple(self.set) if isinstance(self.set, list) else self.set,
            tuple(self.add) if isinstance(self.add, list) else self.add,
            tuple(self.remove) if isinstance(self.remove, list) else self.remove,
        )


field_type_map: Dict[
    Union[
        Type[fields.Field],
        Type[related.RelatedField],
        Type[reverse_related.ForeignObjectRel],
    ],
    type,
] = {
    fields.AutoField: strawberry.ID,
    fields.BigAutoField: strawberry.ID,
    fields.BigIntegerField: int,
    fields.BooleanField: bool,
    fields.CharField: str,
    fields.DateField: datetime.date,
    fields.DateTimeField: datetime.datetime,
    fields.DecimalField: decimal.Decimal,
    fields.EmailField: str,
    fields.FilePathField: str,
    fields.FloatField: float,
    fields.GenericIPAddressField: str,
    fields.IntegerField: int,
    fields.PositiveIntegerField: int,
    fields.PositiveSmallIntegerField: int,
    fields.SlugField: str,
    fields.SmallAutoField: strawberry.ID,
    fields.SmallIntegerField: int,
    fields.TextField: str,
    fields.TimeField: datetime.time,
    fields.URLField: str,
    fields.UUIDField: uuid.UUID,
    files.FileField: DjangoFileType,
    files.ImageField: DjangoImageType,
    related.ForeignKey: DjangoModelType,
    related.ManyToManyField: List[DjangoModelType],
    related.OneToOneField: DjangoModelType,
    reverse_related.ManyToManyRel: List[DjangoModelType],
    reverse_related.ManyToOneRel: List[DjangoModelType],
    reverse_related.OneToOneRel: DjangoModelType,
}

if hasattr(fields, "NullBooleanField"):
    # NullBooleanField was deprecated and will soon be removed
    field_type_map[fields.NullBooleanField] = Optional[bool]  # type: ignore

if django.VERSION >= (3, 1):
    field_type_map.update(
        {
            json.JSONField: JSON,
            fields.PositiveBigIntegerField: int,
        },
    )

try:
    from django.contrib.gis import geos
    from django.contrib.gis.db import models as geos_fields

except ImproperlyConfigured:
    # If gdal is not available, skip.
    Point = None
    LineString = None
    LinearRing = None
    Polygon = None
    MultiPoint = None
    MultilineString = None
    MultiPolygon = None
else:
    Point = strawberry.scalar(
        NewType("Point", Tuple[float, float, Optional[float]]),
        serialize=lambda v: v.tuple if isinstance(v, geos.Point) else v,
        parse_value=lambda v: geos.Point(v),
        description="Represents a point as `(x, y, z)` or `(x, y)`.",
    )

    LineString = strawberry.scalar(
        NewType("LineString", Tuple[Point]),
        serialize=lambda v: v.tuple if isinstance(v, geos.LineString) else v,
        parse_value=lambda v: geos.LineString(v),
        description=(
            "A geographical line that gets multiple 'x, y' or 'x, y, z'"
            " tuples to form a line."
        ),
    )

    LinearRing = strawberry.scalar(
        NewType("LinearRing", Tuple[Point]),
        serialize=lambda v: v.tuple if isinstance(v, geos.LinearRing) else v,
        parse_value=lambda v: geos.LinearRing(v),
        description=(
            "A geographical line that gets multiple 'x, y' or 'x, y, z' "
            "tuples to form a line. It must be a circle. "
            "E.g. It maps back to itself."
        ),
    )

    Polygon = strawberry.scalar(
        NewType("Polygon", Tuple[LinearRing]),
        serialize=lambda v: v.tuple if isinstance(v, geos.Polygon) else v,
        parse_value=lambda v: geos.Polygon(*[geos.LinearRing(x) for x in v]),
        description=(
            "A geographical object that gets 1 or 2 LinearRing objects"
            " as external and internal rings."
        ),
    )

    MultiPoint = strawberry.scalar(
        NewType("MultiPoint", Tuple[Point]),
        serialize=lambda v: v.tuple if isinstance(v, geos.MultiPoint) else v,
        parse_value=lambda v: geos.MultiPoint(*[geos.Point(x) for x in v]),
        description="A geographical object that contains multiple Points.",
    )

    MultiLineString = strawberry.scalar(
        NewType("MultiLineString", Tuple[LineString]),
        serialize=lambda v: v.tuple if isinstance(v, geos.MultiLineString) else v,
        parse_value=lambda v: geos.MultiLineString(*[geos.LineString(x) for x in v]),
        description="A geographical object that contains multiple line strings.",
    )

    MultiPolygon = strawberry.scalar(
        NewType("MultiPolygon", Tuple[Polygon]),
        serialize=lambda v: v.tuple if isinstance(v, geos.MultiPolygon) else v,
        parse_value=lambda v: geos.MultiPolygon(
            *[geos.Polygon(*list(x)) for x in v],
        ),
        description="A geographical object that contains multiple polygons.",
    )

    field_type_map.update(
        {
            geos_fields.PointField: Point,
            geos_fields.LineStringField: LineString,
            geos_fields.PolygonField: Polygon,
            geos_fields.MultiPointField: MultiPoint,
            geos_fields.MultiLineStringField: MultiLineString,
            geos_fields.MultiPolygonField: MultiPolygon,
        },
    )


input_field_type_map: Dict[
    Union[
        Type[fields.Field],
        Type[related.RelatedField],
        Type[reverse_related.ForeignObjectRel],
    ],
    type,
] = {
    files.FileField: NotImplemented,
    files.ImageField: NotImplemented,
    related.ForeignKey: OneToManyInput,
    related.ManyToManyField: ManyToManyInput,
    related.OneToOneField: OneToOneInput,
    reverse_related.ManyToManyRel: ManyToManyInput,
    reverse_related.ManyToOneRel: ManyToOneInput,
    reverse_related.OneToOneRel: OneToOneInput,
}


relay_field_type_map: Dict[
    Union[
        Type[fields.Field],
        Type[related.RelatedField],
        Type[reverse_related.ForeignObjectRel],
    ],
    type,
] = {
    fields.AutoField: relay.GlobalID,
    fields.BigAutoField: relay.GlobalID,
    related.ForeignKey: relay.Node,
    related.ManyToManyField: List[relay.Node],
    related.OneToOneField: relay.Node,
    reverse_related.ManyToManyRel: List[relay.Node],
    reverse_related.ManyToOneRel: List[relay.Node],
    reverse_related.OneToOneRel: relay.Node,
}


relay_input_field_type_map: Dict[
    Union[
        Type[fields.Field],
        Type[related.RelatedField],
        Type[reverse_related.ForeignObjectRel],
    ],
    type,
] = {
    related.ForeignKey: NodeInput,
    related.ManyToManyField: ListInput[NodeInputPartial],
    related.OneToOneField: NodeInput,
    reverse_related.ManyToManyRel: ListInput[NodeInputPartial],
    reverse_related.ManyToOneRel: ListInput[NodeInput],
    reverse_related.OneToOneRel: NodeInput,
}


def resolve_model_field_type(
    model_field: Union[Field, reverse_related.ForeignObjectRel],
    django_type: "StrawberryDjangoDefinition",
):
    is_relay = issubclass(django_type.origin, relay.Node)
    model_field_type = type(model_field)
    field_type: Any = None

    if django_type.is_filter and model_field.is_relation:
        field_type = NodeInput if is_relay else filters.DjangoModelFilterInput
    elif django_type.is_input:
        input_type_map = input_field_type_map
        if is_relay:
            input_type_map = {**input_type_map, **relay_input_field_type_map}

        field_type = input_type_map.get(model_field_type, None)

    if field_type is None:
        type_map = field_type_map
        if is_relay:
            type_map = {**type_map, **relay_field_type_map}

        field_type = type_map.get(model_field_type, NotImplemented)

    if field_type is NotImplemented:
        raise NotImplementedError(
            f"GraphQL type for model field '{model_field}' has not been implemented",
        )

    # TODO: could this be moved into filters.py
    if (
        django_type.is_filter == "lookups"
        and not model_field.is_relation
        and field_type is not bool
    ):
        field_type = filters.FilterLookup[field_type]

    return field_type


def resolve_model_field_name(
    model_field: Union[Field, reverse_related.ForeignObjectRel],
    is_input=False,
    is_filter=False,
):
    if isinstance(model_field, reverse_related.ForeignObjectRel):
        return model_field.get_accessor_name()

    if is_input and not is_filter:
        return model_field.attname

    return model_field.name


def get_model_field(model: Type[Model], field_name: str):
    try:
        return model._meta.get_field(field_name)
    except FieldDoesNotExist as e:
        model_field_names = []

        # we need to iterate through all the fields because reverse relation
        # fields cannot be accessed by get_field method
        for field in model._meta.get_fields():
            model_field_name = resolve_model_field_name(field)
            if field_name == model_field_name:
                return field
            model_field_names.append(model_field_name)

        e.args = (
            "{}, did you mean {}?".format(
                e.args[0],
                ", ".join([f"'{n}'" for n in model_field_names]),
            ),
        )
        raise


def is_optional(
    model_field: Union[Field, reverse_related.ForeignObjectRel],
    is_input: bool,
    partial: bool,
):
    if partial:
        return True

    if not model_field:
        return False

    if is_input:
        if isinstance(model_field, fields.AutoField):
            return True

        if isinstance(model_field, reverse_related.OneToOneRel):
            return model_field.null

        if model_field.many_to_many or model_field.one_to_many:
            return True

        if (
            getattr(model_field, "blank", None)
            or getattr(model_field, "default", None) is not fields.NOT_PROVIDED
        ):
            return True

    if not isinstance(
        model_field,
        (reverse_related.ManyToManyRel, reverse_related.ManyToOneRel),
    ) or isinstance(model_field, reverse_related.OneToOneRel):
        # OneToOneRel is the subclass of ManyToOneRel, so additional check is needed
        return model_field.null

    return False
