import abc
import contextlib
import contextvars
import copy
import dataclasses
import enum
import functools
import inspect
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Hashable,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

import strawberry
from asgiref.sync import sync_to_async
from django.core.exceptions import PermissionDenied
from django.db.models import Model, QuerySet
from strawberry import relay, schema_directive
from strawberry.extensions.field_extension import (
    AsyncExtensionResolver,
    FieldExtension,
    SyncExtensionResolver,
)
from strawberry.field import StrawberryField
from strawberry.schema_directive import Location
from strawberry.type import StrawberryList, StrawberryOptional
from strawberry.types.info import Info
from strawberry.union import StrawberryUnion
from typing_extensions import Literal, Self, assert_never

from strawberry_django.auth.utils import get_current_user
from strawberry_django.fields.types import OperationInfo, OperationMessage
from strawberry_django.resolvers import django_resolver

from .utils.query import filter_for_user
from .utils.typing import UserType

if TYPE_CHECKING:
    from strawberry.django.context import StrawberryDjangoContext


_M = TypeVar("_M", bound=Model)


@functools.lru_cache
def _get_user_or_anonymous_getter() -> Optional[Callable[[UserType], UserType]]:
    try:
        from .integrations.guardian import get_user_or_anonymous
    except (ImportError, RuntimeError):  # pragma: no cover
        return None

    return get_user_or_anonymous


@dataclasses.dataclass
class PermContext:
    is_safe_list: List[bool] = dataclasses.field(default_factory=list)
    checkers: List["HasPerm"] = dataclasses.field(default_factory=list)

    def __copy__(self):
        return self.__class__(
            is_safe_list=self.is_safe_list[:],
            checkers=self.checkers[:],
        )

    @property
    def is_safe(self):
        return bool(self.is_safe_list and all(self.is_safe_list))


perm_context: contextvars.ContextVar[PermContext] = contextvars.ContextVar(
    "perm-safe",
    default=PermContext(),
)


@contextlib.contextmanager
def with_perm_checker(checker: "HasPerm"):
    context = copy.copy(perm_context.get())
    context.checkers.append(checker)
    token = perm_context.set(context)
    try:
        yield
    finally:
        perm_context.reset(token)


def set_perm_safe(value: bool):
    perm_context.get().is_safe_list.append(value)


def filter_with_perms(qs: QuerySet[_M], info: Info) -> QuerySet[_M]:
    context = perm_context.get()
    if not context.checkers or context.is_safe:
        return qs

    # Do not do anything is results are cached
    if qs._result_cache is not None:  # type: ignore
        set_perm_safe(False)
        return qs

    user = cast("StrawberryDjangoContext", info.context).request.user
    # If the user is anonymous, we can't filter object permissions for it
    if user.is_anonymous:
        set_perm_safe(False)
        return qs.none()

    for check in context.checkers:
        if check.target != PermTarget.RETVAL:
            continue

        qs = filter_for_user(
            qs,
            user,
            [p.perm for p in check.perms],
            any_perm=check.any_perm,
            with_superuser=check.with_superuser,
        )

    set_perm_safe(True)
    return qs


@overload
def get_with_perms(
    pk: strawberry.ID,
    info: Info,
    *,
    required: Literal[True],
    model: Type[_M],
    key_attr: Optional[str] = ...,
) -> _M: ...


@overload
def get_with_perms(
    pk: strawberry.ID,
    info: Info,
    *,
    required: bool = ...,
    model: Type[_M],
    key_attr: Optional[str] = ...,
) -> Optional[_M]: ...


@overload
def get_with_perms(
    pk: relay.GlobalID,
    info: Info,
    *,
    required: Literal[True],
    model: Type[_M],
    key_attr: Optional[str] = ...,
) -> _M: ...


@overload
def get_with_perms(
    pk: relay.GlobalID,
    info: Info,
    *,
    required: bool = ...,
    model: Type[_M],
    key_attr: Optional[str] = ...,
) -> Optional[_M]: ...


