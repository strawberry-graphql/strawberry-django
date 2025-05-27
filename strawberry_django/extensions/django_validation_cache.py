from collections.abc import Iterator

from graphql.validation import validate
from strawberry.schema.validation_rules.one_of import OneOfInputValidationRule

from .django_cache_base import DjangoCacheBase


class DjangoValidationCache(DjangoCacheBase):
    def on_validate(self) -> Iterator[None]:
        execution_context = self.execution_context

        errors = self.execute_cached(
            validate,
            execution_context.schema._schema,
            execution_context.graphql_document,
            (
                *execution_context.validation_rules,
                OneOfInputValidationRule,
            ),
        )
        execution_context.errors = errors
        yield None
