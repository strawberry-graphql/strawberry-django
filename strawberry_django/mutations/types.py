from __future__ import annotations

import dataclasses
from typing import Any, TypeVar, Union

import strawberry
from django.db import models
from django.db.models import Model
from strawberry import UNSET
from typing_extensions import TypeAlias, TypedDict

_T = TypeVar("_T")  # noqa: PYI018
_M = TypeVar("_M", bound=Model)
InputListTypes: TypeAlias = Union[strawberry.ID, "ParsedObject"]


class FullCleanOptions(TypedDict, total=False):
    exclude: list[str]
    validate_unique: bool
    validate_constraints: bool


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

        return model._default_manager.get(pk=self.pk), self.data


@dataclasses.dataclass
class ParsedObjectList:
    add: list[InputListTypes] | None = None
    remove: list[InputListTypes] | None = None
    set: list[InputListTypes] | None = None  # noqa: A003