@overload
def get_with_perms(
    pk: relay.GlobalID,
    info: Info,
    *,
    required: Literal[True],
    key_attr: Optional[str] = ...,
) -> Any: ...


@overload
def get_with_perms(
    pk: relay.GlobalID,
    info: Info,
    *,
    required: bool = ...,
    key_attr: Optional[str] = ...,
) -> Optional[Any]: ...


def get_with_perms(
    pk,
    info,
    *,
    required=False,
    model=None,
    key_attr: Optional[str] = "pk",
):
    if isinstance(pk, relay.GlobalID):
        instance = pk.resolve_node_sync(info, required=required, ensure_type=model)
    else:
        assert model
        instance = model._default_manager.get(**{key_attr: pk})

    if instance is None:
        return None

    context = perm_context.get()
    if not context.checkers or context.is_safe:
        return instance

    user = cast("StrawberryDjangoContext", info.context).request.user
    if user and (get_user_or_anonymous := _get_user_or_anonymous_getter()) is not None:
        user = get_user_or_anonymous(user)

    for check in context.checkers:
        f = any if check.any_perm else all
        checker = check.obj_perm_checker(info, user)
        if not f(checker(p, instance) for p in check.perms):
            raise PermissionDenied(check.message)

    return instance


_return_condition = """\
When the condition fails, the following can be returned (following this priority):
1) `OperationInfo`/`OperationMessage` if those types are allowed at the return type
2) `null` in case the field is not mandatory (e.g. `String` or `[String]`)
3) An empty list in case the field is a list (e.g. `[String]!`)
4) An empty `Connection` in case the return type is a relay connection
2) Otherwise, an error will be raised
"""


def _desc(desc):
    return f"{desc}\n\n{_return_condition.strip()}"


class DjangoNoPermission(Exception):  # noqa: N818
    """Raise to identify that the user doesn't have perms for a given retval."""


