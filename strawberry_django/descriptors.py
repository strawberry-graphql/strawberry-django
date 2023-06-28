import inspect
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
    overload,
)

from django.db.models.base import Model
from strawberry.exceptions import MissingFieldAnnotationError
from typing_extensions import Self

if TYPE_CHECKING:
    from strawberry_django.optimizer import OptimizerStore

    from .utils.typing import PrefetchType, TypeOrSequence

__all__ = [
    "ModelProperty",
    "model_property",
    "model_cached_property",
]

_T = TypeVar("_T")
_M = TypeVar("_M", bound=Model)
_R = TypeVar("_R")


class ModelProperty(Generic[_M, _R]):
    """Model property with optimization hinting functionality."""

    name: str
    store: "OptimizerStore"

    def __init__(
        self,
        func: Callable[[_M], _R],
        *,
        cached: bool = False,
        meta: Optional[Dict[Any, Any]] = None,
        only: Optional["TypeOrSequence[str]"] = None,
        select_related: Optional["TypeOrSequence[str]"] = None,
        prefetch_related: Optional["TypeOrSequence[PrefetchType]"] = None,
    ):
        from .optimizer import OptimizerStore

        super().__init__()

        self.func = func
        self.cached = cached
        self.meta = meta
        self.store = OptimizerStore.with_hints(
            only=only,
            select_related=select_related,
            prefetch_related=prefetch_related,
        )

    def __set_name__(self, owner: Type[_M], name: str):
        self.origin = owner
        self.name = name

    @overload
    def __get__(self, obj: _M, cls: Type[_M]) -> _R:
        ...

    @overload
    def __get__(self, obj: None, cls: Type[_M]) -> Self:
        ...

    def __get__(self, obj, cls=None):
        if obj is None:
            return self

        if not self.cached:
            return self.func(obj)

        try:
            ret = obj.__dict__[self.name]
        except KeyError:
            ret = self.func(obj)
            obj.__dict__[self.name] = ret

        return ret

    @property
    def description(self) -> Optional[str]:
        if not self.func.__doc__:
            return None
        return inspect.cleandoc(self.func.__doc__)

    @property
    def type_annotation(self) -> Union[object, str]:
        ret = self.func.__annotations__.get("return")
        if ret is None:
            raise MissingFieldAnnotationError(self.name, self.origin)
        return ret


@overload
def model_property(
    func: Callable[[_M], _R],
    *,
    cached: bool = False,
    meta: Optional[Dict[Any, Any]] = None,
    only: Optional["TypeOrSequence[str]"] = None,
    select_related: Optional["TypeOrSequence[str]"] = None,
    prefetch_related: Optional["TypeOrSequence[PrefetchType]"] = None,
) -> ModelProperty[_M, _R]:
    ...


@overload
def model_property(
    func: None = ...,
    *,
    cached: bool = False,
    meta: Optional[Dict[Any, Any]] = None,
    only: Optional["TypeOrSequence[str]"] = None,
    select_related: Optional["TypeOrSequence[str]"] = None,
    prefetch_related: Optional["TypeOrSequence[PrefetchType]"] = None,
) -> Callable[[Callable[[_M], _R]], ModelProperty[_M, _R]]:
    ...


def model_property(
    func=None,
    *,
    cached: bool = False,
    meta: Optional[Dict[Any, Any]] = None,
    only: Optional["TypeOrSequence[str]"] = None,
    select_related: Optional["TypeOrSequence[str]"] = None,
    prefetch_related: Optional["TypeOrSequence[PrefetchType]"] = None,
) -> Any:
    def wrapper(f):
        return ModelProperty(
            f,
            cached=cached,
            meta=meta,
            only=only,
            select_related=select_related,
            prefetch_related=prefetch_related,
        )

    if func is not None:
        return wrapper(func)

    return wrapper


def model_cached_property(
    func=None,
    *,
    meta: Optional[Dict[Any, Any]] = None,
    only: Optional["TypeOrSequence[str]"] = None,
    select_related: Optional["TypeOrSequence[str]"] = None,
    prefetch_related: Optional["TypeOrSequence[PrefetchType]"] = None,
):
    """Property with gql optimization hinting.

    Decorate a method, just like you would do with a `@property`, and when
    accessing it through a graphql resolver, if `DjangoOptimizerExtension`
    is enabled, it will automatically optimize the hintings on this field.

    Args:
    ----
        func:
            The method to decorate.
        meta:
            Some extra metadata to be attached to the field.
        only:
            Optional sequence of values to optimize using `QuerySet.only`
        select_related:
            Optional sequence of values to optimize using `QuerySet.select_related`
        prefetch_related:
            Optional sequence of values to optimize using `QuerySet.prefetch_related`

    Returns:
    -------
        The decorated method.

    Examples:
    --------
        In a model, define it like this to have the hintings defined in
        `col_b_formatted` automatically optimized.

        >>> class SomeModel(models.Model):
        ...     col_a = models.CharField()
        ...     col_b = models.CharField()
        ...
        ...     @model_cached_property(only=["col_b"])
        ...     def col_b_formatted(self):
        ...         return f"Formatted: {self.col_b}"
        ...
        >>> @gql.django.type(SomeModel)
        ... class SomeModelType
        ...     col_a: gql.auto
        ...     col_b_formatted: gql.auto

    """
    return model_property(
        func,
        cached=True,
        meta=meta,
        only=only,
        select_related=select_related,
        prefetch_related=prefetch_related,
    )
