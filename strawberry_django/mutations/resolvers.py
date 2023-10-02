from __future__ import annotations

import dataclasses
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    List,
    TypeVar,
    Union,
    cast,
    overload,
)

import strawberry
from django.db import models, transaction
from django.db.models.base import Model
from django.db.models.fields.related import ManyToManyField
from django.db.models.fields.reverse_related import (
    ForeignObjectRel,
    ManyToManyRel,
    ManyToOneRel,
    OneToOneRel,
)
from django.utils.functional import LazyObject
from strawberry import UNSET, relay
from typing_extensions import Literal, TypeAlias, TypedDict

from strawberry_django.fields.types import (
    ListInput,
    ManyToManyInput,
    ManyToOneInput,
    NodeInput,
    OneToManyInput,
    OneToOneInput,
)
from strawberry_django.utils.inspect import get_model_fields

if TYPE_CHECKING:
    from django.db.models.manager import ManyToManyRelatedManager, RelatedManager
    from strawberry.file_uploads.scalars import Upload
    from strawberry.types.info import Info

_T = TypeVar("_T")
_M = TypeVar("_M", bound=Model)
_InputListTypes: TypeAlias = Union[strawberry.ID, "ParsedObject"]


class FullCleanOptions(TypedDict, total=False):
    exclude: list[str]
    validate_unique: bool
    validate_constraints: bool


def _parse_pk(
    value: ParsedObject | strawberry.ID | _M | None,
    model: type[_M],
) -> tuple[_M | None, dict[str, Any] | None]:
    if value is None:
        return None, None

    if isinstance(value, Model):
        return value, None

    if isinstance(value, ParsedObject):
        return value.parse(model)

    if isinstance(value, dict):
        return None, value

    return cast(_M, model._default_manager.get(pk=value)), None


def _parse_data(info: Info, model: type[_M], value: Any):
    obj, data = _parse_pk(value, model)

    parsed_data = {}
    if data:
        for k, v in data.items():
            if v is UNSET:
                continue

            if isinstance(v, ParsedObject):
                if v.pk is None:
                    v = cast(_M, create(info, model(), v.data or {}))  # noqa: PLW2901
                elif isinstance(v.pk, models.Model) and v.data:
                    v = update(info, v.pk, v.data)  # noqa: PLW2901
                else:
                    v = v.pk  # noqa: PLW2901

            if k == "through_defaults" or not obj or getattr(obj, k) != v:
                parsed_data[k] = v

    return obj, parsed_data


@dataclasses.dataclass
class ParsedObject:
    pk: strawberry.ID | Model | None
    data: dict[str, Any] | None = None

    def parse(self, model: type[_M]) -> tuple[_M | None, dict[str, Any] | None]:
        if self.pk is None or self.pk is UNSET:
            return None, self.data

        if isinstance(self.pk, models.Model):
            assert isinstance(self.pk, model)
            return self.pk, self.data

        return cast(_M, model._default_manager.get(pk=self.pk)), self.data


@dataclasses.dataclass
class ParsedObjectList:
    add: list[_InputListTypes] | None = None
    remove: list[_InputListTypes] | None = None
    set: list[_InputListTypes] | None = None  # noqa: A003


@overload
def parse_input(info: Info, data: dict[str, _T]) -> dict[str, _T]: ...


@overload
def parse_input(info: Info, data: list[_T]) -> list[_T]: ...


@overload
def parse_input(info: Info, data: relay.GlobalID) -> relay.Node: ...


@overload
def parse_input(info: Info, data: Any) -> Any: ...


def parse_input(info: Info, data: Any):
    if isinstance(data, dict):
        return {k: parse_input(info, v) for k, v in data.items()}

    if isinstance(data, list):
        return [parse_input(info, v) for v in data]

    if isinstance(data, relay.GlobalID):
        return data.resolve_node_sync(info, required=True)

    if isinstance(data, NodeInput):
        pk = cast(Any, parse_input(info, getattr(data, "id", UNSET)))
        parsed = {}
        for field in dataclasses.fields(data):
            if field.name == "id":
                continue
            parsed[field.name] = parse_input(info, getattr(data, field.name))

        return ParsedObject(
            pk=pk,
            data=parsed if len(parsed) else None,
        )

    if isinstance(data, (OneToOneInput, OneToManyInput)):
        return ParsedObject(
            pk=parse_input(info, data.set),
        )

    if isinstance(data, (ManyToOneInput, ManyToManyInput, ListInput)):
        d = getattr(data, "data", None)
        if dataclasses.is_dataclass(d):
            d = {
                f.name: parse_input(info, getattr(data, f.name))
                for f in dataclasses.fields(d)
            }

        return ParsedObjectList(
            add=cast(List[_InputListTypes], parse_input(info, data.add)),
            remove=cast(List[_InputListTypes], parse_input(info, data.remove)),
            set=cast(List[_InputListTypes], parse_input(info, data.set)),
        )

    if dataclasses.is_dataclass(data):
        return {
            f.name: parse_input(info, getattr(data, f.name))
            for f in dataclasses.fields(data)
        }

    return data