class DjangoPermissionExtension(FieldExtension, abc.ABC):
    """Base django permission extension."""

    DEFAULT_ERROR_MESSAGE: ClassVar[str] = "User does not have permission."
    SCHEMA_DIRECTIVE_LOCATIONS: ClassVar[List[Location]] = [Location.FIELD_DEFINITION]
    SCHEMA_DIRECTIVE_DESCRIPTION: ClassVar[Optional[str]] = None

    def __init__(
        self,
        *,
        message: Optional[str] = None,
        use_directives: bool = True,
        fail_silently: bool = True,
    ):
        super().__init__()
        self.message = message if message is not None else self.DEFAULT_ERROR_MESSAGE
        self.fail_silently = fail_silently
        self.use_directives = use_directives

    def apply(self, field: StrawberryField) -> None:  # pragma: no cover
        if self.use_directives:
            directive = self.schema_directive
            # Avoid interfaces duplicating the directives
            if directive not in field.directives:
                field.directives.append(self.schema_directive)

    @functools.cached_property
    def schema_directive(self) -> object:
        key = "__strawberry_directive_type__"
        directive_class = getattr(self.__class__, key, None)

        if directive_class is None:

            @schema_directive(
                name=self.__class__.__name__,
                locations=self.SCHEMA_DIRECTIVE_LOCATIONS,
                description=self.SCHEMA_DIRECTIVE_DESCRIPTION,
                repeatable=True,
            )
            class AutoDirective: ...

            directive_class = AutoDirective

        return directive_class()

    @django_resolver(qs_hook=None)
    def resolve(
        self,
        next_: SyncExtensionResolver,
        source: Any,
        info: Info,
        **kwargs: Dict[str, Any],
    ) -> Any:
        user = get_current_user(info)

        if (
            user
            and (get_user_or_anonymous := _get_user_or_anonymous_getter()) is not None
        ):
            user = get_user_or_anonymous(user)

        # make sure the user is loaded
        if user is not None:
            user.is_authenticated  # noqa: B018

        try:
            retval = self.resolve_for_user(
                functools.partial(next_, source, info, **kwargs),
                user,
                info=info,
                source=source,
            )
        except DjangoNoPermission as e:
            retval = self.handle_no_permission(e, info=info)

        return retval

    async def resolve_async(
        self,
        next_: AsyncExtensionResolver,
        source: Any,
        info: Info,
        **kwargs: Dict[str, Any],
    ) -> Any:
        user = get_current_user(info)

        try:
            from .integrations.guardian import get_user_or_anonymous
        except (ImportError, RuntimeError):  # pragma: no cover
            pass
        else:
            user = user and await sync_to_async(get_user_or_anonymous)(user)

        # make sure the user is loaded
        await sync_to_async(getattr)(user, "is_anonymous")

        try:
            retval = self.resolve_for_user(
                functools.partial(next_, source, info, **kwargs),
                user,
                info=info,
                source=source,
            )
            while inspect.isawaitable(retval):
                retval = await retval
        except DjangoNoPermission as e:
            retval = self.handle_no_permission(e, info=info)

        return retval

    def handle_no_permission(self, exception: BaseException, *, info: Info):
        if not self.fail_silently:
            raise PermissionDenied(self.message) from exception

        ret_type = info.return_type

        if isinstance(ret_type, StrawberryOptional):
            ret_type = ret_type.of_type
            is_optional = True
        else:
            is_optional = False

        if isinstance(ret_type, StrawberryUnion):
            ret_types = []
            for type_ in ret_type.types:
                ret_types.append(ret_type)

                if not isinstance(type_, type):
                    continue

                if issubclass(type_, OperationInfo):
                    return type_(
                        messages=[
                            OperationMessage(
                                kind=OperationMessage.Kind.PERMISSION,
                                message=self.message,
                                field=info.field_name,
                            ),
                        ],
                    )

                if issubclass(type_, OperationMessage):
                    return type_(
                        kind=OperationMessage.Kind.PERMISSION,
                        message=self.message,
                        field=info.field_name,
                    )
        else:
            ret_types = [ret_type]

        if is_optional:
            return None

        if isinstance(ret_type, StrawberryList):
            return []

        # If it is a Connection, try to return an empty connection, but only if
        # it is the only possibility available...
        for ret_possibility in ret_types:
            if isinstance(ret_possibility, type) and issubclass(
                ret_possibility,
                relay.Connection,
            ):
                return []

        # In last case, raise an error
        raise PermissionDenied(self.message) from exception

    @abc.abstractmethod
    def resolve_for_user(  # pragma: no cover
        self,
        resolver: Callable,
        user: Optional[UserType],
        *,
        info: Info,
        source: Any,
    ): ...


class IsAuthenticated(DjangoPermissionExtension):
    """Mark a field as only resolvable by authenticated users."""

    DEFAULT_ERROR_MESSAGE: ClassVar[str] = "User is not authenticated."
    SCHEMA_DIRECTIVE_DESCRIPTION: ClassVar[str] = _desc(
        "Can only be resolved by authenticated users.",
    )

    @django_resolver(qs_hook=None)
    def resolve_for_user(
        self,
        resolver: Callable,
        user: Optional[UserType],
        *,
        info: Info,
        source: Any,
    ):
        if user is None or not user.is_authenticated or not user.is_active:
            raise DjangoNoPermission

        return resolver()


class IsStaff(DjangoPermissionExtension):
    """Mark a field as only resolvable by staff users."""

    DEFAULT_ERROR_MESSAGE: ClassVar[str] = "User is not a staff member."
    SCHEMA_DIRECTIVE_DESCRIPTION: ClassVar[str] = _desc(
        "Can only be resolved by staff users.",
    )

    @django_resolver(qs_hook=None)
    def resolve_for_user(
        self,
        resolver: Callable,
        user: Optional[UserType],
        *,
        info: Info,
        source: Any,
    ):
        if (
            user is None
            or not user.is_authenticated
            or not getattr(user, "is_staff", False)
        ):
            raise DjangoNoPermission

        return resolver()


