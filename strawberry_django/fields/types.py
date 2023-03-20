import datetime
import decimal
import uuid
from typing import TYPE_CHECKING, Any, List, NewType, Optional, Tuple, Type, Union

import django
import strawberry
from django.db.models import Field, Model, fields
from django.db.models.fields.reverse_related import ForeignObjectRel
from strawberry import UNSET
from strawberry.auto import StrawberryAuto
from strawberry.scalars import JSON

from strawberry_django import filters

if TYPE_CHECKING:
    from strawberry_django.type import StrawberryDjangoType


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


field_type_map = {
    fields.AutoField: strawberry.ID,
    fields.BigAutoField: strawberry.ID,
    fields.BigIntegerField: int,
    fields.BooleanField: bool,
    fields.CharField: str,
    fields.DateField: datetime.date,
    fields.DateTimeField: datetime.datetime,
    fields.DecimalField: decimal.Decimal,
    fields.EmailField: str,
    fields.files.FileField: DjangoFileType,
    fields.FilePathField: str,
    fields.FloatField: float,
    fields.files.ImageField: DjangoImageType,
    fields.GenericIPAddressField: str,
    fields.IntegerField: int,
    fields.NullBooleanField: Optional[bool],
    fields.PositiveIntegerField: int,
    fields.PositiveSmallIntegerField: int,
    fields.SlugField: str,
    fields.SmallAutoField: strawberry.ID,
    fields.SmallIntegerField: int,
    fields.TextField: str,
    fields.TimeField: datetime.time,
    fields.URLField: str,
    fields.UUIDField: uuid.UUID,
    fields.related.ForeignKey: DjangoModelType,
    fields.reverse_related.ManyToOneRel: List[DjangoModelType],
    fields.related.OneToOneField: DjangoModelType,
    fields.reverse_related.OneToOneRel: DjangoModelType,
    fields.related.ManyToManyField: List[DjangoModelType],
    fields.reverse_related.ManyToManyRel: List[DjangoModelType],
}

if django.VERSION >= (3, 1):
    field_type_map.update(
        {
            fields.json.JSONField: JSON,
            fields.PositiveBigIntegerField: int,
        },
    )

try:
    from django.contrib.gis import geos
    from django.contrib.gis.db import models as geos_fields

except django.core.exceptions.ImproperlyConfigured:
    # If gdal is not available, skip.
    pass

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


input_field_type_map = {
    fields.files.FileField: NotImplemented,
    fields.files.ImageField: NotImplemented,
    fields.related.ForeignKey: OneToManyInput,
    fields.reverse_related.ManyToOneRel: ManyToOneInput,
    fields.related.OneToOneField: OneToOneInput,
    fields.reverse_related.OneToOneRel: OneToOneInput,
    fields.related.ManyToManyField: ManyToManyInput,
    fields.reverse_related.ManyToManyRel: ManyToManyInput,
}


def resolve_model_field_type(
    model_field: Union[Field, ForeignObjectRel],
    django_type: "StrawberryDjangoType",
):
    model_field_type = type(model_field)
    field_type: Any = None
    if django_type.is_filter and model_field.is_relation:
        field_type = filters.DjangoModelFilterInput
    elif django_type.is_input:
        field_type = input_field_type_map.get(model_field_type, None)
    if field_type is None:
        field_type = field_type_map.get(model_field_type, NotImplemented)
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
    model_field: Union[Field, ForeignObjectRel],
    is_input=False,
    is_filter=False,
):
    if isinstance(model_field, ForeignObjectRel):
        return model_field.get_accessor_name()

    if is_input and not is_filter:
        return model_field.attname

    return model_field.name


def get_model_field(model: Type[Model], field_name: str):
    try:
        return model._meta.get_field(field_name)
    except django.core.exceptions.FieldDoesNotExist as e:
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


def is_auto(type_):
    return isinstance(type_, StrawberryAuto)


def is_optional(model_field, is_input, partial):
    if partial:
        return True
    if not model_field:
        return False
    if is_input:
        if isinstance(model_field, fields.AutoField):
            return True
        if isinstance(model_field, fields.reverse_related.OneToOneRel):
            return model_field.null
        if model_field.many_to_many or model_field.one_to_many:
            return True
        has_default = model_field.default is not fields.NOT_PROVIDED
        if model_field.blank or has_default:
            return True
    if not isinstance(
        model_field,
        (fields.reverse_related.ManyToManyRel, fields.reverse_related.ManyToOneRel),
    ) or isinstance(model_field, fields.reverse_related.OneToOneRel):
        # OneToOneRel is the subclass of ManyToOneRel, so additional check is needed
        return model_field.null
    return False