@overload
def create(
    info: Info,
    model: type[_M],
    data: dict[str, Any],
    *,
    full_clean: bool | FullCleanOptions = True,
    pre_save_hook: Callable[[_M], None] | None = None,
) -> _M: ...


@overload
def create(
    info: Info,
    model: type[_M],
    data: list[dict[str, Any]],
    *,
    full_clean: bool | FullCleanOptions = True,
    pre_save_hook: Callable[[_M], None] | None = None,
) -> list[_M]: ...


@transaction.atomic
def create(
    info: Info,
    model: type[_M],
    data: dict[str, Any] | list[dict[str, Any]],
    *,
    full_clean: bool | FullCleanOptions = True,
    pre_save_hook: Callable[[_M], None] | None = None,
):
    if isinstance(data, list):
        return [create(info, model, d, full_clean=full_clean) for d in data]

    if dataclasses.is_dataclass(data):
        data = vars(cast(object, data))

    return update(
        info,
        model(),
        data,
        full_clean=full_clean,
        pre_save_hook=pre_save_hook,
    )


@overload
def update(
    info: Info,
    instance: _M,
    data: dict[str, Any],
    *,
    full_clean: bool | FullCleanOptions = True,
    pre_save_hook: Callable[[_M], None] | None = None,
) -> _M: ...


@overload
def update(
    info: Info,
    instance: Iterable[_M],
    data: dict[str, Any],
    *,
    full_clean: bool | FullCleanOptions = True,
    pre_save_hook: Callable[[_M], None] | None = None,
) -> list[_M]: ...


@transaction.atomic
def update(
    info: Info,
    instance: _M | Iterable[_M],
    data: dict[str, Any],
    *,
    full_clean: bool | FullCleanOptions = True,
    pre_save_hook: Callable[[_M], None] | None = None,
) -> _M | list[_M]:
    # Unwrap lazy objects since they have a proxy __iter__ method that will make
    # them iterables even if the wrapped object isn't
    if isinstance(instance, LazyObject):
        instance = cast(_M, instance.__reduce__()[1][0])

    if isinstance(instance, Iterable):
        many = True
        instances = list(instance)
        if not instances:
            return []
    else:
        many = False
        instances = [instance]

    obj_models = [obj.__class__ for obj in instances]
    assert len(set(obj_models)) == 1
    fields = get_model_fields(obj_models[0])
    files: list[
        tuple[
            models.FileField,
            Upload | Literal[False],
        ]
    ] = []
    m2m: list[tuple[ManyToManyField | ForeignObjectRel, Any]] = []

    if dataclasses.is_dataclass(data):
        data = vars(data)

    for name, value in data.items():
        field = fields.get(name)

        if field is None or value is UNSET:
            continue

        if isinstance(field, models.FileField):
            if value is None:
                # We want to reset the file field value when None was passed in the
                # input, but `FileField.save_form_data` ignores None values. In that
                # case we manually pass False which clears the file.
                value = False  # noqa: PLW2901

            # set filefields at the same time so their hooks can use other set values
            files.append((field, value))
            continue

        if isinstance(field, (ManyToManyField, ForeignObjectRel)):
            # m2m will be processed later
            m2m.append((field, value))
            continue

        if isinstance(field, models.ForeignKey) and isinstance(
            value,
            # We are using str here because strawberry.ID can't be used for isinstance
            (ParsedObject, str),
        ):
            value, value_data = _parse_data(  # noqa: PLW2901
                info,
                field.related_model,
                value,
            )
            if value is None and not value_data:
                value = None  # noqa: PLW2901
            elif value is None:
                value = field.related_model._default_manager.create(  # noqa: PLW2901
                    **value_data,
                )
            else:
                update(info, value, value_data, full_clean=full_clean)

        for instance in instances:
            update_field(info, instance, field, value)

    retval = []
    for instance in instances:
        for file_field, value in files:
            file_field.save_form_data(instance, value)

        if pre_save_hook is not None:
            pre_save_hook(instance)

        full_clean_options = full_clean if isinstance(full_clean, dict) else {}
        if full_clean:
            instance.full_clean(**full_clean_options)  # type: ignore

        instance.save()

        for field, value in m2m:
            update_m2m(info, instance, field, value)

        retval.append(instance.__class__._default_manager.get(pk=instance.pk))

    return retval if many else retval[0]


@overload
def delete(
    info: Info,
    instance: _M,
    *,
    data: dict[str, Any] | None = None,
) -> _M: ...


@overload
def delete(
    info: Info,
    instance: Iterable[_M],
    *,
    data: dict[str, Any] | None = None,
) -> list[_M]: ...