class IsSuperuser(DjangoPermissionExtension):
    """Mark a field as only resolvable by superuser users."""

    DEFAULT_ERROR_MESSAGE: ClassVar[str] = "User is not a superuser."
    SCHEMA_DIRECTIVE_DESCRIPTION: ClassVar[str] = _desc(
        "Can only be resolved by superuser users.",
    )

    @django_resolver(qs_hook=None)
    def resolve_for_user(
        self,
        resolver: Callable,
        user: Optional[UserType],
        *,
        info: Info,
        source: Any,
    ):
        if (
            user is None
            or not user.is_authenticated
            or not getattr(user, "is_superuser", False)
        ):
            raise DjangoNoPermission

        return resolver()


@strawberry.input(description="Permission definition for schema directives.")
class PermDefinition:
    """Permission definition.

    Attributes
    ----------
        app:
            The app to which we are requiring permission.
        permission:
            The permission itself

    """

    app: Optional[str] = strawberry.field(
        description=(
            "The app to which we are requiring permission. If this is "
            "empty that means that we are checking the permission directly."
        ),
    )
    permission: Optional[str] = strawberry.field(
        description=(
            "The permission itself. If this is empty that means that we "
            "are checking for any permission for the given app."
        ),
    )

    @classmethod
    def from_perm(cls, perm: str):
        parts = perm.split(".")
        if len(parts) != 2:  # noqa: PLR2004
            raise TypeError(
                "Permissions need to be defined as `app_label.perm`, `app_label.`"
                " or `.perm`",
            )
        return cls(
            app=parts[0].strip() or None,
            permission=parts[1].strip() or None,
        )

    @property
    def perm(self):
        return f"{self.app or ''}.{self.permission or ''}".strip(".")

    def __eq__(self, other: Self):
        if not isinstance(other, PermDefinition):
            return NotImplemented

        return self.perm == other.perm

    def __hash__(self):
        return hash((self.__class__, self.perm))


class PermTarget(enum.IntEnum):
    """Permission location."""

    GLOBAL = enum.auto()
    SOURCE = enum.auto()
    RETVAL = enum.auto()


def _default_perm_checker(info: Info, user: UserType):
    def perm_checker(perm: PermDefinition) -> bool:
        return (
            user.has_perm(perm.perm)  # type: ignore
            if perm.permission
            else user.has_module_perms(cast(str, perm.app))  # type: ignore
        )

    return perm_checker


def _default_obj_perm_checker(info: Info, user: UserType):
    def perm_checker(perm: PermDefinition, obj: Any) -> bool:
        # Check global perms first, then object specific
        return user.has_perm(perm.perm) or user.has_perm(  # type: ignore
            perm.perm,
            obj=obj,
        )

    return perm_checker


