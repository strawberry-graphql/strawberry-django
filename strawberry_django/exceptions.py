from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from strawberry.exceptions.exception import StrawberryException
from strawberry.exceptions.utils.source_finder import SourceFinder

if TYPE_CHECKING:
    from strawberry.exceptions.exception_source import ExceptionSource

    from strawberry_django.fields.filter_order import FilterOrderFieldResolver


class MissingFieldArgumentError(StrawberryException):
    def __init__(self, field_name: str, resolver: FilterOrderFieldResolver):
        self.function = resolver.wrapped_func

        self.message = f'Missing required argument "{field_name}" in "{resolver.name}"'
        self.rich_message = (
            f'[bold red]Missing argument [underline]"{field_name}" for field '
            f"`[underline]{resolver.name}[/]`"
        )
        self.annotation_message = "field missing argument"

        super().__init__(self.message)

    @cached_property
    def exception_source(self) -> ExceptionSource | None:  # pragma: no cover
        source_finder = SourceFinder()

        return source_finder.find_function_from_object(self.function)  # type: ignore


class ForbiddenFieldArgumentError(StrawberryException):
    def __init__(self, resolver: FilterOrderFieldResolver, arguments: list[str]):
        self.extra_arguments = arguments
        self.function = resolver.wrapped_func
        self.argument_name = arguments[0]

        self.message = (
            f'Found disallowed {self.extra_arguments_str} in field "{resolver.name}"'
        )
        self.rich_message = (
            f"Found disallowed {self.extra_arguments_str} in "
            f"`[underline]{resolver.name}[/]`"
        )
        self.suggestion = "To fix this error, remove offending argument(s)"

        self.annotation_message = "forbidden field argument"

        super().__init__(self.message)

    @property
    def extra_arguments_str(self) -> str:
        arguments = self.extra_arguments

        if len(arguments) == 1:
            return f'argument "{arguments[0]}"'

        head = ", ".join(arguments[:-1])
        return f'arguments "{head}" and "{arguments[-1]}"'

    @cached_property
    def exception_source(self) -> ExceptionSource | None:  # pragma: no cover
        source_finder = SourceFinder()

        return source_finder.find_argument_from_object(
            self.function,  # type: ignore
            self.argument_name,
        )