@transaction.atomic
def delete(info: Info, instance: _M | Iterable[_M], *, data=None) -> _M | list[_M]:
    # Unwrap lazy objects since they have a proxy __iter__ method that will make
    # them iterables even if the wrapped object isn't
    if isinstance(instance, LazyObject):
        instance = cast(_M, instance.__reduce__()[1][0])

    if isinstance(instance, Iterable):
        many = True
        instances = list(instance)
    else:
        many = False
        instances = [instance]

    assert len({obj.__class__ for obj in instances}) == 1
    for instance in instances:
        pk = instance.pk
        instance.delete()
        # After the instance is deleted, set its ID to the original database's
        # ID so that the success response contains ID of the deleted object.
        instance.pk = pk

    return instances if many else instances[0]


def update_field(info: Info, instance: Model, field: models.Field, value: Any):
    if value is UNSET:
        return

    data = None
    if (
        value
        and isinstance(field, models.ForeignObject)
        and not isinstance(value, Model)
    ):
        value, data = _parse_pk(value, field.related_model)

    field.save_form_data(instance, value)
    # If data was passed to the foreign key, update it recursively
    if data and value:
        update(info, value, data)


def update_m2m(
    info: Info,
    instance: Model,
    field: ManyToManyField | ForeignObjectRel,
    value: Any,
):
    if value is UNSET:
        return

    if isinstance(field, OneToOneRel):
        remote_field = field.remote_field
        value, data = _parse_pk(value, remote_field.model)
        if value is None:
            value = getattr(instance, field.name)
        else:
            remote_field.save_form_data(value, instance)
            value.save()

        # If data was passed to the field, update it recursively
        if data:
            update(info, value, data)
        return

    use_remove = True
    if isinstance(field, ManyToManyField):
        manager = cast("RelatedManager", getattr(instance, field.attname))
    else:
        assert isinstance(field, (ManyToManyRel, ManyToOneRel))
        accessor_name = field.get_accessor_name()
        assert accessor_name
        manager = cast("RelatedManager", getattr(instance, accessor_name))
        if field.one_to_many:
            # remove if field is nullable, otherwise delete
            use_remove = field.remote_field.null is True

    to_add = []
    to_remove = []
    to_delete = []
    need_remove_cache = False

    values = value.set if isinstance(value, ParsedObjectList) else value
    if isinstance(values, list):
        if isinstance(value, ParsedObjectList) and getattr(value, "add", None):
            raise ValueError("'add' cannot be used together with 'set'")
        if isinstance(value, ParsedObjectList) and getattr(value, "remove", None):
            raise ValueError("'remove' cannot be used together with 'set'")

        existing = set(manager.all())
        need_remove_cache = need_remove_cache or bool(values)
        for v in values:
            obj, data = _parse_data(info, manager.model, v)

            if obj:
                through_defaults = data.pop("through_defaults", {})
                if data:
                    for k, inner_value in data.items():
                        setattr(obj, k, inner_value)
                    obj.save()

                if hasattr(manager, "through"):
                    manager = cast("ManyToManyRelatedManager", manager)
                    intermediate_model = manager.through
                    try:
                        im = intermediate_model._default_manager.get(
                            **{
                                manager.source_field_name: instance,  # type: ignore
                                manager.target_field_name: obj,  # type: ignore
                            },
                        )
                    except intermediate_model.DoesNotExist:
                        im = intermediate_model(
                            **{
                                manager.source_field_name: instance,  # type: ignore
                                manager.target_field_name: obj,  # type: ignore
                            },
                        )

                    for k, inner_value in through_defaults.items():
                        setattr(im, k, inner_value)
                    im.save()
                elif obj not in existing:
                    to_add.append(obj)

                existing.discard(obj)
            else:
                obj, _ = manager.get_or_create(**data)
                existing.discard(obj)

        for remaining in existing:
            if use_remove:
                to_remove.append(remaining)
            else:
                to_delete.append(remaining)

    else:
        need_remove_cache = need_remove_cache or bool(value.add)
        for v in value.add or []:
            obj, data = _parse_data(info, manager.model, v)
            if obj and data:
                manager.add(obj, **data)
            elif obj:
                # Do this later in a bulk
                to_add.append(obj)
            elif data:
                manager.get_or_create(**data)
            else:
                raise AssertionError

        need_remove_cache = need_remove_cache or bool(value.remove)
        for v in value.remove or []:
            obj, data = _parse_data(info, manager.model, v)
            assert not data
            to_remove.append(obj)

    if to_add:
        manager.add(*to_add)
    if to_remove:
        manager.remove(*to_remove)
    if to_delete:
        manager.filter(pk__in=[item.pk for item in to_delete]).delete()

    if need_remove_cache:
        manager._remove_prefetched_objects()  # type: ignore