class HasPerm(DjangoPermissionExtension):
    """Defines permissions required to access the given object/field.

    Given a `app` name, the user can access the decorated object/field
    if he has any of the permissions defined in this directive.

    Examples
    --------
        To indicate that a mutation can only be done by someone who
        has "product.add_product" perm in the django system:

        >>> @strawberry.type
        ... class Query:
        ...     @strawberry.mutation(directives=[HasPerm("product.add_product")])
        ...     def create_product(self, name: str) -> ProductType:
        ...         ...

    Attributes
    ----------
        perms:
            Perms required to access this app.
        any_perm:
            If any perm or all perms are required to resolve the object/field.
        target:
            The target to check for permissions. Use `HasSourcePerm` or
            `HasRetvalPerm` as a shortcut for this.
        with_anonymous:
            If we should optimize the permissions check and consider an anonymous
            user as not having any permissions. This is true by default, which means
            that anonymous users will not trigger has_perm checks.
        with_superuser:
            If we should optimize the permissions check and consider a superuser
            as having permissions foe everything. This is false by default to avoid
            returning unexpected results. Setting this to true will avoid triggering
            has_perm checks.

    """

    DEFAULT_TARGET: ClassVar[PermTarget] = PermTarget.GLOBAL
    DEFAULT_ERROR_MESSAGE: ClassVar[
        str
    ] = "You don't have permission to access this app."
    SCHEMA_DIRECTIVE_DESCRIPTION: ClassVar[str] = _desc(
        "Will check if the user has any/all permissions to resolve this.",
    )

    def __init__(
        self,
        perms: Union[List[str], str],
        *,
        message: Optional[str] = None,
        use_directives: bool = True,
        fail_silently: bool = True,
        target: Optional[PermTarget] = None,
        any_perm: bool = True,
        perm_checker: Optional[
            Callable[[Info, UserType], Callable[[PermDefinition], bool]]
        ] = None,
        obj_perm_checker: Optional[
            Callable[[Info, UserType], Callable[[PermDefinition, Any], bool]]
        ] = None,
        with_anonymous: bool = True,
        with_superuser: bool = False,
    ):
        super().__init__(
            message=message,
            use_directives=use_directives,
            fail_silently=fail_silently,
        )

        if isinstance(perms, str):
            perms = [perms]

        if not perms:
            raise TypeError(f"At least one perm is required for {self!r}")

        self.perms: Tuple[PermDefinition, ...] = tuple(
            PermDefinition.from_perm(p) if isinstance(p, str) else p for p in perms
        )

        assert all(isinstance(p, PermDefinition) for p in self.perms)
        self.target = target if target is not None else self.DEFAULT_TARGET
        self.permissions = perms
        self.any_perm = any_perm
        self.perm_checker = (
            perm_checker if perm_checker is not None else _default_perm_checker
        )
        self.obj_perm_checker = (
            obj_perm_checker
            if obj_perm_checker is not None
            else _default_obj_perm_checker
        )
        self.with_anonymous = with_anonymous
        self.with_superuser = with_superuser

    @functools.cached_property
    def schema_directive(self) -> object:
        key = "__strawberry_directive_class__"
        directive_class = getattr(self.__class__, key, None)

        if directive_class is None:

            @schema_directive(
                name=self.__class__.__name__,
                locations=self.SCHEMA_DIRECTIVE_LOCATIONS,
                description=self.SCHEMA_DIRECTIVE_DESCRIPTION,
                repeatable=True,
            )
            class AutoDirective:
                permissions: List[PermDefinition] = strawberry.field(
                    description="Required perms to access this resource.",
                    default_factory=list,
                )
                any: bool = strawberry.field(  # noqa: A003
                    description="If any or all perms listed are required.",
                    default=True,
                )

            directive_class = AutoDirective

        return directive_class(
            permissions=list(self.perms),
            any=self.any_perm,
        )

    @django_resolver(qs_hook=None)
    def resolve_for_user(
        self,
        resolver: Callable,
        user: Optional[UserType],
        *,
        info: Info,
        source: Any,
    ):
        if user is None or self.with_anonymous and user.is_anonymous:
            raise DjangoNoPermission

        if (
            self.with_superuser
            and user.is_active
            and getattr(user, "is_superuser", False)
        ):
            return resolver()

        return self.resolve_for_user_with_perms(
            resolver,
            user,
            info=info,
            source=source,
        )

    def resolve_for_user_with_perms(
        self,
        resolver: Callable,
        user: Optional[UserType],
        *,
        info: Info,
        source: Any,
    ):
        if user is None:
            raise DjangoNoPermission

        if self.target == PermTarget.GLOBAL:
            if not self._has_perm(source, user, info=info):
                raise DjangoNoPermission

            retval = resolver()
        elif self.target == PermTarget.SOURCE:
            # Just call _resolve_obj, it will raise DjangoNoPermission
            # if the user doesn't have permission for it
            self._resolve_obj(source, user, source, info=info)
            retval = resolver()
        elif self.target == PermTarget.RETVAL:
            with with_perm_checker(self):
                obj = resolver()
                retval = self._resolve_obj(source, user, obj, info=info)
        else:
            assert_never(self.target)

        return retval

    def _get_cache(
        self,
        info: Info,
        user: UserType,
    ) -> Dict[Tuple[Hashable, ...], bool]:
        cache_key = "_strawberry_django_permissions_cache"

        cache = getattr(user, cache_key, None)
        if cache is None:
            cache = {}
            setattr(user, cache_key, cache)

        cache = {}
        setattr(user, cache_key, cache)
        return cache

    def _has_perm(
        self,
        source: Any,
        user: UserType,
        *,
        info: Info,
    ) -> bool:
        cache = self._get_cache(info, user)

        # Maybe the result ended up in the cache in the meantime
        cache_key = (self.perms, self.any_perm)
        if cache_key in cache:
            return cache[cache_key]

        f = any if self.any_perm else all
        checker = self.perm_checker(info, user)
        has_perm = f(checker(p) for p in self.perms)
        cache[cache_key] = has_perm

        return has_perm

    def _resolve_obj(
        self,
        source: Any,
        user: UserType,
        obj: Any,
        *,
        info: Info,
    ) -> Any:
        context = perm_context.get()
        if context.is_safe:
            return obj

        if isinstance(obj, Iterable):
            return list(self._resolve_iterable_obj(source, user, obj, info=info))

        cache = self._get_cache(info, user)
        cache_key = (self.perms, self.any_perm, obj)
        has_perm = cache.get(cache_key)

        if has_perm is None:
            if isinstance(obj, OperationInfo):
                has_perm = True
            else:
                f = any if self.any_perm else all
                checker = self.obj_perm_checker(info, user)
                has_perm = f(checker(p, obj) for p in self.perms)

            cache[cache_key] = has_perm

        if not has_perm:
            raise DjangoNoPermission

        return obj

    def _resolve_iterable_obj(
        self,
        source: Any,
        user: UserType,
        objs: Iterable[Any],
        *,
        info: Info,
    ) -> Any:
        cache = self._get_cache(info, user)
        f = any if self.any_perm else all
        checker = self.obj_perm_checker(info, user)

        for obj in objs:
            cache_key = (self.perms, self.any_perm, obj)
            has_perm = cache.get(cache_key)

            if has_perm is None:
                if isinstance(obj, OperationInfo):
                    has_perm = True
                else:
                    has_perm = f(checker(p, obj) for p in self.perms)

                cache[cache_key] = has_perm

            if has_perm:
                yield obj


class HasSourcePerm(HasPerm):
    """Defines permissions required to access the given field at object level.

    This will check the permissions for the source object to access the given field.

    Unlike `HasRetvalPerm`, this uses the source value (the object where the field
    is defined) to resolve the field, which means that this cannot be used for source
    queries and types.

    Examples
    --------
        To indicate that a field inside a `ProductType` can only be accessed if
        the user has "product.view_field" in it in the django system:

        >>> @gql.django.type(Product)
        ... class ProductType:
        ...     some_field: str = strawberry.field(
        ...         directives=[HasSourcePerm(".add_product")],
        ...     )

    """

    DEFAULT_TARGET: ClassVar[PermTarget] = PermTarget.SOURCE
    SCHEMA_DIRECTIVE_DESCRIPTION: ClassVar[str] = _desc(
        "Will check if the user has any/all permissions for the parent "
        "of this field to resolve this.",
    )


class HasRetvalPerm(HasPerm):
    """Defines permissions required to access the given object/field at object level.

    Given a `app` name, the user can access the decorated object/field
    if he has any of the permissions defined in this directive.

    Note that this depends on resolving the object to check the permissions
    specifically for that object, unlike `HasPerm` which checks it before resolving.

    Examples
    --------
        To indicate that a field that returns a `ProductType` can only be accessed
        by someone who has "product.view_product"
        has "product.view_product" perm in the django system:

        >>> @strawberry.type
        ... class SomeType:
        ...     product: ProductType = strawberry.field(
        ...         directives=[HasRetvalPerm(".add_product")],
        ...     )

    """

    DEFAULT_TARGET: ClassVar[PermTarget] = PermTarget.RETVAL
    SCHEMA_DIRECTIVE_DESCRIPTION: ClassVar[str] = _desc(
        "Will check if the user has any/all permissions for the resolved "
        "value of this field before returning it.",
    )
